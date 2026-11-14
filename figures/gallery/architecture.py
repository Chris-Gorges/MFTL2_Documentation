"""Figures for ``pages/architecture.md`` -- the one idea and the three invariants."""

from __future__ import annotations


from mftlfig import register
from mftlfig.style import C, arrow, box, canvas, code, curved_arrow, fheading, figure, label, lighten, note

AOS, SOA, DER = (C.blue_fill, C.blue), (C.cyan_fill, C.cyan), (C.amber_fill, C.amber)


def _segment(ax, x, y, w, h, name, nbytes, kind, small=False):
    fc, ec = kind
    box(ax, x, y, w, h, fc=fc, ec=ec, lw=0.9, r=0.035)
    if small:
        code(ax, x + w / 2, y + h * 0.62, name, size=5.6)
        note(ax, x + w / 2, y + h * 0.3, f"{nbytes}", size=6.2, color=C.ink_soft)
    else:
        code(ax, x + w / 2, y + h * 0.62, name, size=7.2)
        note(ax, x + w / 2, y + h * 0.3, f"{nbytes} B", size=6.8, color=C.ink_soft)


@register("pool-layout")
def pool_layout():
    fig = figure(7.0, 3.7)
    ax = canvas(fig, [0, 0, 1, 1], (0, 7.0), (0, 3.7))
    fheading(fig, 0.0, 0.955, "a", "one allocation per entity class, drawn to scale in bytes per entity")
    fheading(fig, 0.0, 0.385, "b", "two access patterns, one per layout")

    s = 5.05 / 140.0  # inches per byte of one entity
    gap = 0.045
    h = 0.46
    x0 = 0.95

    rows = [
        (2.66, "vertex", [("rec", 16, AOS), ("pos", 24, SOA), ("normal", 24, SOA)], "64 B / vertex"),
        (1.86, "triangle", [("rec", 12, AOS), ("he", 48, AOS), ("area", 8, SOA), ("normal", 24, SOA),
                            ("center", 24, SOA), ("verts", 12, DER), ("nbrs", 12, DER)], "140 B / triangle"),
    ]
    for y, name, segs, total in rows:
        note(ax, x0 - 0.12, y + h / 2 + 0.07, name, ha="right", size=8.0, color=C.ink)
        note(ax, x0 - 0.12, y + h / 2 - 0.12, "block", ha="right", size=6.8)
        x = x0
        for seg, nb, kind in segs:
            w = nb * s - gap
            _segment(ax, x, y, w, h, seg, nb, kind, small=w < 0.36)
            x += nb * s
        # the block outline: one malloc
        box(ax, x0 - 0.05, y - 0.05, x - x0 + 0.05, h + 0.1, fc="none", ec=C.ink_soft, lw=0.7, r=0.06, zorder=1)
        note(ax, x + 0.08, y + h / 2, total, ha="left", size=7.6, color=C.ink)

    # cache-line alignment ticks, on the triangle row
    y = 1.86
    x = x0
    for nb in (12, 48, 8, 24, 24, 12):
        x += nb * s
        ax.plot([x - gap / 2] * 2, [y - 0.13, y - 0.05], color=C.ink_soft, lw=0.7)
    note(ax, x0 + 2.6, y - 0.24, "every sub-array starts on a 64 B cache line", size=6.8)

    # legend
    lx, ly = 1.75, 3.33
    for i, ((fc, ec), txt) in enumerate(((AOS, "AoS: topology and identity"), (SOA, "one array per field: geometry"),
                                         (DER, "derived connectivity (a cache)"))):
        xx = lx + [0.0, 1.72, 3.5][i]
        box(ax, xx, ly - 0.06, 0.16, 0.13, fc=fc, ec=ec, lw=0.8, r=0.02)
        note(ax, xx + 0.22, ly, txt, ha="left", size=6.9, color=C.ink)

    # ---------------------------------------------------------------- (b) access
    # AoS: the remesher touches few records, most of each
    y = 0.9
    cw, fw = 0.52, 0.52 / 4
    note(ax, x0 - 0.12, y + 0.17, "tris.he", ha="right", size=7.2, color=C.ink, fontfamily="monospace")
    n = 9
    for i in range(n):
        xx = x0 + i * (cw + 0.04)
        hot = i in (3, 4, 5)
        for f in range(4):
            box(ax, xx + f * fw, y, fw - 0.012, 0.34,
                fc=C.coral_fill if hot else lighten(C.blue_fill, 0.15), ec=C.coral if hot else C.blue_mid,
                lw=0.6, r=0.012)
    xa = x0 + 3 * (cw + 0.04)
    xb = x0 + 6 * (cw + 0.04) - 0.04
    ax.plot([xa, xa, xb, xb], [y - 0.05, y - 0.09, y - 0.09, y - 0.05], color=C.coral, lw=0.9)
    note(ax, (xa + xb) / 2, y - 0.2, "a collapse: a few records, every field of each", size=6.8, color=C.coral)
    note(ax, x0 + n * (cw + 0.04) + 0.02, y + 0.17, "target · twin · id · flags", ha="left", size=6.6)

    # one array per field, vectors interleaved: the update kernel streams one array
    y = 0.1
    note(ax, x0 - 0.12, y + 0.14, "verts.pos", ha="right", size=7.2, color=C.ink, fontfamily="monospace")
    for i in range(27):
        xx = x0 + i * 0.187
        comp = "xyz"[i % 3]
        box(ax, xx, y, 0.172, 0.28, fc=lighten(C.cyan_fill, 0.1), ec=C.cyan_mid, lw=0.55, r=0.012)
        label(ax, xx + 0.086, y + 0.14, rf"${comp}$", size=7.2, color=C.ink_soft)
    arrow(ax, (x0 + 0.02, y + 0.39), (x0 + 27 * 0.187 - 0.02, y + 0.39), color=C.cyan, lw=1.1, head=0.1)
    note(ax, x0 + 27 * 0.187 + 0.1, y + 0.14, "a geometry pass: every entity,\none stream", ha="left", size=6.6,
         color=C.cyan, linespacing=1.25)
    return fig


@register("ownership-prefix")
def ownership_prefix():
    fig = figure(7.0, 2.55)
    ax = canvas(fig, [0, 0, 1, 1], (0, 7.0), (0, 2.55))
    x0, W, h = 1.55, 4.9, 0.36

    def bar(y, parts, caption, marks):
        x = x0
        for w, text, fc, ec, hatch in parts:
            p = box(ax, x, y, w * W - 0.03, h, fc=fc, ec=ec, lw=0.8, r=0.03)
            if hatch:
                p.set_hatch(hatch)
            note(ax, x + (w * W - 0.03) / 2, y + h / 2, text, size=6.9, color=C.ink)
            x += w * W
        note(ax, x0 - 0.15, y + h / 2, caption, ha="right", size=7.2, color=C.ink, linespacing=1.2)
        for frac, s in marks:
            xm = x0 + frac * W - 0.015
            ax.plot([xm, xm], [y - 0.06, y + h + 0.06], color=C.ink, lw=1.1)
            label(ax, xm, y + h + 0.17, s, size=8.4)

    own, ghost = (C.blue_fill, C.blue), (C.amber_fill, C.amber)
    new = (C.green_fill, C.green)
    free = ("#ffffff", C.rule)
    bar(1.82, [(0.52, "owned", *own, None), (0.3, "ghosts", *ghost, None), (0.18, "", *free, "////")],
        "a pool", [(0.0, r"$0$"), (0.52, r"$n_\mathrm{local}$"), (0.82, r"$n$"), (1.0, r"$\mathrm{capacity}$")])
    bar(1.02, [(0.34, "kept owned", *own, None), (0.18, "new owned", C.blue_mid, C.blue, None),
               (0.2, "kept ghost", *ghost, None), (0.1, "new", C.amber_mid, C.amber, None),
               (0.18, "", *free, "////")],
        "after a\nredistribution", [(0.52, r"$n_\mathrm{local}$"), (0.82, r"$n$")])
    bar(0.22, [(0.52, "owned", *own, None), (0.2, "ghosts", *ghost, None), (0.12, "created", *new, None),
               (0.16, "", *free, "////")],
        "during a\nremesh sweep", [(0.52, r"$n_\mathrm{local}$")])
    # compaction swaps the two trailing blocks
    ya = 0.22 - 0.1
    curved_arrow(ax, (x0 + 0.78 * W, ya), (x0 + 0.55 * W, ya), bend=-0.28, color=C.green, lw=1.0, head=0.09)
    note(ax, x0 + 0.66 * W, ya - 0.2, "compaction moves them before the ghosts", size=6.6, color=C.green)
    note(ax, x0 + W + 0.05, 1.82 + h / 2, "index < n_local\nis ownership", ha="left", size=6.6,
         linespacing=1.2)
    return fig
