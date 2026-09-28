"""Figures for ``src/geometry/README.md`` -- periodic geometry, normals, closest points."""

from __future__ import annotations

import numpy as np

from mftlfig import register
from mftlfig.scene3d import Camera, arrow3d, draw_mesh, face_normals, label3d, point3d, polyline3d
from mftlfig.style import C, arrow, box, canvas, dot, fheading, figure, halo_label, label, lighten, note, ring, tri

# ------------------------------------------------------------------ periodic


def _periodic_box(ax, L, H, images=True):
    """The domain [0, L] x [0, H], periodic in x, with its two neighbouring images."""
    if images:
        for s in (-L, L):
            box(ax, s, 0, L, H, fc="#fafbfc", ec=C.rule, lw=0.7, r=0.0, zorder=0, ls=(0, (3, 2)))
    box(ax, 0, 0, L, H, fc=C.paper, ec=C.ink, lw=1.0, r=0.0, zorder=0)
    for x in (0, L):
        ax.plot([x, x], [0, H], color=C.ink, lw=1.0, zorder=1)


def _wrap(p, L):
    return np.array([p[0] - L * np.floor(p[0] / L), p[1]])


@register("minimum-image")
def minimum_image():
    fig = figure(7.0, 2.3)
    L, H = 3.0, 2.0
    q = [np.array([2.62, 0.62]), np.array([3.55, 0.82]), np.array([3.02, 1.52])]  # the true triangle
    p = [_wrap(v, L) for v in q]  # what is stored

    fheading(fig, 0.0, 0.93, "a", "raw differences of stored corners")
    fheading(fig, 0.5, 0.93, "b", "minimum-image edges")

    for k, (x0, mode) in enumerate(((0.0, "raw"), (0.5, "mi"))):
        ax = canvas(fig, [x0 + 0.005, 0.0, 0.49, 0.86], (-0.75, 4.1), (-0.35, 2.25))
        ax.set_clip_on(True)
        _periodic_box(ax, L, H)
        note(ax, L / 2, -0.2, r"domain, periodic in $x$", size=6.8)
        note(ax, L + 0.55, -0.2, "image", size=6.4, color=C.ink_faint)
        if mode == "raw":
            tri(ax, p, C.coral_fill, ec=C.coral, lw=1.1, ls=(0, (4, 2)), zorder=2, alpha=0.9)
            arrow(ax, p[0], p[1], color=C.coral, lw=1.2, head=0.11, shorten=0.07, zorder=4)
            arrow(ax, p[0], p[2], color=C.coral, lw=1.2, head=0.11, shorten=0.07, zorder=4)
            c_naive = sum(p) / 3.0
            ax.plot(*c_naive, marker="x", color=C.coral, ms=7, mew=1.6, zorder=6)
            ax.plot([c_naive[0], c_naive[0] + 0.25], [c_naive[1] + 0.08, 1.58], color=C.coral, lw=0.6)
            halo_label(ax, c_naive[0] + 0.28, 1.66, "centroid of the stored corners", color=C.coral, size=6.8,
                       ha="left")
            halo_label(ax, 1.5, 0.52, r"$\mathbf{p}_1-\mathbf{p}_0$", color=C.coral, size=9.2)
            halo_label(ax, 1.68, 1.28, r"$\mathbf{p}_2-\mathbf{p}_0$", color=C.coral, size=9.2)
        else:
            # the true triangle in both images it touches
            for s in (0.0, -L):
                qq = [v + np.array([s, 0.0]) for v in q]
                tri(ax, qq, C.blue_fill, ec=C.blue, lw=1.1, zorder=2)
            e1, e2 = q[1] - q[0], q[2] - q[0]
            arrow(ax, p[0], p[0] + e1, color=C.blue_dark, lw=1.3, head=0.11, shorten=0.06, zorder=4)
            arrow(ax, p[0], p[0] + e2, color=C.blue_dark, lw=1.3, head=0.11, shorten=0.06, zorder=4)
            halo_label(ax, 3.2, 0.46, r"$\mathbf{e}_1$", color=C.blue_dark, size=10)
            halo_label(ax, 2.6, 1.2, r"$\mathbf{e}_2$", color=C.blue_dark, size=10)
            c = p[0] + (e1 + e2) / 3.0
            cw = _wrap(c, L)
            ring(ax, c, r=0.05, ec=C.blue_dark, lw=1.0)
            dot(ax, cw, r=0.06, fc=C.blue_dark)
            halo_label(ax, 0.42, 1.14, r"$\mathbf{c}$, wrapped", color=C.blue_dark, size=8.4, ha="left")
            label(ax, 1.62, 1.74, r"$\Delta_k = d_k - L_k\,\mathrm{nearbyint}(d_k/L_k)$", size=9.2)
            # faded image corners
            for v in q[1:]:
                ring(ax, v, r=0.045, ec=C.ink_soft, lw=0.8)
        for i, v in enumerate(p):
            dot(ax, v, r=0.055)
            off = {0: (0.0, -0.2), 1: (0.02, -0.2), 2: (-0.02, 0.2)}[i]
            halo_label(ax, v[0] + off[0], v[1] + off[1], rf"$\mathbf{{p}}_{i}$", size=9.6)
    return fig


# ------------------------------------------------------------------ normals


def _fan():
    """A deliberately uneven vertex fan: one long face, one skinny face, a tilt."""
    # found by a search maximising the angle between the two weightings (27 deg)
    # subject to every face still facing up: an honest, if spiky, vertex
    v = np.array([0.0, 0.0, 0.4])
    ang = np.radians([0, 34, 93, 187, 279, 317])
    rad = np.array([1.25, 1.92, 0.83, 0.88, 1.84, 2.27])
    z = np.array([-0.88, -0.07, 0.33, -0.78, 0.53, -0.69])
    U = np.stack([rad * np.cos(ang), rad * np.sin(ang), z], axis=1)
    V = np.vstack([v, U])
    F = np.array([[0, 1 + i, 1 + (i + 1) % 6] for i in range(6)])
    return V, F


def _vertex_normals(V, F):
    n, A = face_normals(V, F)
    alpha = []
    for f in F:
        a, b, c = V[f]
        u, w = b - a, c - a
        alpha.append(np.arctan2(np.linalg.norm(np.cross(u, w)), np.dot(u, w)))
    alpha = np.array(alpha)
    Na = (A[:, None] * n).sum(0)
    Ng = (alpha[:, None] * n).sum(0)
    return n, A, alpha, Na / np.linalg.norm(Na), Ng / np.linalg.norm(Ng)


@register("vertex-normals")
def vertex_normals():
    fig = figure(7.0, 2.75)
    fheading(fig, 0.0, 0.94, "a", "one triangle")
    fheading(fig, 0.34, 0.94, "b", "area-weighted")
    fheading(fig, 0.67, 0.94, "c", "angle-weighted")

    # ---------------------------------------------------------------- (a)
    cam = Camera(elev=24, azim=-62)
    ax = canvas(fig, [0.0, 0.0, 0.32, 0.88], (-1.2, 1.35), (-0.9, 1.45))
    P = np.array([[-0.8, -0.6, 0.0], [0.95, -0.35, 0.05], [-0.1, 0.9, 0.2]])
    draw_mesh(ax, cam, P, np.array([[0, 1, 2]]), color=C.blue_fill, lw=0.9, zorder=2)
    e1, e2 = P[1] - P[0], P[2] - P[0]
    arrow3d(ax, cam, P[0], e1 * 0.97, color=C.blue_dark, lw=1.3, head=0.1)
    arrow3d(ax, cam, P[0], e2 * 0.97, color=C.blue_dark, lw=1.3, head=0.1)
    nrm = np.cross(e1, e2)
    nh = nrm / np.linalg.norm(nrm)
    c = P[0] + (e1 + e2) / 3.0
    arrow3d(ax, cam, c, 0.95 * nh, color=C.coral, lw=1.5, head=0.11, zorder=9)
    point3d(ax, cam, c, r=0.04, fc=C.coral)
    for i, (dx, dy) in enumerate(((-0.12, -0.14), (0.14, -0.08), (-0.12, 0.12))):
        point3d(ax, cam, P[i], r=0.045)
        label3d(ax, cam, P[i], rf"$\mathbf{{p}}_{i}$", offset=(dx, dy))
    label3d(ax, cam, P[0] + 0.55 * e1, r"$\mathbf{e}_1$", offset=(0.02, -0.16), color=C.blue_dark)
    label3d(ax, cam, P[0] + 0.55 * e2, r"$\mathbf{e}_2$", offset=(-0.17, 0.0), color=C.blue_dark)
    label3d(ax, cam, c + 0.95 * nh, r"$\hat{\mathbf{n}}$", offset=(0.12, 0.02), color=C.coral)
    label3d(ax, cam, c, r"$\mathbf{c}$", offset=(0.11, -0.1), color=C.coral)
    note(ax, 0.1, -0.82, r"$\mathbf{n}=\mathbf{e}_1\times\mathbf{e}_2,\;\; A=\frac{1}{2}\Vert\mathbf{n}\Vert$",
         size=8.6, color=C.ink)

    # ---------------------------------------------------------------- (b), (c)
    V, F = _fan()
    n, A, alpha, Na, Ng = _vertex_normals(V, F)
    cam = Camera(elev=40, azim=-72, scale=0.6, offset=(0.0, 0.05))
    wA = (A - A.min()) / (A.max() - A.min())
    for k, (x0, mode) in enumerate(((0.34, "area"), (0.67, "angle"))):
        ax = canvas(fig, [x0, 0.0, 0.33, 0.88], (-1.45, 1.6), (-1.4, 1.5))
        if mode == "area":
            cols = [lighten(C.blue, 0.9 - 0.6 * w) for w in wA]
        else:
            cols = [C.grey_fill] * len(F)
        # flat fills: in (b) the colour IS the weight, so no lighting may compete with it
        draw_mesh(ax, cam, V, F, colors=cols, lw=0.8, zorder=2, cull=False, shading=False)
        v = V[0]
        if mode == "angle":
            # corner angle arcs at v, drawn in 3D, sized by the angle
            for f, a_ in zip(F, alpha):
                b, c_ = V[f[1]] - v, V[f[2]] - v
                bu, cu = b / np.linalg.norm(b), c_ / np.linalg.norm(c_)
                t = np.linspace(0, 1, 30)
                r = 0.42
                arc = []
                for tt in t:
                    d = np.sin((1 - tt) * a_) * bu + np.sin(tt * a_) * cu
                    arc.append(v + r * d / np.sin(a_))
                arc = np.array(arc)
                wedge = np.vstack([v, arc])
                from matplotlib.patches import Polygon

                ax.add_patch(Polygon(cam.project(wedge), closed=True, fc=lighten(C.cyan, 0.72 - 0.5 * a_ / alpha.max()),
                                     ec="none", zorder=3))
                polyline3d(ax, cam, arc, color=C.cyan, lw=0.9, zorder=4)
        # face normals at the centroids
        for f, nn in zip(F, n):
            cc = V[f].mean(0)
            arrow3d(ax, cam, cc, 0.45 * nn, color=C.ink_soft, lw=0.8, head=0.07, zorder=5)
        other = Ng if mode == "area" else Na
        mine = Na if mode == "area" else Ng
        col = C.blue_dark if mode == "area" else C.cyan
        ocol = C.cyan if mode == "area" else C.blue_dark
        arrow3d(ax, cam, v, 1.35 * other, color=ocol, lw=1.0, head=0.09, zorder=8, ls=(0, (3, 2)), alpha=0.8)
        arrow3d(ax, cam, v, 1.35 * mine, color=col, lw=1.8, head=0.12, zorder=9)
        point3d(ax, cam, v, r=0.05, fc=C.coral)
        sym = r"$\mathbf{N}_v^{\mathrm{area}}$" if mode == "area" else r"$\mathbf{N}_v^{\mathrm{angle}}$"
        label3d(ax, cam, v + 1.35 * mine, sym, offset=(0.02, 0.2), color=col, size=10)
        if mode == "area":
            note(ax, 0.05, -1.28, r"$\sum_f A_f\,\hat{\mathbf{n}}_f$,  shade $\propto A_f$", size=8.4, color=C.ink)
        else:
            note(ax, 0.05, -1.28, r"$\sum_f \alpha_f(v)\,\hat{\mathbf{n}}_f$,  wedge $=\alpha_f$", size=8.4,
                 color=C.ink)
    return fig


# ------------------------------------------------------------------ closest point


def _clip(poly, p, n):
    """Clip a convex polygon to the half-plane (x - p) . n >= 0 (Sutherland-Hodgman)."""
    out = []
    m = len(poly)
    for i in range(m):
        a, b = poly[i], poly[(i + 1) % m]
        da, db = np.dot(a - p, n), np.dot(b - p, n)
        if da >= 0:
            out.append(a)
        if da * db < 0:
            out.append(a + (b - a) * (da / (da - db)))
    return out


@register("closest-point")
def closest_point():
    fig = figure(7.0, 2.85)
    fheading(fig, 0.0, 0.94, "a", "seven regions select the closest feature")
    fheading(fig, 0.56, 0.94, "b", "why an edge needs two normals")

    # ---------------------------------------------------------------- (a)
    ax = canvas(fig, [0.0, 0.0, 0.54, 0.88], (-1.75, 2.95), (-1.35, 2.1))
    P = [np.array([0.0, 0.0]), np.array([1.6, -0.15]), np.array([0.55, 1.2])]
    frame = [np.array(v, float) for v in ((-1.75, -1.35), (2.95, -1.35), (2.95, 2.1), (-1.75, 2.1))]
    for k in range(3):
        a, b = P[k], P[(k + 1) % 3]
        d = b - a
        nout = np.array([d[1], -d[0]])  # right of a->b = outside of a CCW triangle
        poly = _clip(_clip(_clip(frame, a, nout), a, d), b, -d)
        tri(ax, poly, C.cyan_fill, ec="none", lw=0, zorder=0)
        g = 0.5 * (a + b) + 0.55 * nout / np.linalg.norm(nout)
        label(ax, *g, f"edge {k}", size=7.4, color=C.cyan)
    for k in range(3):
        a, b, c = P[k], P[(k + 1) % 3], P[(k + 2) % 3]
        poly = _clip(_clip(frame, a, a - b), a, a - c)
        tri(ax, poly, C.coral_fill, ec="none", lw=0, zorder=0)
        out = (a - b) / np.linalg.norm(a - b) + (a - c) / np.linalg.norm(a - c)
        g = a + 0.62 * out / np.linalg.norm(out) + (np.array([0.05, 0.3]) if k == 0 else 0.0)
        label(ax, *g, f"corner {k}", size=7.4, color=C.coral)
    # the region boundaries: perpendiculars through the corners
    for k in range(3):
        a, b = P[k], P[(k + 1) % 3]
        d = (b - a) / np.linalg.norm(b - a)
        nout = np.array([d[1], -d[0]])
        for base in (a, b):
            ax.plot([base[0], base[0] + 3 * nout[0]], [base[1], base[1] + 3 * nout[1]], color=C.ink_faint, lw=0.6,
                    ls=(0, (2, 2)), zorder=1)
    tri(ax, P, C.blue_fill, ec=C.ink, lw=1.1, zorder=2)
    label(ax, 0.82, 0.3, "face", size=7.8, color=C.blue_dark)
    for k, v in enumerate(P):
        dot(ax, v, r=0.05, zorder=5)
    # three queries and their closest points (all in the triangle's plane)
    for x, q, col in ((np.array([1.5, 1.35]), None, C.cyan), (np.array([-0.95, -0.85]), P[0], C.coral),
                      (np.array([0.52, 0.62]), None, C.blue_dark)):
        if q is None:
            if x[1] > 1.0:  # edge 1: project onto P1 P2
                a, b = P[1], P[2]
                t = np.dot(x - a, b - a) / np.dot(b - a, b - a)
                q = a + t * (b - a)
            else:
                q = x
        ax.plot([x[0], q[0]], [x[1], q[1]], color=col, lw=0.9, ls=(0, (1.5, 1.5)), zorder=4)
        ring(ax, x, r=0.045, ec=col, lw=1.0)
        if np.linalg.norm(x - q) > 1e-9:
            dot(ax, q, r=0.04, fc=col, zorder=6)
    label(ax, 1.62, 1.52, r"$\mathbf{x}$", size=9.4, color=C.cyan)
    label(ax, 1.05, 0.72, r"$\mathbf{q}$", size=9.4, color=C.cyan)
    note(ax, 0.6, -1.2, "every region boundary is a perpendicular through a corner", size=6.8)

    # ---------------------------------------------------------------- (b) knife edge
    bx = canvas(fig, [0.57, 0.0, 0.43, 0.88], (-1.85, 1.75), (-1.35, 1.6))
    q = np.array([0.0, 0.0])
    s = 0.3
    dT, dT2 = np.array([-1.0, s]), np.array([-1.0, -s])
    far = 1.8
    solid = [q, q + far * dT, q + far * dT2]
    tri(bx, solid, C.blue_fill, ec="none", lw=0, zorder=1)
    nT = np.array([s, 1.0]) / np.hypot(1, s)
    nT2 = np.array([s, -1.0]) / np.hypot(1, s)
    # the edge's Voronoi region: the wedge between the two normals
    a0, a1 = np.degrees(np.arctan2(nT2[1], nT2[0])), np.degrees(np.arctan2(nT[1], nT[0]))
    from matplotlib.patches import Wedge

    bx.add_patch(Wedge(q, 1.6, a0, a1, fc=C.cyan_fill, ec="none", zorder=0))
    for d in (dT, dT2):
        bx.plot([q[0], q[0] + far * d[0]], [q[1], q[1] + far * d[1]], color=C.ink, lw=1.6, zorder=3)
    label(bx, -1.15, 0.62, r"$T$", size=10.5)
    label(bx, -1.15, -0.62, r"$T'$", size=10.5)
    note(bx, -1.2, 0.0, "inside", size=7.2, color=C.blue_dark)
    note(bx, 1.05, 1.28, "edge region", size=6.8, color=C.cyan)
    arrow(bx, q, q + 0.75 * nT, color=C.ink_soft, lw=1.0, head=0.09)
    arrow(bx, q, q + 0.75 * nT2, color=C.ink_soft, lw=1.0, head=0.09)
    label(bx, 0.42, 0.95, r"$\hat{\mathbf{n}}_T$", size=9.6, color=C.ink_soft)
    label(bx, 0.42, -0.95, r"$\hat{\mathbf{n}}_{T'}$", size=9.6, color=C.ink_soft)
    ps = nT + nT2
    arrow(bx, q, q + 1.0 * ps / np.linalg.norm(ps), color=C.cyan, lw=1.6, head=0.11)
    label(bx, 1.02, 0.17, r"$\hat{\mathbf{n}}_T+\hat{\mathbf{n}}_{T'}$", size=9.2, color=C.cyan, ha="left")
    x = np.array([0.95, -0.52])
    bx.plot([q[0], x[0]], [q[1], x[1]], color=C.coral, lw=0.9, ls=(0, (1.5, 1.5)), zorder=4)
    ring(bx, x, r=0.05, ec=C.coral, lw=1.1)
    dot(bx, q, r=0.055, zorder=6)
    label(bx, -0.14, 0.2, r"$\mathbf{q}$", size=9.4)
    label(bx, 1.1, -0.64, r"$\mathbf{x}$", size=9.4, color=C.coral)
    label(bx, -0.05, -1.13, r"$(\mathbf{x}-\mathbf{q})\cdot\hat{\mathbf{n}}_T<0$: inside?  wrong", size=8.4,
          color=C.coral)
    label(bx, -0.05, -1.4, r"$(\mathbf{x}-\mathbf{q})\cdot(\hat{\mathbf{n}}_T+\hat{\mathbf{n}}_{T'})>0$: outside",
          size=8.4, color=C.cyan)
    return fig
