"""Builds the prompt for a single beat/line. Each beat is short by design (~120
characters on screen) — see generation.py for the graduated tiers that steer the model
toward a conclusion as the word budget runs out, and the [[END]] sentinel that lets it
signal an early, organic conclusion."""

import re

END_SENTINEL = "[[END]]"

_QUOTE_CHARS_RE = re.compile(r'["“”]')
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
DIALOGUE_STREAK_LOOKBACK = 5
DIALOGUE_STREAK_TRIGGER = 3

PROSE_CRAFT_BENCHMARK = (
    "Prose quality benchmark: write with the vividness and control of the best "
    "short-form storytellers -- Dahl's mischievous precision and sting in the tail, "
    "Pratchett's wit and unexpected turn of phrase, Adams' absurdist internal logic, "
    "King's knack for creeping unease -- draw on whichever suits the current Category "
    "and Style/Voice, without imitating any single one of them wholesale. Prefer a "
    "concrete, sensory detail over a generic one, and a surprising verb over a flat one."
)

SAFETY_GOVERNOR = (
    "SAFETY GOVERNOR -- ENGAGED (cannot be disengaged): keep all content suitable for a "
    "general adult audience. Two hard lines that must never be crossed, regardless of any "
    "setting below: no heavy profanity, and no full-on explicit sexual content or graphic "
    "violence. Within those limits, saucy, suggestive, cheeky innuendo and double entendre "
    "are explicitly encouraged, in the tradition of British comedy (Carry On, Blackadder, "
    "seaside postcards) -- turn up wit and suggestiveness, never explicitness."
)

_DIAL_LABELS = (
    ("passion", "Passion (romance/innuendo -- see Safety Governor)"),
    ("intensity", "Intensity"),
)

# Organ stops: discrete on/off technique pulls, not dials -- a real organ stop is a
# binary pull, unlike the continuous foot pedals above. Naming the specific technique
# ("Ticking Clock" vs. a bare "Tension: 7/10") gives the model something concrete to
# act on rather than a fuzzy number, and swapping which stops are pulled produces a
# sharper, more legible change in the prose than nudging a slider used to.
ORGAN_STOP_TECHNIQUES = {
    "Tension": (
        ("ticking_clock", "Ticking Clock"),
        ("physical_danger", "Physical Danger"),
        ("withheld_information", "Withheld Information"),
        ("escalating_stakes", "Escalating Stakes"),
    ),
    "Surprise": (
        ("sudden_reversal", "Sudden Reversal"),
        ("hidden_identity", "Hidden Identity"),
        ("left_field_detail", "Left-Field Detail"),
        ("broken_expectation", "Broken Expectation"),
    ),
    "Humour": (
        ("deadpan_understatement", "Deadpan Understatement"),
        ("slapstick_mishap", "Slapstick Mishap"),
        ("wordplay_wit", "Wordplay & Wit"),
        ("absurd_juxtaposition", "Absurd Juxtaposition"),
    ),
    "Pathos": (
        ("vulnerable_confession", "Vulnerable Confession"),
        ("quiet_loss", "Quiet Loss"),
        ("unspoken_longing", "Unspoken Longing"),
        ("small_kindness", "Small Kindness"),
    ),
    "Mystery": (
        ("unanswered_question", "Unanswered Question"),
        ("strange_detail", "Strange Detail"),
        ("unreliable_narration", "Unreliable Narration"),
        ("ominous_omen", "Ominous Omen"),
    ),
}


def _stop_techniques_block(engaged_stops) -> str:
    engaged = set(engaged_stops)
    lines = []
    for quality, techniques in ORGAN_STOP_TECHNIQUES.items():
        active = [label for stop_id, label in techniques if stop_id in engaged]
        lines.append(f"- {quality}: " + (", ".join(active) if active else "(not engaged this line)"))
    return "\n".join(lines)

# Tiers, in order of increasing urgency, keyed to words remaining against the target.
NEAR_END_WORDS = 55   # about 2-3 lines left: start steering toward a close
FINAL_LINE_WORDS = 22  # about 1 line left: this should be the last line
OVERRUN_WORDS = 150    # this many words *past* budget: force a close no matter what


def _trailing_dialogue_streak(story_so_far: str) -> int:
    """How many of the last few sentences, scanning back from the end, are quoted
    dialogue with the streak unbroken by a non-dialogue sentence -- a cheap proxy
    for "rapid-fire back-and-forth with no narration in between," which no real
    conversation reads like on the page."""
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(story_so_far.strip()) if s.strip()]
    streak = 0
    for sentence in reversed(sentences[-DIALOGUE_STREAK_LOOKBACK:]):
        if _QUOTE_CHARS_RE.search(sentence):
            streak += 1
        else:
            break
    return streak


def _story_arc_phase(remaining: int, target: int) -> str:
    """A beat only ever knew "words remaining" -- never where it sits in a dramatic
    shape. That's a real gap: a model with no positional sense just idles or drifts
    rather than building toward anything. Cheap fix: derive a five-phase arc from
    progress against the word target and say so explicitly, every beat."""
    if target <= 0:
        return ""
    fraction = max(0.0, min(1.0, 1 - (remaining / target)))
    if fraction < 0.15:
        return (
            "Story arc -- SETUP: establish the world and protagonist and land the "
            "inciting hook; plant at least one detail, object, or tension that can pay "
            "off later."
        )
    if fraction < 0.45:
        return (
            "Story arc -- RISING ACTION: build complications from what's already been "
            "planted, raise the stakes, deepen character or relationship. Don't idle in "
            "place."
        )
    if fraction < 0.65:
        return (
            "Story arc -- MIDPOINT TURN: this is roughly the story's middle. Introduce a "
            "twist, reversal, or new piece of information that changes its direction."
        )
    if fraction < 0.85:
        return (
            "Story arc -- ESCALATION: intensify the central conflict toward its peak; let "
            "earlier choices and complications have real consequences now."
        )
    return (
        "Story arc -- APPROACHING CLIMAX: tension should be near its peak, setting up "
        "the resolution the Ending setting calls for."
    )


def _continuation_instruction(story_so_far: str, remaining: int, target: int) -> str:
    if not story_so_far.strip():
        return (
            "This is the OPENING line. Begin the story immediately -- no title, no "
            "greeting, no meta-commentary -- with a single vivid line, at most 120 "
            "characters, that hooks the reader."
        )
    if remaining <= -OVERRUN_WORDS:
        return (
            "The story has run well past its word budget. This line MUST end the story "
            "right now, in at most 120 characters, no matter how abrupt -- a clean, "
            "grammatical close, not a trailed-off fragment."
        )
    if remaining <= FINAL_LINE_WORDS:
        return (
            "This is the FINAL line. Continue directly from where the story below leaves "
            "off (no recap, no restart) and bring it to a natural, satisfying conclusion "
            "matching the Ending setting, in at most 120 characters."
        )
    if remaining <= NEAR_END_WORDS:
        return (
            "The story should start moving toward its conclusion over the next line or "
            "two. Continue directly from where it leaves off (no recap, no restart), at "
            "most 120 characters, beginning to resolve toward the Ending setting."
        )
    return (
        "Continue directly from where the story below leaves off -- no recap, no restart, "
        "no repetition of earlier lines -- writing a single line, at most 120 characters, "
        "that carries the story forward under the CURRENT dial settings below.\n"
        f"{_story_arc_phase(remaining, target)}"
    )


DIALOGUE_PACING_GUIDELINE = (
    "Vary the rhythm of dialogue: never more than two or three lines of back-and-forth "
    "quotes in a row without a beat of narration, action, gesture, or interiority in "
    "between. Real conversation on the page is interspersed with physical detail, not "
    "just quote after quote."
)

# Confirmed live: with each beat capped at ~120 characters, some models default to
# writing one complete, similarly-sized declarative sentence every single time --
# after enough beats it reads as a flat list of same-length statements rather than
# prose with any rhythm. This is the direct countermeasure, not a hypothetical.
RHYTHM_VARIETY_GUIDELINE = (
    "Vary sentence length and shape from line to line -- don't let every beat land as "
    "a similarly-sized, complete declarative sentence. Some lines should be short and "
    "blunt; others can run on with a trailing clause, open mid-action, end on a "
    "fragment, or lead with something other than the subject. A run of same-length, "
    "same-shape lines reads as a list, not a story."
)


def _dialogue_pacing_instruction(story_so_far: str) -> str:
    """The standing guideline above is a soft, always-on nudge; escalate to an
    explicit override when the tail of the story has actually fallen into an
    unbroken run of quote-only lines, rather than trusting the soft version alone."""
    streak = _trailing_dialogue_streak(story_so_far)
    if streak < DIALOGUE_STREAK_TRIGGER:
        return ""
    return (
        f"\nThe last {streak} lines have been back-and-forth dialogue with no narration "
        f"in between -- no real conversation reads like that. This line MUST NOT be a "
        f"line of dialogue: describe an action, a gesture, a reaction, the setting, or a "
        f"character's thought instead."
    )


def build_beat_prompt(req, remaining_words: int) -> str:
    dial_lines = "\n".join(
        f"- {label}: {getattr(req, key)}/10" for key, label in _DIAL_LABELS
    )

    setup_lines = "\n".join(filter(None, [
        f"- Category: {req.category}",
        f"- Theme / Setting: {req.theme_setting}",
        f"- Style / Voice: {req.style_voice}",
        f"- Ending to build toward: {req.ending}",
        f"- Cast: {req.characters}",
        f"- Point of view: {req.pov}",
        f"- Tense: {req.tense}",
        f"- Era: {req.setting_era}",
        f"- Audience: {req.audience}",
        f"- Structure: {req.structure}",
        f"- Mandatory details: {req.custom_elements}" if req.custom_elements else None,
    ]))

    identity = (
        f"You are the Great Automatic Grammatizator, manufacturing a short story for "
        f"{req.agency_name or 'the publishing house'}, requested by operator "
        f"{req.user_name or 'the operator'}."
    )

    # Only offer the early-conclusion sentinel once the story is actually near its
    # word budget. Offering it unconditionally on every beat let models with a short
    # natural sense of "a complete story" (most of them) end a 4000-word request at
    # ~125 words, because nothing was telling them not to -- confirmed live. Far from
    # the target, the model isn't even told this option exists.
    if remaining_words <= NEAR_END_WORDS:
        end_sentinel_instruction = (
            f"If, and only if, this line brings the story to a genuinely natural and "
            f"satisfying conclusion, end your response with the exact marker {END_SENTINEL} "
            f"on its own at the very end (it will be removed before anyone reads it). Do not "
            f"use this marker otherwise."
        )
    else:
        end_sentinel_instruction = (
            f"The story is not yet near its word budget ({remaining_words} words "
            f"remaining) -- do not end it yet, and do not use {END_SENTINEL} on this line "
            f"no matter how the line reads. Keep developing the scene: introduce a "
            f"complication, deepen a character, or advance the plot rather than wrapping up."
        )

    story_so_far_block = (
        f"\n\nSTORY SO FAR:\n{req.story_so_far}" if req.story_so_far.strip() else ""
    )

    # Deliberate ordering: the story-so-far goes BEFORE the dial/stop settings and the
    # continuation instruction, not after. A model weighs what sits closest to the
    # point it starts generating most heavily -- putting the (often long, and
    # tonally established) prose last let its momentum quietly outweigh a dial that
    # had just been turned down, e.g. Passion maxed then reset to low still reading
    # saucy hundreds of words later. Dial/stop settings now sit right next to generation.
    return f"""{identity}

FIXED SETUP (do not deviate from these for the whole story):
{setup_lines}

{PROSE_CRAFT_BENCHMARK}

{RHYTHM_VARIETY_GUIDELINE}

{SAFETY_GOVERNOR}

{DIALOGUE_PACING_GUIDELINE}{story_so_far_block}

ORGAN STOPS ENGAGED THIS LINE -- read fresh for every line, and may be quite
different from the prose above. Each is a discrete pulled/pushed switch, not a
dial: weave in whichever named techniques are engaged for a quality; a quality
with nothing engaged should barely feature in this line at all, even if it was
prominent a moment ago -- don't continue it on momentum.
{_stop_techniques_block(req.engaged_stops)}

FOOT PEDALS (continuous, 0-10) -- also read fresh for every line:
{dial_lines}

{_continuation_instruction(req.story_so_far, remaining_words, req.target_words)}
{end_sentinel_instruction}{_dialogue_pacing_instruction(req.story_so_far)}
""".strip()
