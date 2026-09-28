#!/usr/bin/env python3
"""Draw the manual's figures into ``images/``.

    python3 figures/build_figures.py                 # every figure
    python3 figures/build_figures.py halfedge-implicit icosphere
    python3 figures/build_figures.py --list
    python3 figures/build_figures.py --png DIR       # also write PNG previews

The SVGs are committed: building the manual needs neither this script nor
matplotlib. Output is deterministic (fixed hash salt, no timestamp), so
re-running it on an unchanged tree leaves ``git status`` clean, and a diff in
``images/`` is a real change to a figure.

Requires numpy, scipy and matplotlib (``figures/requirements.txt``).
"""

from __future__ import annotations

import argparse
import importlib
import os
import pkgutil
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(os.path.dirname(HERE), "images")
sys.path.insert(0, HERE)

#: Intrinsic display scale. Figures are composed at print size (a 7 in column,
#: 8-10 pt labels); the web manual's column is wider than 7 in at 96 px/in, so
#: the SVG's width/height are scaled up and the viewBox left alone. Labels then
#: show at about the size of the body text instead of a footnote's.
DISPLAY_SCALE = 1.25

import mftlfig  # noqa: E402
from mftlfig import style  # noqa: E402


def load_gallery() -> None:
    """Import every module of ``gallery/``; each registers its figures."""
    import gallery

    for mod in pkgutil.iter_modules(gallery.__path__):
        importlib.import_module(f"gallery.{mod.name}")


def render(name: str, png_dir: str | None) -> str:
    """Draw one figure and write ``images/<name>.svg`` (and a PNG preview).

    :returns: the SVG path.
    """
    import matplotlib.pyplot as plt

    fig = mftlfig.REGISTRY[name]()
    out = os.path.join(IMAGES, f"{name}.svg")
    fig.savefig(out, format="svg", bbox_inches="tight", pad_inches=0.06, metadata={"Date": None})
    plt.close(fig)
    with open(out, encoding="utf-8") as fh:
        svg = fh.read()

    def scaled(m: re.Match) -> str:
        return f'{m.group(1)}="{float(m.group(2)) * DISPLAY_SCALE:.2f}pt"'

    head, rest = svg.split("<svg", 1)
    tag, body = rest.split(">", 1)
    tag = re.sub(r'(width|height)="([0-9.]+)pt"', scaled, tag)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(head + "<svg" + tag + ">" + body)
    if png_dir:
        os.makedirs(png_dir, exist_ok=True)
        png = os.path.join(png_dir, f"{name}.png")
        subprocess.run(["rsvg-convert", "-z", "1.6", "-b", "white", "-o", png, out], check=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="figures to draw (default: all)")
    ap.add_argument("--list", action="store_true", help="list the registered figures and exit")
    ap.add_argument("--png", metavar="DIR", help="also write PNG previews into DIR (needs rsvg-convert)")
    args = ap.parse_args()

    style.apply_rc()
    load_gallery()
    if args.list:
        for name in sorted(mftlfig.REGISTRY):
            print(name)
        return 0
    names = args.names or sorted(mftlfig.REGISTRY)
    unknown = [n for n in names if n not in mftlfig.REGISTRY]
    if unknown:
        print(f"unknown figure(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    for name in names:
        path = render(name, args.png)
        print(f"  {os.path.relpath(path, os.path.dirname(HERE))}  ({os.path.getsize(path) / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
