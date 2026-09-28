"""Figures for ``src/io/README.md`` -- periodic unwrapping and the shared-file layout."""

from __future__ import annotations

import numpy as np

from mftlfig import register
from mftlfig.style import C, arrow, box, canvas, fheading, figure, label, note, ring, tri


def _strip(L=3.0):
    """A band of triangles crossing the periodic seam at x = L (true, unwrapped positions)."""
    xs = np.linspace(1.35, 4.2, 7)
    top = np.column_stack([xs, 1.25 + 0.12 * np.sin(2.2 * xs)])
    bot = np.column_stack([xs + 0.24, 0.55 + 0.1 * np.cos(1.7 * xs)])
    T = []
    for i in range(len(xs) - 1):
        T.append([bot[i], bot[i + 1], top[i]])
        T.append([top[i], bot[i + 1], top[i + 1]])
    return [np.array(t) for t in T]


@register("vtu-unwrap")
def vtu_unwrap():
    fig = figure(7.0, 2.3)
    fheading(fig, 0.0, 0.93, "a", "stored corners, drawn as they are")
    fheading(fig, 0.5, 0.93, "b", "MFTLWriteVtu: straddlers get private points")
    L, H = 3.0, 1.8
    T = _strip(L)
    for k in range(2):
        ax = canvas(fig, [k * 0.5 + 0.005, 0.0, 0.49, 0.86], (-0.5, 4.35), (-0.25, 2.1))
        box(ax, 0, 0, L, H, fc=C.paper, ec=C.ink, lw=1.0, r=0.0, zorder=0)
        box(ax, L, 0, 1.3, H, fc="#fafbfc", ec=C.rule, lw=0.7, r=0.0, zorder=0, ls=(0, (3, 2)))
        box(ax, -0.45, 0, 0.45, H, fc="#fafbfc", ec=C.rule, lw=0.7, r=0.0, zorder=0, ls=(0, (3, 2)))
        note(ax, L / 2, -0.14, "domain", size=6.6)
        note(ax, L + 0.65, -0.14, "outside the box", size=6.4, color=C.ink_faint)
        for t in T:
            wrapped = np.column_stack([t[:, 0] % L, t[:, 1]])
            straddles = np.ptp(np.floor(t[:, 0] / L)) > 0
            if k == 0:
                col = (C.coral_fill, C.coral) if straddles else (C.blue_fill, C.blue)
                tri(ax, wrapped, col[0], ec=col[1], lw=0.9, zorder=3 if straddles else 2, alpha=0.9)
            else:
                if straddles:
                    # three private points p0, p0 + e1, p0 + e2 (minimum-image edges): may leave the box
                    p0 = wrapped[0]
                    P = np.array([p0, p0 + (t[1] - t[0]), p0 + (t[2] - t[0])])
                    tri(ax, P, C.cyan_fill, ec=C.cyan, lw=1.0, zorder=3)
                    for p in P:
                        ring(ax, p, r=0.04, ec=C.cyan, lw=0.9, zorder=5)
                else:
                    tri(ax, wrapped, C.blue_fill, ec=C.blue, lw=0.9, zorder=2)
        if k == 0:
            note(ax, 1.5, 1.97, "each straddler spans the whole domain", size=6.8, color=C.coral)
        else:
            note(ax, 1.5, 1.97, "the mesh in memory is untouched", size=6.8, color=C.ink_soft)
    return fig


@register("vtu-layout")
def vtu_layout():
    fig = figure(7.0, 2.1)
    ax = canvas(fig, [0, 0, 1, 1], (0, 7.0), (0, 2.1), equal=False)
    ranks = [(C.blue_fill, C.blue, "rank 0"), (C.cyan_fill, C.cyan, "rank 1"), (C.amber_fill, C.amber, "rank 2")]
    npts, ncells = [4, 6, 3], [5, 7, 4]
    y, h = 1.05, 0.42
    x = 0.25
    s = 0.07  # inches per unit of the smaller block
    # header
    box(ax, x, y, 0.7, h, fc=C.grey_fill, ec=C.ink_soft, lw=0.8, r=0.02)
    note(ax, x + 0.35, y + h / 2, "XML\nheader H", size=6.4, color=C.ink, linespacing=1.15)
    x += 0.74
    blocks = [("points", 3 * 8, npts, "24 B / point"), ("connectivity", 3 * 4, ncells, "12 B / cell")]
    starts = {}
    for name, unit, counts, unit_txt in blocks:
        box(ax, x, y, 0.22, h, fc=C.grey_mid, ec=C.ink_soft, lw=0.8, r=0.02)
        note(ax, x + 0.11, y + h / 2, "len", size=5.8, color=C.ink, rotation=90)
        x += 0.25
        x_block = x
        for r, (fc, ec, _) in enumerate(ranks):
            w = counts[r] * unit * s / 12.0
            starts[(name, r)] = x
            box(ax, x, y, w - 0.02, h, fc=fc, ec=ec, lw=0.9, r=0.02)
            x += w
        note(ax, (x_block + x) / 2, y + h + 0.13, f"{name}  ({unit_txt})", size=6.8, color=C.ink)
        x += 0.06
    note(ax, x + 0.3, y + h / 2, "· · ·", size=9, color=C.ink_faint)
    box(ax, x + 0.62, y, 0.5, h, fc=C.grey_fill, ec=C.ink_soft, lw=0.8, r=0.02)
    note(ax, x + 0.87, y + h / 2, "footer", size=6.4, color=C.ink)
    # where rank 1 writes in the connectivity block
    xs = starts[("connectivity", 1)]
    arrow(ax, (xs, y - 0.42), (xs, y - 0.03), color=C.cyan, lw=1.0, head=0.08)
    label(ax, xs + 0.05, y - 0.62, r"$\mathrm{offset}_b = H+\sum_{b'<b}(8+S_{b'})+8+u_b\sum_{r<\mathrm{rank}}n^{(r)}_{\mathrm{kind}(b)}$",
          size=8.8, ha="left" if xs < 3.0 else "center")
    note(ax, 3.5, 0.08, "one exclusive scan of (points, cells) places every slice of every block; "
         "MPI_File_write_at_all merges them", size=6.6)
    for i, (fc, ec, t) in enumerate(ranks):
        box(ax, 0.25 + i * 0.95, 1.86, 0.16, 0.12, fc=fc, ec=ec, lw=0.8, r=0.02)
        note(ax, 0.47 + i * 0.95, 1.92, t, size=6.6, color=C.ink, ha="left")
    return fig
