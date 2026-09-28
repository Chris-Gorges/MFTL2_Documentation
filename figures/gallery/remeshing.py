"""Figures for ``src/remeshing/README.md`` -- operators, predicates, smoothing, parallel strategies."""

from __future__ import annotations

import numpy as np

from mftlfig import register
from mftlfig.meshes import icosphere, triangle_neighbours
from mftlfig.scene3d import Camera, arrow3d, draw_mesh, label3d, planar_patch, point3d, polyline3d
from mftlfig.style import (C, arrow, box, canvas, curved_arrow, dim_line, dot, fheading, figure, halo_label, label, lighten, note, tri)

# ------------------------------------------------------------------ the band


@register("length-band")
def length_band():
    fig = figure(7.0, 1.7)
    ax = canvas(fig, [0, 0, 1, 1], (-0.05, 2.12), (-0.6, 0.6), equal=False)
    y = 0.0
    lmin, lmax = 0.8, 4.0 / 3.0
    for (a, b, fc, txt, col) in ((0.0, lmin, C.coral_fill, "collapse", C.coral), (lmin, lmax, C.blue_fill, "keep", C.blue_dark),
                                 (lmax, 2.1, C.cyan_fill, "split", C.cyan)):
        box(ax, a, y - 0.07, b - a, 0.14, fc=fc, ec="none", r=0.0, zorder=0)
        note(ax, (a + b) / 2 if b < 2 else 1.85, y + 0.14, txt, size=7.4, color=col)
    # split/collapse ping-pong: (4/3, 8/5) splits into halves below lmin
    p = box(ax, lmax, y - 0.07, 1.6 - lmax, 0.14, fc="none", ec=C.coral, lw=0.0, r=0.0, zorder=1)
    p.set_hatch("////")
    p.set_edgecolor(C.coral)
    ax.plot([0, 2.1], [y, y], color=C.ink, lw=0.9, zorder=2)
    for x, s_, big in ((0.0, r"$0$", True), (2.0 / 3.0, r"$\frac{2}{3}L$", False), (lmin, r"$\frac{4}{5}L$", True),
                       (1.0, r"$L$", True), (lmax, r"$\frac{4}{3}L$", True), (1.6, r"$\frac{8}{5}L$", True), (2.0, r"$2L$", True)):
        ax.plot([x, x], [y - 0.07, y + 0.07], color=C.ink if big else C.ink_soft, lw=0.9 if big else 0.7, zorder=2)
        label(ax, x, y - 0.2, s_, size=9.4 if big else 8.4, color=C.ink if big else C.ink_soft)
    # the split map l -> l/2 never moves an edge further from L
    curved_arrow(ax, (lmax, y + 0.24), (2.0 / 3.0, y + 0.24), bend=-0.3, color=C.blue_dark, lw=1.0, head=0.035)
    note(ax, 1.0, 0.52, r"split: $\ell\mapsto\ell/2$, and $\left|\frac{4}{3}L-L\right| = \left|\frac{2}{3}L-L\right|$",
         size=7.6, color=C.blue_dark)
    curved_arrow(ax, (1.47, y - 0.34), (0.735, y - 0.34), bend=0.12, color=C.coral, lw=0.8, head=0.03)
    note(ax, 1.1, -0.53, r"$(\frac{4}{3}L, \frac{8}{5}L)$ splits into halves below $\frac{4}{5}L$: "
         "held off by the sweep bound, the stretch clause and smoothing", size=6.8, color=C.coral)
    return fig


# ------------------------------------------------------------------ operators


def _patch(ax, V, T, fills=None, lw=0.9, ec=None, zorder=2):
    for i, t in enumerate(T):
        fc = (fills or {}).get(i, C.grey_fill)
        tri(ax, [V[k] for k in t], fc, ec=ec or C.ink, lw=lw, zorder=zorder)


def _vlabels(ax, V, names, offsets=None, skip=()):
    for k, p in V.items():
        if k in skip:
            continue
        dot(ax, p, r=0.05, zorder=6)
        if k in names:
            off = (offsets or {}).get(k, (0.0, 0.16))
            halo_label(ax, p[0] + off[0], p[1] + off[1], names[k], size=9.6)


@register("remesh-operators")
def remesh_operators():
    fig = figure(7.0, 3.45)
    fheading(fig, 0.0, 0.955, "a", r"split: $\ell>\ell_{\max}$")
    fheading(fig, 0.345, 0.955, "b", r"collapse: $\ell<\ell_{\min}$")
    fheading(fig, 0.69, 0.955, "c", "flip: lower valence energy")
    ylo, yhi = -1.12, 1.05
    over = canvas(fig, [0, 0, 1, 1], (0, 7.0), (0, 3.45), equal=False)

    def pair(x0, draw_before, draw_after, caption):
        top = canvas(fig, [x0, 0.54, 0.31, 0.38], (-1.75, 1.75), (ylo, yhi))
        bot = canvas(fig, [x0, 0.09, 0.31, 0.38], (-1.75, 1.75), (ylo, yhi))
        draw_before(top)
        draw_after(bot)
        xa = (x0 + 0.29) * 7.0
        arrow(over, (xa, 0.53 * 3.45), (xa, 0.45 * 3.45), color=C.ink_soft, lw=1.0, head=0.09)
        note(over, (x0 + 0.155) * 7.0, 0.035 * 3.45, caption, size=6.7)

    # ---------------------------------------------------------------- split
    def split_before(ax):
        V = dict(a=np.array([-0.9, 0.0]), b=np.array([0.9, 0.0]), c=np.array([0.0, 0.8]), d=np.array([0.05, -0.8]))
        _patch(ax, V, [("a", "b", "c"), ("b", "a", "d")], fills={0: C.blue_fill, 1: C.blue_fill})
        ax.plot(*np.array([V["a"], V["b"]]).T, color=C.coral, lw=2.0, zorder=3)
        _vlabels(ax, V, dict(a=r"$a$", b=r"$b$", c=r"$c$", d=r"$d$"),
                 dict(a=(-0.17, 0.0), b=(0.17, 0.0), c=(0.0, 0.17), d=(0.0, -0.17)))

    def split_after(ax):
        V = dict(a=np.array([-0.9, 0.0]), b=np.array([0.9, 0.0]), c=np.array([0.0, 0.8]), d=np.array([0.05, -0.8]),
                 m=np.array([0.0, 0.0]))
        _patch(ax, V, [("a", "m", "c"), ("m", "b", "c"), ("b", "m", "d"), ("m", "a", "d")],
               fills={0: C.blue_fill, 1: C.cyan_fill, 2: C.blue_fill, 3: C.cyan_fill})
        for q in ("c", "d"):
            ax.plot(*np.array([V["m"], V[q]]).T, color=C.cyan, lw=1.8, zorder=3)
        _vlabels(ax, V, dict(a=r"$a$", b=r"$b$", m=r"$m$", c=r"$c$", d=r"$d$"),
                 dict(a=(-0.17, 0.0), b=(0.17, 0.0), m=(0.18, 0.12), c=(0.0, 0.17), d=(0.0, -0.17)))
        dot(ax, V["m"], r=0.07, fc=C.cyan, zorder=7)

    pair(0.0, split_before, split_after, "+1 vertex, +2 triangles (one per side)")

    # ---------------------------------------------------------------- collapse
    ring6 = [np.array([np.cos(t), np.sin(t)]) * r for t, r in zip(np.radians([90, 150, 210, 270, 330, 30]),
                                                                    [0.85, 0.95, 0.95, 0.85, 0.95, 0.95])]

    def collapse_verts(pa, pb):
        V = dict(a=pa, b=pb, c=ring6[0] * 1.0, e=ring6[1] + np.array([-0.35, 0]), f=ring6[2] + np.array([-0.35, 0]),
                 d=ring6[3], g=ring6[4] + np.array([0.35, 0]), h=ring6[5] + np.array([0.35, 0]))
        return V

    fanA = [("a", "c", "e"), ("a", "e", "f"), ("a", "f", "d")]
    fanB = [("b", "d", "g"), ("b", "g", "h"), ("b", "h", "c")]

    def collapse_before(ax):
        V = collapse_verts(np.array([-0.2, 0.0]), np.array([0.2, 0.0]))
        T = [("a", "b", "c"), ("b", "a", "d")] + fanA + fanB
        _patch(ax, V, T, fills={0: C.coral_fill, 1: C.coral_fill, 2: C.amber_fill, 3: C.amber_fill, 4: C.amber_fill})
        arrow(ax, V["a"], V["b"], color=C.coral, lw=1.8, head=0.1, shorten=0.05, start_shorten=0.05, zorder=4)
        _vlabels(ax, V, dict(a=r"$a$", b=r"$b$", c=r"$w_1$", d=r"$w_2$"),
                 dict(a=(-0.1, 0.17), b=(0.1, 0.17), c=(0.0, 0.18), d=(0.0, -0.18)))

    def collapse_after(ax):
        pm = np.array([0.0, 0.0])
        V = collapse_verts(pm, pm)
        T = [(t[0].replace("a", "b"), t[1], t[2]) for t in fanA] + fanB
        _patch(ax, V, T, fills={0: C.amber_fill, 1: C.amber_fill, 2: C.amber_fill})
        _vlabels(ax, V, dict(b=r"$p_m$", c=r"$w_1$", d=r"$w_2$"),
                 dict(b=(0.2, 0.17), c=(0.0, 0.18), d=(0.0, -0.18)), skip=("a",))
        dot(ax, pm, r=0.07, fc=C.coral, zorder=7)

    pair(0.345, collapse_before, collapse_after, r"$a$ and two triangles marked dead; $a$'s fan rewritten")

    # ---------------------------------------------------------------- flip
    def flip_verts():
        return dict(a=np.array([-1.0, 0.0]), b=np.array([1.0, 0.0]), c=np.array([0.0, 0.62]), d=np.array([0.05, -0.62]))

    def stubs(ax, V, counts):
        """Short edges to neighbours outside the quad, so the valences are visible."""
        ang0 = dict(a=np.pi, b=0.0, c=np.pi / 2, d=-np.pi / 2)
        for k, n in counts.items():
            for t in np.linspace(-0.6, 0.6, n) if n > 1 else [0.0]:
                u = np.array([np.cos(ang0[k] + t), np.sin(ang0[k] + t)])
                ax.plot(*np.array([V[k], V[k] + 0.36 * u]).T, color=C.ink_faint, lw=0.8, zorder=1)

    def flip_before(ax):
        V = flip_verts()
        stubs(ax, V, dict(a=4, b=4, c=3, d=3))
        _patch(ax, V, [("a", "b", "c"), ("b", "a", "d")], fills={0: C.blue_fill, 1: C.blue_fill})
        ax.plot(*np.array([V["a"], V["b"]]).T, color=C.coral, lw=2.0, zorder=3)
        for k, s, off in (("a", "7", (-0.05, 0.22)), ("b", "7", (0.05, 0.22)), ("c", "5", (0.26, 0.02)), ("d", "5", (0.26, -0.02))):
            halo_label(ax, V[k][0] + off[0], V[k][1] + off[1], s, size=7.6, color=C.coral if s == "7" else C.ink_soft)
        _vlabels(ax, V, {})
        note(ax, -1.2, 0.8, r"$E=4\cdot1^2=4$", size=7.8, color=C.ink)

    def flip_after(ax):
        V = flip_verts()
        stubs(ax, V, dict(a=4, b=4, c=3, d=3))
        _patch(ax, V, [("a", "d", "c"), ("d", "b", "c")], fills={0: C.cyan_fill, 1: C.cyan_fill})
        ax.plot(*np.array([V["c"], V["d"]]).T, color=C.cyan, lw=2.0, zorder=3)
        for k, off in (("a", (-0.05, 0.22)), ("b", (0.05, 0.22)), ("c", (0.26, 0.02)), ("d", (0.26, -0.02))):
            halo_label(ax, V[k][0] + off[0], V[k][1] + off[1], "6", size=7.6, color=C.cyan)
        _vlabels(ax, V, {})
        note(ax, -1.2, 0.8, r"$E=0$", size=7.8, color=C.ink)

    pair(0.69, flip_before, flip_after, r"$E=\sum(\deg v-6)^2$ must strictly drop")
    return fig


# ------------------------------------------------------------------ the collapse predicate


@register("collapse-predicate")
def collapse_predicate():
    fig = figure(7.0, 2.3)
    titles = [("a", "allowed"), ("b", "link condition"), ("c", "wing valence"), ("d", "feature chord")]
    verdicts = [(r"$|W|=2$", C.blue_dark), (r"$|W|=3$: welds two sheets", C.coral),
                (r"$|N(w)|=3$: dissolves", C.coral), ("rim pinched inward", C.coral)]
    for k, ((letter, t), (v, vc)) in enumerate(zip(titles, verdicts)):
        fheading(fig, k * 0.25, 0.94, letter, t)
        note_ax = canvas(fig, [k * 0.25, 0.0, 0.24, 0.12], (0, 1), (0, 1), equal=False)
        note(note_ax, 0.5, 0.5, v, size=7.4, color=vc)

    def edge_ab(ax, a, b):
        arrow(ax, a, b, color=C.coral, lw=1.8, head=0.1, shorten=0.06, start_shorten=0.06, zorder=5)

    # ---------------------------------------------------------------- (a)
    ax = canvas(fig, [0.0, 0.12, 0.24, 0.72], (-1.3, 1.3), (-1.2, 1.2))
    a, b, w1, w2 = np.array([-0.45, 0]), np.array([0.45, 0]), np.array([0, 0.85]), np.array([0, -0.85])
    o = [np.array([-1.15, 0.6]), np.array([-1.15, -0.6]), np.array([1.15, 0.6]), np.array([1.15, -0.6])]
    for t in ((a, w1, o[0]), (a, o[0], o[1]), (a, o[1], w2), (b, o[2], w1), (b, o[3], o[2]), (b, w2, o[3])):
        tri(ax, t, C.grey_fill, lw=0.8)
    tri(ax, (a, b, w1), C.coral_fill, lw=0.8)
    tri(ax, (b, a, w2), C.coral_fill, lw=0.8)
    edge_ab(ax, a, b)
    for p, s, off in ((a, "$a$", (-0.05, 0.2)), (b, "$b$", (0.05, 0.2)), (w1, "$w_1$", (0, 0.2)), (w2, "$w_2$", (0, -0.2))):
        dot(ax, p, r=0.055, fc=C.blue_dark if s.startswith("$w") else C.ink, zorder=6)
        halo_label(ax, p[0] + off[0], p[1] + off[1], s, size=9.4)
    for p in o:
        dot(ax, p, r=0.045, zorder=6)

    # ---------------------------------------------------------------- (b)
    ax = canvas(fig, [0.25, 0.12, 0.24, 0.72], (-1.3, 1.3), (-1.2, 1.2))
    a, b, x, w1, w2 = (np.array([-0.55, -0.1]), np.array([0.55, -0.1]), np.array([0, 1.0]), np.array([0, 0.3]),
                       np.array([0, -0.9]))
    for t in ((a, b, w1), (b, x, w1), (x, a, w1), (b, a, w2)):
        tri(ax, t, C.coral_fill if (t[0] is a and t[1] is b) or (t[0] is b and t[1] is a) else C.grey_fill, lw=0.8)
    for t in ((a, x, np.array([-1.1, 0.7])), (x, b, np.array([1.1, 0.7])), (a, w2, np.array([-1.1, -0.7])),
              (b, np.array([1.1, -0.7]), w2)):
        tri(ax, t, "#f6f7f9", ec=C.ink_faint, lw=0.6, zorder=1)
    edge_ab(ax, a, b)
    for p, s, off, col in ((a, "$a$", (-0.18, 0.0), C.ink), (b, "$b$", (0.18, 0.0), C.ink), (x, "$x$", (0.0, 0.2), C.coral),
                           (w1, "$w_1$", (0.19, 0.1), C.blue_dark), (w2, "$w_2$", (0, -0.2), C.blue_dark)):
        dot(ax, p, r=0.055, fc=col, zorder=6)
        halo_label(ax, p[0] + off[0], p[1] + off[1], s, size=9.4, color=col if col != C.ink else C.ink)

    # ---------------------------------------------------------------- (c) the tetrahedron
    ax = canvas(fig, [0.5, 0.12, 0.24, 0.72], (-1.3, 1.3), (-1.2, 1.2))
    # oriented so the collapsing edge a-b is the front edge between the two visible faces
    cam = Camera(elev=40, azim=-55, scale=1.0, offset=(0.0, -0.05))
    V = np.array([[0.85, -0.1, 0.45], [-0.85, -0.1, 0.45], [0.0, 0.85, 0.45], [0.0, 0.1, -0.8]], float)
    F = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]])
    # every face outward
    for f in F:
        n = np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])
        if np.dot(n, V[f].mean(0) - V.mean(0)) < 0:
            f[[1, 2]] = f[[2, 1]]
    draw_mesh(ax, cam, V, F, color=C.grey_fill, lw=0.9, zorder=2)
    polyline3d(ax, cam, V[[0, 1]], color=C.coral, lw=1.8, zorder=5)
    for i, s in enumerate(("$a$", "$b$", "$w_1$", "$w_2$")):
        xy = point3d(ax, cam, V[i], r=0.05, fc=C.blue_dark if i > 1 else C.ink, zorder=6)
        d = xy - cam.project(V.mean(0))
        d = d / np.linalg.norm(d)
        halo_label(ax, *(xy + 0.22 * d), s, size=9.4)

    # ---------------------------------------------------------------- (d) a chord across the rim
    ax = canvas(fig, [0.75, 0.12, 0.24, 0.72], (-1.3, 1.3), (-1.2, 1.2))
    xs = np.linspace(-1.2, 1.2, 7)
    rim = [np.array([x, -0.45]) for x in xs]
    rim[3] = np.array([0.0, -0.95])  # the rim bulges out between a and b
    inner = [np.array([x, 0.45 + 0.05 * np.cos(2 * x)]) for x in np.linspace(-1.0, 1.0, 6)]
    a, c, b = rim[2], rim[3], rim[4]
    T = [(rim[0], rim[1], inner[0]), (rim[1], inner[1], inner[0]), (rim[1], a, inner[1]), (a, inner[2], inner[1]),
         (a, b, inner[2]), (b, inner[3], inner[2]), (b, rim[5], inner[3]), (rim[5], inner[4], inner[3]),
         (rim[5], rim[6], inner[4]), (rim[6], inner[5], inner[4])]
    for i, t in enumerate(T):
        tri(ax, t, C.coral_fill if i == 4 else C.grey_fill, lw=0.8)
    tri(ax, (a, c, b), C.coral_fill, lw=0.8)
    ax.plot(*np.array(rim).T, color=C.amber, lw=2.6, zorder=3, solid_capstyle="round")
    edge_ab(ax, a, b)
    for p in rim:
        dot(ax, p, r=0.05, fc=C.amber, zorder=6)
    for p in inner:
        dot(ax, p, r=0.045, zorder=6)
    halo_label(ax, a[0] - 0.14, a[1] - 0.2, "$a$", size=9.4)
    halo_label(ax, b[0] + 0.14, b[1] - 0.2, "$b$", size=9.4)
    halo_label(ax, c[0] + 0.2, c[1] - 0.05, "$c$", size=9.4)
    note(ax, -0.95, -0.72, "rim", size=6.6, color=C.amber)
    return fig


# ------------------------------------------------------------------ smoothing


def _sphere_fan(R=1.2, n=6, tilt=(0.4, -0.2)):
    """A vertex p on a sphere of radius R, displaced from the middle of its one-ring."""
    ang = np.radians(np.array([10, 68, 128, 185, 245, 300]) + 0.0)
    rad = np.array([0.95, 0.85, 1.0, 0.9, 1.05, 0.9])
    ring_ = np.stack([rad * np.cos(ang), rad * np.sin(ang)], 1)

    def lift(xy):
        xy = np.atleast_2d(xy)
        z = np.sqrt(R * R - (xy ** 2).sum(1)) - R
        return np.column_stack([xy, z])

    U = lift(ring_)
    p = lift(np.array(tilt))[0]
    return p, U, lift


@register("smoothing")
def smoothing():
    fig = figure(7.0, 2.55)
    fheading(fig, 0.0, 0.94, "a", "free: tangent plane")
    fheading(fig, 0.3, 0.94, "b", "ridge: curve tangent")
    fheading(fig, 0.58, 0.94, "c", "corner")
    fheading(fig, 0.75, 0.94, "d", "cutting the chord")

    # ---------------------------------------------------------------- (a)
    ax = canvas(fig, [0.0, 0.0, 0.29, 0.86], (-1.3, 1.3), (-1.05, 1.35))
    cam = Camera(elev=28, azim=-70, scale=1.25, offset=(0.0, 0.0))
    p, U, lift = _sphere_fan()
    V = np.vstack([p, U])
    F = np.array([[0, 1 + i, 1 + (i + 1) % 6] for i in range(6)])
    draw_mesh(ax, cam, V, F, color=C.grey_fill, lw=0.8, zorder=2)
    # triangle-based target: area-weighted centroid of the incident triangles
    A = np.array([0.5 * np.linalg.norm(np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])) for f in F])
    cen = np.array([V[f].mean(0) for f in F])
    target = (A[:, None] * cen).sum(0) / A.sum()
    d = target - p
    nrm = sum(np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]]) for f in F)
    n = nrm / np.linalg.norm(nrm)
    t1 = np.cross(n, [1, 0, 0])
    t1 /= np.linalg.norm(t1)
    t2 = np.cross(n, t1)
    planar_patch(ax, cam, p - 0.55 * t1 - 0.55 * t2, 1.1 * t1, 1.1 * t2, fc=C.cyan, alpha=0.18, zorder=3)
    d = 1.8 * d  # drawn at a common scale: the step is sigma * d anyway
    dt = d - np.dot(d, n) * n
    arrow3d(ax, cam, p, 0.75 * n, color=C.coral, lw=1.3, head=0.09, zorder=8)
    arrow3d(ax, cam, p, d, color=C.ink_soft, lw=1.1, head=0.08, zorder=8, ls=(0, (2, 1.5)))
    arrow3d(ax, cam, p, dt, color=C.blue_dark, lw=1.8, head=0.1, zorder=9)
    point3d(ax, cam, p, r=0.05, fc=C.ink, zorder=10)
    label3d(ax, cam, p + 0.75 * n, r"$\hat{\mathbf{n}}$", offset=(0.12, 0.02), color=C.coral)
    label3d(ax, cam, p, r"$\mathbf{p}$", offset=(0.14, 0.12))
    label3d(ax, cam, p + d, r"$\mathbf{d}$", offset=(-0.06, -0.16), color=C.ink_soft)
    label(ax, -1.25, 1.12, r"$(\mathbf{I}-\hat{\mathbf{n}}\hat{\mathbf{n}}^{\top})\,\mathbf{d}$", color=C.blue_dark,
          size=9.4, ha="left")

    # ---------------------------------------------------------------- (b) a curved ridge, side view
    bx = canvas(fig, [0.3, 0.0, 0.27, 0.86], (-1.25, 1.25), (-1.05, 1.35))
    R, c0 = 1.9, np.array([0.0, -1.35])
    th = np.radians(np.array([118, 82, 62]))  # q1, p, q2 on the ridge curve
    arc = np.radians(np.linspace(128, 52, 80))
    curve = c0 + R * np.stack([np.cos(arc), np.sin(arc)], 1)
    bx.fill_between(curve[:, 0], curve[:, 1], -0.6, color=C.grey_fill, lw=0, zorder=0)
    bx.plot(*curve.T, color=C.amber, lw=2.6, zorder=2, solid_capstyle="round")
    q1, p, q2 = (c0 + R * np.array([np.cos(t), np.sin(t)]) for t in th)
    d1, d2 = q1 - p, q2 - p
    tau = d2 - d1
    Delta = 0.5 * (d1 + d2)
    proj = np.dot(Delta, tau) / np.dot(tau, tau) * tau
    bx.plot(*np.array([q1, q2]).T, color=C.coral, lw=0.8, ls=(0, (2, 1.5)), zorder=3)
    arrow(bx, p, p + Delta, color=C.coral, lw=1.2, head=0.08, zorder=5, ls=(0, (2, 1.5)))
    arrow(bx, p, p + proj, color=C.blue_dark, lw=1.8, head=0.1, zorder=6)
    for q, s_ in ((q1, r"$\mathbf{q}_1$"), (q2, r"$\mathbf{q}_2$")):
        dot(bx, q, r=0.05, fc=C.amber, zorder=7)
        label(bx, q[0], q[1] + 0.18, s_, size=9.2)
    dot(bx, p, r=0.055, fc=C.ink, zorder=7)
    label(bx, p[0] + 0.02, p[1] + 0.2, r"$\mathbf{p}$", size=9.6)
    halo_label(bx, (p + Delta)[0] + 0.02, (p + Delta)[1] - 0.2, r"$\boldsymbol{\Delta}$: into the chord", color=C.coral,
               size=8.4)
    label(bx, 0.0, -0.9, r"$\frac{\boldsymbol{\Delta}\cdot\boldsymbol{\tau}}{\Vert\boldsymbol{\tau}\Vert^2}\,\boldsymbol{\tau},\quad"
          r"\boldsymbol{\tau}=\mathbf{d}_2-\mathbf{d}_1$", color=C.blue_dark, size=9.2)
    note(bx, -1.0, -0.45, "surface", size=6.4, color=C.ink_faint, ha="left")

    # ---------------------------------------------------------------- (c) corner
    cx = canvas(fig, [0.58, 0.0, 0.16, 0.86], (-0.8, 0.8), (-1.05, 1.35))
    cam = Camera(elev=32, azim=45, scale=0.9, offset=(0.0, 0.05))
    o = np.zeros(3)
    ex, ey, ez = np.eye(3) * -0.85
    Vc = np.array([o, ex, ey, ez, ex + ey, ey + ez, ez + ex])
    Fc = np.array([[0, 1, 4], [0, 4, 2], [0, 2, 5], [0, 5, 3], [0, 3, 6], [0, 6, 1]])
    draw_mesh(cx, cam, Vc, Fc, color=C.grey_fill, lw=0.8, zorder=2, cull=False)
    for e in (ex, ey, ez):
        polyline3d(cx, cam, np.array([o, e]), color=C.amber, lw=2.4, zorder=4)
    point3d(cx, cam, o, r=0.06, fc=C.coral, zorder=10)
    label3d(cx, cam, o, r"$\mathbf{p}$", offset=(0.0, 0.18), color=C.coral)
    note(cx, 0.0, -0.88, "three feature\nedges: locked", size=6.8, linespacing=1.3)

    # ---------------------------------------------------------------- (d) the 24-gon
    dx = canvas(fig, [0.76, 0.0, 0.24, 0.86], (-1.2, 1.2), (-1.05, 1.35))
    t = np.linspace(0, 2 * np.pi, 25)
    dx.plot(np.cos(t), np.sin(t), color=C.blue_dark, lw=1.4, zorder=3)
    s = np.cos(np.pi / 24) ** 20
    dx.plot(s * np.cos(t + np.pi / 24 * 0), s * np.sin(t), color=C.coral, lw=1.2, ls=(0, (3, 2)), zorder=3)
    dx.scatter(np.cos(t[:-1]), np.sin(t[:-1]), s=7, color=C.blue_dark, zorder=4, linewidths=0)
    note(dx, 0.0, 0.07, "projected:\nfixed point", size=6.6, color=C.blue_dark, linespacing=1.25)
    note(dx, 0.0, -0.4, f"to the midpoint:\n{s:.3f} R after 20", size=6.6, color=C.coral, linespacing=1.25)
    return fig


# ------------------------------------------------------------------ the spanning strategy


def frozen_on_grid(V, F, shift, h=1.0, lo=-1.0, cuts=2):
    """Owner cells of a sphere on a periodic cuts^3 grid with shifted planes, and the frozen set.

    Ownership as in MFTLRemeshOwnerProc: floor((x - lo - shift) / h) mod cuts per
    axis; a triangle by its centre. An owned triangle is frozen iff it is
    replicated: a corner or an edge neighbour belongs to another rank.
    """
    def cell(P):
        idx = np.floor((P - lo - np.asarray(shift)) / h).astype(int) % cuts
        return idx[:, 0] + cuts * (idx[:, 1] + cuts * idx[:, 2]), idx

    vown, _ = cell(V)
    cen = V[F].mean(axis=1)
    town, tidx = cell(cen)
    nb = triangle_neighbours(F)
    frozen = np.zeros(len(F), bool)
    for t in range(len(F)):
        if any(vown[v] != town[t] for v in F[t]) or any(town[s] != town[t] for s in nb[t] if s >= 0):
            frozen[t] = True
    parity = tidx.sum(axis=1) % 2
    return town, parity, frozen


@register("spanning-placements")
def spanning_placements():
    fig = figure(7.0, 2.65)
    fheading(fig, 0.0, 0.95, "a", r"placement 000")
    fheading(fig, 0.3, 0.95, "b", r"placement 111: planes shifted by $h/2$")
    fheading(fig, 0.66, 0.95, "c", r"why $h>4\delta$ covers everything")
    V, F = icosphere(3, radius=0.72)
    cam = Camera(elev=22, azim=-58)
    for k, shift in enumerate(((0.0, 0.0, 0.0), (0.5, 0.5, 0.5))):
        ax = canvas(fig, [k * 0.3, 0.0, 0.3, 0.88], (-0.95, 0.95), (-1.0, 0.92))
        town, parity, frozen = frozen_on_grid(V, F, shift)
        cols = np.where(frozen, C.coral_mid, np.where(parity == 0, C.blue_fill, C.cyan_fill)).tolist()
        draw_mesh(ax, cam, V, F, colors=cols, lw=0.25, zorder=2, edgecolor=C.ink_soft)
        share = frozen.mean()
        note(ax, 0.0, -0.9, f"frozen: {100 * share:.0f} % of the triangles", size=6.9, color=C.coral)

    # ---------------------------------------------------------------- (c) one axis
    cx = canvas(fig, [0.66, 0.0, 0.34, 0.88], (-0.1, 2.25), (-0.85, 1.05), equal=False)
    h, delta = 1.0, 0.18
    y0, y1 = 0.45, -0.15
    for (y, planes, col, name) in ((y0, [0.0, 1.0, 2.0], C.coral, "000"), (y1, [0.5, 1.5], C.cyan, "111")):
        cx.plot([0, 2.0], [y, y], color=C.ink, lw=0.8, zorder=1)
        for x in planes:
            box(cx, x - delta, y - 0.09, 2 * delta, 0.18, fc=lighten(col, 0.7), ec="none", r=0.0, zorder=0)
            cx.plot([x, x], [y - 0.16, y + 0.16], color=col, lw=1.6, zorder=2)
        note(cx, -0.05, y + 0.26, f"planes of {name}", ha="left", size=6.6, color=col)
    # a point in the band of 000 is interior in 111
    xp = 1.0 + 0.1
    for y in (y0, y1):
        dot(cx, (xp, y), r=0.03, fc=C.ink, zorder=5)
    cx.plot([xp, xp], [y1, y0], color=C.ink_soft, lw=0.6, ls=(0, (2, 2)), zorder=1)
    dim_line(cx, (1.0, y0 + 0.28), (1.0 + delta, y0 + 0.28), r"$\delta$", text_offset=0.1, head=0.035, size=9)
    dim_line(cx, (1.0, y1 - 0.3), (1.5, y1 - 0.3), r"$h/2$", text_offset=-0.12, head=0.035, size=9)
    label(cx, 1.05, -0.78, r"$\frac{h}{2}-\delta>\delta \;\Longleftrightarrow\; h>4\delta$", size=9.6)
    return fig


# ------------------------------------------------------------------ the two regimes


def _cells(ax, n=3, dashed_shift=None):
    for i in range(n + 1):
        ax.plot([0, n], [i, i], color=C.ink_faint, lw=0.9, zorder=0)
        ax.plot([i, i], [0, n], color=C.ink_faint, lw=0.9, zorder=0)
    if dashed_shift is not None:
        for i in range(n):
            x = i + dashed_shift
            ax.plot([x, x], [0, n], color=C.cyan, lw=1.0, ls=(0, (3, 2)), zorder=0)
            ax.plot([0, n], [x, x], color=C.cyan, lw=1.0, ls=(0, (3, 2)), zorder=0)


def _droplet(ax, c, r, fc=C.blue_fill, ec=C.blue, lw=1.0, zorder=3, alpha=1.0):
    from matplotlib.patches import Circle

    ax.add_patch(Circle(c, r, fc=fc, ec=ec, lw=lw, zorder=zorder, alpha=alpha))


@register("remesh-regimes")
def remesh_regimes():
    fig = figure(7.0, 2.7)
    fheading(fig, 0.0, 0.95, "a", r"dispersed, $R_b\leq0.4\,h$")
    fheading(fig, 0.35, 0.95, "b", r"spanning, $R_b\gtrsim h$")
    fheading(fig, 0.7, 0.95, "c", "dispersed, clustered")

    # ---------------------------------------------------------------- (a)
    ax = canvas(fig, [0.01, 0.02, 0.3, 0.86], (-0.1, 3.1), (-0.25, 3.1))
    _cells(ax)
    drops = [((0.95, 2.4), 0.2), ((2.1, 2.05), 0.22), ((0.45, 0.62), 0.17), ((1.55, 1.05), 0.21), ((2.55, 0.45), 0.16),
             ((1.4, 2.5), 0.15), ((2.5, 1.5), 0.18)]
    for c, r in drops:
        c = np.array(c)
        straddles = any(abs(c[k] - round(c[k])) < r for k in range(2))
        _droplet(ax, c, r, fc=C.coral_fill if straddles else C.blue_fill, ec=C.coral if straddles else C.blue)
        dot(ax, c, r=0.028, fc=C.ink, zorder=5)
        if straddles:
            home = np.floor(c) + 0.5
            arrow(ax, c, c + 0.55 * (home - c), color=C.coral, lw=0.9, head=0.09, zorder=6, start_shorten=0.05)
    note(ax, 1.5, -0.14, "a body on a plane moves whole to its centroid's rank", size=6.5, color=C.coral)

    # ---------------------------------------------------------------- (b)
    bx = canvas(fig, [0.36, 0.02, 0.3, 0.86], (-0.1, 3.1), (-0.25, 3.1))
    _cells(bx, dashed_shift=0.5)
    t = np.linspace(0, 2 * np.pi, 160)
    r = 1.12 + 0.08 * np.cos(3 * t + 0.4) + 0.05 * np.sin(5 * t)
    blob = np.stack([1.5 + r * np.cos(t), 1.55 + 0.92 * r * np.sin(t)], 1)
    tri(bx, blob, lighten(C.blue_fill, 0.1), ec=C.blue, lw=1.2, zorder=2, alpha=0.9)
    for x in (1.0, 2.0):
        arrow(bx, (x, 3.02), (x + 0.5, 3.02), color=C.cyan, lw=0.9, head=0.08)
    note(bx, 1.5, -0.14, "the planes move by h/2 (solid 000, dashed 111)", size=6.5, color=C.ink_soft)

    # ---------------------------------------------------------------- (c)
    cx = canvas(fig, [0.71, 0.02, 0.3, 0.86], (-0.1, 3.1), (-0.25, 3.1))
    _cells(cx)
    box(cx, 1.03, 1.03, 0.94, 0.94, fc=C.coral_fill, ec="none", r=0.02, zorder=0)
    cl = [(1.25, 1.3), (1.5, 1.25), (1.75, 1.35), (1.3, 1.6), (1.55, 1.55), (1.8, 1.65), (1.35, 1.82), (1.65, 1.8)]
    moved = {0: (0.55, 0.62), 5: (2.45, 1.55), 6: (1.4, 2.5), 2: (2.5, 0.6)}
    for i, c in enumerate(cl):
        _droplet(cx, c, 0.09, fc=C.blue_fill, ec=C.blue, lw=0.8, alpha=0.45 if i in moved else 1.0)
        if i in moved:
            d = np.array(moved[i])
            _droplet(cx, d, 0.09, fc=C.cyan_fill, ec=C.cyan, lw=0.9)
            arrow(cx, c, d, color=C.cyan, lw=0.8, head=0.08, shorten=0.1, start_shorten=0.1, zorder=6)
    note(cx, 1.5, -0.14, r"one hop to a neighbour with room below the cap", size=6.5, color=C.cyan)
    return fig
