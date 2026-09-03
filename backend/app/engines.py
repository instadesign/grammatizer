"""Engine registry + dispatch — the same pattern originally proven in the Streamlit
prototype's ENGINES dict / generate_story(), ported essentially unchanged."""

import os
from typing import Optional

from google import genai
from google.genai import types as genai_types
from openai import OpenAI

ENGINES = {
    "gemini": {
        "env_var": "GEMINI_API_KEY",
        # Went through two models to get here, both confirmed live against the API:
        # "gemini-2.5-flash" is retired for new users; "gemini-3.5-flash" is live but
        # this project's free tier caps it at a startling 20 requests/DAY (not a
        # transient per-minute limit -- confirmed via the actual 429 body's
        # GenerateRequestsPerDayPerProjectPerModel-FreeTier quota, not assumed).
        # Quota is tracked per model, and Google's own aggregate lite-tier alias
        # carries a separate, far more workable allowance -- it's also a better
        # long-term bet than pinning a concrete model given "2.5-flash-lite" itself
        # went stale mid-session today.
        "model": "gemini-flash-lite-latest",
    },
    "groq": {
        "env_var": "GROQ_API_KEY",
        # Four models tried here, in order -- every one of them confirmed live
        # against the real API (not docs, which turned out to be stale/wrong
        # repeatedly: both Llama models below still showed as current on Groq's
        # own docs pages after they'd actually been pulled):
        #   1. llama-3.3-70b-versatile -- 404 model_not_found, live. Gone.
        #   2. llama-3.1-8b-instant -- 404 model_not_found, live. Also gone (the
        #      same June deprecation notice named both Llama models together --
        #      missed that the first time round).
        #   3. openai/gpt-oss-120b -- exists, but it's a REASONING model: under
        #      ~1000 max_tokens (our beats need ~220) it spends the whole budget
        #      on hidden reasoning and returns EMPTY message.content, 100% of the
        #      time, confirmed via the backend log.
        # "qwen/qwen3.6-27b" is what's actually in use now -- but it ALSO defaults
        # to a thinking mode that wraps output in a <think>...</think> block and
        # blows straight through a 220-token budget without ever reaching an
        # answer (confirmed live, same failure shape as gpt-oss). The difference:
        # Groq exposes `reasoning_effort` for this model, and "none" cleanly
        # suppresses thinking -- confirmed live, clean vivid prose, natural
        # finish_reason "stop", no truncation, no leaked reasoning. See the
        # reasoning_effort param on the call itself, below -- it's load-bearing,
        # not optional, for this specific model.
        "model": "qwen/qwen3.6-27b",
    },
}


# Finish reasons that mean the provider blocked the candidate outright -- its
# `candidate.content` is cleared, so `response.text` doesn't come back empty, it
# RAISES (an AttributeError, confirmed against the live SDK). Without catching
# this, a safety-filtered beat crashed as an unmapped exception straight through
# to main.py's generic 500 handler and killed the whole manuscript -- and this
# app's own Erotic category / Passion / Intensity dials can legitimately trip a
# provider-side filter even within the Safety Governor's own bounds, so this
# isn't an edge case for this app specifically, it's an expected path.
_GEMINI_BLOCKED_FINISH_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "RECITATION", "BLOCKLIST", "SPII"}


class ContentFilteredError(Exception):
    """Raised instead of letting a safety-filtered Gemini response crash on
    `response.text`. Google's own guidance is that a block can be probabilistic --
    the same prompt can pass on a retry -- so this is deliberately just another
    condition generate_beat's existing retry loop knows how to handle (see
    RETRYABLE_CODES in generation.py), not a dead end."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"content filtered: {reason}")


def resolve_api_key(engine_key: str, supplied_key: Optional[str]) -> Optional[str]:
    """BYOK first; falls back to the server-side env var for this engine, if any."""
    if supplied_key:
        return supplied_key
    return os.environ.get(ENGINES[engine_key]["env_var"])


def call_engine(engine_key: str, api_key: str, prompt: str, temperature: float, max_tokens: int):
    """One completion call. Returns (text, finish_reason, usage_tokens) where
    finish_reason is normalized to 'stop' (finished naturally) or 'length' (cut off
    by max_tokens). usage_tokens is always None -- both engines here are BYOK, so
    there's no shared server-side budget to track against it."""
    engine = ENGINES[engine_key]

    if engine_key == "gemini":
        client = genai.Client(api_key=api_key)
        # "gemini-flash-lite-latest" is an ALIAS Google repoints over time, not a
        # pinned model, and its thinking support has flip-flopped under us across
        # this same session: at one point it silently emitted thinking content
        # (eating into max_output_tokens), so passing thinking_config to disable it
        # was the fix -- but confirmed live just now, the alias has moved again and
        # the *current* resolution 400s on thinking_config entirely, with a fully
        # generic "Request contains an invalid argument." that says nothing about
        # thinking specifically. A message-content check for "thinking" is exactly
        # what missed this. Retry without thinking_config on ANY 400 from the first
        # attempt instead of trying to pattern-match the message -- if that wasn't
        # the actual cause, the retry fails too and its own error still propagates
        # normally.
        # presence_penalty is a mechanical nudge against reusing a word that's
        # already appeared, layered under the prompt-level REPETITION_GUIDELINE and
        # generation.py's own mechanical retry -- it doesn't replace either (a
        # penalty alone won't stop genuine fixation the way the retry's hard block
        # does), but it should mean that retry needs to fire less often, which is
        # itself a small reliability win (fewer retries -> fewer chances to burn a
        # beat's time budget or trip a rate limit on a retry attempt).
        config_kwargs = dict(
            temperature=temperature, max_output_tokens=max_tokens, presence_penalty=0.3
        )
        try:
            response = client.models.generate_content(
                model=engine["model"],
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
                    **config_kwargs,
                ),
            )
        except genai.errors.ClientError as exc:
            if getattr(exc, "code", None) == 400:
                response = client.models.generate_content(
                    model=engine["model"],
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(**config_kwargs),
                )
            else:
                raise
        candidate = response.candidates[0] if response.candidates else None
        raw_reason = getattr(candidate, "finish_reason", None)
        reason_name = getattr(raw_reason, "name", str(raw_reason))
        if candidate is None or reason_name in _GEMINI_BLOCKED_FINISH_REASONS:
            # Check this BEFORE touching response.text -- see _GEMINI_BLOCKED_FINISH_REASONS.
            raise ContentFilteredError(reason_name if candidate is not None else "NO_CANDIDATES")
        finish_reason = "stop" if reason_name == "STOP" else "length"
        return (response.text or ""), finish_reason, None

    if engine_key == "groq":
        # Groq exposes an OpenAI-compatible API — the `openai` SDK works unchanged,
        # just pointed at Groq's base URL.
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model=engine["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            presence_penalty=0.3,  # see the matching comment on the Gemini branch above
            # Load-bearing, not optional -- see the ENGINES["groq"] comment above.
            # "qwen/qwen3.6-27b" defaults to a thinking mode that otherwise burns
            # the whole max_tokens budget before ever reaching an answer.
            reasoning_effort="none",
        )
        choice = response.choices[0]
        finish_reason = "stop" if choice.finish_reason == "stop" else "length"
        return (choice.message.content or ""), finish_reason, None

    raise ValueError(f"Unknown engine: {engine_key}")
