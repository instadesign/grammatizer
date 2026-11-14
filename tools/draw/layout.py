"""Where everything sits on the console, in one place.

Coordinates are in "safe area" units: a 1600 x 900 rectangle that is always fully
visible. The plate itself is drawn larger (2100 x 1200) so wider or taller windows see
more workshop rather than empty bars; SAFE_X / SAFE_Y is the safe area's offset within
it. build.py writes these numbers out as CSS custom properties (css/layout.css), so the
drawing and the live controls laid over it cannot drift apart.
"""

PLATE_W, PLATE_H = 2100, 1200
SAFE_W, SAFE_H = 1600, 900
SAFE_X, SAFE_Y = 250, 150

FLOOR_Y = 868

# ---- left cabinet: the pre-selectors ---------------------------------------------
LEFT = dict(x=24, y=128, w=412, h=724)
SHUTTER = dict(x=36, y=170, w=388, h=600)         # what the tambour covers when locked
DRUM = dict(x=172, w=250, h=42, label_x=40, label_w=126)
DRUM_ROW = 43
DRUMS_MAIN_Y = 176                                  # 4 rows
DRUMS_AUX_Y = 376                                   # 6 rows
AUX_PLATE = dict(x=40, y=350, w=382, h=22)
WORDAGE = dict(x=44, y=640, w=376, h=66)
SLIP = dict(x=44, y=712, w=376, h=50)
CRANK = dict(x=386, y=806)                          # centre of the scramble crank's boss

# ---- centre tower: the paper ------------------------------------------------------
TOWER = dict(x=496, w=608)
NAMEPLATE = dict(x=560, y=8, w=480, h=76)
HEAD = dict(x=496, y=82, w=608, h=68)
FLAG = dict(x=516, y=96, w=262, h=42)
ODOMETER = dict(x=822, y=96, w=262, h=42)
PLATEN = dict(x=500, y=150, w=600, h=34)
PAPER = dict(x=520, y=176, w=560, h=524)
TRAY = dict(x=496, y=696, w=608, h=26)
RAIL = dict(x=506, y=726, w=588, h=42)
WELL = dict(x=506, y=772, w=588, h=94)
GAUGE_PASSION = dict(x=520, y=768)
PEDAL_PASSION = dict(x=636, y=772)
GOVERNOR = dict(x=752, y=764)
PEDAL_INTENSITY = dict(x=854, y=772)
GAUGE_INTENSITY = dict(x=976, y=768)

# ---- the gaps either side of the paper ---------------------------------------------
GEAR_COLUMN = dict(x=466, ys=(236, 284, 332))       # small cogs, meshing down the gap
VALVES = dict(x=1134, y=204, step=74, n=5)          # valve centres, top one first

# ---- right cabinet: organ stops, sight-glass, lever --------------------------------
RIGHT = dict(x=1164, y=128, w=412, h=468)
PLINTH = dict(x=1164, y=596, w=412, h=256)
STOPS = dict(x=1244, y=168, cell_w=78, cell_h=84, quality_x=1174, quality_w=66)
SIGHT = dict(x=1182, y=612, w=150, h=234)
LEVER = dict(x=1330, y=650, scale=0.92)             # top-left of lever-base.svg

# ---- along the top ------------------------------------------------------------------
CARD = dict(x=36, y=26, w=214, h=86)                # operator's card
BIG_COGS = dict(ax=1226, ay=70, bx=1306, by=86)
WHISTLE = dict(x=1352, y=10, scale=0.7)
HORN = dict(x=1462, y=14, w=112, h=104)             # the ear-trumpet (sound)


def css():
    """The same numbers as CSS custom properties."""
    def px(v):
        return "%spx" % v
    rows = [
        ("plate-w", px(PLATE_W)), ("plate-h", px(PLATE_H)),
        ("safe-w", px(SAFE_W)), ("safe-h", px(SAFE_H)),
        ("safe-x", px(SAFE_X)), ("safe-y", px(SAFE_Y)),
    ]

    def box(name, d):
        for key in ("x", "y", "w", "h"):
            if key in d:
                rows.append(("%s-%s" % (name, key), px(d[key])))

    for name, d in (
        ("left", LEFT), ("shutter", SHUTTER), ("aux-plate", AUX_PLATE), ("wordage", WORDAGE),
        ("slip", SLIP), ("crank", CRANK), ("nameplate", NAMEPLATE), ("head", HEAD),
        ("flag", FLAG), ("odometer", ODOMETER), ("platen", PLATEN), ("paper", PAPER),
        ("tray", TRAY), ("rail", RAIL), ("well", WELL), ("gauge-passion", GAUGE_PASSION),
        ("pedal-passion", PEDAL_PASSION), ("governor", GOVERNOR),
        ("pedal-intensity", PEDAL_INTENSITY), ("gauge-intensity", GAUGE_INTENSITY),
        ("right", RIGHT), ("plinth", PLINTH), ("sight", SIGHT), ("lever", LEVER),
        ("card", CARD), ("whistle", WHISTLE), ("horn", HORN),
    ):
        box(name, d)
    rows += [
        ("drum-x", px(DRUM["x"])), ("drum-w", px(DRUM["w"])), ("drum-h", px(DRUM["h"])),
        ("drum-label-x", px(DRUM["label_x"])), ("drum-label-w", px(DRUM["label_w"])),
        ("drum-row", px(DRUM_ROW)), ("drums-main-y", px(DRUMS_MAIN_Y)), ("drums-aux-y", px(DRUMS_AUX_Y)),
        ("gear-x", px(GEAR_COLUMN["x"])),
        ("valve-x", px(VALVES["x"])), ("valve-y", px(VALVES["y"])), ("valve-step", px(VALVES["step"])),
        ("stops-x", px(STOPS["x"])), ("stops-y", px(STOPS["y"])),
        ("stop-w", px(STOPS["cell_w"])), ("stop-h", px(STOPS["cell_h"])),
        ("quality-x", px(STOPS["quality_x"])), ("quality-w", px(STOPS["quality_w"])),
        ("lever-scale", str(LEVER["scale"])), ("whistle-scale", str(WHISTLE["scale"])),
        ("cog-a-x", px(BIG_COGS["ax"])), ("cog-a-y", px(BIG_COGS["ay"])),
        ("cog-b-x", px(BIG_COGS["bx"])), ("cog-b-y", px(BIG_COGS["by"])),
    ]
    for i, y in enumerate(GEAR_COLUMN["ys"]):
        rows.append(("gear-y-%d" % (i + 1), px(y)))
    lines = ["/* Written by tools/draw/build.py from tools/draw/layout.py. Do not edit by hand:",
             "   change layout.py and re-run the build, so the drawing moves with it. */", "", ":root {"]
    lines += ["  --%s: %s;" % row for row in rows]
    lines += ["}", ""]
    return "\n".join(lines)
