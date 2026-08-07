"""Engine registry + dispatch — the same pattern originally proven in the Streamlit
prototype's ENGINES dict / generate_story(), ported essentially unchanged."""

import os
from typing import Optional

import anthropic
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
    "claude": {
        # Backup engine, server-side key only (no BYOK field in the UI) -- see
        # budget.py for the shared daily cap this engine alone is subject to.
        # Haiku 4.5 deliberately, not a frontier model: this key is the operator's
        # own, shared across every visitor, so cost-per-call matters here in a way
        # it doesn't for the BYOK engines.
        "env_var": "CLAUDE_API_KEY",
        "model": "claude-haiku-4-5",
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
    by max_tokens), and usage_tokens is the real output-token count when the engine
    reports one (currently just Claude, for budget.py's shared cap) or None."""
    engine = ENGINES[engine_key]

    if engine_key == "gemini":
        client = genai.Client(api_key=api_key)
        # Note there's no thinking_config here: "gemini-flash-lite-latest" has no
        # thinking capability at all (confirmed live: thoughts_token_count is None,
        # and passing thinking_config explicitly -- even to disable it -- 400s). The
        # earlier "thinking eats the output budget" workaround was specific to the
        # heavier flash model this replaced; this lite tier never had that problem.
        response = client.models.generate_content(
            model=engine["model"],
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
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

    if engine_key == "claude":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=engine["model"],
            max_tokens=max_tokens,
            # Claude's temperature range tops out at 1.0; our dial goes to 1.5 for
            # the other engines' looser ranges, so clamp rather than let it 400.
            temperature=min(temperature, 1.0),
            messages=[{"role": "user", "content": prompt}],
            # Haiku 4.5 doesn't think by default (that's an Opus/Sonnet-tier
            # behavior) — no thinking_budget footgun to work around here.
        )
        text = next((b.text for b in response.content if b.type == "text"), "") or ""
        finish_reason = "stop" if response.stop_reason == "end_turn" else "length"
        usage_tokens = getattr(response.usage, "output_tokens", None)
        return text, finish_reason, usage_tokens

    raise ValueError(f"Unknown engine: {engine_key}")
