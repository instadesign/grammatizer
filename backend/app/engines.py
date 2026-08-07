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
        "model": "llama-3.3-70b-versatile",
    },
}


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
        config_kwargs = dict(temperature=temperature, max_output_tokens=max_tokens)
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
        )
        choice = response.choices[0]
        finish_reason = "stop" if choice.finish_reason == "stop" else "length"
        return (choice.message.content or ""), finish_reason, None

    raise ValueError(f"Unknown engine: {engine_key}")
