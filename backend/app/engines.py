"""Engine registry + dispatch — the same pattern originally proven in the Streamlit
prototype's ENGINES dict / generate_story(), ported essentially unchanged."""

import os
import re
from typing import Optional

import anthropic
import pydantic
from google import genai
from google.genai import types as genai_types
from openai import OpenAI

from .errors import gemini_refused_the_key

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
        # The price of an alias: Google repoints it at each new model, and each new
        # model has accepted a different set of request settings from the last. See
        # _GEMINI_REQUEST_SHAPES below, which is how the call keeps up.
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
    "openai": {
        "env_var": "OPENAI_API_KEY",
        # What the title page calls ChatGPT. Unlike the two above there is no free
        # tier: the key has to belong to an API account with credit on it (a ChatGPT
        # subscription is billed separately and does not count).
        # Model taken from OpenAI's models page on 14 Nov 2026. The whole GPT-6 line
        # reasons before it writes; this one is the second tier ("near-Astra
        # performance ... at a lower cost", $2 in / $10 out per million tokens).
        # gpt-6-astra is the top model at five times the price; gpt-6-luna is the
        # cheap one at a twentieth. Changing tier is this one line, plus
        # ENGINE_MODEL_NAMES in js/screens/console.js (the name printed on the PDF).
        "model": "gpt-6.1-sol",
    },
    "claude": {
        "env_var": "ANTHROPIC_API_KEY",
        # Also paid only: needs API credit at platform.claude.com, which a claude.ai
        # subscription does not include (the reason the keyless Claude engine was
        # taken out in August; this one is bring-your-own-key like the rest).
        # $4 in / $20 out per million tokens. claude-sonnet-5-5 is half that and
        # claude-haiku-5-5 a fortieth; either can be put here as the call stands.
        "model": "claude-opus-5-5",
    },
}

# Both of the paid engines think before they write, and the thinking is billed against
# the same output limit as the words. So the limit they are given is the caller's
# max_tokens PLUS this, or a 220-token beat would be spent entirely on thought and come
# back empty (the same failure the Groq notes above describe). It is a ceiling, not a
# cost: unused room is not charged for. Gemini gets it too, whenever its thinking
# cannot be switched off outright (Google counts thought against the limit as well).
REASONING_HEADROOM_TOKENS = 3000

# How to ask Gemini for a line, in order of preference: as little thinking as the
# model allows, and the temperature dial honoured if the model still has one.
#
# Why a list and not one request: "gemini-flash-lite-latest" is whichever model Google
# currently puts behind that name, and the settings they accept have changed with
# every generation (Google's migration notes, read 15 Nov 2026):
#   - 2.5 Flash-Lite: thinking_budget=0 turns thinking off. The first shape.
#   - 3.1 / 3.5 Flash-Lite: thinking cannot be turned off, only down to "minimal",
#     with thinking_level in place of thinking_budget. temperature is "deprecated
#     and ignored".
#   - 3.8 Flash and the Gemini 4 models: "minimal" is refused ("low" is the floor),
#     and for generations after 3.5/3.6 the notes say temperature and its relatives
#     return an HTTP 400.
# A setting the model does not take comes back as a 400 that never says which
# setting it was ("Request contains an invalid argument."), so the only dependable
# move is to try the next shape. This used to be a single fallback that dropped
# thinking_budget and kept everything else. A model that refuses temperature as well
# fails both of those attempts, and the reader gets a jam with nothing on the paper:
# the likeliest reading of exactly that report on 15 Nov 2026, though not a proven
# one (there was no Gemini key to hand to reproduce it with). The shape that works is
# remembered (_gemini_shape below), so the search costs a few quick refusals once per
# server start, not once per line.
#
# Each entry: (thinking_config or None, send temperature and presence_penalty,
# the model may think and so needs REASONING_HEADROOM_TOKENS).
_GEMINI_REQUEST_SHAPES = (
    ({"thinking_budget": 0}, True, False),
    ({"thinking_level": "minimal"}, True, True),
    ({"thinking_level": "minimal"}, False, True),
    ({"thinking_level": "low"}, False, True),
    # The two below name no thinking setting at all, so they also work with a copy of
    # Google's library too old to know thinking_level (it refuses the three above
    # before sending anything; see _gemini_generate).
    (None, True, True),
    (None, False, True),
)
_gemini_shape = 0  # index of the shape that last worked

# generation.py allows a beat 30 seconds in all and has its own retry loop with that
# deadline, so the SDKs' built-in retries are switched off (two layers of retries
# stacking is how beats used to outlast the frontend's timeout) and one call may not
# hang for longer than this.
ENGINE_TIMEOUT_SECONDS = 25.0

_WORD_RE = re.compile(r"\S+")


def _hold_to_budget(text: str, max_tokens: int):
    """With the headroom above, max_tokens no longer limits how much the engine can
    WRITE, only how much it can think and write together. This puts the old limit
    back on the words alone (about three words to four tokens), so every engine hands
    generation.py the same thing: at most a beat's worth, marked "length" if it had
    to be cut, for trim_to_last_sentence to tidy."""
    words = list(_WORD_RE.finditer(text))
    limit = max(1, int(max_tokens * 0.75))
    if len(words) <= limit:
        return text, False
    return text[: words[limit - 1].end()], True


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
    RETRYABLE_CODES in generation.py), not a dead end. The OpenAI and Claude branches
    raise it too, when the provider declines a line instead of writing it."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"content filtered: {reason}")


def resolve_api_key(engine_key: str, supplied_key: Optional[str]) -> Optional[str]:
    """BYOK first; falls back to the server-side env var for this engine, if any."""
    if supplied_key:
        return supplied_key
    return os.environ.get(ENGINES[engine_key]["env_var"])


def _gemini_generate(client, model: str, prompt: str, temperature: float, max_tokens: int):
    """Asks Gemini for a line using the first of _GEMINI_REQUEST_SHAPES it accepts,
    starting from the one that worked last time. Returns (response, may_think).
    Only a refusal of the request itself moves on to the next shape; a bad key, a
    rate limit or an outage is raised at once, since no other shape would cure it."""
    global _gemini_shape
    refusal = None
    for step in range(len(_GEMINI_REQUEST_SHAPES)):
        index = (_gemini_shape + step) % len(_GEMINI_REQUEST_SHAPES)
        thinking_config, with_sampling, may_think = _GEMINI_REQUEST_SHAPES[index]
        config = {"max_output_tokens": max_tokens + (REASONING_HEADROOM_TOKENS if may_think else 0)}
        if thinking_config:
            config["thinking_config"] = thinking_config
        if with_sampling:
            # presence_penalty is a mechanical nudge against reusing a word that's
            # already appeared, layered under the prompt-level REPETITION_GUIDELINE and
            # generation.py's own mechanical retry -- it doesn't replace either (a
            # penalty alone won't stop genuine fixation the way the retry's hard block
            # does), but it should mean that retry needs to fire less often.
            config.update(temperature=temperature, presence_penalty=0.3)
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
        except pydantic.ValidationError as exc:
            # Google's library checks the settings before sending, and this copy of it
            # does not know one of them. Nothing went over the wire; try the next.
            refusal = exc
            continue
        except genai.errors.ClientError as exc:
            invalid_request = getattr(exc, "code", None) == 400 and getattr(exc, "status", None) in (
                None, "", "INVALID_ARGUMENT"
            )
            if not invalid_request or gemini_refused_the_key(exc):
                raise
            refusal = exc
            continue
        _gemini_shape = index
        return response, may_think
    raise refusal


def call_engine(engine_key: str, api_key: str, prompt: str, temperature: float, max_tokens: int):
    """One completion call. Returns (text, finish_reason, usage_tokens) where
    finish_reason is normalized to 'stop' (finished naturally) or 'length' (cut off
    by max_tokens). usage_tokens is always None -- every engine here is BYOK, so
    there's no shared server-side budget to track against it. The two paid engines
    (openai, claude) take no temperature: their current models reject the setting."""
    engine = ENGINES[engine_key]

    if engine_key == "gemini":
        client = genai.Client(
            api_key=api_key,
            # Milliseconds. Without it a slow answer could outlast generation.py's
            # whole allowance for the beat.
            http_options=genai_types.HttpOptions(timeout=int(ENGINE_TIMEOUT_SECONDS * 1000)),
        )
        response, may_think = _gemini_generate(client, engine["model"], prompt, temperature, max_tokens)
        candidate = response.candidates[0] if response.candidates else None
        raw_reason = getattr(candidate, "finish_reason", None)
        reason_name = getattr(raw_reason, "name", str(raw_reason))
        if candidate is None or reason_name in _GEMINI_BLOCKED_FINISH_REASONS:
            # Check this BEFORE touching response.text -- see _GEMINI_BLOCKED_FINISH_REASONS.
            raise ContentFilteredError(reason_name if candidate is not None else "NO_CANDIDATES")
        text, cut = (response.text or ""), False
        if may_think:
            # The limit sent was max_tokens plus headroom: put the old limit back on
            # the words, as for the two paid engines.
            text, cut = _hold_to_budget(text, max_tokens)
        finish_reason = "stop" if (reason_name == "STOP" and not cut) else "length"
        return text, finish_reason, None

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

    if engine_key == "openai":
        # The Responses API, not Chat Completions as on the Groq branch: it is the one
        # OpenAI recommends for the GPT-6 models. No temperature or presence_penalty:
        # these models refuse sampling settings whenever reasoning is on, and on this
        # model it cannot be turned off, only down ("low" is the floor).
        client = OpenAI(api_key=api_key, timeout=ENGINE_TIMEOUT_SECONDS, max_retries=0)
        response = client.responses.create(
            model=engine["model"],
            input=prompt,
            reasoning={"effort": "low"},
            max_output_tokens=max_tokens + REASONING_HEADROOM_TOKENS,
            # OpenAI otherwise keeps every response for 30 days. Nothing here needs
            # to be fetched again, and it is somebody's story.
            store=False,
        )
        incomplete = getattr(getattr(response, "incomplete_details", None), "reason", None)
        if incomplete == "content_filter":
            raise ContentFilteredError("content_filter")
        for item in response.output or []:
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", None) == "refusal":
                    raise ContentFilteredError("refusal")
        text, cut = _hold_to_budget(response.output_text or "", max_tokens)
        ran_out = response.status == "incomplete" and incomplete == "max_output_tokens"
        return text, ("length" if (cut or ran_out) else "stop"), None

    if engine_key == "claude":
        # No `thinking` and no temperature: on this model thinking is always on and
        # sampling settings are rejected. `effort` is the one control, and "low" is
        # plenty for sixty words of prose (the default, "medium", only adds delay).
        client = anthropic.Anthropic(api_key=api_key, timeout=ENGINE_TIMEOUT_SECONDS, max_retries=0)
        request = dict(
            model=engine["model"],
            max_tokens=max_tokens + REASONING_HEADROOM_TOKENS,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            # `fallbacks` asks Anthropic to re-run the line on another of its models,
            # inside this same call, if this model's safety classifiers decline it:
            # a jam the reader then never sees. It is a beta option. Should a key's
            # account not have it (the API answers 400), ask again without it, the
            # same way the Gemini branch above drops thinking_config; any other cause
            # of a 400 fails the second time too and is reported as usual.
            response = client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request
            )
        except anthropic.BadRequestError:
            response = client.messages.create(**request)
        if response.stop_reason == "refusal":
            # Check before reading the content, which is empty or partial here.
            raise ContentFilteredError("refusal")
        written = "".join(block.text for block in response.content if block.type == "text")
        text, cut = _hold_to_budget(written, max_tokens)
        ran_out = response.stop_reason == "max_tokens"
        return text, ("length" if (cut or ran_out) else "stop"), None

    raise ValueError(f"Unknown engine: {engine_key}")
