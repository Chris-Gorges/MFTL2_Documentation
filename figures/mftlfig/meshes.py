"""Meshes the figures are drawn from, built with the library's own conventions.

The icosphere follows ``src/mesh_creation/sphere_creation.c``: vertices
``(0, +-1, +-phi)`` and cyclic permutations, counter-clockwise faces seen from
outside, 1-to-4 midpoint subdivision, projected ONCE onto the sphere at the end.
A figure of the icosphere is therefore a picture of what the library builds,
not of an icosphere in general.
"""

from __future__ import annotations

import numpy as np

PHI = (1.0 + 5.0 ** 0.5) / 2.0


def icosahedron():
    """The regular icosahedron on the unit sphere, outward (CCW) faces."""
    V = np.array(
        [
            [-1, PHI, 0], [1, PHI, 0], [-1, -PHI, 0], [1, -PHI, 0],
            [0, -1, PHI], [0, 1, PHI], [0, -1, -PHI], [0, 1, -PHI],
            [PHI, 0, -1], [PHI, 0, 1], [-PHI, 0, -1], [-PHI, 0, 1],
        ],
        float,
    )
    V /= np.linalg.norm(V, axis=1)[:, None]
    F = np.array(
        [
            [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
            [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
            [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
            [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
        ],
        int,
    )
    return V, F


def subdivide(V, F):
    """One 1-to-4 midpoint subdivision, sub-triangles in the parent's rotational order.

    Midpoints are identified per undirected edge (the library does it per
    half-edge and twin; the result is the same mesh).
    """
    V = list(map(tuple, V))
    mid = {}

    def m(i, j):
        key = (min(i, j), max(i, j))
        if key not in mid:
            a, b = np.array(V[i]), np.array(V[j])
            V.append(tuple(0.5 * (a + b)))
            mid[key] = len(V) - 1
        return mid[key]

    out = []
    for a, b, c in F:
        ab, bc, ca = m(a, b), m(b, c), m(c, a)
        out += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]
    return np.array(V, float), np.array(out, int)


def icosphere(r, radius=1.0, project=True):
    """Icosphere of refinement ``r``: flat subdivision, projected once at the end."""
    V, F = icosahedron()
    for _ in range(r):
        V, F = subdivide(V, F)
    if project:
        V = radius * V / np.linalg.norm(V, axis=1)[:, None]
    return V, F


def jittered_patch(nx, ny, jitter=0.18, seed=7, spacing=1.0, hexagonal=True):
    """A planar Delaunay triangulation of a jittered (hexagonal) point lattice.

    :returns: ``(P, F)`` with ``P`` of shape (n, 2) and CCW triangles ``F``.
    """
    from scipy.spatial import Delaunay

    rng = np.random.default_rng(seed)
    pts = []
    for j in range(ny):
        for i in range(nx):
            x = i * spacing + (0.5 * spacing if (hexagonal and j % 2) else 0.0)
            y = j * spacing * (np.sqrt(3) / 2 if hexagonal else 1.0)
            pts.append((x, y))
    P = np.array(pts, float)
    P += rng.uniform(-jitter, jitter, P.shape) * spacing
    tri = Delaunay(P)
    F = tri.simplices.copy()
    # CCW orientation
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    F[cross < 0] = F[cross < 0][:, [0, 2, 1]]
    # drop slivers on the convex hull
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    area = 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    e = np.stack([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)], 1)
    q = 4 * np.sqrt(3) * area / (e ** 2).sum(1)
    F = F[q > 0.25]
    return P, F


def edges_of(F):
    """Undirected edges -> list of incident triangles."""
    E = {}
    for t, (a, b, c) in enumerate(F):
        for u, v in ((a, b), (b, c), (c, a)):
            E.setdefault((min(u, v), max(u, v)), []).append(t)
    return E


def triangle_neighbours(F):
    """``nb[t][k]`` = triangle across edge (corner k -> corner k+1), or -1."""
    E = edges_of(F)
    nb = -np.ones((len(F), 3), int)
    for t, tri_ in enumerate(F):
        for k in range(3):
            u, v = tri_[k], tri_[(k + 1) % 3]
            ts = E[(min(u, v), max(u, v))]
            for s in ts:
                if s != t:
                    nb[t, k] = s
    return nb
