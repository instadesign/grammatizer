"""Pydantic request/response models. Every enumerated field here is a Literal matching
exactly the options presented in the frontend's setup/auxiliary/dial controls — see the
control taxonomy in the project plan for where each one comes from (Dahl's text, or a
deliberate, flagged addition)."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Engine = Literal["gemini", "groq"]

# Setup panel — locked once composition starts.
Category = Literal[
    "Historical", "Satirical", "Philosophical", "Political",
    "Romantic", "Erotic", "Humorous", "Straight",
]

ThemeSetting = Literal[
    "Army Life", "Pioneer Days", "Civil War", "World War",
    "Social Upheaval", "Wild West", "Country Life",
    "Childhood Memories", "Seafaring", "The Sea Bottom",
]

StyleVoice = Literal[
    "Classical", "Whimsical", "Racy", "Hard-Boiled",
    "Stream-of-Consciousness", "Gothic & Dense", "Lyrical",
]

Ending = Literal[
    "Happy & Resolved", "Tragic & Heartbreaking",
    "A Mind-Bending Plot Twist", "An Unresolved Cliffhanger",
]

# Auxiliary panel — also locked once composition starts.
Characters = Literal["A Lone Protagonist", "A Pair (Allies or Rivals)", "An Ensemble Cast"]
PointOfView = Literal[
    "First Person", "Third Person Limited", "Third Person Omniscient", "Second Person (Novelty)"
]
Tense = Literal["Past Tense", "Present Tense"]
SettingEra = Literal["Victorian", "Interwar", "Contemporary", "Far Future"]
Audience = Literal["Children's", "Young Adult", "Adult"]
Structure = Literal["Single Unbroken Scene", "Chaptered Sketch"]


class BeatRequest(BaseModel):
    engine: Engine
    api_key: Optional[str] = Field(default=None, max_length=512)

    # Machine internals — set once at engine-connect, not part of the story levers.
    temperature: float = Field(default=0.9, ge=0.1, le=1.5)

    # Setup panel
    category: Category
    theme_setting: ThemeSetting
    style_voice: StyleVoice
    ending: Ending
    target_words: int = Field(ge=500, le=10000)
    custom_elements: str = Field(default="", max_length=280)

    # Auxiliary panel
    characters: Characters
    pov: PointOfView
    tense: Tense
    setting_era: SettingEra
    audience: Audience
    structure: Structure

    # Organ stops: discrete on/off technique pulls, not dials -- a real organ stop is
    # a binary pull, not a continuous knob. Sends only the IDs currently pulled; the
    # registry of valid IDs (grouped by quality) lives in prompts.py, the only place
    # that needs to know what each one means. An unrecognized ID here is just ignored,
    # not rejected -- see build_beat_prompt.
    engaged_stops: List[str] = Field(default_factory=list, max_length=20)

    # Foot pedals: still continuous, 0-10 -- these are worked by pressure, per Dahl's
    # own text, unlike the organ stops above.
    passion: int = Field(ge=0, le=10)
    intensity: int = Field(ge=0, le=10)

    # Personalization (letterhead)
    user_name: str = Field(default="", max_length=80)
    agency_name: str = Field(default="", max_length=80)

    # Composition state — held client-side, resent every call. This is what makes the
    # backend fully stateless: no session/connection bookkeeping server-side.
    story_so_far: str = Field(default="", max_length=20000)


class BeatResponse(BaseModel):
    beat: str
    word_count: int
    concluded: bool


class PdfExportRequest(BaseModel):
    story: str = Field(max_length=20000)
    user_name: str = Field(default="", max_length=80)
    agency_name: str = Field(default="", max_length=80)
    engine: Engine
    model: str
    word_count: int
