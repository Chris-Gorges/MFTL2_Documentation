"""Figures for ``src/ensemble/README.md`` -- per-body collectives over the holders."""

from __future__ import annotations

import numpy as np

from mftlfig import register
from mftlfig.style import C, box, canvas, dot, fheading, figure, halo_label, label, lighten, note


def _grid(ax, n=3, h=1.0):
    for i in range(n + 1):
        ax.plot([0, n * h], [i * h, i * h], color=C.rule, lw=0.9, zorder=0)
        ax.plot([i * h, i * h], [0, n * h], color=C.rule, lw=0.9, zorder=0)


def _tube(ax, pts, width=0.2, fc=None, ec=None):
    """A closed 'body': a thick rounded polyline outline."""

    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=ec or C.blue, lw=13, solid_capstyle="round", solid_joinstyle="round", zorder=2)
    ax.plot(xs, ys, color=fc or C.blue_fill, lw=10.4, solid_capstyle="round", solid_joinstyle="round", zorder=2)


def _holder(ax, cell, col, text=None, h=1.0):
    i, j = cell
    box(ax, i * h + 0.05, j * h + 0.05, h - 0.1, h - 0.1, fc=lighten(col, 0.86), ec=col, lw=1.0, r=0.06, zorder=1)
    if text:
        label(ax, i * h + 0.17, j * h + 0.83, text, size=7.0, color=col, ha="left")


@register("holder-certificate")
def holder_certificate():
    fig = figure(7.0, 2.85)
    fheading(fig, 0.0, 0.95, "a", "holders span one cell per axis: a clique")
    fheading(fig, 0.51, 0.95, "b", "a bent body: the ends never meet")

    # ---------------------------------------------------------------- (a)
    ax = canvas(fig, [0.0, 0.0, 0.46, 0.88], (-0.2, 3.35), (-0.4, 3.1))
    _grid(ax)
    H = [(0, 1), (1, 1), (0, 2), (1, 2)]
    for c in H:
        _holder(ax, c, C.blue)
    t = np.linspace(0, 2 * np.pi, 120)
    r = 1.0 + 0.08 * np.cos(3 * t) + 0.05 * np.sin(2 * t)
    blob = np.stack([1.0 + 0.62 * r * np.cos(t), 2.0 + 0.5 * r * np.sin(t)], 1)
    from mftlfig.style import tri as _poly

    _poly(ax, blob, C.blue_fill, ec=C.blue, lw=1.4, zorder=2)
    cen = {c: np.array([c[0] + 0.5, c[1] + 0.5]) for c in H}
    for a in H:
        for b in H:
            if a < b:
                ax.plot(*np.array([cen[a], cen[b]]).T, color=C.blue_dark, lw=0.9, zorder=3, ls=(0, (3, 2)))
    for c in H:
        dot(ax, cen[c], r=0.07, fc=C.blue_dark, zorder=4)
    note(ax, 1.5, -0.2, "every holder hears every other: fold locally", size=6.9, color=C.blue_dark)
    note(ax, 3.1, 2.5, "rank\ncells", size=6.4, color=C.ink_faint, ha="left")

    # ---------------------------------------------------------------- (b)
    bx = canvas(fig, [0.51, 0.0, 0.49, 0.88], (-0.2, 3.75), (-0.4, 3.1))
    _grid(bx)
    a, m1, m2, c = (0, 0), (1, 0), (1, 1), (2, 1)
    for cell, col, t in ((a, C.cyan, r"$a$"), (m1, C.blue, r"$m$"), (m2, C.blue, r"$m'$"), (c, C.cyan, r"$c$")):
        _holder(bx, cell, col)
        label(bx, cell[0] + 0.2, cell[1] + 0.8, t, size=10, color=col)
    _tube(bx, [(0.3, 0.45), (1.5, 0.4), (1.55, 1.55), (2.7, 1.6)])
    cen = {k: np.array([k[0] + 0.5, k[1] + 0.5]) for k in (a, m1, m2, c)}
    # graph edges among the holders (each a neighbour of the next)
    for p, q in ((a, m1), (m1, m2), (m2, c), (a, m2), (m1, c)):
        bx.plot(*np.array([cen[p], cen[q]]).T, color=C.blue_dark, lw=0.9, zorder=3, ls=(0, (3, 2)))
    # a and c are two cells apart on x: not neighbours
    bx.plot(*np.array([cen[a], cen[c]]).T, color=C.coral, lw=1.2, zorder=3)
    mid = 0.5 * (cen[a] + cen[c])
    halo_label(bx, mid[0] + 0.05, mid[1] - 0.02, "×", color=C.coral, size=12)
    for k in (a, m1, m2, c):
        dot(bx, cen[k], r=0.07, fc=C.blue_dark if k in (m1, m2) else C.cyan, zorder=4)
    note(bx, 3.1, 1.5, "before the exchange\nevery rank sees only\nneighbours: passes", ha="left", size=6.6,
         color=C.ink, linespacing=1.3)
    note(bx, 3.1, 0.55, "after it, $m$ holds\nrecords from $a$ and $c$:\nspan 3 cells, veto", ha="left",
         size=6.6, color=C.coral, linespacing=1.3)
    note(bx, 1.5, -0.2, "one MPI_LAND agrees the veto; the global route runs", size=6.9, color=C.coral)
    return fig
