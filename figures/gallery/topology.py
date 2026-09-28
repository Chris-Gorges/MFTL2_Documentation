"""Figures for ``src/topology/README.md`` -- the half-edge structure."""

from __future__ import annotations

import numpy as np

from mftlfig import register
from mftlfig.style import C, arrow, box, canvas, curved_arrow, dot, fheading, figure, halo_label, label, note, tri


def halfedge_arrow(ax, a, b, c, color, lw=1.25, amount=0.2, head=0.11, trim=0.17):
    """Draw half-edge a->b inside triangle (a, b, c), offset towards the centroid.

    :returns: ``(midpoint of the arrow, unit vector from it towards the centroid)``.
    """
    a, b, c = (np.asarray(v, float) for v in (a, b, c))
    g = (a + b + c) / 3.0
    a2 = a + (g - a) * amount
    b2 = b + (g - b) * amount
    p, q = a2 + trim * (b2 - a2), b2 - trim * (b2 - a2)
    arrow(ax, p, q, color=color, lw=lw, head=head)
    m = 0.5 * (p + q)
    d = b - a
    inward = np.array([-d[1], d[0]]) / np.linalg.norm(d)  # left of a->b = interior of a CCW triangle
    return m, inward


@register("halfedge-implicit")
def halfedge_implicit():
    fig = figure(7.0, 2.75)
    fheading(fig, 0.0, 0.95, "a", "two triangles, six half-edges")
    fheading(fig, 0.47, 0.95, "b", "what is stored, and what is arithmetic")

    # ---------------------------------------------------------------- (a) geometry
    ax = canvas(fig, [0.0, 0.0, 0.44, 0.88], (-0.75, 4.15), (-0.62, 2.55))
    v0, v1, v2, w = np.array([-0.35, 0.95]), np.array([1.7, -0.25]), np.array([1.7, 2.15]), np.array([3.75, 0.95])
    tri(ax, [v0, v1, v2], C.blue_fill, ec=C.ink, lw=0.9)
    tri(ax, [v1, w, v2], C.cyan_fill, ec=C.ink, lw=0.9)

    # outer half-edges are labelled outside their edge, the shared pair inside
    spec = [(v0, v1, v2, C.blue, r"$3t$", C.blue_dark, -0.3), (v1, v2, v0, C.coral, r"$3t{+}1$", C.coral, 0.5),
            (v2, v0, v1, C.blue, r"$3t{+}2$", C.blue_dark, -0.36), (v1, w, v2, C.cyan, r"$3t'$", C.cyan, -0.3),
            (w, v2, v1, C.cyan, r"$3t'{+}1$", C.cyan, -0.38), (v2, v1, w, C.coral, r"$3t'{+}2$", C.coral, 0.52)]
    for a, b, c, col, s, tcol, off in spec:
        halfedge_arrow(ax, a, b, c, col)
        m = 0.5 * (a + b)
        d = b - a
        inward = np.array([-d[1], d[0]]) / np.linalg.norm(d)
        p = m + off * inward
        halo_label(ax, p[0], p[1], s, color=tcol, size=9.4)
    label(ax, 0.62, 0.95, r"$t$", size=14, color=C.blue_dark)
    label(ax, 2.78, 0.95, r"$t'$", size=14, color=C.cyan)

    for p, s, off in ((v0, r"$v_0$", (-0.27, 0.0)), (v1, r"$v_1$", (0.0, -0.25)), (v2, r"$v_2$", (0.0, 0.25)),
                      (w, r"$w$", (0.25, 0.0))):
        dot(ax, p, r=0.058)
        label(ax, p[0] + off[0], p[1] + off[1], s)

    # ---------------------------------------------------------------- (b) storage
    bx = canvas(fig, [0.47, 0.0, 0.53, 0.88], (-0.55, 7.3), (-1.95, 2.35))
    cw, ch, y0 = 0.92, 0.86, 0.0
    cells = [(0.0, r"$3t$", r"$v_1$", r"$\cdots$", C.blue_fill, C.blue),
             (1.0, r"$3t{+}1$", r"$v_2$", r"$3t'{+}2$", C.coral_fill, C.coral),
             (2.0, r"$3t{+}2$", r"$v_0$", r"$\cdots$", C.blue_fill, C.blue),
             (4.2, r"$3t'$", r"$w$", r"$\cdots$", C.cyan_fill, C.cyan),
             (5.2, r"$3t'{+}1$", r"$v_2$", r"$\cdots$", C.cyan_fill, C.cyan),
             (6.2, r"$3t'{+}2$", r"$v_1$", r"$3t{+}1$", C.coral_fill, C.coral)]
    for x, h, tgt, tw, fc, ec in cells:
        box(bx, x, y0, cw, ch, fc=fc, ec=ec, lw=0.9, r=0.06)
        label(bx, x + cw / 2, y0 + ch + 0.2, h, size=9.2)
        label(bx, x + cw / 2, y0 + 0.6, tgt, size=9.4)
        label(bx, x + cw / 2, y0 + 0.24, tw, size=8.6, color=C.ink_soft)
    note(bx, 3.56, y0 + ch / 2, r"$\cdots$", size=12, color=C.ink_faint)
    note(bx, -0.1, y0 + 0.6, "target", ha="right", size=6.8)
    note(bx, -0.1, y0 + 0.24, "twin", ha="right", size=6.8)

    # the twin relation, arching over the array
    ytop = y0 + ch + 0.45
    curved_arrow(bx, (1.46, ytop), (6.66, ytop), bend=0.12, color=C.coral, lw=1.0, head=0.11)
    curved_arrow(bx, (6.66, ytop), (1.46, ytop), bend=-0.12, color=C.coral, lw=0.0, head=0.11)
    halo_label(bx, 4.06, ytop + 0.5 * 0.12 * 5.2 + 0.2, "twin", color=C.coral, size=7.4)

    # each triple is one triangle
    for x0, x1, s, col, fc in ((0.0, 2.92, r"triangle $t$", C.blue_dark, C.blue_fill),
                               (4.2, 7.12, r"triangle $t'$", C.cyan, C.cyan_fill)):
        box(bx, x0 - 0.1, y0 - 0.52, x1 - x0 + 0.2, ch + 0.62, fc=C.grey_fill, ec="none", r=0.1, zorder=0)
        label(bx, (x0 + x1) / 2, y0 - 0.28, s, color=col, size=8.2)

    fy = -1.25
    label(bx, 3.3, fy,
          r"$\mathrm{face}(h)=\lfloor h/3\rfloor \qquad \mathrm{next}(h)=3\lfloor h/3\rfloor+(h{+}1)\,\mathrm{mod}\,3"
          r"\qquad \mathrm{origin}(h)=\mathrm{target}(\mathrm{prev}(h))$", size=8.8)
    note(bx, 3.3, fy - 0.45, "stored: target and twin (with id and flags, 16 B)   ·   arithmetic: face, next, prev, "
         "origin", size=6.9)
    return fig


def _fan_axes(ax, v, U, fills, closed=True, lw=0.9):
    n = len(U)
    last = n if closed else n - 1
    for i in range(last):
        tri(ax, [v, U[i], U[(i + 1) % n]], fills[i % len(fills)], ec=C.ink, lw=lw)


@register("vertex-fan")
def vertex_fan():
    fig = figure(7.0, 3.05)
    fheading(fig, 0.0, 0.95, "a", "interior vertex: the fan closes")
    fheading(fig, 0.54, 0.95, "b", "boundary vertex: one neighbour more")

    # ---------------------------------------------------------------- (a) closed fan
    ax = canvas(fig, [0.0, 0.0, 0.5, 0.9], (-2.05, 3.85), (-2.0, 2.0))
    v = np.array([0.0, 0.0])
    ang = np.radians([6, 64, 120, 178, 238, 298])
    rad = [1.62, 1.45, 1.6, 1.5, 1.58, 1.52]
    U = [np.array([r * np.cos(a), r * np.sin(a)]) for a, r in zip(ang, rad)]
    _fan_axes(ax, v, U, [C.grey_fill, "#f4f6f9"])
    n = len(U)
    for i in range(n):
        if i in (0, 1, 5):
            continue
        halfedge_arrow(ax, v, U[i], U[(i + 1) % n], C.ink_faint, lw=0.9, amount=0.16, head=0.1, trim=0.2)
    # h, its twin, and the two rotation steps
    halfedge_arrow(ax, v, U[0], U[1], C.coral, lw=1.5, amount=0.16, head=0.13, trim=0.2)
    halfedge_arrow(ax, U[0], v, U[5], C.coral, lw=1.0, amount=0.16, head=0.1, trim=0.2)
    halfedge_arrow(ax, U[1], v, U[0], C.cyan, lw=1.0, amount=0.16, head=0.1, trim=0.2)
    halfedge_arrow(ax, v, U[5], U[0], C.blue, lw=1.5, amount=0.16, head=0.13, trim=0.2)
    halfedge_arrow(ax, v, U[1], U[2], C.cyan, lw=1.5, amount=0.16, head=0.13, trim=0.2)
    for i, u in enumerate(U):
        dot(ax, u, r=0.055)
        d = u / np.linalg.norm(u)
        label(ax, *(u + 0.24 * d), rf"$u_{i}$")
    dot(ax, v, r=0.07, fc=C.coral)
    halo_label(ax, -0.25, -0.18, r"$v$", size=11)

    halo_label(ax, 1.08, 0.36, r"$h$", color=C.coral, size=10.5)
    halo_label(ax, 1.02, -0.36, r"$\mathrm{twin}(h)$", color=C.coral, size=8.8)
    halo_label(ax, 0.98, -1.07, r"$h'$", color=C.blue, size=10.5)
    halo_label(ax, 0.66, 0.6, r"$\mathrm{prev}(h)$", color=C.cyan, size=8.8)
    halo_label(ax, -0.28, 1.22, r"$h''$", color=C.cyan, size=10.5)

    # rotation arcs, drawn outside the fan, and what they are
    R = 1.98
    for a0, a1, col in ((-12, -48, C.blue), (20, 54, C.cyan)):
        t = np.radians(np.linspace(a0, a1, 30))
        ax.plot(R * np.cos(t), R * np.sin(t), color=col, lw=1.0)
        arrow(ax, (R * np.cos(t[-2]), R * np.sin(t[-2])), (R * np.cos(t[-1]), R * np.sin(t[-1])), color=col,
              lw=0.0, head=0.13)
    label(ax, 2.2, -0.95, r"$h'=\mathrm{next}(\mathrm{twin}(h))$", color=C.blue, size=9.0, ha="left")
    note(ax, 2.2, -1.3, "clockwise", ha="left", size=7.0)
    label(ax, 2.2, 1.25, r"$h''=\mathrm{twin}(\mathrm{prev}(h))$", color=C.cyan, size=9.0, ha="left")
    note(ax, 2.2, 0.9, "counter-clockwise", ha="left", size=7.0)

    # ---------------------------------------------------------------- (b) open fan
    bx = canvas(fig, [0.54, 0.0, 0.46, 0.9], (-2.1, 2.1), (-0.95, 2.3))
    v = np.array([0.0, 0.0])
    ang = np.radians([0, 41, 88, 136, 180])
    rad = [1.62, 1.5, 1.58, 1.46, 1.62]
    U = [np.array([r * np.cos(a), r * np.sin(a)]) for a, r in zip(ang, rad)]
    _fan_axes(bx, v, U, [C.blue_fill, "#e7f0f9"], closed=False)
    # the rim: the surface ends here
    for a, b in ((U[0], v), (v, U[4])):
        bx.plot([a[0], b[0]], [a[1], b[1]], color=C.amber, lw=3.2, zorder=3, solid_capstyle="round")
    bx.fill_between([-2.0, 2.0], [-0.02, -0.02], [-0.55, -0.55], color=C.grey_fill, zorder=0, lw=0)
    note(bx, 1.35, -0.3, "no surface", size=7.0)

    for i in range(4):
        col = C.blue if i != 3 else C.blue_dark
        halfedge_arrow(bx, v, U[i], U[i + 1], col, lw=1.3, amount=0.16, head=0.12, trim=0.2)
    halfedge_arrow(bx, U[4], v, U[3], C.coral, lw=1.5, amount=0.16, head=0.12, trim=0.2)
    for i, u in enumerate(U):
        dot(bx, u, r=0.055)
        d = u / np.linalg.norm(u)
        label(bx, *(u + 0.25 * d + (np.array([0, 0.1]) if i in (0, 4) else 0)), rf"$u_{i}$")
    dot(bx, v, r=0.07, fc=C.coral)
    label(bx, 0.0, -0.25, r"$v$", size=11)

    # the walk: rewind to the fan's first half-edge, then step with next(twin(.))
    halo_label(bx, -0.52, 1.02, "fan start", color=C.blue_dark, size=7.2)
    R = 1.95
    t = np.radians(np.linspace(128, 12, 60))
    bx.plot(R * np.cos(t), R * np.sin(t), color=C.blue, lw=1.0)
    arrow(bx, (R * np.cos(t[-2]), R * np.sin(t[-2])), (R * np.cos(t[-1]), R * np.sin(t[-1])), color=C.blue,
          lw=0.0, head=0.12)
    label(bx, 1.35, 1.95, r"walk: $h\mapsto\mathrm{next}(\mathrm{twin}(h))$", color=C.blue, size=8.4)
    halo_label(bx, -1.12, 0.3, r"incoming only", color=C.coral, size=7.2)
    label(bx, -1.9, 1.95, "4 triangles\n5 neighbours", size=7.6, ha="left", color=C.ink_soft, linespacing=1.3)
    return fig
