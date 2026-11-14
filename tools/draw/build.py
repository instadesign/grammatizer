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
            size = write(os.path.join(OUT_PLATES, name + ".svg"), make().svg())
            total += size
            print("%-16s %6.1f KB" % (name, size / 1024.0))
    write(os.path.join(ROOT, "css", "layout.css"), layout.css())
    print("total %.1f KB" % (total / 1024.0))


if __name__ == "__main__":
    main(sys.argv)
