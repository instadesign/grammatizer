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


# The two paid engines (openai, claude) fail in one way the free ones cannot: a key
# that is perfectly valid, on an account with nothing to spend. People arrive there
# honestly, assuming a ChatGPT or Claude subscription covers it. It gets its own code
# so the frontend can send the reader back to the title page with the reason, as it
# does for a bad key, instead of calling it a jam and offering to try again.
_NO_CREDIT_MESSAGES = {
    "openai": (
        "OpenAI accepted this key, but its account has no API credit. A ChatGPT "
        "subscription does not include any: add credit at platform.openai.com, or "
        "choose another engine."
    ),
    "claude": (
        "Anthropic accepted this key, but its account has no API credit. A Claude "
        "subscription does not include any: add credit at platform.claude.com, or "
        "choose another engine."
    ),
}


def _no_credit(engine_key: str) -> GenerationError:
    return GenerationError("no_credit", _NO_CREDIT_MESSAGES[engine_key], 402)


def _retry_after_header(exc: Exception):
    """Seconds from a rate-limit response's Retry-After header, when it has one.
    (A header, not the error text: see the note at the top of this module.)"""
    try:
        return float(exc.response.headers.get("retry-after"))
    except (AttributeError, TypeError, ValueError):
        return None


def _rate_limited(exc: Exception) -> GenerationError:
    return GenerationError(
        "rate_limited",
        "The engine is rate-limiting this key right now.",
        429,
        retry_after_seconds=_retry_after_header(exc),
    )


_OVERLOADED_TYPES = (
    "APIConnectionError", "APITimeoutError", "InternalServerError",
    "OverloadedError", "ServiceUnavailableError", "DeadlineExceededError",
)


def translate_exception(engine_key: str, exc: Exception) -> GenerationError:
    type_name = type(exc).__name__

    if type_name == "ContentFilteredError":
        # See engines.ContentFilteredError -- deliberately retryable (the same
        # RETRYABLE_CODES path rate limits use), since the same prompt can pass
        # on a second attempt rather than being a hard, permanent block.
        return GenerationError(
            "content_filtered",
            "The Safety Governor intervened for this line — the machine will try a different phrasing.",
            422,
        )

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

    if engine_key == "openai":
        if type_name == "AuthenticationError":
            return GenerationError("invalid_api_key", "The engine rejected this API key.", 401)
        if type_name == "RateLimitError":
            # OpenAI reports an empty account as a 429 too, told apart only by the
            # error's code. Waiting does not cure it, so it must not be retried as one.
            if getattr(exc, "code", None) == "insufficient_quota":
                return _no_credit(engine_key)
            return _rate_limited(exc)
        if type_name in ("PermissionDeniedError", "NotFoundError"):
            return GenerationError("invalid_api_key", "This key doesn't have access to that model.", 403)
        if type_name in _OVERLOADED_TYPES:
            return GenerationError("engine_overloaded", "The engine is overloaded right now.", 503)
        return GenerationError("engine_error", "The engine failed to respond.", 502)

    if engine_key == "claude":
        if type_name == "AuthenticationError":
            return GenerationError("invalid_api_key", "The engine rejected this API key.", 401)
        # An empty account is a 402 "billing_error" by Anthropic's error table, though
        # it has also been served as a plain 400 whose message names the credit
        # balance. Only tested for here, never passed on.
        if (
            getattr(exc, "status_code", None) == 402
            or getattr(exc, "type", None) == "billing_error"
            or (type_name == "BadRequestError" and "credit balance" in str(exc).lower())
        ):
            return _no_credit(engine_key)
        if type_name == "RateLimitError":
            return _rate_limited(exc)
        if type_name in ("PermissionDeniedError", "NotFoundError"):
            return GenerationError("invalid_api_key", "This key doesn't have access to that model.", 403)
        if type_name in _OVERLOADED_TYPES:
            return GenerationError("engine_overloaded", "The engine is overloaded right now.", 503)
        return GenerationError("engine_error", "The engine failed to respond.", 502)

    return GenerationError("engine_error", "The engine failed to respond.", 502)
