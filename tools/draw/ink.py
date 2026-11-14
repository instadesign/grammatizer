"""A small pen-and-wash drawing engine.

Every drawing in assets/svg/ is produced by this package and committed as a plain
static SVG -- the site itself still has no build step. The engine exists so the line
quality is consistent across a few hundred parts: each pen stroke is emitted as a
filled, tapered, slightly wobbling outline (not an SVG `stroke`), which is what makes
it read as drawn with a nib rather than plotted; washes are loose translucent fills
that deliberately miss the line a little; hatching is real individual strokes clipped
to a shape, not a tiling pattern.

Nothing here uses SVG filters. All the irregularity is baked into the geometry, so the
output rasterises fast, stays sharp at any scale, and costs nothing while animating.

Painter's order: call things in the order they should be painted. A typical object is
knock-out (hide what is behind) -> wash -> hatch -> pen lines.
"""

import math
import random

# ---- palette (mirrors css/tokens.css) -------------------------------------------
PAPER = "#ede0c8"
PAPER_LIGHT = "#f7f1e1"
INK = "#2a211b"
BRASS = "#b8863b"
BRASS_LIGHT = "#d9ab5c"
VERDIGRIS = "#5b8a76"
EMBER = "#d98a2b"
MADDER = "#a63d40"
PAYNE = "#5d6b7a"
SIENNA = "#9a6239"   # wood
UMBER = "#6b4a32"    # dark wood, leather
GOUACHE = "#fffaf0"  # opaque white, for glints


def fmt(x):
    s = "%.1f" % x
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def _op(x):
    return ("%.2f" % x).rstrip("0").rstrip(".")


def pt(p):
    return "%s %s" % (fmt(p[0]), fmt(p[1]))


def mid(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---- geometry helpers ---------------------------------------------------------------

def rect_pts(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def arc_pts(cx, cy, rx, ry, a0, a1, n=None):
    """Points along an ellipse arc. Angles in degrees, 0 = east, clockwise on screen."""
    if n is None:
        n = max(6, int(abs(a1 - a0) / 12))
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def circle_pts(cx, cy, r, n=None):
    if n is None:
        n = max(10, int(r * 0.9))
    return arc_pts(cx, cy, r, r, 0, 360, n)[:-1]


def ellipse_pts(cx, cy, rx, ry, n=None):
    if n is None:
        n = max(10, int(max(rx, ry) * 0.9))
    return arc_pts(cx, cy, rx, ry, 0, 360, n)[:-1]


def round_rect_pts(x, y, w, h, r, n=4):
    r = min(r, w / 2.0, h / 2.0)
    out = []
    out += arc_pts(x + w - r, y + r, r, r, -90, 0, n)
    out += arc_pts(x + w - r, y + h - r, r, r, 0, 90, n)
    out += arc_pts(x + r, y + h - r, r, r, 90, 180, n)
    out += arc_pts(x + r, y + r, r, r, 180, 270, n)
    return out


def annulus_sector(cx, cy, r0, r1, a0, a1, n=None):
    return arc_pts(cx, cy, r1, r1, a0, a1, n) + arc_pts(cx, cy, r0, r0, a1, a0, n)


def rotate_pts(pts, deg, cx=0, cy=0):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def shift_pts(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def scale_pts(pts, k, cx=None, cy=None):
    if cx is None:
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in pts]


def spline(pts, closed=False, seg=6):
    """Catmull-Rom through pts, returned as a dense polyline."""
    n = len(pts)
    if n < 3:
        return list(pts)
    out = []
    count = n if closed else n - 1
    for i in range(count):
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[0]
        p1 = pts[i % n]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else pts[-1]
        for k in range(seg):
            t = k / float(seg)
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    if not closed:
        out.append(pts[-1])
    return out


def resample(pts, step, closed=False):
    """Evenly spaced points along a polyline (ends kept for an open one)."""
    if closed:
        pts = list(pts) + [pts[0]]
    segs = []
    total = 0.0
    for a, b in zip(pts, pts[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length > 0:
            segs.append((a, b, length))
            total += length
    if not segs:
        return [pts[0], pts[0]], 0.0
    n = max(3 if closed else 2, int(round(total / step)))
    out = []
    si = 0
    acc = 0.0
    for k in range(n + (0 if closed else 1)):
        target = total * k / n
        while si < len(segs) - 1 and acc + segs[si][2] < target:
            acc += segs[si][2]
            si += 1
        a, b, length = segs[si]
        t = min(1.0, max(0.0, (target - acc) / length))
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out, total


def qpath(pts, closed):
    """Smooth path through the midpoints of pts (quadratic B-spline)."""
    n = len(pts)
    if closed:
        m = [mid(pts[i], pts[(i + 1) % n]) for i in range(n)]
        d = ["M" + pt(m[-1])]
        for i in range(n):
            d.append("Q%s %s" % (pt(pts[i]), pt(m[i])))
        d.append("Z")
        return "".join(d)
    d = ["M" + pt(pts[0])]
    for i in range(1, n - 1):
        d.append("Q%s %s" % (pt(pts[i]), pt(mid(pts[i], pts[i + 1]))))
    d.append("L" + pt(pts[-1]))
    return "".join(d)


def lpath(pts, closed=True):
    return "M" + "L".join(pt(p) for p in pts) + ("Z" if closed else "")


class _Wobble(object):
    """Smooth 1-D value noise in [-1, 1], sampled by distance along a stroke."""

    def __init__(self, rnd, wavelength):
        self.rnd = rnd
        self.wl = float(wavelength)
        self.phase = rnd.random() * 1000.0
        self.vals = {}

    def _v(self, i):
        if i not in self.vals:
            self.vals[i] = self.rnd.uniform(-1.0, 1.0)
        return self.vals[i]

    def at(self, s):
        x = s / self.wl + self.phase
        i = int(math.floor(x))
        t = x - i
        t = t * t * (3 - 2 * t)
        a, b = self._v(i), self._v(i + 1)
        return a + (b - a) * t


class Drawing(object):
    def __init__(self, w, h, seed=1, bg=None):
        self.w, self.h = w, h
        self.rnd = random.Random(seed)
        self.out = []
        self._ink = []
        self.bg = bg

    # ---- emission ---------------------------------------------------------------
    def _flush(self):
        if self._ink:
            self.out.append('<path d="%s"/>' % "".join(self._ink))
            self._ink = []

    def raw(self, s):
        self._flush()
        self.out.append(s)

    def svg(self):
        self._flush()
        head = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" width="%s" height="%s">' % (fmt(self.w), fmt(self.h), fmt(self.w), fmt(self.h))
        body = []
        if self.bg:
            body.append('<rect width="100%%" height="100%%" fill="%s"/>' % self.bg)
        body.append('<g fill="%s">' % INK)
        body.extend(self.out)
        body.append("</g>")
        return head + "\n" + "\n".join(body) + "\n</svg>\n"

    def group_open(self, attrs=""):
        self.raw("<g %s>" % attrs)

    def group_close(self):
        self.raw("</g>")

    # ---- pen ----------------------------------------------------------------------
    def pen(self, pts, w=2.0, amp=0.9, step=11.0, taper=0.42, over=0.0, color=None, wl=34.0, opacity=None):
        """One stroke of the nib through pts: tapered, pressure-varied, slightly
        wandering. `over` lets it overshoot its ends by up to that many units, the way
        a quick hand does at corners."""
        pts = [(float(x), float(y)) for x, y in pts]
        if over and len(pts) >= 2:
            pts = self._overshoot(pts, over)
        P, total = resample(pts, step)
        if total <= 0.01:
            return
        n = len(P)
        wob = _Wobble(self.rnd, wl)
        press = _Wobble(self.rnd, wl * 0.6)
        ramp = max(1.0, min(13.0, total * 0.32))
        amp = min(amp, total * 0.035 + 0.25)
        left, right = [], []
        for i in range(n):
            a = P[max(0, i - 1)]
            b = P[min(n - 1, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            tl = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / tl, tx / tl
            s = total * i / (n - 1)
            d = amp * wob.at(s)
            px, py = P[i][0] + nx * d, P[i][1] + ny * d
            env = taper + (1 - taper) * smoothstep(min(s, total - s) / ramp)
            hw = 0.5 * w * env * (1 + 0.17 * press.at(s))
            left.append((px + nx * hw, py + ny * hw))
            right.append((px - nx * hw, py - ny * hw))
        d = qpath(left + right[::-1], True)
        if color or opacity is not None:
            extra = ' fill="%s"' % color if color else ""
            if opacity is not None:
                extra += ' fill-opacity="%s"' % fmt(opacity)
            self.raw('<path d="%s"%s/>' % (d, extra))
        else:
            self._ink.append(d)

    def _overshoot(self, pts, over):
        def ext(a, b, amount):
            dx, dy = a[0] - b[0], a[1] - b[1]
            length = math.hypot(dx, dy) or 1.0
            return (a[0] + dx / length * amount, a[1] + dy / length * amount)
        pts = list(pts)
        pts[0] = ext(pts[0], pts[1], self.rnd.uniform(0.2, 1.0) * over)
        pts[-1] = ext(pts[-1], pts[-2], self.rnd.uniform(0.2, 1.0) * over)
        return pts

    def line(self, a, b, w=2.0, over=2.5, **kw):
        self.pen([a, b], w=w, over=over, **kw)

    def edges(self, pts, w=2.0, over=2.5, closed=True, **kw):
        """A polygon drawn the way a hand draws one: a separate stroke per side."""
        n = len(pts)
        for i in range(n if closed else n - 1):
            self.pen([pts[i], pts[(i + 1) % n]], w=w, over=over, **kw)

    def loop(self, pts, w=2.0, overlap=0.12, **kw):
        """A closed curve in one stroke, the end running on past the start."""
        dense = spline(pts, closed=True, seg=4)
        extra = max(2, int(len(dense) * overlap))
        start = self.rnd.randrange(len(dense))
        dense = dense[start:] + dense[:start]
        self.pen(dense + dense[:extra], w=w, **kw)

    def outline(self, pts, w=2.0, overlap=6.0, **kw):
        """A closed shape in one stroke, following pts exactly (no splining), the end
        running a little way past the start. For shapes whose corners are already
        rounded with enough points."""
        pts = list(pts)
        start = self.rnd.randrange(len(pts))
        pts = pts[start:] + pts[:start]
        tail = [pts[0]]
        run = 0.0
        for a, b in zip(pts, pts[1:]):
            run += math.hypot(b[0] - a[0], b[1] - a[1])
            tail.append(b)
            if run >= overlap:
                break
        kw.setdefault("amp", 0.4)
        self.pen(pts + tail, w=w, **kw)

    def circle(self, cx, cy, r, w=2.0, squash=1.0, **kw):
        """A hand-drawn circle: very slightly out of true, closed with an overlap."""
        wob = _Wobble(self.rnd, 1.3)
        n = max(12, int(r * 1.1))
        start = self.rnd.uniform(0, 2 * math.pi)
        lap = min(0.5, 5.0 / max(r, 1.0)) + 0.06     # radians of overlap
        steps = int(round(n * (1 + lap / (2 * math.pi))))
        pts = []
        for i in range(steps + 1):
            a = start + 2 * math.pi * i / n
            rr = r + min(0.9, r * 0.016) * wob.at(a) + min(0.4, r * 0.006) * wob.at(a * 3)
            pts.append((cx + rr * math.cos(a), cy + rr * squash * math.sin(a)))
        kw.setdefault("amp", 0.0)
        kw.setdefault("step", max(2.0, min(11.0, r * 0.45)))
        kw.setdefault("taper", 0.55)
        self.pen(pts, w=w, **kw)

    def arc(self, cx, cy, rx, ry, a0, a1, w=2.0, **kw):
        kw.setdefault("amp", 0.4)
        self.pen(arc_pts(cx, cy, rx, ry, a0, a1), w=w, **kw)

    def curve(self, pts, w=2.0, **kw):
        self.pen(spline(pts), w=w, **kw)

    def dot(self, x, y, r=1.4, color=None):
        pts = circle_pts(x + self.rnd.uniform(-0.2, 0.2), y + self.rnd.uniform(-0.2, 0.2), r * self.rnd.uniform(0.85, 1.15), 7)
        d = qpath(pts, True)
        if color:
            self.raw('<path d="%s" fill="%s"/>' % (d, color))
        else:
            self._ink.append(d)

    # ---- fills ----------------------------------------------------------------------
    def ko(self, pts, color=PAPER):
        """Knock-out: opaque paper under an object so nothing behind shows through."""
        self.raw('<path d="%s" fill="%s"/>' % (lpath(pts), color))

    def wash(self, pts, color, op=0.5, amp=1.6, edge=0.2, grow=0.0, shift=(0, 0), step=15.0, smooth=True, glaze=True):
        """A loose watercolour fill: its own wandering edge (so it misses the pen line
        here and there) and a slightly darker rim where pigment would pool."""
        pts = [(float(x), float(y)) for x, y in pts]
        if grow:
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            rad = sum(math.hypot(p[0] - cx, p[1] - cy) for p in pts) / len(pts) or 1.0
            pts = scale_pts(pts, 1 + grow / rad, cx, cy)
        if shift != (0, 0):
            pts = shift_pts(pts, shift[0], shift[1])
        P, total = resample(pts, step, closed=True)
        wob = _Wobble(self.rnd, 46.0)
        n = len(P)
        Q = []
        for i in range(n):
            a = P[(i - 1) % n]
            b = P[(i + 1) % n]
            tx, ty = b[0] - a[0], b[1] - a[1]
            tl = math.hypot(tx, ty) or 1.0
            d = amp * wob.at(total * i / n)
            Q.append((P[i][0] - ty / tl * d, P[i][1] + tx / tl * d))
        d = qpath(Q, True) if smooth else lpath(Q)
        stroke = ""
        if edge:
            stroke = ' stroke="%s" stroke-opacity="%s" stroke-width="1.5"' % (color, fmt(edge))
        xs = [p[0] for p in Q]
        ys = [p[1] for p in Q]
        size = min(max(xs) - min(xs), max(ys) - min(ys))
        if not glaze or size < 12 or op < 0.3:
            self.raw('<path d="%s" fill="%s" fill-opacity="%s"%s/>' % (d, color, _op(op), stroke))
            return
        # first pass thin, then a second pass over most of it, pulled towards the
        # shadow side: the overlap edge is what makes it look painted
        self.raw('<path d="%s" fill="%s" fill-opacity="%s"%s/>' % (d, color, _op(op * 0.68), stroke))
        cx = sum(xs) / n
        cy = sum(ys) / n
        wob2 = _Wobble(self.rnd, 30.0)
        k = self.rnd.uniform(0.80, 0.9)
        off = min(4.0, size * 0.06)
        G = []
        for i in range(n):
            kk = k + 0.07 * wob2.at(total * i / n)
            G.append((cx + (Q[i][0] - cx) * kk + off, cy + (Q[i][1] - cy) * kk + off))
        self.raw('<path d="%s" fill="%s" fill-opacity="%s"/>' % (qpath(G, True), color, _op(op * 0.5)))

    def hatch(self, poly, angle=-45, gap=4.5, w=0.75, trim=0.22, skip=0.04, jit=0.6, fade=None, color=None, opacity=None):
        """Individual hatch strokes clipped to a polygon. `fade` = "a" or "b" lets the
        strokes die away from one end, for a shadow that feathers out."""
        a = math.radians(angle)
        c, s = math.cos(a), math.sin(a)
        R = [(x * c + y * s, -x * s + y * c) for x, y in poly]  # rotate by -angle
        ys = [p[1] for p in R]
        y = min(ys) + gap * 0.5
        n = len(R)
        segs = []
        while y < max(ys):
            yy = y + self.rnd.uniform(-jit, jit) * 0.5
            xs = []
            for i in range(n):
                p, q = R[i], R[(i + 1) % n]
                if (p[1] <= yy < q[1]) or (q[1] <= yy < p[1]):
                    xs.append(p[0] + (yy - p[1]) / (q[1] - p[1]) * (q[0] - p[0]))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                x0, x1 = xs[k], xs[k + 1]
                span = x1 - x0
                if span < 1.5 or self.rnd.random() < skip:
                    continue
                t0 = self.rnd.uniform(0, trim) * span
                t1 = self.rnd.uniform(0, trim) * span
                if fade == "a":
                    t0 = self.rnd.uniform(0.15, 0.75) * span
                    t1 *= 0.3
                elif fade == "b":
                    t1 = self.rnd.uniform(0.15, 0.75) * span
                    t0 *= 0.3
                x0 += t0
                x1 -= t1
                if x1 - x0 < 1.2:
                    continue
                y0 = yy + self.rnd.uniform(-jit, jit) * 0.4
                y1 = yy + self.rnd.uniform(-jit, jit) * 0.4
                bow = self.rnd.uniform(-jit, jit) * 0.8
                segs.append(((x0, y0), ((x0 + x1) / 2, (y0 + y1) / 2 + bow), (x1, y1)))
            y += gap * self.rnd.uniform(0.82, 1.18)
        if not segs:
            return
        d = []
        for p0, pm, p1 in segs:
            back = [(x * c - yv * s, x * s + yv * c) for x, yv in (p0, pm, p1)]
            d.append("M%sQ%s %s" % (pt(back[0]), pt(back[1]), pt(back[2])))
        extra = ""
        if opacity is not None:
            extra = ' stroke-opacity="%s"' % fmt(opacity)
        self.raw('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"%s/>' % ("".join(d), color or INK, fmt(w), extra))

    # ---- ready-made objects -------------------------------------------------------
    def box(self, x, y, w, h, fill=None, op=0.5, lw=2.0, over=2.5, ko=True, shade=True):
        pts = rect_pts(x, y, w, h)
        if ko:
            self.ko(pts)
        if fill:
            self.wash(pts, fill, op=op, grow=-1.5, shift=(1.0, 1.0))
            if shade:
                self.wash([(x + w * 0.62, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y + h * 0.7), (x + w * 0.62, y + h * 0.7)], PAYNE, op=0.16, edge=0)
        self.edges(pts, w=lw, over=over)

    def disc(self, cx, cy, r, fill=None, op=0.5, lw=2.0, ko=True, shade=True, squash=1.0):
        pts = ellipse_pts(cx, cy, r, r * squash)
        if ko:
            self.ko(pts)
        if fill:
            self.wash(pts, fill, op=op, grow=-1.2, shift=(0.8, 0.8))
            if shade:
                self.wash(self.crescent(cx, cy, r, squash), PAYNE, op=0.2, edge=0, amp=0.8)
        self.circle(cx, cy, r, w=lw, squash=squash)

    def crescent(self, cx, cy, r, squash=1.0, depth=0.42):
        """The shadow side of a disc lit from the upper left."""
        outer = arc_pts(cx, cy, r, r * squash, -35, 125, 12)
        inner = arc_pts(cx - r * depth, cy - r * depth * squash, r, r * squash, 108, -18, 12)
        return outer + inner

    def rivet(self, x, y, r=2.2):
        self.circle(x, y, r, w=1.0, amp=0.15)
        self.dot(x + r * 0.25, y + r * 0.3, r * 0.42)

    def screw(self, x, y, r=3.0, angle=None):
        if angle is None:
            angle = self.rnd.uniform(0, 180)
        self.ko(circle_pts(x, y, r, 10))
        self.wash(circle_pts(x, y, r, 10), BRASS, op=0.5, amp=0.3, step=4)
        self.circle(x, y, r, w=1.0, amp=0.15)
        a = math.radians(angle)
        self.pen([(x - math.cos(a) * r * 0.75, y - math.sin(a) * r * 0.75), (x + math.cos(a) * r * 0.75, y + math.sin(a) * r * 0.75)], w=1.0, amp=0.1)

    def glint(self, pts, w=2.0, opacity=0.85):
        self.pen(pts, w=w, color=GOUACHE, opacity=opacity, amp=0.3)

    def cog(self, cx, cy, r, teeth, depth=None, fill=BRASS, hub=None, spokes=5, lw=1.8, op=0.55):
        depth = depth or max(4.0, r * 0.16)
        ri = r - depth
        pts = []
        step = 360.0 / teeth
        for i in range(teeth):
            a = i * step
            pts += arc_pts(cx, cy, ri, ri, a, a + step * 0.38, 2)
            pts += arc_pts(cx, cy, r, r, a + step * 0.5, a + step * 0.88, 2)
        self.ko(pts)
        self.wash(pts, fill, op=op, amp=0.6, step=6, grow=-0.8)
        self.wash(self.crescent(cx, cy, ri), PAYNE, op=0.2, edge=0, amp=0.8)
        self.edges(pts, w=lw, over=0.6, amp=0.3, taper=0.7)
        hub = hub or r * 0.24
        if spokes:
            r_in, r_out = hub + r * 0.1, ri - r * 0.13
            sweep = 360.0 / spokes
            for i in range(spokes):
                a0 = i * sweep + sweep * 0.14
                a1 = (i + 1) * sweep - sweep * 0.14
                hole = annulus_sector(cx, cy, r_in, r_out, a0, a1, 5)
                self.ko(hole)
                self.wash(hole, PAYNE, op=0.22, edge=0, amp=0.5, step=6)
                self.hatch(hole, gap=3.2, w=0.6, trim=0.3)
                self.loop(hole, w=1.2, amp=0.3)
        self.disc(cx, cy, hub, fill=fill, op=op + 0.1, lw=1.5, shade=hub > 9)
        axle = circle_pts(cx, cy, max(2.0, hub * 0.4), 8)
        self.ko(axle)
        self.wash(axle, INK, op=0.6, amp=0.1, step=3, edge=0)
        self.circle(cx, cy, max(2.0, hub * 0.4), w=1.0)

    def pipe(self, pts, r=8.0, fill=VERDIGRIS, op=0.5, bend=None, lw=1.8, flanges=(), hatch=True):
        """A pipe along a polyline with rounded elbows; `flanges` are distances (0..1)
        along it at which to bolt a collar."""
        bend = bend if bend is not None else r * 1.6
        centre = self._rounded(pts, bend)
        P, total = resample(centre, 7.0)
        left, right, lo = [], [], []
        n = len(P)
        for i in range(n):
            a = P[max(0, i - 1)]
            b = P[min(n - 1, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            tl = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / tl, tx / tl
            left.append((P[i][0] + nx * r, P[i][1] + ny * r))
            right.append((P[i][0] - nx * r, P[i][1] - ny * r))
            lo.append((P[i][0] + nx * r * 0.35, P[i][1] + ny * r * 0.35))
        body = left + right[::-1]
        self.ko(body)
        self.wash(body, fill, op=op, amp=0.7, step=10, glaze=False)
        # the underside/right side takes the shadow: whichever offset curve lies lower-right
        dark = left if (left[n // 2][0] + left[n // 2][1]) > (right[n // 2][0] + right[n // 2][1]) else right
        inner = [(P[i][0] + (dark[i][0] - P[i][0]) * 0.3, P[i][1] + (dark[i][1] - P[i][1]) * 0.3) for i in range(n)]
        band = dark + inner[::-1]
        self.wash(band, PAYNE, op=0.24, edge=0, amp=0.4, step=10)
        if hatch:
            self.hatch(band, gap=3.4, w=0.6, trim=0.3, skip=0.12)
        self.pen(left, w=lw, amp=0.5)
        self.pen(right, w=lw, amp=0.5)
        for t in flanges:
            i = int(round(t * (n - 1)))
            i = max(1, min(n - 2, i))
            a, b = P[i - 1], P[i + 1]
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            self.flange(P[i][0], P[i][1], r, ang, fill=BRASS)
        return P

    def flange(self, x, y, r, angle, fill=BRASS, thick=7.0):
        hw, hh = thick / 2.0, r + 4.0
        pts = rotate_pts(rect_pts(x - hw, y - hh, thick, hh * 2), angle, x, y)
        self.ko(pts)
        self.wash(pts, fill, op=0.6, amp=0.4, step=6)
        self.edges(pts, w=1.5, over=1.0, amp=0.3)
        for dy in (-hh + 2.6, hh - 2.6):
            p = rotate_pts([(x, y + dy)], angle, x, y)[0]
            self.dot(p[0], p[1], 1.1)

    def _rounded(self, pts, radius):
        if len(pts) < 3 or radius <= 0:
            return list(pts)
        out = [pts[0]]
        for i in range(1, len(pts) - 1):
            p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
            d0 = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            d1 = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            rr = min(radius, d0 / 2.0, d1 / 2.0)
            a = (p1[0] + (p0[0] - p1[0]) * rr / d0, p1[1] + (p0[1] - p1[1]) * rr / d0)
            b = (p1[0] + (p2[0] - p1[0]) * rr / d1, p1[1] + (p2[1] - p1[1]) * rr / d1)
            for k in range(7):
                t = k / 6.0
                out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * p1[0] + t * t * b[0],
                            (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * p1[1] + t * t * b[1]))
        out.append(pts[-1])
        return out
