"""House style of the MFTL figures: palette, typography, and 2D drawing helpers.

Every figure in the manual is drawn through this module so that the whole set
reads as one family: the same ink, the same fills, the same arrowheads, the
same way of setting a label. The palette is the manual's own -- hue 209, the
blue of ``manual/stylesheets/mftl.css`` and ``HTML_COLORSTYLE_HUE`` -- plus a
small set of categorical accents, each with a pale fill that carries the same
meaning over a large area.

Conventions the figures follow:

* **Blue** is "this rank", "owned", "the object being described".
* **Cyan** is the second party: the other rank, the neighbour, the twin.
* **Coral** is the one thing the eye should land on: the edge being collapsed,
  the vector that is wrong, the event.
* **Amber** marks derived or replicated state (ghosts, frozen, caches).
* **Grey** is context.

Mathematics is set in Computer Modern through matplotlib's mathtext, and all
text is converted to outlines in the SVG, so a figure renders identically on a
machine with none of the fonts installed.
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon  # noqa: E402

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Palette:
    """Named colours; every figure takes its colours from here, never inline."""

    ink: str = "#1b2331"
    ink_soft: str = "#5a6577"
    ink_faint: str = "#9aa4b2"
    rule: str = "#cfd6df"
    paper: str = "#ffffff"

    blue: str = "#1f67a8"
    blue_dark: str = "#12507e"
    blue_fill: str = "#dbe8f5"
    blue_mid: str = "#9cc0e4"

    cyan: str = "#0a8fa3"
    cyan_fill: str = "#d4eff3"
    cyan_mid: str = "#8fd3de"

    coral: str = "#dd5a35"
    coral_fill: str = "#fbe2d8"
    coral_mid: str = "#f2a88f"

    amber: str = "#d99a2b"
    amber_fill: str = "#fbefd6"
    amber_mid: str = "#f0cf8f"

    green: str = "#3a9467"
    green_fill: str = "#dcefe4"

    violet: str = "#7658a6"
    violet_fill: str = "#e9e2f3"

    grey_fill: str = "#eef1f5"
    grey_mid: str = "#d5dbe3"


C = Palette()

#: Diverging map for signed quantities (negative = inside = blue, positive = coral).
SIGNED_CMAP = matplotlib.colors.LinearSegmentedColormap.from_list(
    "mftl_signed", ["#12507e", "#5b9bd0", "#e8eef5", "#f3b39c", "#c9482a"]
)
#: Sequential map for orders and indices.
ORDER_CMAP = matplotlib.colors.LinearSegmentedColormap.from_list(
    "mftl_order", ["#0a3a5e", "#1f67a8", "#0a8fa3", "#6cc3a0", "#e8c35a"]
)

# --------------------------------------------------------------------------
# Typography
# --------------------------------------------------------------------------

#: Text face for annotations. Math is always Computer Modern (mathtext "cm").
TEXT_FONTS = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]  # resolved in apply_rc()

def _installed(names: list[str]) -> list[str]:
    """The subset of ``names`` matplotlib can find, in order (no fallback warnings)."""
    from matplotlib import font_manager

    have = {f.name for f in font_manager.fontManager.ttflist}
    found = [n for n in names if n in have]
    return found or [names[-1]]


#: Face for identifiers (struct fields, array names).
MONO_FONTS = _installed(["JetBrains Mono", "Menlo", "SF Mono", "DejaVu Sans Mono"])

FS_SMALL = 7.6
FS = 8.6
FS_MATH = 10.0
FS_TITLE = 9.2


def apply_rc() -> None:
    """Install the house rcParams. Called once by the driver."""
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": _installed(TEXT_FONTS),
            "font.size": FS,
            "mathtext.fontset": "cm",
            "mathtext.default": "it",
            "svg.fonttype": "path",
            "svg.hashsalt": "mftl-figures",
            "axes.unicode_minus": True,
            "lines.solid_capstyle": "round",
            "lines.solid_joinstyle": "round",
            "lines.dash_capstyle": "round",
            "patch.linewidth": 0.8,
            "hatch.linewidth": 0.6,
            "figure.dpi": 100,
            "savefig.transparent": True,
        }
    )


# --------------------------------------------------------------------------
# Figures and panels
# --------------------------------------------------------------------------

#: Width of a full-column figure, inches. The manual's text column is about
#: 45 rem = 720 px, so a figure is shown at roughly its natural size.
FULL = 7.0


def figure(width: float = FULL, height: float = 3.0):
    """A blank figure with no axes."""
    return plt.figure(figsize=(width, height))


def canvas(fig, rect, xlim, ylim, equal: bool = True):
    """An invisible axes in figure-fraction ``rect`` with data limits.

    :param fig: the figure.
    :param rect: ``[left, bottom, width, height]`` in figure fractions.
    :param xlim: data x-range.
    :param ylim: data y-range.
    :param equal: lock the aspect ratio (geometry is always drawn true to shape).
    :returns: the axes.
    """
    ax = fig.add_axes(rect)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    if equal:
        ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    return ax


def heading(ax, letter: str, text: str = "", x: float = 0.0, y: float = 1.0, ha: str = "left",
            size: float = FS_TITLE, color=None) -> None:
    """Set a panel heading ``(a)  Text`` in axes fraction: the letter bold, the text regular.

    The text is placed after the letter by measuring the letter, so the gap is
    the same in every panel whatever its width.
    """
    color = color or C.ink
    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    t1 = ax.text(0, 0, f"({letter})", transform=ax.transAxes, fontsize=size, fontweight="bold", color=color,
                 ha="left", va="baseline")
    w1 = t1.get_window_extent(renderer).width
    t2 = ax.text(0, 0, text, transform=ax.transAxes, fontsize=size, color=color, ha="left", va="baseline")
    w2 = t2.get_window_extent(renderer).width if text else 0.0
    gap = 0.45 * size * fig.dpi / 72.0
    total = w1 + (gap + w2 if text else 0.0)
    axw = ax.get_window_extent(renderer).width
    x0 = x if ha == "left" else (x - 0.5 * total / axw if ha == "center" else x - total / axw)
    t1.set_position((x0, y))
    t2.set_position((x0 + (w1 + gap) / axw, y))


def fheading(fig, x: float, y: float, letter: str, text: str = "", size: float = FS_TITLE, color=None) -> None:
    """A panel heading ``(a)  Text`` at figure-fraction ``(x, y)`` (baseline, left-aligned).

    Headings are placed in figure coordinates so that panels of different
    aspect ratio still have their headings on one line.
    """
    color = color or C.ink
    renderer = fig.canvas.get_renderer()
    t1 = fig.text(x, y, f"({letter})", fontsize=size, fontweight="bold", color=color, ha="left", va="baseline")
    if text:
        w1 = t1.get_window_extent(renderer).width / fig.bbox.width
        gap = 0.45 * size / 72.0 / fig.get_figwidth()
        fig.text(x + w1 + gap, y, text, fontsize=size, color=color, ha="left", va="baseline")


#: Annotation text below this size is enlarged by SMALL_TEXT_BOOST: a full-width
#: figure is shown at about the column width, where 6.5 pt would read as a footnote.
SMALL_TEXT = 8.0
SMALL_TEXT_BOOST = 1.12


def _readable(size: float) -> float:
    return size * SMALL_TEXT_BOOST if size < SMALL_TEXT else size


def label(ax, x, y, s, color=None, size=None, ha="center", va="center", **kw):
    """Place a label at data coordinates. Math labels are sized up a little."""
    if size is None:
        size = FS_MATH if s.startswith("$") and s.endswith("$") else FS
    return ax.text(x, y, s, color=color or C.ink, fontsize=_readable(size), ha=ha, va=va, **kw)


def halo_label(ax, x, y, s, color=None, size=None, halo=C.paper, lw=2.6, **kw):
    """A label with a paper-coloured outline so it stays legible over lines."""
    import matplotlib.patheffects as pe

    t = label(ax, x, y, s, color=color, size=size, **kw)
    t.set_path_effects([pe.withStroke(linewidth=lw, foreground=halo)])
    return t


def code(ax, x, y, s, color=None, size=7.4, **kw):
    """An identifier set in the monospace face."""
    kw.setdefault("ha", "center")
    kw.setdefault("va", "center")
    return ax.text(x, y, s, color=color or C.ink, fontsize=_readable(size), fontfamily=MONO_FONTS, **kw)


def note(ax, x, y, s, color=None, size=FS_SMALL, **kw):
    """Secondary annotation text (soft ink, small)."""
    return label(ax, x, y, s, color=color or C.ink_soft, size=size, **kw)


# --------------------------------------------------------------------------
# Arrows: a TikZ "stealth" head drawn as a polygon in data coordinates
# --------------------------------------------------------------------------


def stealth_head(tip, direction, length=0.1, width=0.075, inset=0.28):
    """Vertices of a stealth arrowhead (a concave kite) pointing along ``direction``.

    Drawn in data coordinates, so it is only correct on an equal-aspect axes --
    which every geometric figure here is.
    """
    d = np.asarray(direction, float)
    n = np.linalg.norm(d)
    if n == 0.0:
        return None
    d = d / n
    p = np.array([-d[1], d[0]])
    tip = np.asarray(tip, float)
    back = tip - length * d
    return np.array([tip, back + 0.5 * width * p, tip - (1.0 - inset) * length * d, back - 0.5 * width * p])


def arrow(ax, p, q, color=None, lw=1.1, head=0.09, width=None, zorder=5, shorten=0.0,
          start_shorten=0.0, ls="-", both=False, alpha=1.0, capstyle="round"):
    """A straight arrow from ``p`` to ``q`` with a stealth head.

    :param shorten: pull the tip back from ``q`` by this data length (to stop at a dot).
    :param start_shorten: likewise for the tail.
    :param both: heads at both ends.
    """
    color = color or C.ink
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    d = q - p
    L = np.linalg.norm(d)
    if L == 0.0:
        return
    u = d / L
    p = p + start_shorten * u
    q = q - shorten * u
    width = head * 0.78 if width is None else width
    tail = q - 0.72 * head * u
    tail0 = p + 0.72 * head * u if both else p
    ax.plot([tail0[0], tail[0]], [tail0[1], tail[1]], color=color, lw=lw, ls=ls, zorder=zorder,
            alpha=alpha, solid_capstyle=capstyle)
    for tip, dd in ([(q, u)] + ([(p, -u)] if both else [])):
        hv = stealth_head(tip, dd, head, width)
        ax.add_patch(Polygon(hv, closed=True, fc=color, ec=color, lw=0.4, zorder=zorder, alpha=alpha,
                             joinstyle="miter"))


def curved_arrow(ax, p, q, bend=0.25, color=None, lw=1.0, head=0.08, zorder=5, n=40, ls="-", shorten=0.0,
                 start_shorten=0.0):
    """A circular-arc arrow from ``p`` to ``q``; ``bend`` is the sagitta over the chord."""
    color = color or C.ink
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    m = 0.5 * (p + q)
    d = q - p
    L = np.linalg.norm(d)
    nrm = np.array([-d[1], d[0]]) / L
    c = m + bend * L * nrm
    t = np.linspace(0, 1, n)
    pts = (1 - t)[:, None] ** 2 * p + 2 * ((1 - t) * t)[:, None] * c + (t ** 2)[:, None] * q
    # trim by arc length
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    keep = (s >= start_shorten) & (s <= s[-1] - shorten - 0.6 * head)
    pts_line = pts[keep]
    ax.plot(pts_line[:, 0], pts_line[:, 1], color=color, lw=lw, zorder=zorder, ls=ls)
    tip_idx = np.searchsorted(s, s[-1] - shorten)
    tip_idx = min(tip_idx, len(pts) - 1)
    tip = pts[tip_idx]
    direction = pts[tip_idx] - pts[max(tip_idx - 3, 0)]
    hv = stealth_head(tip, direction, head, head * 0.78)
    ax.add_patch(Polygon(hv, closed=True, fc=color, ec=color, lw=0.4, zorder=zorder, joinstyle="miter"))


def dim_line(ax, p, q, text, offset=0.0, color=None, lw=0.7, head=0.06, text_offset=0.08, size=None, **kw):
    """A dimension line with heads at both ends and a label beside its middle."""
    color = color or C.ink_soft
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    d = q - p
    n = np.array([-d[1], d[0]]) / np.linalg.norm(d)
    p2, q2 = p + offset * n, q + offset * n
    arrow(ax, p2, q2, color=color, lw=lw, head=head, both=True)
    m = 0.5 * (p2 + q2) + text_offset * n
    label(ax, m[0], m[1], text, color=color, size=size, **kw)


def dot(ax, p, r=0.045, fc=None, ec=None, lw=0.9, zorder=8):
    """A vertex marker: a filled disc with a paper-coloured ring."""
    from matplotlib.patches import Circle

    ax.add_patch(Circle(p, r, fc=fc or C.ink, ec=ec or C.paper, lw=lw, zorder=zorder))


def ring(ax, p, r=0.045, ec=None, fc=None, lw=0.9, zorder=8):
    """A hollow vertex marker."""
    from matplotlib.patches import Circle

    ax.add_patch(Circle(p, r, fc=fc or C.paper, ec=ec or C.ink, lw=lw, zorder=zorder))


def tri(ax, pts, fc, ec=None, lw=0.8, zorder=2, alpha=1.0, hatch=None, ls="-"):
    """A filled polygon (usually a triangle) in data coordinates."""
    poly = Polygon(np.asarray(pts), closed=True, fc=fc, ec=ec or C.ink, lw=lw, zorder=zorder, alpha=alpha,
                   joinstyle="round", ls=ls)
    if hatch:
        poly.set_hatch(hatch)
    ax.add_patch(poly)
    return poly


def box(ax, x, y, w, h, fc, ec=None, lw=0.8, r=0.02, zorder=2, **kw):
    """A rounded rectangle from its lower-left corner."""
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec or C.ink, lw=lw,
                       zorder=zorder, **kw)
    ax.add_patch(p)
    return p


def lighten(color, amount):
    """Mix ``color`` with white; ``amount`` = 0 keeps it, 1 is white."""
    rgb = np.array(matplotlib.colors.to_rgb(color))
    return tuple(rgb + (1.0 - rgb) * amount)


def mix(c1, c2, t):
    """Linear mix of two colours."""
    a = np.array(matplotlib.colors.to_rgb(c1))
    b = np.array(matplotlib.colors.to_rgb(c2))
    return tuple(a * (1 - t) + b * t)
