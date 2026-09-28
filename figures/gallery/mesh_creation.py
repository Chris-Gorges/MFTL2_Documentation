"""Figures for ``src/mesh_creation/README.md`` -- the icosphere and marching cubes."""

from __future__ import annotations

import numpy as np

from mftlfig import register
from mftlfig.meshes import icosphere
from mftlfig.scene3d import Camera, arrow3d, draw_mesh, point3d, polyline3d
from mftlfig.style import C, arrow, canvas, dot, fheading, figure, label, note, ring, tri

# ------------------------------------------------------------------ icosphere


def _ccw_marker(ax, pts, color, r=0.09):
    """A small counter-clockwise circular arrow at the centroid of a triangle."""
    g = np.mean(pts, axis=0)
    t = np.radians(np.linspace(-30, 240, 40))
    ax.plot(g[0] + r * np.cos(t), g[1] + r * np.sin(t), color=color, lw=0.8)
    arrow(ax, (g[0] + r * np.cos(t[-2]), g[1] + r * np.sin(t[-2])), (g[0] + r * np.cos(t[-1]), g[1] + r * np.sin(t[-1])),
          color=color, lw=0.0, head=0.075)
    return g


@register("icosphere")
def icosphere_figure():
    fig = figure(7.0, 2.55)
    fheading(fig, 0.0, 0.94, "a", "1-to-4 subdivision of one face")
    fheading(fig, 0.37, 0.94, "b", r"refinement $r$, projected once onto the sphere")

    # ---------------------------------------------------------------- (a)
    ax = canvas(fig, [0.0, 0.0, 0.35, 0.86], (-0.25, 2.3), (-0.72, 1.95))
    v0, v1, v2 = np.array([0.0, 0.0]), np.array([2.0, 0.0]), np.array([1.0, 1.73])
    m0, m1, m2 = (v0 + v1) / 2, (v1 + v2) / 2, (v2 + v0) / 2
    # the neighbour across v0-v1 finds m0 through the twin, not a hash map
    w = np.array([1.0, -0.62])
    tri(ax, [v0, w, v1], "#f6f7f9", ec=C.ink_faint, lw=0.7, ls=(0, (3, 2)), zorder=1)
    note(ax, 1.0, -0.36, "twin shares $m_0$", size=6.6)
    kids = [([v0, m0, m2], "0"), ([v1, m1, m0], "1"), ([v2, m2, m1], "2"), ([m0, m1, m2], "3")]
    fills = [C.blue_fill, C.cyan_fill, C.amber_fill, C.grey_fill]
    for (pts, s), fc in zip(kids, fills):
        tri(ax, pts, fc, ec=C.ink, lw=0.9, zorder=2)
        g = _ccw_marker(ax, pts, C.ink_soft, r=0.1)
        label(ax, g[0], g[1], s, size=7.2, color=C.ink)
    for p, s, off in ((v0, r"$v_0$", (-0.14, -0.1)), (v1, r"$v_1$", (0.14, -0.1)), (v2, r"$v_2$", (0.0, 0.15)),
                      (m0, r"$m_0$", (0.0, -0.17)), (m1, r"$m_1$", (0.17, 0.05)), (m2, r"$m_2$", (-0.17, 0.05))):
        (dot if s.startswith("$v") else ring)(ax, p, r=0.045, zorder=5)
        label(ax, p[0] + off[0], p[1] + off[1], s, size=9.2)

    # ---------------------------------------------------------------- (b)
    cam = Camera(elev=18, azim=-60)
    counts = [(12, 20), (42, 80), (162, 320), (642, 1280)]
    for r in range(4):
        bx = canvas(fig, [0.37 + r * 0.158, 0.02, 0.155, 0.84], (-1.15, 1.15), (-1.9, 1.3))
        V, F = icosphere(r)
        draw_mesh(bx, cam, V, F, color=C.blue_fill, lw=[0.8, 0.6, 0.45, 0.3][r], zorder=2)
        label(bx, 0.0, -1.33, rf"$r={r}$", size=9.6)
        note(bx, 0.0, -1.68, f"{counts[r][0]} V · {counts[r][1]} F", size=6.8)
    return fig


# ------------------------------------------------------------------ marching cubes


def _cube_edge(p, q):
    """Port of ``cube_edge`` in marching_cubes.c."""
    diff = p ^ q
    a = 0 if diff == 1 else (1 if diff == 2 else 2)
    lower = p & q
    b, c = (a + 1) % 3, (a + 2) % 3
    return 4 * a + ((lower >> b) & 1) + 2 * ((lower >> c) & 1)


def _edge_lower_corner(e):
    a = e // 4
    b, c = (a + 1) % 3, (a + 2) % 3
    return ((e & 1) << b) | (((e >> 1) & 1) << c)


def _edge_faces(e):
    a = e // 4
    b, c = (a + 1) % 3, (a + 2) % 3
    return (1 << (2 * b + (e & 1))) | (1 << (2 * c + ((e >> 1) & 1)))


def build_case(mask):
    """Port of ``build_case`` + ``triangulate_loop``: loops and triangles of one case."""
    nxt = [-1] * 12
    ccw = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for f in range(6):
        a, side = f // 2, f % 2
        b, c = (a + 1) % 3, (a + 2) % 3
        cyc = []
        for i in range(4):
            o = ccw[i] if side else ccw[(4 - i) % 4]
            cyc.append((side << a) | (o[0] << b) | (o[1] << c))
        for i in range(4):
            s0, s1 = (mask >> cyc[i]) & 1, (mask >> cyc[(i + 1) % 4]) & 1
            if not (s0 == 0 and s1 == 1):
                continue
            for j in range(1, 4):
                u = (i + j) % 4
                t0, t1 = (mask >> cyc[u]) & 1, (mask >> cyc[(u + 1) % 4]) & 1
                if t0 == 1 and t1 == 0:
                    nxt[_cube_edge(cyc[i], cyc[(i + 1) % 4])] = _cube_edge(cyc[u], cyc[(u + 1) % 4])
                    break
    used = [False] * 12
    loops, tris = [], []
    for e in range(12):
        if nxt[e] < 0 or used[e]:
            continue
        poly = []
        u = e
        while not used[u]:
            used[u] = True
            poly.append(u)
            u = nxt[u]
        loops.append(poly)
        n = len(poly)
        for apex in range(n):
            ok = all(not (_edge_faces(poly[apex]) & _edge_faces(poly[j]))
                     for j in range(n) if j not in (apex, (apex + 1) % n, (apex + n - 1) % n))
            if ok:
                for j in range(1, n - 1):
                    tris.append((poly[apex], poly[(apex + j) % n], poly[(apex + j + 1) % n]))
                break
    return loops, tris


def _corner(c):
    return np.array([c & 1, (c >> 1) & 1, (c >> 2) & 1], float)


def _face_square(ax, x0, y0, signs, title, s=1.0):
    """One cell face walked counter-clockwise; signs[i] = True where corner i is inside."""
    P = [np.array([x0, y0]), np.array([x0 + s, y0]), np.array([x0 + s, y0 + s]), np.array([x0, y0 + s])]
    # crossing points (midpoints) on edges with a sign change
    cross = {}
    for i in range(4):
        if signs[i] != signs[(i + 1) % 4]:
            cross[i] = 0.5 * (P[i] + P[(i + 1) % 4])
    # segments: entering (out -> in) to the next leaving (in -> out) along the walk
    segs = []
    for i in range(4):
        if not signs[i] and signs[(i + 1) % 4]:
            for j in range(1, 4):
                u = (i + j) % 4
                if signs[u] and not signs[(u + 1) % 4]:
                    segs.append((i, u))
                    break
    # the inside region of the face, polygon walk
    region = []
    for i in range(4):
        if signs[i]:
            region.append(P[i])
        if i in cross:
            region.append(cross[i])
    # shade each inside piece: split at segments by building polygons per segment
    for i, u in segs:
        piece = [cross[i]]
        k = (i + 1) % 4
        while True:
            piece.append(P[k])
            if k == u:
                break
            k = (k + 1) % 4
        piece.append(cross[u])
        tri(ax, piece, C.blue_fill, ec="none", lw=0, zorder=1)
    tri(ax, P, "none", ec=C.ink, lw=0.9, zorder=2)
    # walk direction, faint, just outside the square
    for i in range(4):
        a, b = P[i], P[(i + 1) % 4]
        d = (b - a) / s
        nout = np.array([d[1], -d[0]])
        arrow(ax, a + 0.3 * (b - a) + 0.1 * nout * s, a + 0.7 * (b - a) + 0.1 * nout * s, color=C.ink_faint, lw=0.7,
              head=0.07)
    for i, u in segs:
        arrow(ax, cross[i], cross[u], color=C.coral, lw=1.5, head=0.1, shorten=0.03, start_shorten=0.03, zorder=4)
    for i in range(4):
        if signs[i]:
            dot(ax, P[i], r=0.055, fc=C.blue_dark, zorder=5)
        else:
            ring(ax, P[i], r=0.05, ec=C.ink, zorder=5)
    for q in cross.values():
        dot(ax, q, r=0.035, fc=C.coral, zorder=6)
    note(ax, x0 + s / 2, y0 - 0.26, title, size=6.9)


@register("marching-cubes")
def marching_cubes():
    fig = figure(7.0, 2.45)
    fheading(fig, 0.0, 0.94, "a", "the face rule: enter the inside, connect to the next exit")
    fheading(fig, 0.66, 0.94, "b", "one case in 3D")

    ax = canvas(fig, [0.0, 0.02, 0.63, 0.86], (-0.2, 6.35), (-0.55, 1.62))
    cases = [((True, False, False, False), "one corner in"), ((True, True, False, False), "an edge in"),
             ((True, False, True, False), "ambiguous: diagonal"), ((True, True, True, False), "three in")]
    for k, (signs, t) in enumerate(cases):
        _face_square(ax, 0.2 + k * 1.55, 0.05, signs, t, s=1.05)
    # legend
    dot(ax, (0.3, 1.45), r=0.05, fc=C.blue_dark)
    note(ax, 0.42, 1.45, r"inside, $\phi<0$", ha="left", size=6.9, color=C.ink)
    ring(ax, (1.72, 1.45), r=0.045)
    note(ax, 1.84, 1.45, r"outside", ha="left", size=6.9, color=C.ink)
    arrow(ax, (2.72, 1.45), (3.02, 1.45), color=C.ink_faint, lw=0.7, head=0.07)
    note(ax, 3.1, 1.45, "walk, counter-clockwise from outside", ha="left", size=6.9, color=C.ink)

    # ---------------------------------------------------------------- (b)
    bx = canvas(fig, [0.66, 0.0, 0.34, 0.88], (-0.95, 1.05), (-0.95, 1.05))
    cam = Camera(elev=26, azim=-58, scale=0.86, offset=(-0.02, 0.0))
    mask = 0b00000111  # corners 0, 1, 2: an L on the bottom face
    phi = np.array([-0.7, -0.35, -0.55, 0.45, 0.8, 0.6, 0.5, 0.9])
    loops, tris = build_case(mask)
    X = np.array([_corner(c) for c in range(8)]) - 0.5

    def crossing(e):
        c0 = _edge_lower_corner(e)
        c1 = c0 | (1 << (e // 4))
        t = phi[c0] / (phi[c0] - phi[c1])
        return X[c0] + t * (X[c1] - X[c0])

    # cube edges: back ones dashed
    edges = [(p, q) for p in range(8) for q in range(8) if p < q and bin(p ^ q).count("1") == 1]
    back = int(np.argmax(cam.depth(X)))
    for p, q in edges:
        hidden = back in (p, q)
        polyline3d(bx, cam, np.array([X[p], X[q]]), color=C.ink_soft if hidden else C.ink, lw=0.7 if hidden else 0.9,
                   ls=(0, (3, 2)) if hidden else "-", zorder=1)
    Q = {e: crossing(e) for loop in loops for e in loop}
    Vt = np.array([Q[e] for t in tris for e in t])
    Ft = np.arange(len(Vt)).reshape(-1, 3)
    draw_mesh(bx, cam, Vt, Ft, color=C.cyan_fill, lw=0.8, cull=False, zorder=3, alpha=0.78)
    for loop in loops:
        P = np.array([Q[e] for e in loop + loop[:1]])
        polyline3d(bx, cam, P, color=C.coral, lw=1.4, zorder=4)
    for e, q in Q.items():
        point3d(bx, cam, q, r=0.028, fc=C.coral, zorder=6)
    for t in tris:
        a, b, c = (Q[e] for e in t)
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n)
        arrow3d(bx, cam, (a + b + c) / 3, 0.28 * n, color=C.cyan, lw=1.0, head=0.06, zorder=7)
    for c in range(8):
        if (mask >> c) & 1:  # below the surface: drawn under it, seen through it
            point3d(bx, cam, X[c], r=0.04, fc=C.blue_dark, zorder=2)
        else:
            xy = cam.project(X[c])
            ring(bx, xy, r=0.035, ec=C.ink, zorder=5)
    note(bx, 0.0, -0.9, f"{len(loops[0])} crossings, {len(tris)} triangles; normals point out", size=6.8)
    return fig
