"""Maps SDK-specific exceptions to a generic, safe error the API can return.
Never include the raw exception text in what's returned or logged — for BYOK requests it
can echo back request details we don't want surfacing, including near the API key."""

import re


class GenerationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502, retry_after_seconds=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        # Only set when the provider told us a concrete wait (currently just Groq's
        # daily-token-cap message) -- lets generation.py skip pointless quick retries
        # against a cooldown measured in minutes, not seconds.
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


def _gemini_reason(exc: Exception):
    """google-genai's ClientError carries the real Google API error as a nested dict
    on `.details` — `{"error": {"code": 400, "details": [{"reason": "API_KEY_INVALID", ...}]}}`.
    Note the invalid-key case comes back as HTTP 400 INVALID_ARGUMENT, not 401/403 —
    confirmed against the live API, not assumed from generic REST conventions."""
    details = getattr(exc, "details", None) or {}
    try:
        for item in details.get("error", {}).get("details", []):
            reason = item.get("reason")
            if reason:
                return reason
    except (AttributeError, TypeError):
        pass
    return None


def _gemini_quota_ids(exc: Exception):
    """Confirmed live: a RESOURCE_EXHAUSTED error's own RetryInfo.retryDelay can be
    misleadingly short ("6s") even when the real cause is a hard PerDay quota that
    won't clear until tomorrow no matter how long you wait -- retrying twice at 10s
    each against that is exactly what made the app feel "stuck" rather than just
    telling the reader plainly. The QuotaFailure detail's quotaId (e.g.
    "GenerateRequestsPerDayPerProjectPerModel-FreeTier") is the reliable signal."""
    details = getattr(exc, "details", None) or {}
    ids = []
    try:
        for item in details.get("error", {}).get("details", []):
            if str(item.get("@type", "")).endswith("QuotaFailure"):
                for violation in item.get("violations", []):
                    quota_id = violation.get("quotaId")
                    if quota_id:
                        ids.append(quota_id)
    except (AttributeError, TypeError):
        pass
    return ids


# Groq's RateLimitError message includes a concrete cooldown, e.g. "...on tokens
# per day (TPD): Limit 100000, Used 99935... Please try again in 11m43.29s." --
# worth parsing just the number (never the surrounding text, per this module's own
# rule above) so a genuine daily-cap exhaustion can say "try again in ~12 minutes"
# instead of the same vague message as a two-second blip.
_GROQ_RETRY_RE = re.compile(r"try again in (?:([\d.]+)m)?(?:([\d.]+)s)?", re.IGNORECASE)


def _groq_retry_seconds(exc: Exception):
    match = _GROQ_RETRY_RE.search(str(exc))
    if not match or not (match.group(1) or match.group(2)):
        return None
    minutes = float(match.group(1) or 0)
    seconds = float(match.group(2) or 0)
    return minutes * 60 + seconds


def translate_exception(engine_key: str, exc: Exception) -> GenerationError:
    type_name = type(exc).__name__

    if engine_key == "gemini":
        status = getattr(exc, "code", None)
        reason = _gemini_reason(exc)
        message = str(getattr(exc, "message", "") or "")

        api_status = str(getattr(exc, "status", "") or "")

        if reason == "API_KEY_INVALID" or "API key not valid" in message:
            return GenerationError("invalid_api_key", "The engine rejected this API key.", 401)
        if status == 429 or reason == "RESOURCE_EXHAUSTED":
            quota_ids = _gemini_quota_ids(exc)
            if any("PerDay" in qid for qid in quota_ids):
                return GenerationError(
                    "rate_limited",
                    "Gemini's free daily quota for this key is used up for today — try again tomorrow, or switch engines.",
                    429,
                    retry_after_seconds=86400,  # a hard daily cap -- Gemini's own RetryInfo delay for this case can say a few seconds, which is not actually true
                )
            return GenerationError("rate_limited", "The engine is rate-limiting this key right now.", 429)
        if status == 403 or reason == "PERMISSION_DENIED":
            return GenerationError("invalid_api_key", "This key doesn't have access to that model.", 403)
        if status == 503 or api_status == "UNAVAILABLE":
            # Google's own infrastructure overloaded, not the caller's key/quota --
            # confirmed live: "This model is currently experiencing high demand."
            # Distinct from rate_limited (which is about *this key's* usage) even
            # though both are transient and worth retrying the same way.
            return GenerationError("engine_overloaded", "The engine is overloaded right now.", 503)
        return GenerationError("engine_error", "The engine failed to respond.", 502)

    if engine_key == "groq":
        if type_name == "AuthenticationError":
            return GenerationError("invalid_api_key", "The engine rejected this API key.", 401)
        if type_name == "RateLimitError":
            retry_seconds = _groq_retry_seconds(exc)
            if retry_seconds and retry_seconds > 30:
                minutes = max(1, round(retry_seconds / 60))
                message = (
                    f"Groq's free daily quota for this key is exhausted for now — try again "
                    f"in about {minutes} minute{'s' if minutes != 1 else ''}."
                )
            else:
                message = "The engine is rate-limiting this key right now."
            return GenerationError("rate_limited", message, 429, retry_after_seconds=retry_seconds)
        if type_name in ("APIConnectionError", "InternalServerError"):
            return GenerationError("engine_overloaded", "The engine is overloaded right now.", 503)
        return GenerationError("engine_error", "The engine failed to respond.", 502)

    if engine_key == "claude":
        # Same anthropic-SDK exception names on this path as any other Claude API
        # caller -- see shared/error-codes.md's typed-exception table.
        if type_name == "AuthenticationError":
            return GenerationError("invalid_api_key", "The backup engine's key was rejected — the operator needs to check it.", 401)
        if type_name == "PermissionDeniedError":
            return GenerationError("invalid_api_key", "The backup engine's key doesn't have access to that model.", 403)
        if type_name == "RateLimitError":
            return GenerationError("rate_limited", "The backup engine is rate-limited right now.", 429)
        if type_name in ("APIConnectionError", "InternalServerError"):
            return GenerationError("engine_overloaded", "The backup engine is overloaded right now.", 503)
        return GenerationError("engine_error", "The backup engine failed to respond.", 502)

    return GenerationError("engine_error", "The engine failed to respond.", 502)
