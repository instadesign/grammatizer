"""Contact sheets: a drawing's motion laid out as still frames, to look at.

    python3 -m tools.draw.frames OUT.html NAME[:SECONDS[:COUNT]] ...     (from the repo root)

    python3 -m tools.draw.frames /tmp/sheet.html engine-gemini:2.6 life-cat:12:16

Each NAME is a file in assets/svg/parts/ (build it first). The sheet shows COUNT frames
(default 12) spread evenly over SECONDS (default 8), each one the drawing frozen at that
moment. It works because every animation the drawing engine writes can be frozen from
outside by two custom properties on the root (see Drawing.animate in ink.py).

Nothing on the site uses this. It exists because motion cannot be reviewed from a single
screenshot, and a headless browser's clock is not a dependable way to catch a pose.
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PARTS = os.path.join(ROOT, "assets", "svg", "parts")

PAGE = """<!doctype html><meta charset="utf-8"><title>frames</title>
<style>
  body { margin: 16px; background: #f7f1e1; font: 13px/1.3 ui-monospace, monospace; color: #2a211b; }
  h2 { font: inherit; font-weight: 700; margin: 18px 0 6px; }
  .row { display: flex; flex-wrap: wrap; gap: 8px; }
  figure { margin: 0; }
  .shadow { background: #ede0c8; outline: 1px solid rgba(42,33,27,.25); line-height: 0; }
  figcaption { text-align: center; opacity: .7; }
</style>
%s
"""


def frozen(svg, t, zoom):
    """The drawing's markup, stopped at t seconds and scaled for the sheet."""
    head, rest = svg.split(">", 1)
    w = float(head.split('width="')[1].split('"')[0])
    h = float(head.split('height="')[1].split('"')[0])
    head = head.replace('width="%s"' % head.split('width="')[1].split('"')[0], 'width="%g"' % (w * zoom))
    head = head.replace('height="%s"' % head.split('height="')[1].split('"')[0], 'height="%g"' % (h * zoom))
    return '%s style="--t:%gs;--ps:paused">%s' % (head, t, rest)


def main(argv):
    out, specs = argv[1], argv[2:]
    blocks = []
    for n, spec in enumerate(specs):
        bits = spec.split(":")
        name = bits[0]
        seconds = float(bits[1]) if len(bits) > 1 else 8.0
        count = int(bits[2]) if len(bits) > 2 else 12
        zoom = float(bits[3]) if len(bits) > 3 else 1.5
        with open(os.path.join(PARTS, name + ".svg")) as fh:
            svg = fh.read()
        # Inline, so each copy needs its class names kept apart from the other drawings'
        # on the page: every one goes in its own shadow tree.
        frames = []
        for i in range(count):
            t = seconds * i / float(count)
            frames.append('<figure><div class="shadow" data-svg="%d-%d"></div><figcaption>%.2fs</figcaption></figure>' % (n, i, t))
            frames.append('<template id="t%d-%d">%s</template>' % (n, i, frozen(svg, t, zoom)))
        blocks.append("<h2>%s, %gs</h2><div class=\"row\">%s</div>" % (name, seconds, "".join(frames)))
    script = """<script>
    document.querySelectorAll(".shadow").forEach(function (host) {
      var root = host.attachShadow({ mode: "open" });
      root.appendChild(document.getElementById("t" + host.dataset.svg).content.cloneNode(true));
    });
    </script>"""
    with open(out, "w") as fh:
        fh.write(PAGE % ("".join(blocks) + script))
    print("wrote %s" % out)


if __name__ == "__main__":
    main(sys.argv)
