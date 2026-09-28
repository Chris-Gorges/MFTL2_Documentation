"""Figures for ``src/object/README.md`` -- the Morton renumbering."""

from __future__ import annotations

import numpy as np

from mftlfig import register
from mftlfig.meshes import edges_of, jittered_patch
from mftlfig.style import (C, ORDER_CMAP, box, canvas, fheading, figure, label, lighten, note)


def spread2(v: int, bits: int) -> int:
    """Interleave: bit i of v goes to bit 2i (the 2D analogue of MFTLMortonSpread3)."""
    out = 0
    for i in range(bits):
        out |= ((v >> i) & 1) << (2 * i)
    return out


def morton2(ix: int, iy: int, bits: int) -> int:
    return spread2(ix, bits) | (spread2(iy, bits) << 1)


@register("morton")
def morton():
    fig = figure(7.0, 3.0)
    fheading(fig, 0.0, 0.95, "a", "Z-order over the quantised box (2D for clarity)")
    fheading(fig, 0.47, 0.95, "b", "the key interleaves the bits")
    fheading(fig, 0.47, 0.475, "c", "edges in index space, before and after")

    bits = 3
    n = 1 << bits
    # a small planar mesh
    P, F = jittered_patch(7, 7, jitter=0.2, seed=11)
    P = P - P.min(0)
    s = (n - 1e-6) / P.max()  # one common scale for both axes: cubic cells
    Q = np.floor(P * s).astype(int)
    keys = np.array([morton2(x, y, bits) for x, y in Q])
    order = np.argsort(keys, kind="stable")  # stable, as the radix sort is
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))

    # ---------------------------------------------------------------- (a)
    ax = canvas(fig, [0.0, 0.0, 0.45, 0.9], (-0.35, n + 0.2), (-0.55, n + 0.25))
    for i in range(n + 1):
        ax.plot([0, n], [i, i], color=C.rule, lw=0.5, zorder=0)
        ax.plot([i, i], [0, n], color=C.rule, lw=0.5, zorder=0)
    # the curve through the cell centres
    cells = sorted(((morton2(x, y, bits), x, y) for x in range(n) for y in range(n)))
    pts = np.array([[x + 0.5, y + 0.5] for _, x, y in cells])
    for k in range(len(pts) - 1):
        col = ORDER_CMAP(k / (len(pts) - 1))
        ax.plot(pts[k:k + 2, 0], pts[k:k + 2, 1], color=lighten(col, 0.35), lw=1.3, zorder=1,
                solid_capstyle="round")
    X = P * s
    E = edges_of(F)
    for (a, b) in E:
        ax.plot([X[a, 0], X[b, 0]], [X[a, 1], X[b, 1]], color=C.ink, lw=0.5, zorder=2, alpha=0.45)
    cols = ORDER_CMAP(rank / (len(rank) - 1))
    ax.scatter(X[:, 0], X[:, 1], s=16, c=cols, edgecolors=C.paper, linewidths=0.6, zorder=3)
    for i in range(n):
        note(ax, i + 0.5, -0.25, f"{i:03b}", size=5.8, color=C.ink_faint)
        note(ax, -0.2, i + 0.5, f"{i:03b}", size=5.8, color=C.ink_faint, ha="right")
    label(ax, n / 2, -0.47, r"$x$", size=8.6, color=C.ink_soft)

    # ---------------------------------------------------------------- (b)
    bx = canvas(fig, [0.47, 0.545, 0.53, 0.36], (0, 7.0), (0, 1.55), equal=False)
    xb, yb = "101", "011"  # most significant bit first
    w, zx0 = 0.4, 0.75
    zbits = [yb[0], xb[0], yb[1], xb[1], yb[2], xb[2]]
    for j, ch in enumerate(zbits):
        isy = j % 2 == 0
        fc, ec, tc = (C.cyan_fill, C.cyan, C.cyan) if isy else (C.blue_fill, C.blue, C.blue_dark)
        xc = zx0 + j * w
        box(bx, xc, 0.6, w - 0.05, 0.34, fc=fc, ec=ec, lw=0.7, r=0.03)
        label(bx, xc + (w - 0.05) / 2, 0.77, ch, size=8, color=tc)
        # the source bit, above (x) or below (y) its slot
        ys = 0.08 if isy else 1.12
        box(bx, xc, ys, w - 0.05, 0.34, fc=fc, ec=ec, lw=0.7, r=0.03)
        label(bx, xc + (w - 0.05) / 2, ys + 0.17, ch, size=8, color=tc)
        from mftlfig.style import arrow as _arrow

        y_from, y_to = (0.44, 0.58) if isy else (1.1, 0.96)
        _arrow(bx, (xc + (w - 0.05) / 2, y_from), (xc + (w - 0.05) / 2, y_to), color=ec, lw=0.7, head=0.07)
    label(bx, 0.45, 1.29, r"$x$", size=9.4)
    label(bx, 0.45, 0.25, r"$y$", size=9.4)
    label(bx, 0.45, 0.77, r"$Z$", size=9.4)
    label(bx, 3.35, 0.9, r"$Z=\sum_i x_i\,2^{3i}+y_i\,2^{3i+1}+z_i\,2^{3i+2}$", size=8.8, ha="left")
    note(bx, 3.35, 0.55, "3D: 21 bits per axis, a 63-bit key", size=6.8, ha="left")

    # ---------------------------------------------------------------- (c)
    cx = canvas(fig, [0.47, 0.0, 0.53, 0.41], (0, 7.0), (-0.1, 1.65), equal=False)
    m = len(P)
    rng = np.random.default_rng(3)
    before = rng.permutation(m)  # an arbitrary numbering, as a generator might leave it
    x0, x1 = 0.55, 6.85

    def strip(y, index, colour, name):
        xs = x0 + (x1 - x0) * np.arange(m) / (m - 1)
        cx.plot([x0, x1], [y, y], color=C.rule, lw=0.8, zorder=0)
        dist = []
        for (a, b) in E:
            ia, ib = sorted((index[a], index[b]))
            dist.append(ib - ia)
            xa, xb2 = xs[ia], xs[ib]
            t = np.linspace(0, np.pi, 24)
            r = (xb2 - xa) / 2
            hgt = min(0.55, 0.012 * (ib - ia) + 0.05)
            cx.plot(xa + r - r * np.cos(t), y + hgt * np.sin(t), color=colour, lw=0.5, alpha=0.7, zorder=1)
        note(cx, x0 - 0.08, y + 0.05, name, ha="right", size=6.8, color=C.ink)
        return np.mean(dist)

    d0 = strip(0.9, before, C.coral, "arbitrary")
    d1 = strip(0.05, rank, C.blue, "Morton")
    note(cx, x1, 1.62, f"mean index distance of an edge: {d0:.1f} $\\rightarrow$ {d1:.1f}", ha="right", size=6.8,
         color=C.ink)
    return fig
