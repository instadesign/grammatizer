"""Redraws every SVG in assets/svg/ from the drawing code.

    python3 -m tools.draw.build            (from the repo root)

The output files are committed; the site never runs this. Re-run it only after
changing the drawing code.
"""

import os
import sys

from . import layout, parts

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_PARTS = os.path.join(ROOT, "assets", "svg", "parts")
OUT_PLATES = os.path.join(ROOT, "assets", "svg", "plates")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)
    return len(text)


def main(argv):
    only = set(argv[1:])
    total = 0
    for name, make in sorted(parts.PARTS.items()):
        if only and name not in only:
            continue
        size = write(os.path.join(OUT_PARTS, name + ".svg"), make().svg())
        total += size
        print("%-16s %6.1f KB" % (name, size / 1024.0))
    try:
        from . import plates
    except ImportError:
        plates = None
    if plates:
        for name, make in sorted(plates.PLATES.items()):
            if only and name not in only:
                continue
            drawing = make()
            size = write(os.path.join(OUT_PLATES, name + ".svg"), drawing.svg())
            total += size
            print("%-16s %6.1f KB" % (name, size / 1024.0))
            # What moves on a plate is lifted out of it (Drawing.lift) into small
            # files of its own, laid back over it by the rules in css/layout.css.
            for layer in sorted(drawing.layers):
                size = write(os.path.join(OUT_PARTS, "life-%s.svg" % layer), drawing.layer_svg(layer))
                total += size
                print("  life-%-9s %6.1f KB" % (layer, size / 1024.0))
    write(os.path.join(ROOT, "css", "layout.css"), layout.css())
    print("total %.1f KB" % (total / 1024.0))


if __name__ == "__main__":
    main(sys.argv)
