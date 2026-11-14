"""The machine's separate parts: anything that moves, lights up or repeats.

Each function returns a Drawing sized in stage pixels (the console is laid out on a
1600 x 900 canvas, see css/stage.css). Moving parts are their own files so the browser
can animate them as flat images without ever repainting the big back plate.
"""

import math

from .ink import (
    Drawing, PAPER, PAPER_LIGHT, INK, BRASS, BRASS_LIGHT, VERDIGRIS, EMBER, MADDER,
    PAYNE, SIENNA, UMBER, GOUACHE,
    rect_pts, arc_pts, circle_pts, ellipse_pts, round_rect_pts, annulus_sector,
    rotate_pts, shift_pts, scale_pts, spline, fmt,
)


# ---- the lever ------------------------------------------------------------------------

LEVER_PIVOT = (130, 172)       # in lever-base.svg
LEVER_ARM_PIVOT = (40, 226)    # in lever-arm.svg


def lever_base():
    d = Drawing(260, 214, seed=11)
    px, py = LEVER_PIVOT

    # cast-iron foot, bolted down
    foot = [(34, 186), (226, 186), (236, 208), (24, 208)]
    d.ko(foot)
    d.wash(foot, PAYNE, op=0.5, amp=1.0)
    d.hatch([(130, 190), (232, 190), (236, 208), (120, 208)], gap=3.6, w=0.65, fade="a")
    d.edges(foot, w=2.2, over=3)
    for x in (48, 82, 178, 212):
        d.rivet(x, 197, 2.6)

    # two flat struts carrying the quadrant
    for sign in (-1, 1):
        a = -90 + sign * 56
        tip = (px + 100 * math.cos(math.radians(a)), py + 100 * math.sin(math.radians(a)))
        strut = [(px - 7 * sign, py - 4), (px + 5 * sign, py + 6), (tip[0] + 5 * sign, tip[1] + 7), (tip[0] - 6 * sign, tip[1] - 2)]
        d.ko(strut)
        d.wash(strut, PAYNE, op=0.42, amp=0.6)
        d.edges(strut, w=1.6, over=1.5)

    # the brass quadrant with its ratchet
    quad = annulus_sector(px, py, 92, 122, -152, -28, 16)
    d.ko(quad)
    d.wash(quad, BRASS, op=0.62, amp=1.2, grow=-1.0)
    d.wash(annulus_sector(px, py, 92, 104, -100, -28, 10), PAYNE, op=0.2, edge=0, amp=0.5)
    d.hatch(annulus_sector(px, py, 93, 101, -84, -30, 8), gap=3.2, w=0.6, trim=0.3)
    d.arc(px, py, 92, 92, -152, -28, w=1.9)
    d.line(*[(px + r * math.cos(math.radians(-152)), py + r * math.sin(math.radians(-152))) for r in (92, 122)], w=1.9, over=1.5)
    d.line(*[(px + r * math.cos(math.radians(-28)), py + r * math.sin(math.radians(-28))) for r in (92, 122)], w=1.9, over=1.5)
    # ratchet teeth: little saw-cuts along the outer edge
    teeth = []
    a = -152.0
    while a < -28.5:
        a2 = min(-28.0, a + 6.2)
        teeth.append((px + 122 * math.cos(math.radians(a)), py + 122 * math.sin(math.radians(a))))
        teeth.append((px + 127.5 * math.cos(math.radians(a2 - 0.6)), py + 127.5 * math.sin(math.radians(a2 - 0.6))))
        a = a2
    teeth.append((px + 122 * math.cos(math.radians(-28)), py + 122 * math.sin(math.radians(-28))))
    tooth_fill = teeth + arc_pts(px, py, 121, 121, -28, -152, 16)
    d.ko(tooth_fill)
    d.wash(tooth_fill, BRASS, op=0.62, amp=0.3, step=6, edge=0)
    d.edges(teeth, w=1.5, over=0.4, closed=False, amp=0.2, taper=0.7)
    # the slot the latch rides in
    slot = annulus_sector(px, py, 106, 111, -146, -34, 16)
    d.ko(slot)
    d.wash(slot, PAYNE, op=0.6, edge=0, amp=0.3, step=8)
    d.hatch(slot, gap=2.4, w=0.55, trim=0.1)
    d.outline(slot, w=1.1)
    for a in (-146, -90, -34):
        d.screw(px + 98 * math.cos(math.radians(a)), py + 98 * math.sin(math.radians(a)), 2.6)

    # bearing block at the pivot
    block = [(px - 26, py - 6), (px + 26, py - 6), (px + 32, py + 16), (px - 32, py + 16)]
    d.ko(block)
    d.wash(block, PAYNE, op=0.5, amp=0.7)
    d.hatch([(px + 2, py - 4), (px + 26, py - 4), (px + 31, py + 15), (px + 2, py + 15)], gap=3.2, w=0.6)
    d.edges(block, w=2.0, over=2)
    return d


def lever_arm():
    d = Drawing(80, 252, seed=12)
    px, py = LEVER_ARM_PIVOT
    top = 52

    # latch rod running up the side to a little trigger
    d.curve([(px - 12, py - 34), (px - 13, py - 110), (px - 14, top + 30), (px - 22, top + 12)], w=1.4)
    trig = [(px - 30, top + 6), (px - 18, top + 2), (px - 15, top + 16), (px - 27, top + 20)]
    d.ko(trig)
    d.wash(trig, BRASS, op=0.6, amp=0.4, step=6)
    d.edges(trig, w=1.3, over=1)

    # the bar itself, tapering towards the hand
    bar = [(px - 9, py), (px - 6, top), (px + 6, top), (px + 9, py)]
    d.ko(bar)
    d.wash(bar, PAYNE, op=0.42, amp=0.8)
    d.wash([(px + 2, top), (px + 6, top), (px + 9, py), (px + 3, py)], PAYNE, op=0.25, edge=0, amp=0.4)
    d.hatch([(px + 1.5, top + 6), (px + 5.5, top + 6), (px + 8.5, py - 20), (px + 2.5, py - 20)], gap=3.4, w=0.6, trim=0.15)
    d.line((px - 9, py), (px - 6, top), w=2.0, over=1)
    d.line((px + 9, py), (px + 6, top), w=2.0, over=1)
    for y in (py - 44, py - 96, py - 140):
        d.rivet(px - 0.5, y, 1.8)

    # brass ferrule, then the grip: a turned ball, painted red
    ferr = [(px - 8.5, top - 4), (px + 8.5, top - 4), (px + 7.5, top + 12), (px - 7.5, top + 12)]
    d.ko(ferr)
    d.wash(ferr, BRASS, op=0.65, amp=0.4, step=6)
    d.edges(ferr, w=1.6, over=1)
    d.line((px - 8, top + 3.5), (px + 8, top + 3.5), w=1.0, over=0)
    gx, gy, gr = px, top - 24, 22
    d.disc(gx, gy, gr, fill=MADDER, op=0.78, lw=2.2)
    d.wash(d.crescent(gx, gy, gr, depth=0.3), UMBER, op=0.3, edge=0, amp=0.5)
    d.hatch(annulus_sector(gx, gy, gr * 0.62, gr - 1.2, 0, 96, 8), gap=3.0, w=0.65, trim=0.25)
    d.glint(arc_pts(gx, gy, gr * 0.62, gr * 0.62, 196, 262, 6), w=3.2)
    d.glint(arc_pts(gx, gy, gr * 0.62, gr * 0.62, 274, 288, 3), w=2.2, opacity=0.7)

    # hub and its big square-headed bolt
    d.disc(px, py, 17, fill=BRASS, op=0.66, lw=2.2)
    d.hatch(annulus_sector(px, py, 9.5, 15.5, 5, 100, 8), gap=3.0, w=0.6)
    nut = rotate_pts(rect_pts(px - 6.5, py - 6.5, 13, 13), 18, px, py)
    d.ko(nut)
    d.wash(nut, PAYNE, op=0.5, amp=0.3, step=5)
    d.edges(nut, w=1.5, over=0.8)
    d.dot(px, py, 1.6)
    return d


# ---- organ stops ------------------------------------------------------------------------

def stop_seat():
    d = Drawing(64, 64, seed=21)
    c = 32
    d.disc(c, c, 25, fill=BRASS, op=0.62, lw=1.9)
    hole = circle_pts(c, c, 16.5, 16)
    d.ko(hole)
    d.wash(hole, PAYNE, op=0.62, amp=0.5, step=6)
    d.hatch(hole, gap=2.6, w=0.6, trim=0.12)
    d.hatch(hole, angle=40, gap=3.4, w=0.5, trim=0.3)
    d.circle(c, c, 16.5, w=1.4)
    d.screw(c - 20.5, c, 2.1)
    d.screw(c + 20.5, c, 2.1)
    return d


def stop_shaft():
    """A short brass rod, drawn pointing east from its left end; CSS turns and
    stretches it between the seat and the knob."""
    d = Drawing(34, 14, seed=22)
    body = [(0, 2.5), (33, 2.5), (33, 11.5), (0, 11.5)]
    d.ko(body)
    d.wash(body, BRASS, op=0.7, amp=0.3, step=8)
    d.wash([(0, 7.5), (33, 7.5), (33, 11.5), (0, 11.5)], PAYNE, op=0.3, edge=0, amp=0.2)
    d.line((0, 2.5), (33, 2.5), w=1.5, over=0)
    d.line((0, 11.5), (33, 11.5), w=1.5, over=0)
    d.glint([(3, 5), (30, 5)], w=1.2, opacity=0.6)
    return d


def stop_knob():
    d = Drawing(60, 60, seed=23)
    c = 30
    # turned wooden collar
    d.disc(c, c, 26, fill=SIENNA, op=0.72, lw=2.1)
    d.wash(d.crescent(c, c, 26, depth=0.26), UMBER, op=0.34, edge=0, amp=0.5)
    d.hatch(annulus_sector(c, c, 20.5, 25, -8, 104, 10), gap=2.8, w=0.6, trim=0.2)
    d.circle(c, c, 21.5, w=1.0)
    d.glint(arc_pts(c, c, 23.6, 23.6, 190, 250, 6), w=1.8, opacity=0.7)
    # porcelain face
    face = circle_pts(c, c, 18.5, 16)
    d.ko(face, PAPER_LIGHT)
    d.wash(d.crescent(c, c, 18.5, depth=0.2), PAYNE, op=0.2, edge=0, amp=0.4)
    d.circle(c, c, 18.5, w=1.4)
    d.circle(c, c, 15.2, w=0.7)
    return d


def stop_shadow():
    """The knob's cast shadow on the jamb: grey wash and a few hatch strokes."""
    d = Drawing(72, 72, seed=24)
    blob = ellipse_pts(38, 39, 27, 25, 14)
    d.wash(blob, PAYNE, op=0.3, amp=1.4, edge=0.1)
    d.hatch(blob, gap=3.4, w=0.65, trim=0.3, opacity=0.75)
    return d


def jewel():
    d = Drawing(22, 22, seed=25)
    c = 11
    d.disc(c, c, 8.6, fill=BRASS, op=0.6, lw=1.3, shade=False)
    dome = circle_pts(c, c, 5.6, 10)
    d.ko(dome)
    d.wash(dome, UMBER, op=0.62, amp=0.3, step=4)
    d.circle(c, c, 5.6, w=1.0)
    d.glint(arc_pts(c, c, 3.2, 3.2, 200, 260, 4), w=1.1, opacity=0.7)
    return d


def jewel_glow():
    """The lit state. A glow is the one place a soft gradient is right: it is what a
    wet-in-wet wash of orange does on the page."""
    d = Drawing(64, 64, seed=26)
    d.raw('<defs><radialGradient id="g"><stop offset="0" stop-color="#ffe9b0" stop-opacity="1"/>'
          '<stop offset="0.16" stop-color="#f7b54a" stop-opacity="0.95"/>'
          '<stop offset="0.42" stop-color="%s" stop-opacity="0.42"/>'
          '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient></defs>' % (EMBER, EMBER))
    d.raw('<circle cx="32" cy="32" r="32" fill="url(#g)"/>')
    d.glint(arc_pts(32, 32, 3.2, 3.2, 200, 260, 4), w=1.2, opacity=0.9)
    return d


# ---- pre-selector drum ------------------------------------------------------------------

DRUM_W, DRUM_H = 250, 42
DRUM_WINDOW = (13, 7, 196, 28)   # x, y, w, h of the opening the card shows through


def drum():
    d = Drawing(DRUM_W, DRUM_H, seed=31)
    outer = round_rect_pts(1.5, 1.5, DRUM_W - 3, DRUM_H - 3, 7)
    d.ko(outer)
    d.wash(outer, BRASS, op=0.62, amp=0.9, grow=-0.8)
    d.wash([(DRUM_W * 0.5, DRUM_H * 0.55), (DRUM_W - 3, DRUM_H * 0.3), (DRUM_W - 3, DRUM_H - 3), (4, DRUM_H - 3), (4, DRUM_H * 0.72)], PAYNE, op=0.17, edge=0)
    d.outline(outer, w=2.0)

    wx, wy, ww, wh = DRUM_WINDOW
    win = round_rect_pts(wx, wy, ww, wh, 3)
    d.ko(win, PAPER_LIGHT)
    # the card is on a drum: it darkens as it curves away at top and bottom
    d.wash(rect_pts(wx, wy, ww, 6.5), PAYNE, op=0.36, edge=0, amp=0.5)
    d.wash(rect_pts(wx, wy + wh - 6, ww, 6), PAYNE, op=0.42, edge=0, amp=0.5)
    d.hatch(rect_pts(wx + 1, wy + 0.5, ww - 2, 4.5), angle=0, gap=1.7, w=0.5, trim=0.12, skip=0.1)
    d.hatch(rect_pts(wx + 1, wy + wh - 4.5, ww - 2, 4), angle=0, gap=1.6, w=0.5, trim=0.12, skip=0.1)
    d.outline(win, w=1.5)
    d.screw(7, DRUM_H / 2.0, 2.2)

    # thumbwheel well on the right
    tx = wx + ww + 9
    well = round_rect_pts(tx, 5, 24, DRUM_H - 10, 4)
    d.ko(well)
    d.wash(well, PAYNE, op=0.55, amp=0.4, step=8)
    d.hatch(well, gap=2.6, w=0.55, trim=0.1)
    d.outline(well, w=1.3)
    return d


def thumbwheel():
    """The knurled edge of the wheel that turns a drum, seen through its well."""
    d = Drawing(20, 30, seed=32)
    body = round_rect_pts(1.5, 1, 17, 28, 5)
    d.ko(body)
    d.wash(body, BRASS, op=0.7, amp=0.3, step=6)
    d.wash(rect_pts(1.5, 1, 17, 6), PAYNE, op=0.34, edge=0, amp=0.3)
    d.wash(rect_pts(1.5, 23, 17, 6), PAYNE, op=0.4, edge=0, amp=0.3)
    d.outline(body, w=1.3)
    ys = [3.6, 6.2, 9.4, 13.2, 17.2, 21.0, 24.2, 26.8]
    for y in ys:
        d.pen([(3.6, y), (16.4, y)], w=0.95, amp=0.15, taper=0.6)
    return d


# ---- gauges ---------------------------------------------------------------------------------

GAUGE = 116
GAUGE_SWEEP = (-125.0, 125.0)   # needle rotation in degrees (0 = straight up) at value 0 and 1


def gauge(zones=True, seed=41):
    d = Drawing(GAUGE, GAUGE, seed=seed)
    c = GAUGE / 2.0
    d.disc(c, c, 55, fill=BRASS, op=0.64, lw=2.3)
    d.hatch(annulus_sector(c, c, 47, 54, -5, 105, 12), gap=3.0, w=0.62, trim=0.25)
    d.glint(arc_pts(c, c, 51, 51, 196, 248, 8), w=2.2, opacity=0.7)
    face = circle_pts(c, c, 45.5, 28)
    d.ko(face, PAPER_LIGHT)
    d.wash(d.crescent(c, c, 45.5, depth=0.12), PAYNE, op=0.13, edge=0, amp=0.5)
    # under the bezel's lip, upper left, the face is in shadow
    d.wash(annulus_sector(c, c, 41, 45.5, 160, 290, 12), PAYNE, op=0.2, edge=0, amp=0.4)
    if zones:
        d.wash(annulus_sector(c, c, 31.5, 37, 145, 215, 8), VERDIGRIS, op=0.55, amp=0.5, edge=0.15, step=6)
        d.wash(annulus_sector(c, c, 31.5, 37, -22, 35, 8), MADDER, op=0.62, amp=0.5, edge=0.15, step=6)
    d.circle(c, c, 45.5, w=1.6)
    # ticks: the needle's own sweep, mapped to compass angles (0 = up)
    a0, a1 = GAUGE_SWEEP
    for i in range(21):
        rot = a0 + (a1 - a0) * i / 20.0
        a = math.radians(rot - 90)
        major = i % 2 == 0      # eleven long ticks: the pedal's 0 to 10
        r0, r1 = (30.5 if major else 34.0), 39.5
        d.pen([(c + r0 * math.cos(a), c + r0 * math.sin(a)), (c + r1 * math.cos(a), c + r1 * math.sin(a))],
              w=1.5 if major else 0.85, amp=0.15, taper=0.6)
    d.arc(c, c, 39.8, 39.8, a0 - 90, a1 - 90, w=0.9)
    return d


def gauge_needle():
    """Points straight up; CSS rotates it about the centre."""
    d = Drawing(GAUGE, GAUGE, seed=42)
    c = GAUGE / 2.0
    needle = [(c - 2.6, c + 3), (c - 0.5, c - 37), (c + 0.5, c - 37), (c + 2.6, c + 3)]
    tail = [(c - 2.6, c + 3), (c + 2.6, c + 3), (c + 4.0, c + 13), (c - 4.0, c + 13)]
    d.ko(needle + tail[2:])
    d.wash(needle, MADDER, op=0.85, amp=0.15, step=6, edge=0)
    d.wash(tail, INK, op=0.7, amp=0.15, step=5, edge=0)
    d.pen([(c - 2.6, c + 12), (c - 0.4, c - 37.5)], w=1.1, amp=0.15, taper=0.6)
    d.pen([(c + 2.6, c + 12), (c + 0.4, c - 37.5)], w=1.1, amp=0.15, taper=0.6)
    d.disc(c, c, 5.2, fill=BRASS, op=0.8, lw=1.3, shade=False)
    d.dot(c, c, 1.3)
    return d


def gauge_glass():
    """Reflection on the glass, laid over the needle."""
    d = Drawing(GAUGE, GAUGE, seed=43)
    c = GAUGE / 2.0
    d.glint(arc_pts(c, c, 36, 36, 205, 250, 8), w=3.4, opacity=0.5)
    d.glint(arc_pts(c, c, 36, 36, 258, 268, 3), w=2.4, opacity=0.42)
    d.glint(arc_pts(c, c, 40, 40, 30, 52, 4), w=1.6, opacity=0.3)
    return d


# ---- gearing ---------------------------------------------------------------------------------

def cog(r, teeth, spokes=5, fill=BRASS, seed=51):
    size = r * 2 + 8
    d = Drawing(size, size, seed=seed)
    d.cog(size / 2.0, size / 2.0, r, teeth, spokes=spokes, fill=fill)
    return d


# ---- steam whistle ---------------------------------------------------------------------------

def whistle():
    d = Drawing(120, 170, seed=61)
    # feed pipe coming up from the machine, with a side stub to a hand-wheel
    d.pipe([(60, 170), (60, 96)], r=9, fill=VERDIGRIS, flanges=(0.18,))
    d.pipe([(60, 122), (96, 122)], r=6, fill=VERDIGRIS, hatch=False)
    # hand-wheel, edge-on to us would be dull: face it forward
    wx, wy, wr = 99, 122, 17
    d.disc(wx, wy, wr, fill=MADDER, op=0.7, lw=1.9)
    inner = circle_pts(wx, wy, wr - 5, 14)
    d.ko(inner)
    d.circle(wx, wy, wr - 5, w=1.2)
    for a in (20, 140, 260):
        p = (wx + (wr - 5) * math.cos(math.radians(a)), wy + (wr - 5) * math.sin(math.radians(a)))
        d.pen([(wx, wy), p], w=2.4, amp=0.2, taper=0.8)
    d.disc(wx, wy, 4.2, fill=BRASS, op=0.8, lw=1.2, shade=False)

    # the whistle: a collar, the bell with its slot, a domed cap and a ball
    collar = [(46, 88), (74, 88), (71, 100), (49, 100)]
    d.ko(collar)
    d.wash(collar, BRASS, op=0.66, amp=0.4, step=6)
    d.edges(collar, w=1.7, over=1.2)
    bell = [(47, 40), (73, 40), (73, 82), (47, 82)]
    d.ko(bell)
    d.wash(bell, BRASS, op=0.64, amp=0.7)
    d.wash([(63, 40), (73, 40), (73, 82), (63, 82)], PAYNE, op=0.24, edge=0, amp=0.4)
    d.hatch([(64, 43), (72, 43), (72, 80), (64, 80)], gap=3.2, w=0.6, trim=0.2)
    d.edges(bell, w=1.9, over=1.5)
    d.glint([(51.5, 45), (51.5, 78)], w=2.0, opacity=0.6)
    mouth = round_rect_pts(52, 84, 16, 4.5, 2)
    d.ko(mouth)
    d.wash(mouth, INK, op=0.75, edge=0, amp=0.2, step=5)
    d.pen([(47, 84), (73, 84)], w=1.2, amp=0.2)
    cap = arc_pts(60, 40, 14.5, 13, 180, 360, 10)
    d.ko(cap)
    d.wash(cap, BRASS, op=0.66, amp=0.4, step=6)
    d.pen(cap, w=1.9, amp=0.3)
    d.disc(60, 23, 4.6, fill=BRASS, op=0.75, lw=1.4, shade=False)
    return d



# ---- foot pedals ------------------------------------------------------------------------

def pedal():
    """A swell pedal seen from the front. CSS squashes it from the hinge as it is pressed."""
    d = Drawing(110, 92, seed=71)
    shoe = [(20, 6), (90, 6), (102, 78), (8, 78)]
    d.ko(shoe)
    d.wash(shoe, UMBER, op=0.66, amp=0.8)
    d.wash([(62, 6), (90, 6), (102, 78), (60, 78)], PAYNE, op=0.22, edge=0, amp=0.5, glaze=False)
    d.edges(shoe, w=2.1, over=2)
    for i in range(7):
        t = (i + 1) / 8.0
        y = 6 + 72 * t
        x0 = 20 - 12 * t + 5
        x1 = 90 + 12 * t - 5
        d.pen([(x0, y), (x1, y)], w=1.5, amp=0.4, taper=0.6)
    heel = [(6, 78), (104, 78), (106, 90), (4, 90)]
    d.ko(heel)
    d.wash(heel, BRASS, op=0.68, amp=0.4, step=8)
    d.edges(heel, w=1.8, over=1.5)
    for x in (16, 55, 94):
        d.rivet(x, 84, 1.8)
    d.glint([(25, 12), (17, 62)], w=2.0, opacity=0.35)
    return d


# ---- safety governor ------------------------------------------------------------------------

def governor_base():
    d = Drawing(96, 104, seed=75)
    foot = [(26, 92), (70, 92), (76, 103), (20, 103)]
    d.ko(foot)
    d.wash(foot, PAYNE, op=0.55, amp=0.4, step=6)
    d.edges(foot, w=1.7, over=1.5)
    spindle = rect_pts(45, 12, 6, 82)
    d.ko(spindle)
    d.wash(spindle, BRASS, op=0.7, amp=0.2, step=8, glaze=False)
    d.line((45, 12), (45, 94), w=1.5, over=0)
    d.line((51, 12), (51, 94), w=1.5, over=0)
    d.disc(48, 10, 5.5, fill=BRASS, op=0.78, lw=1.4, shade=False)
    collar = rect_pts(40, 66, 16, 9)
    d.ko(collar)
    d.wash(collar, BRASS, op=0.72, amp=0.2, step=5, glaze=False)
    d.edges(collar, w=1.3, over=0.8)
    return d


def governor_arms():
    """Both arms and their balls, symmetric about the spindle, so flipping the image
    in X (css scaleX 1 -> -1 -> 1) reads as the governor turning."""
    d = Drawing(96, 104, seed=76)
    for sx in (-1, 1):
        top = (48 + sx * 3, 18)
        ball = (48 + sx * 33, 50)
        d.pen([top, ball], w=2.2, amp=0.2, taper=0.8)
        d.pen([(48 + sx * 6, 70), (48 + sx * 22, 40)], w=1.6, amp=0.2, taper=0.8)
        d.disc(ball[0], ball[1], 11.5, fill=BRASS, op=0.74, lw=1.9)
        d.glint(arc_pts(ball[0], ball[1], 6.6, 6.6, 200, 255, 4), w=1.8, opacity=0.75)
    return d


def valve_glow():
    d = Drawing(84, 110, seed=77)
    d.raw('<defs><radialGradient id="g" cx="0.5" cy="0.52" r="0.5"><stop offset="0" stop-color="#ffe7a8" stop-opacity="0.78"/>'
          '<stop offset="0.2" stop-color="#f6b045" stop-opacity="0.5"/>'
          '<stop offset="0.55" stop-color="%s" stop-opacity="0.2"/>'
          '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient></defs>' % (EMBER, EMBER))
    d.raw('<ellipse cx="42" cy="55" rx="42" ry="55" fill="url(#g)"/>')
    return d


# ---- the big wheel out to the right ---------------------------------------------------------

def flywheel():
    R = 118
    size = R * 2 + 10
    c = size / 2.0
    d = Drawing(size, size, seed=81)
    rim = circle_pts(c, c, R, 60)
    d.ko(rim)
    d.wash(rim, PAYNE, op=0.5, amp=1.0)
    d.wash(d.crescent(c, c, R, depth=0.2), PAYNE, op=0.24, edge=0, amp=0.8)
    hole = circle_pts(c, c, R - 20, 50)
    d.ko(hole)
    d.hatch(annulus_sector(c, c, R - 17, R - 3, -10, 110, 16), gap=4.0, w=0.65, trim=0.25)
    for i in range(6):
        a = math.radians(i * 60 + 12)
        a_l, a_r = a - 0.045, a + 0.045
        spoke = [(c + 14 * math.cos(a - 0.5), c + 14 * math.sin(a - 0.5)), (c + (R - 18) * math.cos(a_l), c + (R - 18) * math.sin(a_l)),
                 (c + (R - 18) * math.cos(a_r), c + (R - 18) * math.sin(a_r)), (c + 14 * math.cos(a + 0.5), c + 14 * math.sin(a + 0.5))]
        d.ko(spoke)
        d.wash(spoke, PAYNE, op=0.5, amp=0.4, step=10, glaze=False)
        d.pen([spoke[0], spoke[1]], w=1.7, amp=0.4)
        d.pen([spoke[3], spoke[2]], w=1.7, amp=0.4)
    d.circle(c, c, R, w=2.6)
    d.circle(c, c, R - 20, w=1.9)
    d.disc(c, c, 24, fill=BRASS, op=0.7, lw=2.1)
    d.disc(c, c, 8, fill=PAYNE, op=0.7, lw=1.4, shade=False)
    # one painted spoke-end so the turning is visible
    a = math.radians(12)
    d.disc(c + (R - 10) * math.cos(a), c + (R - 10) * math.sin(a), 5.5, fill=MADDER, op=0.8, lw=1.2, shade=False)
    return d


# ---- carriage bell ---------------------------------------------------------------------------

def bell():
    """Hangs from its top-centre, which is where CSS swings it from."""
    d = Drawing(56, 62, seed=85)
    d.pen([(28, 0), (28, 12)], w=1.8, amp=0.2)
    dome = arc_pts(28, 40, 22, 28, 180, 360, 14)
    d.ko(dome)
    d.wash(dome, BRASS, op=0.72, amp=0.6, step=8)
    d.wash(arc_pts(28, 40, 22, 28, 290, 360, 6) + [(34, 40), (36, 22)], PAYNE, op=0.24, edge=0, amp=0.4, glaze=False)
    d.hatch(arc_pts(28, 40, 20, 25, 300, 360, 5) + [(38, 40), (40, 26)], gap=3.0, w=0.6, trim=0.25)
    d.pen(dome, w=1.9, amp=0.4)
    d.pen([(3, 40), (53, 40)], w=2.0, amp=0.3, over=1)
    d.glint(arc_pts(28, 40, 15, 20, 200, 245, 5), w=2.2, opacity=0.7)
    d.disc(28, 47, 4.4, fill=PAYNE, op=0.8, lw=1.2, shade=False)
    return d


# ---- tambour shutter over the pre-selectors ----------------------------------------------------

def shutter(w=388, h=600):
    d = Drawing(w, h, seed=88)
    body = rect_pts(0, 0, w, h)
    d.ko(body)
    d.wash(body, SIENNA, op=0.6, amp=1.0, step=30)
    slat = 20.0
    y = slat
    i = 0
    while y < h - 34:
        d.pen([(2, y), (w - 2, y)], w=1.5, amp=0.7, step=22, taper=0.8)
        d.pen([(4, y + 3.2), (w - 4, y + 3.2)], w=0.6, amp=0.6, step=26, opacity=0.5)
        if i % 3 == 1:
            x0 = d.rnd.uniform(20, w * 0.6)
            d.pen([(x0, y - slat * 0.5), (x0 + d.rnd.uniform(40, 120), y - slat * 0.5 + d.rnd.uniform(-1.5, 1.5))], w=0.6, amp=0.8, opacity=0.4)
        y += slat
        i += 1
    d.wash(rect_pts(w * 0.6, 0, w * 0.4, h), PAYNE, op=0.1, edge=0, amp=2, step=40, glaze=False)
    bar = rect_pts(0, h - 32, w, 32)
    d.ko(bar)
    d.wash(bar, UMBER, op=0.66, amp=0.6, step=20)
    d.edges(bar, w=2.0, over=0)
    # finger-pull and a padlock
    pull = round_rect_pts(w / 2.0 - 46, h - 23, 92, 14, 6)
    d.ko(pull)
    d.wash(pull, BRASS, op=0.7, amp=0.3, step=8)
    d.outline(pull, w=1.5)
    lx, ly = w - 54, h - 30
    d.pen(arc_pts(lx, ly, 9, 11, 180, 360, 8), w=2.6, amp=0.2, taper=0.8)
    lock = round_rect_pts(lx - 13, ly, 26, 22, 4)
    d.ko(lock)
    d.wash(lock, BRASS, op=0.74, amp=0.3, step=6)
    d.outline(lock, w=1.6)
    d.dot(lx, ly + 9, 2.2)
    d.pen([(lx, ly + 10), (lx, ly + 16)], w=1.6, amp=0.1)
    d.edges(body, w=2.0, over=0)
    return d


def crank():
    """Turns about its centre."""
    d = Drawing(84, 84, seed=91)
    c = 42
    arm = [(c - 6, c - 5), (c + 26, c - 22), (c + 30, c - 13), (c - 2, c + 6)]
    d.ko(arm)
    d.wash(arm, PAYNE, op=0.58, amp=0.4, step=8)
    d.edges(arm, w=1.8, over=1)
    d.disc(c, c, 8.5, fill=BRASS, op=0.76, lw=1.7)
    d.dot(c, c, 1.8)
    d.disc(c + 28, c - 18, 10.5, fill=MADDER, op=0.78, lw=1.9)
    d.glint(arc_pts(c + 28, c - 18, 6, 6, 200, 255, 4), w=1.8, opacity=0.75)
    return d


def regulator_knob():
    """Thumb of the wordage regulator: a pointer below, a grip above."""
    d = Drawing(30, 46, seed=93)
    stem = [(12, 16), (18, 16), (16.5, 40), (13.5, 40)]
    d.ko(stem)
    d.wash(stem, BRASS, op=0.76, amp=0.2, step=6, glaze=False)
    d.pen([(12, 16), (13.5, 40)], w=1.4, amp=0.15)
    d.pen([(18, 16), (16.5, 40)], w=1.4, amp=0.15)
    d.pen([(13.5, 40), (15, 45), (16.5, 40)], w=1.2, amp=0.1)
    d.disc(15, 11, 9.5, fill=MADDER, op=0.8, lw=1.8)
    d.glint(arc_pts(15, 11, 5.4, 5.4, 200, 255, 4), w=1.6, opacity=0.75)
    return d


# ---- plaques (buttons) ---------------------------------------------------------------------------

def plaque(w, h=34, fill=BRASS):
    d = Drawing(w, h, seed=100 + w)
    outer = round_rect_pts(1.5, 1.5, w - 3, h - 5, 5)
    d.wash(shift_pts(outer, 1.5, 3), INK, op=0.32, edge=0, amp=0.5, glaze=False)
    d.ko(outer)
    d.wash(outer, fill, op=0.7, amp=0.7, grow=-0.6)
    d.wash([(w * 0.55, 2), (w - 2, 2), (w - 2, h - 4), (2, h - 4), (2, h * 0.62), (w * 0.55, h * 0.62)], PAYNE, op=0.14, edge=0, amp=0.6, glaze=False)
    d.outline(outer, w=1.9)
    inner = round_rect_pts(5, 5, w - 10, h - 12, 3)
    d.outline(inner, w=0.8, opacity=0.7)
    d.screw(9.5, (h - 3) / 2.0, 1.9)
    d.screw(w - 9.5, (h - 3) / 2.0, 1.9)
    return d


def stop_button():
    d = Drawing(50, 50, seed=110)
    c = 25
    d.wash(circle_pts(c + 2, c + 3, 21, 16), INK, op=0.3, edge=0, amp=0.5, glaze=False)
    d.disc(c, c, 22, fill=BRASS, op=0.68, lw=1.8)
    d.disc(c, c, 16, fill=MADDER, op=0.85, lw=1.9)
    d.hatch(annulus_sector(c, c, 9, 15, 0, 100, 8), gap=2.8, w=0.6, trim=0.25)
    d.glint(arc_pts(c, c, 10, 10, 200, 255, 5), w=2.4, opacity=0.75)
    return d


# ---- ear-trumpet (sound) ----------------------------------------------------------------------------

def horn():
    d = Drawing(112, 106, seed=120)
    # stem up from the stand, an elbow, and a flaring horn opening to the upper left
    d.pipe([(58, 106), (58, 74), (70, 62)], r=5.5, fill=BRASS, op=0.7, hatch=False, bend=8)
    body = [(74, 66), (60, 52), (18, 46), (10, 4), (58, 22), (84, 56)]
    flare = spline([(74, 66), (58, 56), (32, 52), (17, 47)]) + spline([(11, 5), (38, 10), (64, 28), (84, 56)])
    d.ko(flare)
    d.wash(flare, BRASS, op=0.7, amp=0.8)
    d.wash(spline([(74, 66), (58, 56), (32, 52), (17, 47)]) + [(22, 36), (50, 44), (72, 58)], PAYNE, op=0.26, edge=0, amp=0.5, glaze=False)
    d.hatch(spline([(72, 64), (56, 55), (34, 51), (20, 46)]) + [(26, 38), (50, 45), (70, 57)], gap=3.0, w=0.6, trim=0.25)
    d.pen(spline([(74, 66), (58, 56), (32, 52), (17, 47)]), w=2.0, amp=0.4)
    d.pen(spline([(11, 5), (38, 10), (64, 28), (84, 56)]), w=2.0, amp=0.4)
    # the mouth of the horn: an ellipse seen at an angle
    mouth = rotate_pts(ellipse_pts(14, 26, 8.5, 22, 18), -8, 14, 26)
    d.ko(mouth)
    d.wash(mouth, INK, op=0.72, amp=0.3, step=6, glaze=False)
    d.outline(mouth, w=1.9, overlap=4)
    d.glint(spline([(30, 14), (48, 22), (62, 34)]), w=2.2, opacity=0.6)
    d.pen([(74, 66), (84, 56)], w=1.8, amp=0.2)
    return d


def horn_bung():
    """A cork on a string: what the ear-trumpet gets when the sound is off."""
    d = Drawing(112, 106, seed=121)
    cork = rotate_pts([(4, 14), (17, 12), (20, 38), (7, 40)], -8, 12, 26)
    d.ko(cork)
    d.wash(cork, SIENNA, op=0.8, amp=0.3, step=6)
    d.edges(cork, w=1.7, over=0.8)
    for k in range(3):
        d.dot(8 + k * 3.5, 20 + k * 6, 0.8)
    d.pen(spline([(16, 40), (22, 62), (40, 70), (58, 84)]), w=1.0, amp=0.6)
    return d


# ---- small things ---------------------------------------------------------------------------------

def hammer():
    """The write-head: a type slug on its bar, striking at the end of the text."""
    d = Drawing(16, 26, seed=130)
    d.pen([(8, 26), (8, 10)], w=2.0, amp=0.15, taper=0.8)
    slug = rect_pts(2.5, 1.5, 11, 10)
    d.ko(slug)
    d.wash(slug, PAYNE, op=0.7, amp=0.15, step=5, glaze=False)
    d.edges(slug, w=1.3, over=0.6)
    return d


def puff():
    d = Drawing(90, 70, seed=133)
    cloud = spline([(12, 52), (8, 38), (20, 28), (28, 14), (46, 10), (58, 20), (74, 22), (82, 38), (74, 54), (52, 60), (30, 58)], closed=True)
    d.ko(cloud, PAPER_LIGHT)
    d.wash(cloud, PAYNE, op=0.16, amp=1.0, step=10, glaze=False)
    d.pen(cloud + cloud[:3], w=1.4, amp=0.6, opacity=0.75)
    d.pen(spline([(30, 40), (38, 32), (48, 36)]), w=1.0, amp=0.3, opacity=0.6)
    d.pen(spline([(52, 46), (60, 40), (68, 44)]), w=1.0, amp=0.3, opacity=0.6)
    return d


SIGHT_TUBE = (12, 16, 16, 168)      # x, y, w, h of the glass in sight-glass.svg


def sight_glass():
    """The glass and its fittings only; the coloured fluid is a plain element behind."""
    d = Drawing(40, 200, seed=140)
    x, y, w, h = SIGHT_TUBE
    d.line((x, y), (x, y + h), w=1.6, over=0)
    d.line((x + w, y), (x + w, y + h), w=1.6, over=0)
    d.glint([(x + 3.5, y + 8), (x + 3.5, y + h - 10)], w=2.0, opacity=0.6)
    for cy in (y - 12, y + h):
        cap = round_rect_pts(x - 6, cy, w + 12, 12, 3)
        d.ko(cap)
        d.wash(cap, BRASS, op=0.74, amp=0.3, step=6)
        d.outline(cap, w=1.5)
    for i in range(11):
        ty = y + h - h * i / 10.0
        d.pen([(x + w + 3, ty), (x + w + (10 if i % 5 == 0 else 6), ty)], w=1.2 if i % 5 == 0 else 0.8, amp=0.05, taper=0.7)
    return d


def piston():
    d = Drawing(18, 30, seed=145)
    d.pen([(9, 30), (9, 8)], w=2.4, amp=0.1, taper=0.9)
    cap = round_rect_pts(1.5, 1.5, 15, 8, 2.5)
    d.ko(cap)
    d.wash(cap, MADDER, op=0.8, amp=0.2, step=5, glaze=False)
    d.outline(cap, w=1.3, overlap=3)
    return d


def card():
    """The operator's card, pinned up."""
    d = Drawing(214, 92, seed=150)
    sheet = [(4, 8), (208, 5), (210, 84), (6, 88)]
    d.wash(shift_pts(sheet, 3, 4), INK, op=0.26, edge=0, amp=0.6, glaze=False)
    d.ko(sheet, PAPER_LIGHT)
    d.wash([(120, 6), (208, 5), (210, 84), (6, 88), (6, 70), (120, 66)], PAYNE, op=0.08, edge=0, amp=1.0, glaze=False)
    d.edges(sheet, w=1.6, over=1.5)
    d.pen([(14, 36), (200, 34)], w=0.7, amp=0.5, opacity=0.6)
    d.pen([(14, 60), (200, 58)], w=0.7, amp=0.5, opacity=0.6)
    d.disc(107, 9, 5.5, fill=MADDER, op=0.85, lw=1.3, shade=False)
    d.glint(arc_pts(107, 9, 3, 3, 200, 255, 3), w=1.2, opacity=0.8)
    return d


def tag(w=92, h=28):
    """A paper luggage-tag: used for the small tear-off buttons."""
    d = Drawing(w, h, seed=155 + w)
    body = [(12, 2), (w - 2, 2), (w - 2, h - 3), (12, h - 3), (2, h / 2.0)]
    d.wash(shift_pts(body, 1.5, 2.5), INK, op=0.26, edge=0, amp=0.4, glaze=False)
    d.ko(body, PAPER_LIGHT)
    d.wash([(w * 0.5, 2), (w - 2, 2), (w - 2, h - 3), (12, h - 3), (w * 0.5, h * 0.6)], PAYNE, op=0.1, edge=0, amp=0.4, glaze=False)
    d.outline(body, w=1.5, overlap=4)
    d.circle(11.5, h / 2.0, 2.4, w=1.0)
    return d



# ---- the title page and the boot screen -----------------------------------------------------------

def valve():
    """One valve on its own, for the row that warms up on the boot screen."""
    from .plates import thermionic_valve
    d = Drawing(56, 84, seed=160)
    thermionic_valve(d, 28, 46)
    return d


def engine_gemini():
    """The standard engine: twins. Two upright cylinders working one beam."""
    d = Drawing(210, 128, seed=170)
    bed = [(14, 108), (196, 108), (202, 124), (8, 124)]
    d.ko(bed)
    d.wash(bed, PAYNE, op=0.5, amp=0.6)
    d.hatch([(110, 111), (198, 111), (201, 123), (104, 123)], gap=3.4, w=0.6, fade="a")
    d.edges(bed, w=2.0, over=2.5)
    for x in (26, 70, 140, 184):
        d.rivet(x, 116, 2.0)
    # centre column carrying the beam
    col = [(98, 108), (112, 108), (109, 42), (101, 42)]
    d.ko(col)
    d.wash(col, PAYNE, op=0.48, amp=0.4, step=10)
    d.edges(col, w=1.7, over=1.5)
    # the twins
    for cx in (52, 158):
        cyl = rect_pts(cx - 20, 62, 40, 46)
        cap = arc_pts(cx, 62, 20, 9, 180, 360, 8)
        d.ko(cap + [(cx + 20, 108), (cx - 20, 108)])
        d.wash(cap + [(cx + 20, 108), (cx - 20, 108)], VERDIGRIS, op=0.56, amp=0.7)
        d.wash(rect_pts(cx + 8, 60, 12, 48), PAYNE, op=0.24, edge=0, amp=0.3, glaze=False)
        d.hatch(rect_pts(cx + 9, 64, 10, 42), gap=3.2, w=0.6, trim=0.2)
        d.pen(cap, w=1.9, amp=0.3)
        d.line((cx - 20, 62), (cx - 20, 108), w=1.9, over=1)
        d.line((cx + 20, 62), (cx + 20, 108), w=1.9, over=1)
        for by in (70, 96):
            band = rect_pts(cx - 22, by, 44, 6)
            d.ko(band)
            d.wash(band, BRASS, op=0.7, amp=0.2, step=8, glaze=False)
            d.edges(band, w=1.2, over=0.8)
        d.glint([(cx - 14, 66), (cx - 14, 100)], w=1.8, opacity=0.5)
    # piston rods up to the rocking beam, which is caught mid-stroke
    beam = rotate_pts([(24, 32), (186, 32), (186, 42), (24, 42)], -7, 105, 37)
    d.pen([(52, 56), (48, 40)], w=2.2, amp=0.2, taper=0.8)
    d.pen([(158, 56), (160, 28)], w=2.2, amp=0.2, taper=0.8)
    d.ko(beam)
    d.wash(beam, BRASS, op=0.68, amp=0.5)
    d.edges(beam, w=1.9, over=1.5)
    d.disc(105, 37, 7, fill=PAYNE, op=0.7, lw=1.5, shade=False)
    for bx, by in ((36, 45), (174, 29)):
        d.disc(bx, by, 4, fill=BRASS, op=0.8, lw=1.2, shade=False)
    # a puff from each, taking turns
    d.pen(spline([(46, 18), (40, 10), (48, 4)]), w=1.2, amp=0.4, opacity=0.7)
    d.pen(spline([(166, 12), (174, 6), (168, 0)]), w=1.2, amp=0.4, opacity=0.7)
    return d


def engine_groq():
    """The fast engine: a turbine, leaning into it, trailing speed-lines."""
    d = Drawing(210, 128, seed=175)
    for sx in (60, 148):
        leg = [(sx - 10, 92), (sx + 10, 92), (sx + 18, 124), (sx - 18, 124)]
        d.ko(leg)
        d.wash(leg, PAYNE, op=0.5, amp=0.4, step=8)
        d.edges(leg, w=1.8, over=1.5)
    d.pen([(24, 124), (190, 124)], w=2.2, amp=0.5, over=3)
    # barrel
    barrel = [(46, 40), (150, 46), (150, 90), (46, 96)]
    d.ko(barrel)
    d.wash(barrel, MADDER, op=0.62, amp=0.9)
    d.wash([(46, 76), (150, 74), (150, 90), (46, 96)], PAYNE, op=0.26, edge=0, amp=0.5, glaze=False)
    d.hatch([(48, 80), (148, 77), (148, 89), (48, 94)], gap=3.4, w=0.6, trim=0.25)
    d.edges(barrel, w=2.0, over=2)
    for bx in (70, 98, 126):
        d.pen([(bx, 42 + (bx - 46) * 0.058), (bx, 95 - (bx - 46) * 0.058)], w=1.3, amp=0.3)
    d.glint([(54, 48), (140, 52)], w=2.0, opacity=0.45)
    # intake: a flared mouth with the fan showing
    mouth = ellipse_pts(42, 68, 13, 34, 20)
    d.ko(mouth)
    d.wash(mouth, BRASS, op=0.7, amp=0.5, step=8)
    d.outline(mouth, w=2.0, overlap=5)
    inner = ellipse_pts(42, 68, 8.5, 26, 16)
    d.ko(inner)
    d.wash(inner, INK, op=0.7, amp=0.3, step=6, glaze=False)
    d.outline(inner, w=1.3, overlap=4)
    for a in (20, 80, 140, 200, 260, 320):
        ra = math.radians(a)
        d.pen([(42, 68), (42 + 8 * math.cos(ra), 68 + 25 * math.sin(ra))], w=1.1, amp=0.1, color=PAPER_LIGHT, opacity=0.9)
    # exhaust cone and what comes out of it
    cone = [(150, 50), (176, 60), (176, 76), (150, 86)]
    d.ko(cone)
    d.wash(cone, BRASS, op=0.7, amp=0.4, step=8)
    d.edges(cone, w=1.8, over=1.5)
    for i, (y, length) in enumerate(((58, 26), (64, 34), (70, 30), (76, 22), (52, 14), (84, 12))):
        d.pen([(180 + (i % 2) * 3, y), (180 + length, y + (y - 68) * 0.14)], w=1.5 if i < 3 else 1.0, amp=0.4, taper=0.2, opacity=0.8)
    # a governor it has long since outrun
    d.pen([(98, 44), (98, 24)], w=1.8, amp=0.2)
    for sx in (-1, 1):
        d.pen([(98, 26), (98 + sx * 16, 30)], w=1.3, amp=0.2)
        d.disc(98 + sx * 18, 31, 4.6, fill=BRASS, op=0.8, lw=1.2, shade=False)
    return d


FLESH = "#dba77c"      # a face, a hand
CORDUROY = "#a8672e"   # a pair of trousers


def engine_openai():
    """The talkative engine: a horn gramophone, and the parrot it learned from."""
    d = Drawing(210, 128, seed=190)
    d.pen([(8, 124), (204, 124)], w=2.2, amp=0.5, over=3)

    # the parrot's stand
    foot = [(18, 124), (42, 124), (37, 117), (23, 117)]
    d.ko(foot)
    d.wash(foot, PAYNE, op=0.5, amp=0.3, step=6, glaze=False)
    d.edges(foot, w=1.5, over=1)
    d.pen([(30, 117), (30, 71)], w=2.4, amp=0.3, taper=0.8)
    d.pen([(14, 71), (47, 71)], w=2.8, amp=0.3, taper=0.7, over=1.5)

    # the parrot: tail first (it hangs behind the bar), then body, wing, head
    for i, (tx, ty) in enumerate(((17, 97), (21, 101), (25, 98))):
        feather = [(24 + i * 2, 62), (28 + i * 2, 64), (tx + 3, ty), (tx, ty - 1)]
        d.ko(feather)
        d.wash(feather, (MADDER, VERDIGRIS, MADDER)[i], op=0.72, amp=0.3, step=6, glaze=False)
        d.edges(feather, w=1.1, over=0.6, amp=0.2)
    body = rotate_pts(ellipse_pts(31, 51, 10.5, 16.5, 18), 10, 31, 51)
    d.ko(body)
    d.wash(body, MADDER, op=0.72, amp=0.5, step=7)
    d.outline(body, w=1.7, overlap=4)
    wing = rotate_pts(ellipse_pts(26.5, 54, 5.5, 12.5, 14), 14, 26.5, 54)
    d.ko(wing)
    d.wash(wing, VERDIGRIS, op=0.75, amp=0.3, step=6, glaze=False)
    d.outline(wing, w=1.2, overlap=3)
    for wy in (50, 55, 60):
        d.pen([(22.5, wy), (26, wy + 2.5), (29.5, wy)], w=0.8, amp=0.1)
    head = circle_pts(36, 32, 8.6, 14)
    d.ko(head)
    d.wash(head, MADDER, op=0.72, amp=0.3, step=6, glaze=False)
    d.circle(36, 32, 8.6, w=1.6)
    cheek = circle_pts(38.5, 32, 3.6, 9)                 # the bare white patch round the eye
    d.ko(cheek, PAPER_LIGHT)
    d.circle(38.5, 32, 3.6, w=0.8)
    d.dot(39, 31.6, 1.3)
    beak = spline([(43, 27), (50, 28.5), (52, 34), (48.5, 39), (46.5, 35), (43.5, 36)], closed=True)
    d.ko(beak)
    d.wash(beak, BRASS_LIGHT, op=0.85, amp=0.2, step=4, glaze=False)
    d.pen(beak + beak[:2], w=1.3, amp=0.15)
    d.pen([(44, 32.5), (50.5, 32)], w=0.8, amp=0.1)       # beak ajar: it is saying something
    for fx in (28, 34):                                    # feet round the bar
        d.pen([(fx, 66), (fx - 1, 71), (fx + 2, 72.5)], w=1.3, amp=0.15)
    d.pen([(30, 20), (33, 23.5)], w=1.0, amp=0.1)          # crest
    d.pen([(34, 18.5), (35.5, 23)], w=1.0, amp=0.1)
    d.pen([(38.5, 19), (38, 23.3)], w=1.0, amp=0.1)

    # the cabinet
    for fx in (76, 138):
        d.pen([(fx, 117), (fx, 124)], w=3.0, amp=0.1, taper=0.9)
    box = rect_pts(68, 90, 78, 28)
    d.ko(box)
    d.wash(box, SIENNA, op=0.66, amp=0.7)
    d.wash(rect_pts(116, 90, 30, 28), PAYNE, op=0.2, edge=0, amp=0.3, glaze=False)
    d.hatch(rect_pts(120, 93, 24, 23), gap=3.2, w=0.6, trim=0.25)
    d.edges(box, w=2.0, over=2)
    d.pen([(68, 96), (146, 96)], w=1.1, amp=0.3)
    grille = round_rect_pts(78, 101, 30, 12, 3)
    d.ko(grille)
    d.wash(grille, INK, op=0.55, amp=0.2, step=6, glaze=False)
    d.outline(grille, w=1.2, overlap=3)
    for gx in (84, 90, 96, 102):
        d.pen([(gx, 102), (gx, 112)], w=0.8, amp=0.1, color=PAPER_LIGHT, opacity=0.8)
    # its crank
    d.pen([(68, 106), (57, 106), (57, 97)], w=2.0, amp=0.2, taper=0.8)
    d.disc(57, 95, 3.4, fill=UMBER, op=0.8, lw=1.2, shade=False)

    # turntable and record
    plat = ellipse_pts(100, 88, 31, 5.5, 22)
    d.ko(plat)
    d.wash(plat, INK, op=0.72, amp=0.3, step=8, glaze=False)
    d.outline(plat, w=1.6, overlap=4)
    d.arc(100, 88, 22, 3.6, 200, 340, w=0.7, color=PAPER_LIGHT, opacity=0.6)
    label = ellipse_pts(100, 88, 8, 1.8, 10)
    d.wash(label, MADDER, op=0.9, amp=0.1, step=4, glaze=False, edge=0)

    # the horn: a neck up from the tone-arm, flaring to a mouth that faces up and out
    mouth = rotate_pts(ellipse_pts(163, 41, 31, 11, 24), 62, 163, 41)
    top = (148.5, 13.6)
    bottom = (177.5, 68.4)
    flare = spline([(116, 86), (122, 70), (132, 46), top]) + spline([bottom, (146, 72), (130, 84), (122, 89)])
    d.ko(flare)
    d.wash(flare, BRASS, op=0.7, amp=0.8)
    d.wash(spline([(124, 88), (140, 76), bottom, (160, 58), (136, 70)], closed=True), PAYNE, op=0.2, edge=0, amp=0.5)
    d.hatch(spline([(128, 86), (146, 74), (170, 64), (150, 66), (134, 76)], closed=True), gap=3.0, w=0.6, trim=0.25)
    d.pen(spline([(116, 86), (122, 70), (132, 46), top]), w=1.9, amp=0.4)
    d.pen(spline([bottom, (146, 72), (130, 84), (122, 89)]), w=1.9, amp=0.4)
    for t in (0.36, 0.62):                                  # the seams where its petals join
        d.pen([(120 + 6 * t, 87 - 6 * t), (150 + 16 * t, 28 + 36 * t)], w=0.8, amp=0.3, opacity=0.7)
    d.ko(mouth)
    d.wash(mouth, BRASS_LIGHT, op=0.7, amp=0.5, step=8)
    d.outline(mouth, w=2.0, overlap=5)
    throat = rotate_pts(ellipse_pts(160, 43, 19, 5.5, 16), 62, 160, 43)
    d.ko(throat)
    d.wash(throat, INK, op=0.66, amp=0.3, step=6, glaze=False)
    d.outline(throat, w=1.2, overlap=4)
    d.glint([(127, 62), (136, 42), (146, 24)], w=2.0, opacity=0.55)
    # the tone-arm's elbow, down onto the record
    d.pen([(119, 87), (112, 82), (108, 87)], w=2.6, amp=0.2, taper=0.8)
    d.disc(108, 87, 2.6, fill=BRASS, op=0.85, lw=1.1, shade=False)

    # and what comes out of it
    for r, a0, a1, w in ((23, -56, 0, 1.5), (31, -51, -5, 1.25), (39, -46, -10, 1.0)):
        d.arc(163, 41, r, r, a0, a1, w=w, opacity=0.8)
    return d


def engine_claude():
    """The thoughtful engine. A gentleman in corduroy trousers smokes a pipe; the smoke
    is caught in a hood and turns the wheel that does the writing."""
    d = Drawing(210, 128, seed=195)
    d.pen([(6, 124), (204, 124)], w=2.2, amp=0.5, over=3)

    # ---- the armchair (behind him) -----------------------------------------------
    for lx in (26, 70):
        d.pen([(lx, 104), (lx - 1.5, 124)], w=3.2, amp=0.1, taper=0.85, color=UMBER)
        d.pen([(lx - 2, 104), (lx - 3.5, 124)], w=0.9, amp=0.1)
        d.pen([(lx + 2, 104), (lx + 0.5, 124)], w=0.9, amp=0.1)
    back = spline([(22, 104), (15, 70), (17, 40), (27, 30), (37, 36), (41, 62), (42, 104)], closed=False)
    back = back + [(22, 104)]
    d.ko(back)
    d.wash(back, VERDIGRIS, op=0.62, amp=0.8)
    d.pen(back[:-1], w=1.9, amp=0.5)
    for by in (48, 62, 76):                                 # buttoned leather
        d.dot(27, by, 1.2)
    seat = [(20, 88), (78, 88), (80, 104), (20, 104)]
    d.ko(seat)
    d.wash(seat, VERDIGRIS, op=0.62, amp=0.6)
    d.wash([(46, 96), (80, 96), (80, 104), (40, 104)], PAYNE, op=0.2, edge=0, amp=0.3, glaze=False)
    d.hatch([(48, 97), (79, 97), (79, 103), (44, 103)], gap=2.8, w=0.6, trim=0.25)
    d.edges(seat, w=1.8, over=1.5)

    # ---- the gentleman ---------------------------------------------------------------
    # far leg: only the shin and shoe show, a little ahead of the near one
    far_shin = [(104, 88), (116, 90), (117, 115), (106, 115)]
    d.ko(far_shin)
    d.wash(far_shin, CORDUROY, op=0.78, amp=0.3, step=7, glaze=False)
    d.wash(far_shin, PAYNE, op=0.2, edge=0, amp=0.2, glaze=False)
    d.hatch(far_shin, angle=88, gap=2.5, w=0.65, trim=0.06, skip=0, jit=0.3, color=UMBER)
    d.edges(far_shin, w=1.4, over=0.8, amp=0.3)
    far_shoe = spline([(105, 115), (118, 114.5), (129, 118), (131, 123), (105, 123)], closed=True)
    d.ko(far_shoe)
    d.wash(far_shoe, UMBER, op=0.8, amp=0.2, step=5, glaze=False)
    d.pen(far_shoe + far_shoe[:2], w=1.3, amp=0.2)

    # jacket: leaning back into the chair
    jacket = spline([(40, 50), (47, 45), (60, 46), (68, 54), (72, 70), (71, 86), (60, 91), (40, 90), (37, 70)], closed=True)
    d.ko(jacket)
    d.wash(jacket, PAYNE, op=0.6, amp=0.7)
    d.hatch(spline([(40, 56), (52, 58), (60, 88), (41, 88)], closed=True), angle=-58, gap=3.0, w=0.55, trim=0.3)
    d.pen(jacket + jacket[:2], w=1.8, amp=0.4)
    d.pen([(61, 47), (66, 60), (64, 74)], w=1.0, amp=0.2)                    # lapel
    d.dot(67, 72, 1.0)
    d.dot(67.5, 79, 1.0)
    bow = [(60, 47.5), (66, 45), (65.5, 51), (60, 48.5), (55, 51), (54.5, 45)]
    d.wash(bow, MADDER, op=0.9, amp=0.1, step=3, glaze=False, edge=0)
    d.edges(bow, w=0.9, over=0.3, amp=0.1)

    # near leg, in corduroy: thigh along the seat, shin down to the floor.
    # The wales run the length of the leg, so they turn the corner at the knee.
    thigh = spline([(44, 78), (70, 76), (96, 78), (105, 82), (107, 89), (101, 94), (72, 96), (45, 97)], closed=True)
    shin = [(91, 90), (107, 87), (107, 116), (93, 116)]
    d.ko(shin)
    d.wash(shin, CORDUROY, op=0.78, amp=0.3, step=7, glaze=False)
    d.hatch(shin, angle=87, gap=2.5, w=0.7, trim=0.06, skip=0, jit=0.3, color=UMBER)
    d.ko(thigh)
    d.wash(thigh, CORDUROY, op=0.78, amp=0.5, step=8)
    d.hatch(thigh, angle=1, gap=2.5, w=0.7, trim=0.06, skip=0, jit=0.3, color=UMBER)
    # one line round the whole bent leg, left open under the knee where thigh becomes shin
    d.pen(spline([(93, 116), (91.5, 97), (72, 96), (45, 97), (41, 88), (44, 78), (70, 76), (96, 78), (105, 81.5), (107.5, 88)])
          + [(107.5, 116)], w=1.7, amp=0.3)
    d.pen([(101, 90), (105.5, 86.5)], w=0.9, amp=0.1)                        # the crease behind the knee
    d.pen([(91.5, 115.5), (108.5, 115.5)], w=1.6, amp=0.2)                   # turn-up
    d.pen([(92, 112), (108, 112)], w=0.9, amp=0.2)
    shoe = spline([(91, 116), (107, 115.5), (120, 119), (122, 123.5), (91, 123.5)], closed=True)
    d.ko(shoe)
    d.wash(shoe, UMBER, op=0.85, amp=0.2, step=5, glaze=False)
    d.pen(shoe + shoe[:2], w=1.5, amp=0.2)
    d.glint([(109, 118.5), (116, 120.5)], w=1.0, opacity=0.6)

    # head, in profile, facing the machine
    head = spline([(47, 36), (49, 27), (56, 22), (64, 24), (68, 29), (69, 33), (74, 37.5), (69.5, 39),
                   (70, 42), (68, 46), (61, 48), (54, 46), (49, 42)], closed=True)
    d.ko(head)
    d.wash(head, FLESH, op=0.7, amp=0.3, step=6, glaze=False)
    d.pen(head + head[:2], w=1.5, amp=0.2)
    hair = spline([(47, 36), (48, 29), (52, 25), (54, 31), (53, 38), (50, 42)], closed=True)   # what is left of it
    d.wash(hair, PAYNE, op=0.6, amp=0.2, step=4, glaze=False, edge=0)
    d.hatch(hair, angle=70, gap=1.8, w=0.6, trim=0.2)
    d.arc(56, 36, 2.2, 3.2, 60, 300, w=0.9)                                    # ear
    d.circle(65, 32.5, 3.1, w=0.9)                                             # spectacles
    d.pen([(62, 32), (57, 33.5)], w=0.7, amp=0.1)
    d.dot(65.4, 32.6, 0.9)
    d.pen([(62.5, 28), (67.5, 28.6)], w=1.1, amp=0.1)                          # eyebrow
    d.pen([(64.5, 40), (69, 40.5), (70.5, 42.5)], w=1.8, amp=0.15, taper=0.5)  # moustache

    # the pipe, and the hand that steadies it
    d.pen([(69, 42.5), (79, 46.5)], w=1.7, amp=0.1, taper=0.9, color=UMBER)
    d.pen([(69, 41.7), (79, 45.7)], w=0.6, amp=0.1)
    bowl = [(78.5, 40.5), (86.5, 40.5), (85.5, 49), (79.5, 49)]
    d.ko(bowl)
    d.wash(bowl, UMBER, op=0.85, amp=0.2, step=4, glaze=False)
    d.edges(bowl, w=1.2, over=0.5, amp=0.15)
    d.wash(ellipse_pts(82.5, 40.5, 3.2, 1.1, 8), EMBER, op=0.95, amp=0.1, step=3, glaze=False, edge=0)
    sleeve = [(52, 62), (62, 58), (80, 51), (84, 57), (66, 70), (56, 74)]
    d.ko(sleeve)
    d.wash(sleeve, PAYNE, op=0.62, amp=0.4, step=7)
    d.edges(sleeve, w=1.6, over=0.8, amp=0.3)
    hand = spline([(78, 50), (81, 46.5), (87, 47), (89, 51), (86, 55.5), (80.5, 55.5)], closed=True)
    d.ko(hand)
    d.wash(hand, FLESH, op=0.75, amp=0.15, step=4, glaze=False)
    d.pen(hand + hand[:2], w=1.1, amp=0.1)
    d.pen([(82.5, 49), (86.5, 49.5)], w=0.6, amp=0.05)                         # fingers
    d.pen([(82.5, 51.7), (87, 52.2)], w=0.6, amp=0.05)

    # ---- the works: hood, flue, wheel, and the cabinet that does the writing ------------
    cab = rect_pts(150, 84, 46, 40)
    d.ko(cab)
    d.wash(cab, SIENNA, op=0.66, amp=0.6)
    d.wash(rect_pts(178, 84, 18, 40), PAYNE, op=0.2, edge=0, amp=0.3, glaze=False)
    d.hatch(rect_pts(180, 87, 14, 35), gap=3.2, w=0.6, trim=0.25)
    d.edges(cab, w=1.9, over=2)
    d.pen([(150, 91), (196, 91)], w=1.1, amp=0.3)
    # a page coming out of its slot, towards him, already written on
    page = [(150, 95), (150, 107), (130, 119), (125, 108)]
    d.wash(shift_pts(page, 1.2, 2.0), INK, op=0.22, edge=0, amp=0.3, glaze=False)
    d.ko(page, PAPER_LIGHT)
    d.edges(page, w=1.1, over=0.6, amp=0.2)
    for k, (t0, t1) in enumerate(((0.12, 0.9), (0.12, 0.72), (0.12, 0.84))):
        off = 3.0 + k * 2.9
        a = (150 + (125 - 150) * t0, 95 + off + (108 - 95) * t0)
        b = (150 + (125 - 150) * t1, 95 + off + (108 - 95) * t1)
        d.pen([a, b], w=0.6, amp=0.5, wl=6, opacity=0.8)
    # the post and the wheel
    post = [(169, 84), (177, 84), (175.5, 60), (170.5, 60)]
    d.ko(post)
    d.wash(post, PAYNE, op=0.5, amp=0.3, step=7, glaze=False)
    d.edges(post, w=1.5, over=1)
    d.cog(173, 56, 19, 10, spokes=4, lw=1.5)
    # the flue down to it, and the hood that feeds the flue
    d.pipe([(122, 13), (122, 7), (173, 7), (173, 33)], r=3.6, bend=6, lw=1.4, hatch=False, flanges=(0.98,))
    hood = [(103, 30), (141, 30), (130, 13), (114, 13)]
    d.ko(hood)
    d.wash(hood, BRASS, op=0.7, amp=0.5, step=8)
    d.wash([(124, 13), (130, 13), (141, 30), (128, 30)], PAYNE, op=0.22, edge=0, amp=0.3, glaze=False)
    d.edges(hood, w=1.8, over=1.5)
    d.pen([(101, 31), (143, 31)], w=2.4, amp=0.2, taper=0.8)

    # ---- the smoke that drives it all -----------------------------------------------------
    drift = spline([(80, 39), (83, 30), (90, 24), (102, 25), (116, 27), (118, 33), (104, 35), (92, 34), (86, 39)], closed=True)
    d.wash(drift, PAYNE, op=0.16, amp=1.0, step=6, glaze=False, edge=0.1)
    d.pen(spline([(83, 38), (87, 32), (82, 27), (89, 22), (98, 25), (108, 30)]), w=1.3, amp=0.4, opacity=0.75)
    d.pen(spline([(85, 37), (93, 35), (96, 29), (107, 33), (116, 29)]), w=1.1, amp=0.4, opacity=0.7)
    d.circle(92, 17, 3.4, w=0.9, opacity=0.6, squash=0.7)                      # a smoke ring that got away
    d.circle(99, 11, 2.3, w=0.8, opacity=0.5, squash=0.7)
    return d


def key():
    d = Drawing(124, 46, seed=180)
    # bow: a ring with a heart cut in it
    d.disc(22, 23, 19, fill=BRASS, op=0.7, lw=2.0)
    hole = spline([(22, 31), (13, 22), (16, 15), (22, 19), (28, 15), (31, 22)], closed=True)
    d.ko(hole)
    d.pen(hole + hole[:2], w=1.3, amp=0.2)
    d.hatch(annulus_sector(22, 23, 13, 17.5, 0, 100, 8), gap=2.8, w=0.6)
    # collar and shaft
    for cx in (43, 49):
        coll = rect_pts(cx - 2, 15, 4.5, 16)
        d.ko(coll)
        d.wash(coll, BRASS, op=0.75, amp=0.2, step=5, glaze=False)
        d.edges(coll, w=1.2, over=0.6)
    shaft = rect_pts(51, 19.5, 62, 7)
    d.ko(shaft)
    d.wash(shaft, BRASS, op=0.7, amp=0.3, step=10)
    d.wash(rect_pts(51, 23.5, 62, 3), PAYNE, op=0.26, edge=0, amp=0.2, glaze=False)
    d.line((51, 19.5), (114, 19.5), w=1.6, over=1)
    d.line((51, 26.5), (114, 26.5), w=1.6, over=1)
    d.arc(113, 23, 4, 3.5, -90, 90, w=1.6)
    # bit, with its wards
    bit = [(88, 26.5), (110, 26.5), (110, 42), (104, 42), (104, 34), (99, 34), (99, 42), (94, 42), (94, 36), (88, 36)]
    d.ko(bit)
    d.wash(bit, BRASS, op=0.7, amp=0.3, step=6, glaze=False)
    d.edges(bit, w=1.5, over=0.6)
    d.glint([(54, 21.5), (86, 21.5)], w=1.2, opacity=0.6)
    return d


def flourish():
    """A pen flourish to rule off the title: two scrolls meeting at a diamond."""
    d = Drawing(380, 30, seed=185)
    for sx in (-1, 1):
        def P(x, y):
            return (190 + sx * x, y)
        d.curve([P(14, 15), P(52, 9), P(96, 18), P(136, 12), P(160, 15), P(170, 21), P(164, 26), P(157, 21), P(162, 15)], w=1.9, taper=0.25)
        d.curve([P(30, 19), P(70, 23), P(110, 14), P(142, 19)], w=1.1, taper=0.2)
        d.dot(190 + sx * 178, 15, 1.7)
    dia = [(190, 6), (199, 15), (190, 24), (181, 15)]
    d.wash(dia, MADDER, op=0.75, amp=0.3, step=5, glaze=False)
    d.edges(dia, w=1.5, over=0.8)
    return d


PARTS = {
    "lever-base": lever_base,
    "lever-arm": lever_arm,
    "stop-seat": stop_seat,
    "stop-shaft": stop_shaft,
    "stop-knob": stop_knob,
    "stop-shadow": stop_shadow,
    "jewel": jewel,
    "jewel-glow": jewel_glow,
    "drum": drum,
    "thumbwheel": thumbwheel,
    "gauge": gauge,
    "gauge-needle": gauge_needle,
    "gauge-glass": gauge_glass,
    "cog-a": lambda: cog(62, 16, spokes=5, seed=51),
    "cog-b": lambda: cog(40, 11, spokes=4, fill=VERDIGRIS, seed=52),
    "cog-c": lambda: cog(26, 8, spokes=0, seed=53),
    "whistle": whistle,
    "pedal": pedal,
    "governor-base": governor_base,
    "governor-arms": governor_arms,
    "valve-glow": valve_glow,
    "flywheel": flywheel,
    "bell": bell,
    "shutter": shutter,
    "crank": crank,
    "regulator-knob": regulator_knob,
    "plaque-96": lambda: plaque(96),
    "plaque-140": lambda: plaque(140),
    "plaque-196": lambda: plaque(196),
    "plaque-260": lambda: plaque(260, 44),
    "stop-button": stop_button,
    "horn": horn,
    "horn-bung": horn_bung,
    "hammer": hammer,
    "puff": puff,
    "sight-glass": sight_glass,
    "piston": piston,
    "card": card,
    "tag": tag,
    "valve": valve,
    "engine-gemini": engine_gemini,
    "engine-groq": engine_groq,
    "engine-openai": engine_openai,
    "engine-claude": engine_claude,
    "key": key,
    "flourish": flourish,
}
