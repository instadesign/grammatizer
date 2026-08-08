"""The core composition primitive: generate one beat/line at a time. Shared by every
call the frontend makes as it drives the live-composition loop -- there's no separate
'initial generate' vs 'regenerate' path, because the whole point is that there's no such
thing as a finished-then-replaced story; there's only ever 'the next line'."""

import logging
import re
import time

from . import engines
from .errors import GenerationError, translate_exception
from .prompts import END_SENTINEL, NEAR_END_WORDS, OVERRUN_WORDS, build_beat_prompt

logger = logging.getLogger("grammatizator")

MAX_TOKENS_NORMAL = 90
MAX_TOKENS_CONCLUDING = 120

# The beat-loop architecture is, by design, many small calls rather than one big one
# (see the plan) -- which means free-tier per-minute rate limits are a real, expected
# risk, not an edge case. A rate limit is usually transient (resets within the window),
# so it's worth one or two short retries before failing the whole manuscript over it.
MAX_RATE_LIMIT_RETRIES = 2
RETRY_WAIT_CAP_SECONDS = 10.0
DEFAULT_RETRY_WAIT_SECONDS = 5.0

# A blank completion that isn't a sentinel-only conclusion (see generate_beat) is
# usually a one-off bad roll, not systemic -- worth a couple of quick retries before
# failing the whole manuscript over it.
MAX_EMPTY_BEAT_RETRIES = 2

_SENTENCE_END_RE = re.compile(r'[.!?]["\')’”]?(?:\s|$)')
_GEMINI_RETRY_DELAY_RE = re.compile(r"([\d.]+)\s*s")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_EDGE_PUNCT_RE = re.compile(r'^[\s"\'“”‘’.!?,;:—-]+|[\s"\'“”‘’.!?,;:—-]+$')


def _normalize_sentence(sentence: str) -> str:
    return _EDGE_PUNCT_RE.sub("", sentence.strip().lower())


def _duplicates_story_tail(text: str, story_so_far: str) -> bool:
    """Guards against a beat that just re-narrates a sentence the story already
    delivered a moment ago -- e.g. a line of dialogue quoted, then the very next
    beat restates the same sentence as plain narration. Confirmed live, not
    hypothetical. Compares normalized (case/quote/punctuation-stripped) sentences
    against the last couple of sentences already on the page."""
    if not story_so_far.strip() or not text.strip():
        return False
    tail = [s for s in _SENTENCE_SPLIT_RE.split(story_so_far.strip()) if s.strip()][-2:]
    tail_normalized = {_normalize_sentence(s) for s in tail}
    tail_normalized.discard("")
    if not tail_normalized:
        return False
    new_sentences = [s for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]
    return any(_normalize_sentence(s) in tail_normalized for s in new_sentences)


_WORD_RE = re.compile(r"[A-Za-z']+")
REPETITION_WINDOW_WORDS = 100

# Purely word-count-based exceptions: articles, conjunctions, prepositions,
# pronouns, being/auxiliary verbs, and a handful of dialogue-tag verbs so common
# ("said", "asked") that policing them would make ordinary dialogue impossible to
# write. Character/place names get their own exemption below -- not by name (we
# never see one explicitly), but by a proper-noun heuristic.
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "but", "or", "nor", "so", "yet", "for",
    "of", "in", "on", "at", "to", "from", "by", "with", "about", "against",
    "between", "into", "through", "during", "before", "after", "above", "below",
    "up", "down", "over", "under", "again", "further", "then", "once", "here",
    "there", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "only", "own", "same", "than", "too", "very", "just",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "this", "that", "these", "those", "who", "whom", "whose", "which", "what",
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "not", "no", "as", "if", "because", "while", "although", "though",
    "since", "unless", "until", "whether", "said", "asked", "replied",
})


def _likely_proper_nouns(text: str) -> set:
    """Heuristic, not a real NER pass -- and deliberately biased toward precision
    over recall, since the two failure directions aren't symmetric: missing a real
    name just costs one wasted retry, but mistaking an ordinary repeated word (the
    actual thing this whole check exists to catch) for a name would silently
    defeat the feature. A capitalized word that appears in a NON-sentence-initial
    position at least once is a strong, reliable signal of a genuine proper noun --
    ordinary common nouns essentially never get capitalized mid-sentence in
    English. (Tried a "capitalized and recurs 2+ times" version first; it
    correctly caught a name that only ever opened sentences, but then also
    exempted "Shadows" for the same reason when it was actually the exact
    over-used word this check needs to catch -- confirmed live, worse trade.)"""
    names = set()
    for sentence in _SENTENCE_SPLIT_RE.split(text.strip()):
        words = _WORD_RE.findall(sentence)
        for word in words[1:]:
            if word[:1].isupper():
                names.add(word.lower())
    return names


def _repeated_content_words(text: str, story_so_far: str) -> list:
    """A prompt-only version of this rule (REPETITION_GUIDELINE in prompts.py)
    wasn't reliable enough on its own -- confirmed live, the same generation that
    produced the sentence-fragment collapse also repeated "shadows" and "fingers"
    over and over. This is the mechanical backstop the user actually asked for:
    strictly no content word repeated within the last ~100 words, excluding
    stopwords and likely names. Checks both against the story so far AND within
    this beat's own text (a beat can self-repeat in ~20 words on its own)."""
    if not text.strip():
        return []
    recent_words = _WORD_RE.findall(story_so_far.strip())[-REPETITION_WINDOW_WORDS:]
    recent_lower = {w.lower() for w in recent_words}
    # Recurrence has to be checked across the combined text -- a name appearing
    # once in the story so far and once in this new beat is still a recurring
    # name, but neither half alone would show 2+ occurrences on its own.
    names = _likely_proper_nouns(f"{story_so_far} {text}")

    seen_in_beat = set()
    violations = []
    for word in _WORD_RE.findall(text):
        lw = word.lower()
        if lw in _STOPWORDS or lw in names:
            continue
        if lw in recent_lower or lw in seen_in_beat:
            violations.append(lw)
        seen_in_beat.add(lw)
    return violations


def _gemini_retry_delay_seconds(exc: Exception) -> float:
    """Google's 429 RESOURCE_EXHAUSTED error usually carries a suggested wait as a
    RetryInfo detail (e.g. "19s"); use it when present rather than guessing blind."""
    details = getattr(exc, "details", None) or {}
    try:
        for item in details.get("error", {}).get("details", []):
            if str(item.get("@type", "")).endswith("RetryInfo"):
                match = _GEMINI_RETRY_DELAY_RE.match(str(item.get("retryDelay", "")))
                if match:
                    return float(match.group(1))
    except (AttributeError, TypeError):
        pass
    return DEFAULT_RETRY_WAIT_SECONDS


RETRYABLE_CODES = {"rate_limited", "engine_overloaded"}


def _call_engine_with_retry(engine_key: str, api_key: str, prompt: str, temperature: float, max_tokens: int):
    """Wraps engines.call_engine with a short retry loop for transient failures --
    the caller's own rate limit, or the provider's infrastructure being overloaded.
    Any other failure is classified and raised immediately."""
    attempt = 0
    while True:
        try:
            return engines.call_engine(engine_key, api_key, prompt, temperature=temperature, max_tokens=max_tokens)
        except Exception as exc:
            mapped = translate_exception(engine_key, exc)
            # A cooldown longer than our whole retry budget (e.g. Groq's daily-token-cap
            # message giving an exact multi-minute wait) can't be fixed by a couple of
            # quick retries -- surface the real, already-informative error immediately
            # instead of burning ~10s pretending a retry could help.
            known_long_wait = (
                mapped.retry_after_seconds is not None and mapped.retry_after_seconds > RETRY_WAIT_CAP_SECONDS
            )
            if mapped.code in RETRYABLE_CODES and attempt < MAX_RATE_LIMIT_RETRIES and not known_long_wait:
                delay = _gemini_retry_delay_seconds(exc) if engine_key == "gemini" else DEFAULT_RETRY_WAIT_SECONDS
                delay = min(delay, RETRY_WAIT_CAP_SECONDS)
                attempt += 1
                logger.warning(
                    "%s on %s, retrying in %.1fs (attempt %d/%d)",
                    mapped.code, engine_key, delay, attempt, MAX_RATE_LIMIT_RETRIES,
                )
                time.sleep(delay)
                continue
            logger.exception("engine call failed (engine=%s): %s", engine_key, type(exc).__name__)
            raise mapped from exc


def count_words(text: str) -> int:
    return len(text.split())


def trim_to_last_sentence(text: str) -> str:
    """If a beat gets cut off by max_tokens, trim back to the last complete sentence
    rather than ever displaying a mid-word stub. If no sentence boundary is found at
    all, the text is short enough to just show as-is."""
    text = text.strip()
    matches = list(_SENTENCE_END_RE.finditer(text))
    if not matches:
        return text
    return text[: matches[-1].end()].strip()


def generate_beat(req) -> dict:
    api_key = engines.resolve_api_key(req.engine, req.api_key)
    if not api_key:
        raise GenerationError(
            "missing_api_key", "No API key supplied and no server-side fallback configured.", 401
        )

    current_words = count_words(req.story_so_far)
    remaining = req.target_words - current_words
    is_urgent = bool(req.story_so_far.strip()) and remaining <= NEAR_END_WORDS

    prompt = build_beat_prompt(req, remaining_words=remaining)
    max_tokens = MAX_TOKENS_CONCLUDING if is_urgent else MAX_TOKENS_NORMAL

    # A single blank completion shouldn't kill the whole manuscript -- try a couple
    # more times before giving up. One legitimate reason a beat comes back empty
    # AFTER stripping the sentinel isn't actually an error at all: near the end, the
    # model sometimes (correctly) has nothing left to add and replies with bare
    # "[[END]]" because the previous beat already delivered the satisfying final
    # line -- that's a real, silent conclusion, not a failure, so it exits the retry
    # loop immediately rather than being treated as empty output.
    text = ""
    concluded_by_sentinel = False
    finish_reason = None
    for attempt in range(MAX_EMPTY_BEAT_RETRIES + 1):
        # Errors raised here are already-mapped GenerationErrors (and already logged
        # server-side, minus the retried rate-limit attempts) -- see _call_engine_with_retry.
        raw_text, finish_reason, _usage_tokens = _call_engine_with_retry(
            req.engine, api_key, prompt, temperature=req.temperature, max_tokens=max_tokens
        )

        # Trust the sentinel only when the prompt actually offered it (see prompts.py --
        # far from the target, the model is told NOT to use it at all). Defense in depth:
        # if a model ignores that instruction and emits it anyway, ignore the sentinel
        # rather than ending a 4000-word request at 125 words again.
        concluded_by_sentinel = END_SENTINEL in raw_text and remaining <= NEAR_END_WORDS
        text = raw_text.replace(END_SENTINEL, "").strip()

        if finish_reason == "length":
            text = trim_to_last_sentence(text)

        is_duplicate = bool(text) and _duplicates_story_tail(text, req.story_so_far)
        repeated_words = _repeated_content_words(text, req.story_so_far) if text else []
        if (text or concluded_by_sentinel) and not is_duplicate and not repeated_words:
            break
        reason = (
            "duplicated the story's tail" if is_duplicate
            else f"repeated word(s) {repeated_words}" if repeated_words
            else "empty text"
        )
        logger.warning(
            "beat retry %d/%d (engine=%s): %s",
            attempt + 1, MAX_EMPTY_BEAT_RETRIES + 1, req.engine, reason,
        )

    if not text and not concluded_by_sentinel:
        raise GenerationError(
            "engine_error", "The machine produced nothing usable for this line.", 502
        )

    forced_conclusion = remaining <= -OVERRUN_WORDS
    new_word_count = current_words + count_words(text)

    return {
        "beat": text,
        "word_count": new_word_count,
        "concluded": bool(concluded_by_sentinel or forced_conclusion),
    }
