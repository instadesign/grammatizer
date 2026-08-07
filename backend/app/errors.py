"""Maps SDK-specific exceptions to a generic, safe error the API can return.
Never include the raw exception text in what's returned or logged — for BYOK requests it
can echo back request details we don't want surfacing, including near the API key."""


class GenerationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502):
        self.code = code
        self.message = message
        self.status_code = status_code
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
            return GenerationError("rate_limited", "The engine is rate-limiting this key right now.", 429)
        if type_name in ("APIConnectionError", "InternalServerError"):
            return GenerationError("engine_overloaded", "The engine is overloaded right now.", 503)
        return GenerationError("engine_error", "The engine failed to respond.", 502)

    if engine_key == "claude":
        # Same anthropic-SDK exception names on this path as any other Claude API
        # caller -- see shared/error-codes.md's typed-exception table.
        if type_name == "AuthenticationError":
            return GenerationError("invalid_api_key", "The backup engine's key was rejected -- the operator needs to check it.", 401)
        if type_name == "PermissionDeniedError":
            return GenerationError("invalid_api_key", "The backup engine's key doesn't have access to that model.", 403)
        if type_name == "RateLimitError":
            return GenerationError("rate_limited", "The backup engine is rate-limited right now.", 429)
        if type_name in ("APIConnectionError", "InternalServerError"):
            return GenerationError("engine_overloaded", "The backup engine is overloaded right now.", 503)
        return GenerationError("engine_error", "The backup engine failed to respond.", 502)

    return GenerationError("engine_error", "The engine failed to respond.", 502)
