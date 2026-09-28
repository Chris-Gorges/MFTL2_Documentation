"""A small orthographic 3D renderer on top of a 2D matplotlib axes.

mplot3d sorts whole collections, not faces, so a shaded surface with arrows
through it comes out in the wrong order. The figures need very little -- an
orthographic camera (as a TikZ ``3d`` picture uses), Lambert shading, painter's
ordering per face -- so it is done here directly: project, shade, sort, draw
2D polygons. Everything then lives on one equal-aspect 2D axes and mixes
freely with the 2D helpers in :mod:`style`.
"""

from __future__ import annotations

import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
from matplotlib.patches import Polygon

from .style import C, stealth_head


class Camera:
    """Orthographic camera looking at the origin.

    :param elev: elevation in degrees (0 = horizon, 90 = from above).
    :param azim: azimuth in degrees, rotating about the z axis.
    :param scale: uniform scale applied after projection.
    :param offset: 2D offset applied after scaling.
    """

    def __init__(self, elev=22.0, azim=-58.0, scale=1.0, offset=(0.0, 0.0), roll=0.0):
        e, a, r = np.radians(elev), np.radians(azim), np.radians(roll)
        # view direction points from the camera towards the scene
        self.forward = -np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
        up = np.array([0.0, 0.0, 1.0])
        right = np.cross(self.forward, up)
        right /= np.linalg.norm(right)
        upv = np.cross(right, self.forward)
        if r:
            right, upv = np.cos(r) * right + np.sin(r) * upv, -np.sin(r) * right + np.cos(r) * upv
        self.right, self.up = right, upv
        self.scale = scale
        self.offset = np.asarray(offset, float)

    def project(self, P):
        """Project points (..., 3) to 2D (..., 2)."""
        P = np.asarray(P, float)
        xy = np.stack([P @ self.right, P @ self.up], axis=-1)
        return xy * self.scale + self.offset

    def depth(self, P):
        """Distance along the view direction; larger is farther away."""
        return np.asarray(P, float) @ self.forward

    def facing(self, normals):
        """True where a face normal points towards the camera."""
        return np.asarray(normals, float) @ self.forward < 0.0


#: Key light from upper left front, slightly behind the viewer.
LIGHT = np.array([-0.45, -0.55, 0.70])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def face_normals(V, F):
    """Unit normals and areas of triangles ``F`` over vertices ``V``."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(n, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        n = n / (2.0 * area[:, None])
    return np.nan_to_num(n), area


def shade(base, normals, cam=None, light=LIGHT, ambient=0.58, diffuse=0.42, spec=0.10, two_sided=True):
    """Lambert + a touch of Blinn specular, returned as RGB rows.

    The light is fixed in the CAMERA frame when ``cam`` is given (a studio
    light that moves with the viewer), which keeps every figure lit alike
    regardless of its azimuth.
    """
    base = np.array(to_rgb(base))
    N = np.asarray(normals, float)
    if cam is not None:
        L = -cam.forward * 0.62 + cam.up * 0.55 - cam.right * 0.45
        L = L / np.linalg.norm(L)
        H = L - cam.forward
        H = H / np.linalg.norm(H)
    else:
        L = light
        H = L
    d = N @ L
    if two_sided:
        d = np.abs(d)
    d = np.clip(d, 0.0, 1.0)
    s = np.clip(np.abs(N @ H) if two_sided else N @ H, 0.0, 1.0) ** 24
    rgb = base[None, :] * (ambient + diffuse * d[:, None]) + spec * s[:, None]
    return np.clip(rgb, 0.0, 1.0)


def draw_mesh(ax, cam, V, F, color=None, colors=None, edgecolor=None, lw=0.45, cull=True, zorder=2,
              alpha=1.0, shading=True, edge_alpha=1.0, back_color=None):
    """Draw a triangle mesh with painter's ordering.

    :param color: one base colour for every face (shaded).
    :param colors: per-face base colours (overrides ``color``).
    :param cull: drop faces pointing away from the camera (closed surfaces).
    :param back_color: when not culling, the base colour of back faces.
    :returns: the PolyCollection.
    """
    V = np.asarray(V, float)
    F = np.asarray(F, int)
    n, _ = face_normals(V, F)
    front = cam.facing(n)
    keep = front if cull else np.ones(len(F), bool)
    Fk, nk, frk = F[keep], n[keep], front[keep]
    if colors is None:
        base = np.tile(np.array(to_rgb(color or C.blue_fill)), (len(Fk), 1))
    else:
        base = np.array([to_rgb(c) for c in np.asarray(colors, dtype=object)[keep]])
    if back_color is not None:
        base[~frk] = np.array(to_rgb(back_color))
    if shading:
        rgb = np.vstack([shade(b, nn[None, :], cam)[0] for b, nn in zip(base, nk)]) if len(Fk) else base
    else:
        rgb = base
    depth = cam.depth(V[Fk].mean(axis=1))
    order = np.argsort(-depth)
    polys = cam.project(V[Fk][order])
    ec = edgecolor if edgecolor is not None else C.ink
    ecs = np.tile(np.append(to_rgb(ec), edge_alpha), (len(order), 1)) if ec != "face" else "face"
    pc = PolyCollection(polys, facecolors=np.column_stack([rgb[order], np.full(len(order), alpha)]),
                        edgecolors=ecs, linewidths=lw, zorder=zorder, joinstyle="round")
    ax.add_collection(pc)
    return pc


def polyline3d(ax, cam, P, color=None, lw=1.0, zorder=6, ls="-", alpha=1.0):
    """A 3D polyline."""
    xy = cam.project(P)
    ax.plot(xy[:, 0], xy[:, 1], color=color or C.ink, lw=lw, zorder=zorder, ls=ls, alpha=alpha,
            solid_capstyle="round")


def arrow3d(ax, cam, p, v, color=None, lw=1.2, head=0.085, zorder=7, ls="-", alpha=1.0):
    """An arrow from 3D point ``p`` along 3D vector ``v``, with a stealth head in projection.

    The head keeps a constant 2D size; a vector almost along the view axis is
    drawn as a short stub with a head, which is the honest picture.
    """
    color = color or C.ink
    p = np.asarray(p, float)
    q = p + np.asarray(v, float)
    a, b = cam.project(p), cam.project(q)
    d = b - a
    L = np.linalg.norm(d)
    if L < 1e-9:
        return
    u = d / L
    h = min(head, 0.6 * L)
    tail = b - 0.72 * h * u
    ax.plot([a[0], tail[0]], [a[1], tail[1]], color=color, lw=lw, zorder=zorder, ls=ls, alpha=alpha,
            solid_capstyle="round")
    hv = stealth_head(b, u, h, h * 0.78)
    ax.add_patch(Polygon(hv, closed=True, fc=color, ec=color, lw=0.4, zorder=zorder, alpha=alpha,
                         joinstyle="miter"))


def point3d(ax, cam, p, r=0.04, fc=None, ec=None, lw=0.9, zorder=8):
    """A vertex marker at a 3D point."""
    from matplotlib.patches import Circle

    xy = cam.project(p)
    ax.add_patch(Circle(xy, r, fc=fc or C.ink, ec=ec or C.paper, lw=lw, zorder=zorder))
    return xy


def label3d(ax, cam, p, s, offset=(0.0, 0.0), **kw):
    """Label at a projected 3D point, with a 2D offset in data units."""
    from .style import label

    xy = cam.project(p) + np.asarray(offset, float)
    return label(ax, xy[0], xy[1], s, **kw)


def planar_patch(ax, cam, origin, u, v, fc, ec=None, lw=0.6, alpha=0.35, zorder=1, ls="-"):
    """A parallelogram ``origin + s u + t v`` for s, t in [0, 1] (a plane swatch)."""
    o = np.asarray(origin, float)
    u = np.asarray(u, float)
    v = np.asarray(v, float)
    P = np.array([o, o + u, o + u + v, o + v])
    xy = cam.project(P)
    ax.add_patch(Polygon(xy, closed=True, fc=fc, ec=ec or "none", lw=lw, alpha=alpha, zorder=zorder, ls=ls))
    return xy
