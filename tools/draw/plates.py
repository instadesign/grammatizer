"""The big static drawings: one per screen.

The console plate is everything on the console that never moves: the workshop, the
cabinets, the pipework. Anything that moves, lights or repeats is a separate part
(parts.py) laid over it by css/console.css, using the positions in layout.py.
"""

import math

from . import layout as L
from .ink import (
    Drawing, PAPER, PAPER_LIGHT, INK, BRASS, BRASS_LIGHT, VERDIGRIS, EMBER, MADDER,
    PAYNE, SIENNA, UMBER, GOUACHE,
    rect_pts, arc_pts, circle_pts, ellipse_pts, round_rect_pts, annulus_sector,
    rotate_pts, shift_pts, scale_pts, spline,
)

COPPER = "#b5683c"
GINGER = "#c9843a"


# ---- small shared motifs -------------------------------------------------------------

def grain(d, x, y, w, h, n=5, vertical=False):
    """A few long wandering lines: wood grain."""
    for i in range(n):
        t = (i + d.rnd.uniform(0.25, 0.75)) / n
        if vertical:
            xx = x + w * t
            y0 = y + d.rnd.uniform(0.02, 0.3) * h
            y1 = y + h - d.rnd.uniform(0.02, 0.3) * h
            d.pen([(xx, y0), (xx + d.rnd.uniform(-2, 2), (y0 + y1) / 2), (xx + d.rnd.uniform(-1, 1), y1)], w=0.7, amp=1.4, opacity=0.5, wl=60)
        else:
            yy = y + h * t
            x0 = x + d.rnd.uniform(0.02, 0.3) * w
            x1 = x + w - d.rnd.uniform(0.02, 0.3) * w
            d.pen([(x0, yy), ((x0 + x1) / 2, yy + d.rnd.uniform(-2, 2)), (x1, yy + d.rnd.uniform(-1, 1))], w=0.7, amp=1.4, opacity=0.5, wl=60)


def rivets(d, x0, y0, x1, y1, n, r=2.2):
    for i in range(n):
        t = i / float(max(1, n - 1))
        d.rivet(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r)


def enamel_plate(d, x, y, w, h, screws=True):
    """A small cream label plate with a pen border; lettering is laid over in HTML."""
    pts = round_rect_pts(x, y, w, h, 3)
    d.ko(pts, PAPER_LIGHT)
    d.wash([(x + w * 0.5, y + h * 0.5), (x + w, y + h * 0.2), (x + w, y + h), (x, y + h), (x, y + h * 0.8)], PAYNE, op=0.1, edge=0, amp=0.5)
    d.outline(pts, w=1.5)
    if screws:
        d.screw(x + 6, y + h / 2.0, 1.8)
        d.screw(x + w - 6, y + h / 2.0, 1.8)


def window(d, x, y, w, h, pad=6):
    """A brass-framed window onto a paper card (status flag, odometer)."""
    outer = round_rect_pts(x, y, w, h, 6)
    d.ko(outer)
    d.wash(outer, BRASS, op=0.66, amp=0.8, grow=-0.6)
    d.outline(outer, w=1.9)
    inner = round_rect_pts(x + pad, y + pad, w - 2 * pad, h - 2 * pad, 3)
    d.ko(inner, PAPER_LIGHT)
    d.wash(rect_pts(x + pad, y + pad, w - 2 * pad, 5), PAYNE, op=0.3, edge=0, amp=0.4)
    d.hatch(rect_pts(x + pad + 1, y + pad + 0.5, w - 2 * pad - 2, 3.6), angle=0, gap=1.7, w=0.5, trim=0.15, skip=0.1)
    d.outline(inner, w=1.4)


def wooden_cabinet(d, x, y, w, h):
    d.box(x, y, w, h, fill=SIENNA, op=0.56, lw=2.6, over=4)
    grain(d, x + 4, y + 6, 8, h - 12, n=2, vertical=True)
    grain(d, x + w - 12, y + 6, 8, h - 12, n=2, vertical=True)
    # cornice
    cor = [(x - 9, y - 12), (x + w + 9, y - 12), (x + w + 4, y + 2), (x - 4, y + 2)]
    d.ko(cor)
    d.wash(cor, UMBER, op=0.6, amp=0.8)
    d.edges(cor, w=2.2, over=3)
    d.line((x - 6, y - 5), (x + w + 6, y - 5), w=1.0, over=0)


def thermionic_valve(d, cx, cy):
    """A glass valve on its brass base. The glow is a separate part laid on top."""
    base = [(cx - 13, cy + 18), (cx + 13, cy + 18), (cx + 11, cy + 31), (cx - 11, cy + 31)]
    d.ko(base)
    d.wash(base, BRASS, op=0.68, amp=0.4, step=6)
    d.edges(base, w=1.6, over=1)
    d.line((cx - 12, cy + 23), (cx + 12, cy + 23), w=0.9, over=0)
    glass = [(cx - 12, cy + 18), (cx - 14, cy - 2), (cx - 12, cy - 18), (cx - 5, cy - 27), (cx, cy - 30),
             (cx + 5, cy - 27), (cx + 12, cy - 18), (cx + 14, cy - 2), (cx + 12, cy + 18)]
    dense = spline(glass)
    d.ko(dense)
    d.wash(dense, PAYNE, op=0.2, amp=0.4, step=8, glaze=False)
    # the works inside: anode plate, grid, and a hairpin of filament
    plate = rect_pts(cx - 6, cy - 14, 12, 22)
    d.wash(plate, PAYNE, op=0.5, amp=0.3, step=6, edge=0.3, glaze=False)
    d.edges(plate, w=1.0, over=0.5)
    d.pen([(cx - 3, cy + 16), (cx - 2, cy - 8), (cx, cy - 11), (cx + 2, cy - 8), (cx + 3, cy + 16)], w=0.9, amp=0.2)
    for yy in (-9, -4, 1, 6):
        d.pen([(cx - 6, cy + yy), (cx + 6, cy + yy)], w=0.6, amp=0.1)
    d.pen(dense, w=1.7, amp=0.4)
    d.pen([(cx - 2, cy - 30), (cx, cy - 35), (cx + 2, cy - 30)], w=1.2, amp=0.1)
    d.glint([(cx - 9, cy - 14), (cx - 10.5, cy), (cx - 9.5, cy + 10)], w=1.8, opacity=0.75)


def kettle(d, x, y):
    """A copper kettle on a spirit burner, simmering. (x, y) is where it stands."""
    # burner
    burner = [(x - 20, y), (x + 20, y), (x + 15, y - 14), (x - 15, y - 14)]
    d.ko(burner)
    d.wash(burner, BRASS, op=0.66, amp=0.5, step=6)
    d.edges(burner, w=1.7, over=1.5)
    flame = spline([(x - 6, y - 14), (x - 7, y - 21), (x - 1, y - 28), (x + 1, y - 22), (x + 6, y - 25), (x + 6, y - 14)], closed=True)
    d.wash(flame, EMBER, op=0.8, amp=0.4, step=5, glaze=False)
    d.pen(flame + flame[:2], w=1.0, amp=0.2)
    # trivet legs
    for sx in (-30, 30):
        d.pen([(x + sx, y), (x + sx * 0.86, y - 30)], w=1.6, amp=0.4)
    d.pen([(x - 32, y - 30), (x + 32, y - 30)], w=1.8, amp=0.4, over=3)
    # body
    by = y - 30
    body = spline([(x - 34, by), (x - 38, by - 18), (x - 30, by - 40), (x - 12, by - 48), (x + 12, by - 48),
                   (x + 30, by - 40), (x + 38, by - 18), (x + 34, by)], closed=False)
    body = body + [(x - 34, by)]
    d.ko(body)
    d.wash(body, COPPER, op=0.7, amp=1.0)
    d.wash([(x + 6, by - 46), (x + 30, by - 40), (x + 38, by - 18), (x + 34, by), (x + 2, by), (x + 12, by - 22)], PAYNE, op=0.24, edge=0, amp=0.6)
    d.hatch([(x + 18, by - 38), (x + 31, by - 34), (x + 37, by - 16), (x + 33, by - 2), (x + 16, by - 2), (x + 23, by - 20)], gap=3.2, w=0.6, trim=0.25)
    d.pen(body, w=2.0, amp=0.5)
    d.glint([(x - 27, by - 30), (x - 30, by - 18), (x - 28, by - 8)], w=2.4, opacity=0.6)
    # lid and knob
    lid = [(x - 14, by - 47), (x + 14, by - 47), (x + 10, by - 55), (x - 10, by - 55)]
    d.ko(lid)
    d.wash(lid, COPPER, op=0.72, amp=0.4, step=6)
    d.edges(lid, w=1.6, over=1)
    d.disc(x, by - 60, 4.4, fill=UMBER, op=0.7, lw=1.3, shade=False)
    # handle
    d.pen(spline([(x - 24, by - 43), (x - 22, by - 70), (x, by - 82), (x + 22, by - 70), (x + 24, by - 43)]), w=2.8, amp=0.6, taper=0.7)
    # spout, to the right, with a rubber tube off to the pipework
    spout = [(x + 32, by - 14), (x + 52, by - 30), (x + 58, by - 46), (x + 50, by - 48), (x + 44, by - 34), (x + 30, by - 26)]
    d.ko(spout)
    d.wash(spout, COPPER, op=0.7, amp=0.5, step=6)
    d.pen([(x + 32, by - 14), (x + 52, by - 30), (x + 58, by - 46)], w=1.7, amp=0.3)
    d.pen([(x + 30, by - 26), (x + 44, by - 34), (x + 50, by - 48)], w=1.7, amp=0.3)
    return (x + 54, by - 47)


def cat(d, x, y):
    """Asleep, curled, on something warm. (x, y) is the middle of where it lies."""
    body = spline([(x - 44, y), (x - 50, y - 16), (x - 36, y - 34), (x - 8, y - 42), (x + 22, y - 38),
                   (x + 42, y - 24), (x + 48, y - 8), (x + 40, y)], closed=False)
    body = body + [(x - 44, y)]
    d.ko(body)
    d.wash(body, GINGER, op=0.62, amp=1.2)
    d.wash([(x + 8, y - 40), (x + 42, y - 24), (x + 48, y - 8), (x + 40, y), (x, y), (x + 20, y - 18)], PAYNE, op=0.16, edge=0, amp=0.8)
    d.pen(body[:-1], w=1.9, amp=0.7)
    # stripes over the back
    for i, sx in enumerate((-18, -4, 10, 24)):
        d.pen([(x + sx, y - 39 + abs(sx) * 0.12), (x + sx + 5, y - 29 + abs(sx) * 0.1), (x + sx + 4, y - 22)], w=2.0, amp=0.5, color=UMBER, opacity=0.5)
    # head, tucked down at the left
    hx, hy = x - 34, y - 14
    head = ellipse_pts(hx, hy, 17, 14)
    d.ko(head)
    d.wash(head, GINGER, op=0.64, amp=0.6, step=8)
    for sx in (-1, 1):
        ear = [(hx + sx * 5, hy - 11), (hx + sx * 13, hy - 23), (hx + sx * 16, hy - 6)]
        d.ko(ear)
        d.wash(ear, GINGER, op=0.64, amp=0.3, step=5, glaze=False)
        d.pen([ear[0], ear[1]], w=1.5, amp=0.3)
        d.pen([ear[1], ear[2]], w=1.5, amp=0.3)
    d.circle(hx, hy, 15.5, w=1.7, squash=0.9)
    d.arc(hx - 6, hy - 1, 3.6, 2.6, 20, 160, w=1.3)     # closed eyes
    d.arc(hx + 6, hy - 1, 3.6, 2.6, 20, 160, w=1.3)
    d.pen([(hx - 1.5, hy + 4), (hx, hy + 6), (hx + 1.5, hy + 4)], w=1.2, amp=0.1)
    for sx in (-1, 1):
        for dy in (3, 6):
            d.pen([(hx + sx * 7, hy + dy), (hx + sx * 23, hy + dy + (dy - 4) * 1.4)], w=0.6, amp=0.4)
    # tail, wrapped round the front
    tail = spline([(x + 44, y - 10), (x + 36, y + 2), (x + 6, y + 5), (x - 18, y + 3), (x - 24, y - 3)])
    tail_fill = tail + [(x - 20, y - 9), (x + 4, y - 4), (x + 30, y - 7)]
    d.ko(tail_fill)
    d.wash(tail_fill, GINGER, op=0.62, amp=0.5, step=8, glaze=False)
    d.pen(tail, w=1.8, amp=0.5)
    d.pen([(x - 20, y - 9), (x + 4, y - 4), (x + 30, y - 7)], w=1.3, amp=0.4)


def books(d, x, y):
    """A short stack, none of it square. (x, y) is the bottom-left."""
    specs = [(0, 0, 92, 15, MADDER, -1.5), (6, -15, 78, 13, VERDIGRIS, 2.0), (2, -28, 84, 14, PAYNE, -1.0)]
    for dx, dy, w, h, col, tilt in specs:
        pts = rotate_pts(rect_pts(x + dx, y + dy - h, w, h), tilt, x + dx + w / 2, y + dy)
        d.ko(pts)
        d.wash(pts, col, op=0.66, amp=0.6, step=10)
        d.edges(pts, w=1.6, over=1.5)
        a, b = pts[0], pts[3]
        for t in (0.1, 0.16, 0.86):
            p = (a[0] + (pts[1][0] - a[0]) * t, a[1] + (pts[1][1] - a[1]) * t)
            q = (b[0] + (pts[2][0] - b[0]) * t, b[1] + (pts[2][1] - b[1]) * t)
            d.pen([p, q], w=0.8, amp=0.1)


def boiler(d, x, y, w, h):
    """An upright boiler: riveted bands, a domed top, a firebox with a glow in it."""
    body = rect_pts(x, y, w, h)
    dome = arc_pts(x + w / 2.0, y, w / 2.0, 46, 180, 360, 14)
    d.ko(dome + [(x + w, y + h), (x, y + h)])
    d.wash(dome + [(x + w, y + h), (x, y + h)], VERDIGRIS, op=0.52, amp=1.6)
    d.wash([(x + w * 0.66, y - 30), (x + w, y), (x + w, y + h), (x + w * 0.66, y + h)], PAYNE, op=0.26, edge=0, amp=0.8)
    d.hatch([(x + w * 0.78, y + 6), (x + w - 2, y + 6), (x + w - 2, y + h - 4), (x + w * 0.78, y + h - 4)], gap=4.2, w=0.65, trim=0.3)
    d.hatch([(x + w * 0.88, y + 6), (x + w - 2, y + 6), (x + w - 2, y + h - 4), (x + w * 0.88, y + h - 4)], angle=35, gap=4.4, w=0.6, trim=0.3)
    d.pen(dome, w=2.4, amp=0.6)
    d.line((x, y), (x, y + h), w=2.4)
    d.line((x + w, y), (x + w, y + h), w=2.4)
    d.line((x - 6, y + h), (x + w + 6, y + h), w=2.6)
    d.glint([(x + 13, y + 20), (x + 12, y + h * 0.4)], w=3.0, opacity=0.4)
    for by in (y + 2, y + h * 0.36, y + h * 0.7):
        band = rect_pts(x - 3, by, w + 6, 13)
        d.ko(band)
        d.wash(band, BRASS, op=0.6, amp=0.5)
        d.edges(band, w=1.6, over=1.5)
        rivets(d, x + 8, by + 6.5, x + w - 8, by + 6.5, 8, r=2.0)
    # firebox door
    fx, fy = x + w / 2.0, y + h - 62
    door = round_rect_pts(fx - 34, fy - 26, 68, 58, 10)
    d.ko(door)
    d.wash(door, PAYNE, op=0.6, amp=0.6)
    d.outline(door, w=2.0)
    grate = round_rect_pts(fx - 22, fy - 12, 44, 30, 5)
    d.ko(grate)
    d.wash(grate, EMBER, op=0.85, amp=0.4, step=8)
    d.wash(scale_pts(grate, 0.6), "#f7c86a", op=0.7, amp=0.3, step=6, edge=0, glaze=False)
    d.outline(grate, w=1.4)
    for gx in (-12, -4, 4, 12):
        d.pen([(fx + gx, fy - 11), (fx + gx, fy + 17)], w=1.5, amp=0.2)
    d.disc(fx + 27, fy + 3, 3.4, fill=BRASS, op=0.8, lw=1.1, shade=False)
    # pressure gauge on the front
    gx, gy = x + w * 0.36, y + h * 0.2
    d.disc(gx, gy, 23, fill=BRASS, op=0.64, lw=1.9)
    face = circle_pts(gx, gy, 17.5, 16)
    d.ko(face, PAPER_LIGHT)
    d.circle(gx, gy, 17.5, w=1.2)
    for i in range(9):
        a = math.radians(150 + i * 30)
        d.pen([(gx + 12.5 * math.cos(a), gy + 12.5 * math.sin(a)), (gx + 15.5 * math.cos(a), gy + 15.5 * math.sin(a))], w=0.8, amp=0.05)
    d.pen([(gx - 3, gy + 2), (gx + 10, gy - 9)], w=1.4, amp=0.1, color=MADDER)
    d.dot(gx, gy, 1.6)
    # water sight-glass down the side
    sx = x + w * 0.74
    tube = rect_pts(sx - 4, y + h * 0.42, 8, h * 0.22)
    d.ko(tube, PAPER_LIGHT)
    d.wash(rect_pts(sx - 4, y + h * 0.52, 8, h * 0.12), PAYNE, op=0.4, amp=0.2, step=6, edge=0, glaze=False)
    d.edges(tube, w=1.2, over=1)
    for ty in (y + h * 0.42 - 5, y + h * 0.64):
        cap = rect_pts(sx - 7, ty, 14, 6)
        d.ko(cap)
        d.wash(cap, BRASS, op=0.7, amp=0.2, step=5, glaze=False)
        d.edges(cap, w=1.1, over=0.6)


def lamp(d, x, y, drop=70):
    """A hanging oil lamp on its chain; (x, y) is the ceiling hook."""
    d.pen([(x, y), (x, y + drop)], w=1.0, amp=0.5)
    shade = [(x - 30, y + drop + 26), (x - 9, y + drop), (x + 9, y + drop), (x + 30, y + drop + 26)]
    d.ko(shade)
    d.wash(shade, VERDIGRIS, op=0.6, amp=0.6, step=8)
    d.edges(shade, w=1.8, over=2)
    glass = spline([(x - 9, y + drop + 26), (x - 12, y + drop + 40), (x, y + drop + 50), (x + 12, y + drop + 40), (x + 9, y + drop + 26)])
    d.ko(glass, PAPER_LIGHT)
    d.wash(glass, EMBER, op=0.5, amp=0.3, step=6, glaze=False)
    d.pen(glass, w=1.4, amp=0.3)


def spanner(d, x, y, angle):
    pts = [(x, y - 3), (x + 62, y - 3), (x + 62, y + 3), (x, y + 3)]
    shaft = rotate_pts(pts, angle, x, y)
    d.ko(shaft)
    d.wash(shaft, PAYNE, op=0.55, amp=0.3, step=8, glaze=False)
    d.edges(shaft, w=1.4, over=0.5)
    for end, flip in ((0, 1), (62, -1)):
        jaw = [(x + end, y - 9), (x + end - flip * 13, y - 9), (x + end - flip * 13, y - 3.5), (x + end - flip * 6, y - 3.5),
               (x + end - flip * 6, y + 3.5), (x + end - flip * 13, y + 3.5), (x + end - flip * 13, y + 9), (x + end, y + 9)]
        jaw = rotate_pts(jaw, angle, x, y)
        d.ko(jaw)
        d.wash(jaw, PAYNE, op=0.55, amp=0.3, step=6, glaze=False)
        d.edges(jaw, w=1.4, over=0.4)


def oil_can(d, x, y):
    body = [(x - 16, y), (x + 16, y), (x + 11, y - 26), (x - 11, y - 26)]
    d.ko(body)
    d.wash(body, MADDER, op=0.66, amp=0.6, step=8)
    d.edges(body, w=1.8, over=1.5)
    d.pen([(x + 2, y - 26), (x + 8, y - 44), (x + 40, y - 58)], w=1.8, amp=0.3)
    d.pen(spline([(x - 11, y - 20), (x - 28, y - 20), (x - 27, y - 4), (x - 15, y - 3)]), w=1.8, amp=0.3)
    d.dot(x + 44, y - 52, 1.6)


# ---- the console plate ---------------------------------------------------------------

def console():
    d = Drawing(L.PLATE_W, L.PLATE_H, seed=7)
    d.group_open('transform="translate(%d %d)"' % (L.SAFE_X, L.SAFE_Y))
    X0, X1 = -L.SAFE_X, L.PLATE_W - L.SAFE_X          # plate edges in safe coordinates
    Y0, Y1 = -L.SAFE_Y, L.PLATE_H - L.SAFE_Y
    FY = L.FLOOR_Y

    # -- the room: a wall with a dado, bare boards --------------------------------
    d.wash([(X0, 760), (X1, 760), (X1, FY), (X0, FY)], PAYNE, op=0.1, edge=0, amp=6, step=60, glaze=False)
    d.wash([(X0, FY), (X1, FY), (X1, Y1), (X0, Y1)], SIENNA, op=0.3, edge=0, amp=3, step=60, glaze=False)
    d.pen([(X0, FY), (X1, FY)], w=2.4, amp=1.5, step=30)
    d.pen([(X0, FY - 26), (X1, FY - 26)], w=1.2, amp=1.2, step=30)
    for i in range(15):
        bx = X0 + (X1 - X0) * i / 14.0
        d.pen([(bx, FY + 2), (800 + (bx - 800) * 1.6, Y1)], w=1.1, amp=1.0, step=24)
    for i in range(26):
        bx = d.rnd.uniform(X0, X1)
        by = d.rnd.uniform(FY + 14, Y1 - 6)
        d.pen([(bx, by), (bx + d.rnd.uniform(24, 70), by + d.rnd.uniform(-1, 1))], w=0.6, amp=0.8, opacity=0.45)

    # -- overhead: the main steam pipe, hung from the ceiling ---------------------------
    for hx in (-60, 230, 640, 980, 1500, 1740):
        d.pen([(hx, Y0), (hx, -92)], w=1.4, amp=0.6)
        d.arc(hx, -82, 11, 11, 180, 360, w=1.6)
    d.pipe([(-140, 300), (-140, -82), (1700, -82), (1700, 380)], r=9, fill=VERDIGRIS, flanges=(0.12, 0.3, 0.52, 0.7, 0.88))
    # drops into the two gaps beside the paper
    d.pipe([(L.GEAR_COLUMN["x"], -74), (L.GEAR_COLUMN["x"], 176)], r=6.5, fill=VERDIGRIS, flanges=(0.5,))
    d.pipe([(L.VALVES["x"], -74), (L.VALVES["x"], 150)], r=6.5, fill=VERDIGRIS, flanges=(0.42,))
    lamp(d, 330, Y0, drop=44)
    lamp(d, 1270, Y0, drop=44)

    # -- left of everything: the boiler -------------------------------------------------
    boiler(d, -226, 330, 172, FY - 330)
    d.pen([(-236, FY), (-44, FY)], w=2.6, amp=0.8)
    # a shelf above it, with bottles of ink
    d.box(-232, 120, 196, 9, fill=UMBER, op=0.6, lw=1.8)
    for bx, bh, col in ((-216, 46, PAYNE), (-182, 34, MADDER), (-150, 52, INK), (-112, 30, VERDIGRIS), (-82, 40, UMBER)):
        bottle = [(bx, 120), (bx + 22, 120), (bx + 22, 120 - bh * 0.62), (bx + 15, 120 - bh * 0.78), (bx + 15, 120 - bh), (bx + 7, 120 - bh), (bx + 7, 120 - bh * 0.78), (bx, 120 - bh * 0.62)]
        d.ko(bottle)
        d.wash(bottle, col, op=0.6, amp=0.4, step=8)
        d.outline(bottle, w=1.5, overlap=4)
        d.glint([(bx + 4, 116 - bh * 0.5), (bx + 4, 114)], w=1.4, opacity=0.5)
    for bx in (-206, -58):
        d.pen([(bx, 129), (bx - 6, 156), (bx + 12, 129)], w=1.5, amp=0.4)

    # -- right of everything: belt wheel stand, a stool, the engine house ---------------
    d.pen([(1640, FY), (1830, FY)], w=2.6, amp=0.8)
    for sx in (-1, 1):
        leg = [(1728 + sx * 12, 648), (1728 + sx * 74, FY), (1728 + sx * 56, FY), (1728 + sx * 2, 660)]
        d.ko(leg)
        d.wash(leg, PAYNE, op=0.5, amp=0.6)
        d.edges(leg, w=2.0, over=2)
    d.pen([(1688, 780), (1768, 780)], w=2.0, amp=0.5, over=3)
    # the belt up to a pulley on the cabinet's side
    d.pen([(1632, 244), (1680, 560)], w=1.6, amp=0.8)
    d.pen([(1612, 262), (1650, 590)], w=1.6, amp=0.8)
    d.disc(1614, 240, 24, fill=SIENNA, op=0.66, lw=2.0)
    d.disc(1614, 240, 6, fill=BRASS, op=0.8, lw=1.3, shade=False)
    d.box(1576, 232, 30, 16, fill=PAYNE, op=0.5, lw=1.7)
    # a framed certificate on the wall
    d.box(1660, -20, 130, 96, fill=UMBER, op=0.55, lw=2.2)
    cert = rect_pts(1672, -8, 106, 72)
    d.ko(cert, PAPER_LIGHT)
    d.edges(cert, w=1.2, over=1)
    for i, wdt in enumerate((70, 84, 60, 78, 50)):
        d.pen([(1725 - wdt / 2.0, 6 + i * 10), (1725 + wdt / 2.0, 6 + i * 10)], w=0.8 if i else 1.6, amp=0.5, opacity=0.7)
    d.disc(1760, 52, 7, fill=MADDER, op=0.75, lw=1.1, shade=False)
    d.pen([(1725, -20), (1725, -44)], w=0.9, amp=0.3)
    d.dot(1725, -46, 2.0)

    # -- on the floor ------------------------------------------------------------------
    oil_can(d, 1612, FY + 62)
    spanner(d, 380, FY + 70, -14)
    # a mouse-hole in the skirting, and its tenant
    hole = arc_pts(-20, FY, 15, 20, 180, 360, 10)
    d.ko(hole)
    d.wash(hole, INK, op=0.82, amp=0.3, step=6, glaze=False)
    d.pen(hole, w=1.4, amp=0.3)
    mouse = spline([(10, FY + 24), (14, FY + 13), (28, FY + 10), (40, FY + 15), (44, FY + 24)])
    d.ko(mouse + [(10, FY + 24)])
    d.wash(mouse + [(10, FY + 24)], PAYNE, op=0.5, amp=0.3, step=6, glaze=False)
    d.pen(mouse, w=1.4, amp=0.3)
    d.pen([(8, FY + 24), (48, FY + 24)], w=1.0, amp=0.2)
    d.circle(15, FY + 12, 3.6, w=1.0)
    d.dot(13, FY + 19, 0.9)
    d.pen(spline([(44, FY + 22), (58, FY + 26), (66, FY + 18), (76, FY + 22)]), w=1.0, amp=0.3)

    # ====================================================================================
    # LEFT CABINET: the pre-selectors
    # ====================================================================================
    c = L.LEFT
    x, y, w, h = c["x"], c["y"], c["w"], c["h"]
    for fx in (x + 22, x + w - 22):
        foot = [(fx - 14, y + h), (fx + 14, y + h), (fx + 9, FY), (fx - 9, FY)]
        d.ko(foot)
        d.wash(foot, UMBER, op=0.6, amp=0.4, step=6)
        d.edges(foot, w=1.9, over=1.5)
    wooden_cabinet(d, x, y, w, h)
    # the brass face everything is mounted on
    face = rect_pts(x + 10, y + 12, w - 20, h - 24)
    d.ko(face)
    d.wash(face, BRASS_LIGHT, op=0.4, amp=1.2)
    d.wash([(x + w * 0.5, y + h * 0.5), (x + w - 10, y + h * 0.2), (x + w - 10, y + h - 12), (x + 10, y + h - 12), (x + 10, y + h * 0.8)], PAYNE, op=0.07, edge=0, amp=3, glaze=False)
    d.edges(face, w=1.8, over=2.5)
    rivets(d, x + 18, y + 20, x + 18, y + h - 20, 12, r=1.9)
    rivets(d, x + w - 18, y + 20, x + w - 18, y + h - 20, 12, r=1.9)
    # the roll the tambour shutter lives in
    roll = round_rect_pts(x + 26, y + 16, w - 52, 24, 11)
    d.ko(roll)
    d.wash(roll, SIENNA, op=0.62, amp=0.6)
    d.wash(rect_pts(x + 30, y + 30, w - 60, 9), PAYNE, op=0.24, edge=0, amp=0.5)
    d.hatch(rect_pts(x + 34, y + 31, w - 68, 7), angle=0, gap=2.2, w=0.55, trim=0.3, skip=0.15)
    d.outline(roll, w=1.9)
    enamel_plate(d, x + w / 2.0 - 84, y + 18, 168, 20)
    enamel_plate(d, L.AUX_PLATE["x"] + 96, L.AUX_PLATE["y"], L.AUX_PLATE["w"] - 192, L.AUX_PLATE["h"])
    d.pen([(L.AUX_PLATE["x"] + 4, L.AUX_PLATE["y"] + 11), (L.AUX_PLATE["x"] + 88, L.AUX_PLATE["y"] + 11)], w=1.0, amp=0.4)
    d.pen([(L.AUX_PLATE["x"] + L.AUX_PLATE["w"] - 88, L.AUX_PLATE["y"] + 11), (L.AUX_PLATE["x"] + L.AUX_PLATE["w"] - 4, L.AUX_PLATE["y"] + 11)], w=1.0, amp=0.4)
    # wordage regulator: a slot with a scale over it, and a little counter window
    wg = L.WORDAGE
    slot = round_rect_pts(wg["x"] + 10, wg["y"] + 40, 252, 9, 4)
    d.ko(slot)
    d.wash(slot, INK, op=0.6, amp=0.2, step=10, edge=0, glaze=False)
    d.outline(slot, w=1.3)
    for i in range(39):
        tx = wg["x"] + 18 + 236.0 * i / 38
        major = (i - 2) % 4 == 0
        d.pen([(tx, wg["y"] + (25 if major else 30)), (tx, wg["y"] + 36)], w=1.3 if major else 0.75, amp=0.05, taper=0.7)
    window(d, wg["x"] + 276, wg["y"] + 22, 96, 38)
    # the mandatory-details slip in its holder
    sl = L.SLIP
    holder = round_rect_pts(sl["x"], sl["y"] + 14, sl["w"], sl["h"] - 14, 4)
    d.ko(holder)
    d.wash(holder, BRASS, op=0.6, amp=0.7)
    d.outline(holder, w=1.8)
    slip = rect_pts(sl["x"] + 9, sl["y"] + 19, sl["w"] - 18, sl["h"] - 24)
    d.ko(slip, PAPER_LIGHT)
    d.wash(rect_pts(sl["x"] + 9, sl["y"] + 19, sl["w"] - 18, 4), PAYNE, op=0.22, edge=0, amp=0.3, glaze=False)
    d.edges(slip, w=1.2, over=1)
    # bottom rail: maker's plate, a keyhole, the boss for the scramble crank
    rail_y = y + h - 78
    d.pen([(x + 14, rail_y), (x + w - 14, rail_y)], w=1.6, amp=0.6, over=2)
    oval = ellipse_pts(x + 116, rail_y + 37, 82, 24, 26)
    d.ko(oval, PAPER_LIGHT)
    d.wash(d.crescent(x + 116, rail_y + 37, 82, squash=24 / 82.0, depth=0.1), PAYNE, op=0.12, edge=0, amp=0.4)
    d.circle(x + 116, rail_y + 37, 82, w=1.7, squash=24 / 82.0)
    d.circle(x + 116, rail_y + 37, 76, w=0.8, squash=19 / 76.0)
    d.screw(x + 42, rail_y + 37, 2.0)
    d.screw(x + 190, rail_y + 37, 2.0)
    kx, ky = x + 262, rail_y + 36
    d.disc(kx, ky, 15, fill=BRASS, op=0.66, lw=1.7)
    d.ko(ellipse_pts(kx, ky - 3, 4, 4, 8))
    d.wash(ellipse_pts(kx, ky - 3, 4, 4, 8), INK, op=0.85, amp=0.1, step=3, edge=0, glaze=False)
    d.wash([(kx - 1.6, ky - 1), (kx + 1.6, ky - 1), (kx + 3.2, ky + 8), (kx - 3.2, ky + 8)], INK, op=0.85, amp=0.1, step=3, edge=0, glaze=False)
    d.disc(L.CRANK["x"], L.CRANK["y"], 22, fill=BRASS, op=0.66, lw=2.0)
    d.hatch(annulus_sector(L.CRANK["x"], L.CRANK["y"], 13, 20.5, 0, 100, 8), gap=3.0, w=0.6)

    # on top: a stack of books, a kettle on its burner, and the cat
    books(d, x + 222, y - 12)
    spout = kettle(d, x + 352, y - 12)
    d.pen(spline([spout, (spout[0] + 16, spout[1] - 22), (spout[0] + 34, spout[1] - 4), (L.GEAR_COLUMN["x"] - 4, spout[1] + 26), (L.GEAR_COLUMN["x"] - 2, 60)]), w=3.0, amp=0.8, taper=0.8, color=UMBER, opacity=0.85)
    cat(d, x + 268, y - 52)

    # ====================================================================================
    # RIGHT CABINET: organ stops, and below them the sight-glass and the lever
    # ====================================================================================
    c = L.RIGHT
    x, y, w, h = c["x"], c["y"], c["w"], c["h"]
    p = L.PLINTH
    for fx in (p["x"] + 24, p["x"] + p["w"] - 24):
        foot = [(fx - 16, p["y"] + p["h"]), (fx + 16, p["y"] + p["h"]), (fx + 11, FY), (fx - 11, FY)]
        d.ko(foot)
        d.wash(foot, PAYNE, op=0.55, amp=0.4, step=6)
        d.edges(foot, w=1.9, over=1.5)
    # plinth: riveted iron
    d.box(p["x"] - 6, p["y"], p["w"] + 12, p["h"], fill=PAYNE, op=0.42, lw=2.6, over=4)
    d.hatch([(p["x"] + p["w"] * 0.72, p["y"] + 8), (p["x"] + p["w"] + 2, p["y"] + 8), (p["x"] + p["w"] + 2, p["y"] + p["h"] - 6), (p["x"] + p["w"] * 0.72, p["y"] + p["h"] - 6)], gap=5.0, w=0.65, fade="a", skip=0.1)
    rivets(d, p["x"] + 8, p["y"] + 12, p["x"] + p["w"] - 8, p["y"] + 12, 14, r=2.1)
    rivets(d, p["x"] + 8, p["y"] + p["h"] - 10, p["x"] + p["w"] - 8, p["y"] + p["h"] - 10, 14, r=2.1)
    # sight-glass backboard and the six little cylinders beside it
    s = L.SIGHT
    board = round_rect_pts(s["x"], s["y"] + 10, s["w"], s["h"] - 20, 6)
    d.ko(board)
    d.wash(board, SIENNA, op=0.56, amp=0.8)
    d.outline(board, w=1.9)
    grain(d, s["x"] + 6, s["y"] + 18, s["w"] - 12, s["h"] - 36, n=4, vertical=True)
    for i in range(6):
        px = s["x"] + 64 + (i % 3) * 28
        py = s["y"] + (150 if i < 3 else 214)
        cyl = rect_pts(px - 9, py - 26, 18, 30)
        d.ko(cyl)
        d.wash(cyl, BRASS, op=0.68, amp=0.3, step=6)
        d.wash(rect_pts(px + 2, py - 26, 7, 30), PAYNE, op=0.28, edge=0, amp=0.2, glaze=False)
        d.edges(cyl, w=1.4, over=1)
        d.pen([(px - 11, py + 4), (px + 11, py + 4)], w=1.6, amp=0.2)

    # the jamb: an iron frame round a cream enamel panel
    d.box(x, y, w, h, fill=PAYNE, op=0.44, lw=2.6, over=4)
    cor = [(x - 9, y - 12), (x + w + 9, y - 12), (x + w + 4, y + 2), (x - 4, y + 2)]
    d.ko(cor)
    d.wash(cor, PAYNE, op=0.6, amp=0.8)
    d.edges(cor, w=2.2, over=3)
    panel = rect_pts(x + 8, y + 10, w - 16, h - 18)
    d.ko(panel, PAPER_LIGHT)
    d.wash([(x + w * 0.5, y + h * 0.5), (x + w - 8, y + h * 0.15), (x + w - 8, y + h - 8), (x + 8, y + h - 8), (x + 8, y + h * 0.75)], PAYNE, op=0.08, edge=0, amp=3, glaze=False)
    d.wash(rect_pts(x + 8, y + 10, w - 16, 7), PAYNE, op=0.2, edge=0, amp=0.5, glaze=False)
    d.edges(panel, w=1.8, over=2.5)
    rivets(d, x + 4.5, y + 14, x + 4.5, y + h - 12, 9, r=1.8)
    rivets(d, x + w - 4.5, y + 14, x + w - 4.5, y + h - 12, 9, r=1.8)
    enamel_plate(d, x + w / 2.0 - 70, y + 16, 140, 22)
    st = L.STOPS
    for row in range(5):
        ry = st["y"] + row * st["cell_h"]
        plate = round_rect_pts(st["quality_x"], ry + 14, st["quality_w"], 24, 4)
        d.ko(plate)
        d.wash(plate, BRASS, op=0.62, amp=0.5, step=8)
        d.outline(plate, w=1.5)
        if row:
            d.pen([(st["x"] - 2, ry - 1), (x + w - 14, ry - 1)], w=0.7, amp=0.4, opacity=0.5)

    # on top: gear guard, a bracket for the whistle, the ear-trumpet's stand
    b = L.BIG_COGS
    guard = arc_pts(b["ax"], y - 12, 76, 22, 180, 360, 12)
    back = [(b["ax"] - 80, y - 12), (b["bx"] + 60, y - 12), (b["bx"] + 60, y - 30), (b["ax"] - 80, y - 30)]
    d.ko(back)
    d.wash(back, PAYNE, op=0.5, amp=0.6)
    d.edges(back, w=2.0, over=2.5)
    rivets(d, b["ax"] - 70, y - 21, b["bx"] + 50, y - 21, 7, r=1.9)
    hn = L.HORN
    stand = [(hn["x"] + 40, y - 12), (hn["x"] + 76, y - 12), (hn["x"] + 66, y - 34), (hn["x"] + 50, y - 34)]
    d.ko(stand)
    d.wash(stand, PAYNE, op=0.52, amp=0.4, step=6)
    d.edges(stand, w=1.8, over=1.5)

    # ====================================================================================
    # CENTRE TOWER: nameplate, head, platen, paper, tray, rail, pedal well
    # ====================================================================================
    t = L.TOWER
    tx, tw = t["x"], t["w"]
    # the carcass behind the paper, right down to the floor
    carcass = [(tx, L.HEAD["y"] + 30), (tx + tw, L.HEAD["y"] + 30), (tx + tw, FY), (tx, FY)]
    d.ko(carcass)
    d.wash(carcass, UMBER, op=0.62, amp=1.4)
    d.hatch([(tx + tw - 16, L.PLATEN["y"] + 40), (tx + tw - 2, L.PLATEN["y"] + 40), (tx + tw - 2, L.TRAY["y"]), (tx + tw - 16, L.TRAY["y"])], gap=4.0, w=0.65, trim=0.25)
    d.hatch([(tx + 2, L.PLATEN["y"] + 40), (tx + 16, L.PLATEN["y"] + 40), (tx + 16, L.TRAY["y"]), (tx + 2, L.TRAY["y"])], gap=4.4, w=0.6, trim=0.3)
    d.line((tx, L.HEAD["y"] + 30), (tx, FY), w=2.6, over=2)
    d.line((tx + tw, L.HEAD["y"] + 30), (tx + tw, FY), w=2.6, over=2)

    # the sheet of paper, coming down from the platen
    pp = L.PAPER
    sheet = [(pp["x"], pp["y"]), (pp["x"] + pp["w"], pp["y"]), (pp["x"] + pp["w"] + 1, pp["y"] + pp["h"] - 6),
             (pp["x"] + pp["w"] * 0.6, pp["y"] + pp["h"] + 1), (pp["x"] + pp["w"] * 0.25, pp["y"] + pp["h"] - 3), (pp["x"] - 1, pp["y"] + pp["h"])]
    shadow = shift_pts(sheet, 7, 8)
    d.wash(shadow, INK, op=0.34, edge=0, amp=1.0, glaze=False)
    d.ko(sheet, PAPER_LIGHT)
    d.wash(rect_pts(pp["x"], pp["y"], pp["w"], 16), PAYNE, op=0.22, edge=0, amp=0.5, glaze=False)
    d.line(sheet[0], sheet[5], w=1.5, over=0)
    d.line(sheet[1], sheet[2], w=1.5, over=0)

    # head casing
    hd = L.HEAD
    head = [(hd["x"] - 6, hd["y"] + hd["h"]), (hd["x"] - 6, hd["y"] + 16), (hd["x"] + 22, hd["y"]), (hd["x"] + hd["w"] - 22, hd["y"]),
            (hd["x"] + hd["w"] + 6, hd["y"] + 16), (hd["x"] + hd["w"] + 6, hd["y"] + hd["h"])]
    d.ko(head)
    d.wash(head, BRASS, op=0.62, amp=1.2)
    d.wash([(hd["x"] + hd["w"] * 0.6, hd["y"]), (hd["x"] + hd["w"] + 6, hd["y"] + 16), (hd["x"] + hd["w"] + 6, hd["y"] + hd["h"]), (hd["x"] - 6, hd["y"] + hd["h"]), (hd["x"] - 6, hd["y"] + hd["h"] * 0.74), (hd["x"] + hd["w"] * 0.6, hd["y"] + hd["h"] * 0.74)], PAYNE, op=0.15, edge=0, amp=1.0, glaze=False)
    d.edges(head, w=2.4, over=3)
    rivets(d, hd["x"] + 4, hd["y"] + 26, hd["x"] + 4, hd["y"] + hd["h"] - 8, 3, r=2.0)
    rivets(d, hd["x"] + hd["w"] - 4, hd["y"] + 26, hd["x"] + hd["w"] - 4, hd["y"] + hd["h"] - 8, 3, r=2.0)
    window(d, L.FLAG["x"], L.FLAG["y"], L.FLAG["w"], L.FLAG["h"])
    window(d, L.ODOMETER["x"], L.ODOMETER["y"], L.ODOMETER["w"], L.ODOMETER["h"])
    # a spy-hole between them, for no reason anyone remembers
    d.disc(800, hd["y"] + 38, 13, fill=BRASS, op=0.7, lw=1.8)
    lens = circle_pts(800, hd["y"] + 38, 8, 10)
    d.ko(lens)
    d.wash(lens, PAYNE, op=0.6, amp=0.2, step=4, glaze=False)
    d.circle(800, hd["y"] + 38, 8, w=1.2)
    d.glint(arc_pts(800, hd["y"] + 38, 4.6, 4.6, 200, 260, 4), w=1.4, opacity=0.8)

    # nameplate: an arch of cream enamel in a brass rim, on two posts
    n = L.NAMEPLATE
    for px in (n["x"] + 26, n["x"] + n["w"] - 26):
        post = rect_pts(px - 6, n["y"] + n["h"] - 6, 12, hd["y"] - n["y"] - n["h"] + 8)
        d.ko(post)
        d.wash(post, BRASS, op=0.68, amp=0.2, step=5, glaze=False)
        d.edges(post, w=1.5, over=1)
    arch = arc_pts(n["x"] + n["w"] / 2.0, n["y"] + n["h"] - 4, n["w"] / 2.0, n["h"] - 4, 180, 360, 26) + [(n["x"] + n["w"], n["y"] + n["h"]), (n["x"], n["y"] + n["h"])]
    d.ko(arch)
    d.wash(arch, BRASS, op=0.66, amp=1.0)
    d.outline(arch, w=2.4, overlap=10)
    inner = arc_pts(n["x"] + n["w"] / 2.0, n["y"] + n["h"] - 8, n["w"] / 2.0 - 9, n["h"] - 15, 180, 360, 26) + [(n["x"] + n["w"] - 9, n["y"] + n["h"] - 7), (n["x"] + 9, n["y"] + n["h"] - 7)]
    d.ko(inner, PAPER_LIGHT)
    d.wash(arc_pts(n["x"] + n["w"] / 2.0, n["y"] + n["h"] - 8, n["w"] / 2.0 - 9, n["h"] - 15, 180, 360, 26) + arc_pts(n["x"] + n["w"] / 2.0, n["y"] + n["h"] - 2, n["w"] / 2.0 - 9, n["h"] - 15, 360, 180, 26), PAYNE, op=0.2, edge=0, amp=0.4, glaze=False)
    d.outline(inner, w=1.5, overlap=8)
    for fx in (n["x"] - 2, n["x"] + n["w"] + 2):
        d.disc(fx, n["y"] + n["h"] - 6, 8, fill=BRASS, op=0.75, lw=1.6)
    d.disc(n["x"] + n["w"] / 2.0, n["y"] - 2, 7, fill=BRASS, op=0.75, lw=1.6)
    # a bracket for the carriage bell to hang from
    d.pen(spline([(n["x"] + n["w"] - 4, n["y"] + 48), (n["x"] + n["w"] + 12, n["y"] + 34), (n["x"] + n["w"] + 22, n["y"] + 22), (n["x"] + n["w"] + 24, n["y"] + 20)]), w=2.4, amp=0.3, taper=0.7)

    # platen: a rubber roller between two brass cheeks, with a knob at each end
    pl = L.PLATEN
    roller = round_rect_pts(pl["x"] + 8, pl["y"] + 3, pl["w"] - 16, pl["h"] - 6, 12)
    d.ko(roller)
    d.wash(roller, INK, op=0.62, amp=0.6)
    d.wash(rect_pts(pl["x"] + 14, pl["y"] + 6, pl["w"] - 28, 7), GOUACHE, op=0.2, edge=0, amp=0.4, glaze=False)
    d.hatch(rect_pts(pl["x"] + 16, pl["y"] + pl["h"] - 14, pl["w"] - 32, 9), angle=0, gap=2.1, w=0.6, trim=0.35, skip=0.1)
    d.outline(roller, w=2.0)
    for cx_, flip in ((pl["x"], -1), (pl["x"] + pl["w"], 1)):
        cheek = rect_pts(cx_ - 9, pl["y"] - 4, 18, pl["h"] + 10)
        d.ko(cheek)
        d.wash(cheek, BRASS, op=0.68, amp=0.4, step=6)
        d.edges(cheek, w=1.8, over=1.5)
        knob = round_rect_pts(cx_ + flip * 9 - (0 if flip > 0 else 22), pl["y"] + 2, 22, pl["h"] - 4, 5)
        d.ko(knob)
        d.wash(knob, UMBER, op=0.7, amp=0.3, step=6)
        d.outline(knob, w=1.6)
        for k in range(4):
            kx_ = cx_ + flip * (13 + k * 4.4)
            d.pen([(kx_, pl["y"] + 5), (kx_, pl["y"] + pl["h"] - 5)], w=0.8, amp=0.15)
    # paper bail: a thin bar holding the sheet, with two little rollers
    d.pen([(pl["x"] + 4, pl["y"] + pl["h"] + 6), (pl["x"] + pl["w"] - 4, pl["y"] + pl["h"] + 6)], w=2.0, amp=0.4)
    for bx in (pl["x"] + 150, pl["x"] + pl["w"] - 150):
        d.box(bx - 14, pl["y"] + pl["h"] + 1, 28, 10, fill=PAYNE, op=0.6, lw=1.3, over=1, shade=False)

    # tray lip the sheet tucks behind
    tr = L.TRAY
    lip = [(tr["x"] - 8, tr["y"]), (tr["x"] + tr["w"] + 8, tr["y"]), (tr["x"] + tr["w"] + 4, tr["y"] + tr["h"]), (tr["x"] - 4, tr["y"] + tr["h"])]
    d.ko(lip)
    d.wash(lip, SIENNA, op=0.62, amp=0.8)
    d.edges(lip, w=2.2, over=3)
    grain(d, tr["x"] + 10, tr["y"] + 5, tr["w"] - 20, tr["h"] - 10, n=3)
    # rail the plaques hang on: a felt-lined recess
    rl = L.RAIL
    rail = rect_pts(rl["x"], rl["y"], rl["w"], rl["h"])
    d.ko(rail)
    d.wash(rail, VERDIGRIS, op=0.5, amp=0.8)
    d.wash(rect_pts(rl["x"], rl["y"], rl["w"], 8), INK, op=0.3, edge=0, amp=0.5, glaze=False)
    d.hatch(rect_pts(rl["x"] + 2, rl["y"] + 1, rl["w"] - 4, 6), angle=0, gap=2.0, w=0.55, trim=0.2, skip=0.1)
    d.edges(rail, w=1.9, over=2)
    # pedal well
    wl = L.WELL
    well = rect_pts(wl["x"], wl["y"], wl["w"], wl["h"])
    d.ko(well)
    d.wash(well, PAYNE, op=0.34, amp=1.0)
    d.wash(rect_pts(wl["x"], wl["y"], wl["w"], 12), INK, op=0.3, edge=0, amp=0.5, glaze=False)
    d.hatch(rect_pts(wl["x"] + 2, wl["y"] + 1, wl["w"] - 4, 9), angle=0, gap=2.2, w=0.55, trim=0.2, skip=0.1)
    d.edges(well, w=1.9, over=2)
    d.pen([(wl["x"] + 6, wl["y"] + wl["h"] - 12), (wl["x"] + wl["w"] - 6, wl["y"] + wl["h"] - 12)], w=1.2, amp=0.5)
    d.line((tx - 4, FY), (tx + tw + 4, FY), w=2.8, over=3)

    # ====================================================================================
    # THE GAPS: a gear bracket on the left, the valve rack on the right
    # ====================================================================================
    g = L.GEAR_COLUMN
    strap = rect_pts(g["x"] - 9, 176, 18, 430)
    d.ko(strap)
    d.wash(strap, PAYNE, op=0.5, amp=0.5)
    d.edges(strap, w=1.8, over=2)
    for sy in (196, 384, 580):
        tie = rect_pts(L.LEFT["x"] + L.LEFT["w"] - 2, sy, tx - (L.LEFT["x"] + L.LEFT["w"]) + 4, 10)
        d.ko(tie)
        d.wash(tie, PAYNE, op=0.5, amp=0.3, step=8, glaze=False)
        d.edges(tie, w=1.5, over=1.5)
        d.rivet(L.LEFT["x"] + L.LEFT["w"] + 5, sy + 5, 1.8)
        d.rivet(tx - 5, sy + 5, 1.8)
    # a push-rod down from the lowest cog to a bell-crank near the floor
    low = g["ys"][-1]
    d.pen([(g["x"] + 12, low + 14), (g["x"] + 6, 560)], w=2.2, amp=0.5)
    d.disc(g["x"], 600, 15, fill=BRASS, op=0.68, lw=1.8)
    d.disc(g["x"], 600, 4, fill=PAYNE, op=0.7, lw=1.1, shade=False)
    # string, with a weight on it, because there is always string
    d.pen(spline([(g["x"] - 12, 610), (g["x"] - 18, 660), (g["x"] - 10, 716)]), w=0.9, amp=0.8)
    weight = [(g["x"] - 20, 716), (g["x"], 716), (g["x"] + 3, 748), (g["x"] - 23, 748)]
    d.ko(weight)
    d.wash(weight, PAYNE, op=0.62, amp=0.4, step=6)
    d.edges(weight, w=1.6, over=1)

    v = L.VALVES
    rack = rect_pts(v["x"] - 22, v["y"] - 46, 44, v["step"] * (v["n"] - 1) + 96)
    d.ko(rack)
    d.wash(rack, SIENNA, op=0.5, amp=0.6)
    d.edges(rack, w=1.8, over=2)
    for i in range(v["n"]):
        cy = v["y"] + i * v["step"]
        shelf = rect_pts(v["x"] - 26, cy + 31, 52, 7)
        d.ko(shelf)
        d.wash(shelf, UMBER, op=0.62, amp=0.3, step=8, glaze=False)
        d.edges(shelf, w=1.4, over=1.5)
        thermionic_valve(d, v["x"], cy)
    # wires from the rack down behind the plinth
    for k, wx in enumerate((-10, 0, 10)):
        top = v["y"] + (v["n"] - 1) * v["step"] + 50
        d.pen(spline([(v["x"] + wx, top), (v["x"] + wx * 2.2, top + 60), (v["x"] + wx * 0.6, top + 130), (v["x"] + wx * 1.6, top + 190)]), w=1.1, amp=0.8, color=(MADDER, INK, VERDIGRIS)[k], opacity=0.85)

    d.group_close()
    return d


PLATES = {
    "console": console,
}
