"""Figures for ``src/bvh/README.md`` -- the LBVH, periodic images, the narrow phase."""

from __future__ import annotations

import numpy as np
from matplotlib.patches import Rectangle

from mftlfig import register
from mftlfig.scene3d import Camera, draw_mesh, label3d, point3d, polyline3d
from mftlfig.style import C, box, canvas, code, dim_line, dot, fheading, figure, halo_label, label, lighten, note, tri

BITS = 3  # per axis in the figure (the library uses 21 per axis, 3 axes)


def _spread(v):
    out = 0
    for i in range(BITS):
        out |= ((v >> i) & 1) << (2 * i)
    return out


def _key(q):
    return _spread(q[0]) | (_spread(q[1]) << 1)


def _delta(keys, i, j):
    """Common prefix length with the index tie-break (Karras 2012), on 2*BITS-bit keys."""
    nb = 2 * BITS
    if keys[i] != keys[j]:
        x = keys[i] ^ keys[j]
        return nb - x.bit_length()
    x = i ^ j
    return nb + (32 - x.bit_length())


def build_radix_tree(keys):
    """Top-down radix split exactly as the README states it: a node over sorted slots
    [f, l] splits at gamma = max{m in [f, l) : delta(f, m) > delta(f, l)}.

    :returns: list of nodes (f, l, left, right, split_bit); leaves have left = None.
    """
    nodes = []

    def rec(f, l, depth):
        idx = len(nodes)
        nodes.append(None)
        if f == l:
            nodes[idx] = (f, l, None, None, depth, None)
            return idx
        dfl = _delta(keys, f, l)
        g = max(m for m in range(f, l) if _delta(keys, f, m) > dfl)
        left = rec(f, g, depth + 1)
        right = rec(g + 1, l, depth + 1)
        nodes[idx] = (f, l, left, right, depth, dfl)
        return idx

    rec(0, len(keys) - 1, 0)
    return nodes


def _primitives():
    """Ten small triangles on a circular interface; two share a Morton cell (equal keys)."""
    ang = np.radians(np.linspace(20, 330, 10))
    cx = 0.5 + 0.36 * np.cos(ang)
    cy = 0.5 + 0.36 * np.sin(ang)
    cx[4], cy[4] = cx[3] - 0.045, cy[3] + 0.02  # same cell as primitive 3
    tris = []
    for x, y, a in zip(cx, cy, ang):
        r = 0.032
        tris.append(np.array([[x + r * np.cos(a + k * 2.1), y + r * np.sin(a + k * 2.1)] for k in range(3)]))
    return np.array(tris)


@register("lbvh")
def lbvh():
    fig = figure(7.0, 3.1)
    fheading(fig, 0.0, 0.955, "a", "sorted by Morton key, split on dyadic planes")
    fheading(fig, 0.47, 0.955, "b", "the radix tree over the sorted keys")

    T = _primitives()
    cen = T.mean(axis=1)
    n = 1 << BITS
    q = np.floor(cen * n).astype(int).clip(0, n - 1)
    keys0 = np.array([_key(v) for v in q])
    order = np.argsort(keys0, kind="stable")
    keys = [int(k) for k in keys0[order]]
    T, cen = T[order], cen[order]
    nodes = build_radix_tree(keys)

    # ---------------------------------------------------------------- (a) space
    ax = canvas(fig, [0.0, 0.0, 0.45, 0.9], (-0.06, 1.04), (-0.06, 1.04))
    for i in range(n + 1):
        ax.plot([0, 1], [i / n, i / n], color=C.rule, lw=0.4, zorder=0)
        ax.plot([i / n, i / n], [0, 1], color=C.rule, lw=0.4, zorder=0)
    depth_col = [C.blue_dark, C.blue, C.cyan, C.green, C.amber, C.coral]
    for f, l, left, right, depth, _ in nodes:
        if left is None or depth > 3:
            continue
        pts = T[f:l + 1].reshape(-1, 2)
        lo, hi = pts.min(0) - 0.012 * (4 - depth), pts.max(0) + 0.012 * (4 - depth)
        col = depth_col[depth]
        ax.add_patch(Rectangle(lo, *(hi - lo), fc=lighten(col, 0.93), ec=col, lw=0.9, zorder=1 + depth))
    for i, tr in enumerate(T):
        tri(ax, tr, C.grey_mid, ec=C.ink, lw=0.6, zorder=8)
        d = cen[i] - 0.5
        d = d / np.linalg.norm(d)
        halo_label(ax, *(cen[i] + 0.065 * d), str(i), size=6.8, color=C.ink)

    # ---------------------------------------------------------------- (b) tree
    bx = canvas(fig, [0.47, 0.0, 0.53, 0.9], (-0.6, 10.1), (-2.4, 5.2), equal=False)
    m = len(keys)
    xs = {}
    ys = {}

    def place(idx):
        f, l, left, right, depth, _ = nodes[idx]
        if left is None:
            xs[idx] = f * 1.0 + 0.5 * (10 - m) / 2
            ys[idx] = 0.0
        else:
            place(left)
            place(right)
            xs[idx] = 0.5 * (xs[left] + xs[right])
            ys[idx] = 4.6 - 0.95 * depth
        return idx

    place(0)
    for idx, (f, l, left, right, depth, dfl) in enumerate(nodes):
        if left is None:
            continue
        for ch in (left, right):
            yc = ys[ch] + (0.18 if nodes[ch][2] is None else 0.0)
            bx.plot([xs[idx], xs[ch]], [ys[idx], yc], color=C.ink_soft, lw=0.8, zorder=1)
    for idx, (f, l, left, right, depth, dfl) in enumerate(nodes):
        if left is None:
            dot(bx, (xs[idx], ys[idx] + 0.18), r=0.09, fc=C.ink, zorder=3)
            label(bx, xs[idx], ys[idx] - 0.15, str(f), size=7.0, color=C.ink)
            k = keys[f]
            code(bx, xs[idx], ys[idx] - 1.15, "\n".join(f"{k:0{2 * BITS}b}"), size=6.6, color=C.ink, linespacing=1.0)
        else:
            col = depth_col[min(depth, len(depth_col) - 1)] if depth <= 3 else C.ink_soft
            bx.add_patch(Rectangle((xs[idx] - 0.2, ys[idx] - 0.2), 0.4, 0.4, fc=lighten(col, 0.8), ec=col, lw=0.9,
                                   zorder=3))
            if dfl is not None and dfl < 2 * BITS:
                bit = 2 * BITS - 1 - dfl
                axis = "xy"[bit % 2]
                note(bx, xs[idx] + 0.3, ys[idx] + 0.18, f"{axis}", size=6.2, color=col, ha="left")
            elif dfl is not None:
                note(bx, xs[idx] + 0.3, ys[idx] + 0.18, "index", size=6.0, color=C.coral, ha="left")
    note(bx, -0.55, -1.15, "key", size=6.4, ha="left")
    dup = [i for i in range(m - 1) if keys[i] == keys[i + 1]]
    if dup:
        i = dup[0]
        note(bx, 4.8, -2.3, f"equal keys ({i}, {i + 1}) are split by their index: every node splits", size=6.4,
             color=C.coral)
    return fig


# ------------------------------------------------------------------ periodic images, envelope


def _blob(c, r, n=60, seed=0, wob=0.08):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rng = np.random.default_rng(seed)
    k = rng.uniform(0, 2 * np.pi, 3)
    rr = r * (1 + wob * np.cos(3 * t + k[0]) + 0.5 * wob * np.sin(5 * t + k[1]))
    return np.stack([c[0] + rr * np.cos(t), c[1] + rr * np.sin(t)], 1)


@register("periodic-images")
def periodic_images():
    fig = figure(7.0, 2.7)
    fheading(fig, 0.0, 0.95, "a", r"between bodies: traverse each image of $B$")
    fheading(fig, 0.62, 0.95, "b", "the envelope of a pair")

    # ---------------------------------------------------------------- (a)
    ax = canvas(fig, [0.0, 0.0, 0.6, 0.88], (-1.02, 2.12), (-0.08, 1.4))
    L, H = 1.0, 1.3
    for s in (-1, 0, 1):
        box(ax, s * L, 0, L, H, fc="#fafbfc" if s else C.paper, ec=C.ink if s == 0 else C.rule, lw=1.0 if s == 0 else 0.7,
            r=0.0, zorder=0, ls="-" if s == 0 else (0, (3, 2)))
    A = _blob((0.84, 0.72), 0.13, seed=1)
    B = _blob((0.14, 0.6), 0.12, seed=2)
    tri(ax, A, C.blue_fill, ec=C.blue, lw=1.1, zorder=3)
    ra = (A.min(0) - 0.03, A.max(0) + 0.03)
    ax.add_patch(Rectangle(ra[0], *(ra[1] - ra[0]), fc="none", ec=C.blue, lw=0.8, ls=(0, (2, 1.5)), zorder=4))
    label(ax, 0.84, 0.72, r"$A$", size=10.5, color=C.blue_dark)
    for s in (-1, 0, 1):
        Bs = B + np.array([s * L, 0.0])
        hit = s == 1
        tri(ax, Bs, C.cyan_fill if s == 0 else lighten(C.cyan_fill, 0.4), ec=C.cyan, lw=1.1 if s == 0 else 0.8,
            zorder=3, ls="-" if s == 0 else (0, (3, 2)))
        rb = (Bs.min(0) - 0.03, Bs.max(0) + 0.03)
        ax.add_patch(Rectangle(rb[0], *(rb[1] - rb[0]), fc="none", ec=C.coral if hit else C.ink_faint, lw=1.1 if hit else 0.7,
                               ls=(0, (2, 1.5)), zorder=4))
        lab = {-1: r"$B-L$", 0: r"$B$", 1: r"$B+L$"}[s]
        label(ax, Bs[:, 0].mean(), 0.84, lab, size=9.0, color=C.cyan)
        verdict = "root boxes overlap: traverse" if hit else "rejected: one box test"
        halo_label(ax, Bs[:, 0].mean(), 0.33, verdict, size=6.3, color=C.coral if hit else C.ink_soft)
    halo_label(ax, 0.5, 1.33, "the domain, periodic in x", size=6.6, color=C.ink_soft)
    note(ax, 0.5, 0.06, r"$|\mathcal{S}|\leq 27$ images in 3D", size=6.8, color=C.ink)

    # ---------------------------------------------------------------- (b)
    bx = canvas(fig, [0.63, 0.0, 0.37, 0.88], (-0.1, 2.5), (-0.3, 1.6), equal=False)
    ya = 1.05
    tA, tB, gap = 0.28, 0.45, 0.62  # max(tA, tB) < gap < tA + tB
    xa, xb = 0.62, 0.62 + gap
    tri(bx, [(xa - 0.5, ya), (xa, ya + 0.3), (xa, ya - 0.3)], C.blue_fill, ec=C.blue, lw=1.2)
    tri(bx, [(xb + 0.5, ya), (xb, ya + 0.3), (xb, ya - 0.3)], C.cyan_fill, ec=C.cyan, lw=1.2)
    label(bx, xa - 0.2, ya, r"$A$", size=9.4, color=C.blue_dark)
    label(bx, xb + 0.2, ya, r"$B$", size=9.4, color=C.cyan)
    dim_line(bx, (xa, ya + 0.45), (xb, ya + 0.45), r"$g$", text_offset=0.1, head=0.05, size=9.4)
    # each leaf box is inflated by its own tau, so the boxes admit g <= tau_A + tau_B
    for y, x0, w, fc, ec, s_ in ((0.55, xa, tA, C.blue_fill, C.blue, r"$\tau_A$"),
                                 (0.36, xb - tB, tB, C.cyan_fill, C.cyan, r"$\tau_B$")):
        box(bx, x0, y - 0.06, w, 0.12, fc=fc, ec=ec, lw=0.8, r=0.0)
        label(bx, x0 + w / 2 + (0.0 if s_ == r"$\tau_B$" else 0.0), y, s_, size=8.2, color=C.ink)
    for x in (xa, xb):
        bx.plot([x, x], [0.25, ya - 0.3], color=C.ink_faint, lw=0.6, ls=(0, (2, 2)))
    note(bx, 1.93, 0.55, "boxes: admitted", size=6.8, color=C.blue_dark, ha="left")
    note(bx, 1.93, 0.36, r"$g>\max(\tau_A,\tau_B)$: rejected", size=6.8, color=C.coral, ha="left")
    note(bx, 1.25, 0.02, r"never culled: $\max(\tau_A,\tau_B)\leq\tau_A+\tau_B$", size=7.2, color=C.ink)
    note(bx, 1.25, -0.22, r"$\tau=\max(\mathrm{floor},\,\mathrm{factor}\cdot R)$, $R$ the body's global radius", size=6.8,
         color=C.ink_soft)
    return fig


# ------------------------------------------------------------------ Guigue-Devillers


def _plane_line(p1, n1, p2, n2):
    d = np.cross(n1, n2)
    A = np.array([n1, n2, d])
    b = np.array([np.dot(n1, p1), np.dot(n2, p2), 0.0])
    return np.linalg.solve(A, b), d / np.linalg.norm(d)


def _interval(T, n, p, origin, direction):
    """The segment T cuts from the plane (n, p), as parameters along the line."""
    s = (T - p) @ n
    pts = []
    for i in range(3):
        a, b = T[i], T[(i + 1) % 3]
        if s[i] * s[(i + 1) % 3] < 0:
            t = s[i] / (s[i] - s[(i + 1) % 3])
            pts.append(a + t * (b - a))
    return sorted(np.dot(q - origin, direction) for q in pts), s


@register("guigue-devillers")
def guigue_devillers():
    fig = figure(7.0, 2.75)
    fheading(fig, 0.0, 0.95, "a", "two planes meet in a line; each triangle cuts an interval")
    fheading(fig, 0.63, 0.95, "b", "overlap decides, by signs only")

    T1 = np.array([[-1.0, -0.55, -0.35], [0.9, -0.25, -0.2], [-0.05, 0.75, 0.55]])
    T2 = np.array([[-0.45, 0.45, -0.75], [0.75, 0.2, 0.7], [0.15, -0.8, 0.45]])
    n1 = np.cross(T1[1] - T1[0], T1[2] - T1[0])
    n1 /= np.linalg.norm(n1)
    n2 = np.cross(T2[1] - T2[0], T2[2] - T2[0])
    n2 /= np.linalg.norm(n2)
    o, d = _plane_line(T1[0], n1, T2[0], n2)
    I1, s1 = _interval(T1, n2, T2[0], o, d)
    I2, s2 = _interval(T2, n1, T1[0], o, d)

    ax = canvas(fig, [0.0, 0.0, 0.6, 0.88], (-1.45, 1.55), (-1.05, 1.1))
    cam = Camera(elev=20, azim=-50, scale=1.0)
    draw_mesh(ax, cam, T1, np.array([[0, 1, 2]]), color=C.blue_fill, lw=1.0, cull=False, zorder=2, alpha=0.85)
    draw_mesh(ax, cam, T2, np.array([[0, 1, 2]]), color=C.cyan_fill, lw=1.0, cull=False, zorder=3, alpha=0.75)
    t0, t1 = min(I1 + I2) - 0.55, max(I1 + I2) + 0.55
    polyline3d(ax, cam, np.array([o + t0 * d, o + t1 * d]), color=C.ink_soft, lw=0.9, ls=(0, (3, 2)), zorder=4)
    polyline3d(ax, cam, np.array([o + I1[0] * d, o + I1[1] * d]), color=C.blue_dark, lw=3.2, zorder=5)
    polyline3d(ax, cam, np.array([o + I2[0] * d, o + I2[1] * d]), color=C.cyan, lw=2.0, zorder=6)
    label3d(ax, cam, o + t1 * d, r"$L$", offset=(0.1, 0.05), size=10)
    for i, (T, s, col) in enumerate(((T1, s1, C.blue_dark), (T2, s2, C.cyan))):
        for k in range(3):
            xy = point3d(ax, cam, T[k], r=0.035, fc=col, zorder=7)
            sign = "+" if s[k] > 0 else "−"
            halo_label(ax, xy[0] + 0.11, xy[1] + 0.09, sign, size=8.6, color=C.coral)
    label3d(ax, cam, T1.mean(0), r"$T_1$", offset=(-0.35, -0.15), color=C.blue_dark, size=10)
    label3d(ax, cam, T2.mean(0), r"$T_2$", offset=(0.3, 0.3), color=C.cyan, size=10)
    note(ax, 0.05, -0.95, "signs: orient3d of each corner against the other triangle's plane", size=6.6)

    # ---------------------------------------------------------------- (b) the intervals on L
    bx = canvas(fig, [0.63, 0.0, 0.37, 0.88], (-0.1, 2.6), (-0.3, 1.6), equal=False)
    lo, hi = min(I1 + I2), max(I1 + I2)

    def u(t):
        return 0.2 + 2.2 * (t - lo) / (hi - lo)

    bx.plot([0.05, 2.55], [0.95, 0.95], color=C.ink_soft, lw=0.9, ls=(0, (3, 2)))
    bx.plot([u(I1[0]), u(I1[1])], [1.05, 1.05], color=C.blue_dark, lw=4.0, solid_capstyle="butt")
    bx.plot([u(I2[0]), u(I2[1])], [0.85, 0.85], color=C.cyan, lw=4.0, solid_capstyle="butt")
    label(bx, u(I1[0]) - 0.1, 1.2, r"$T_1\cap L$", size=8.6, color=C.blue_dark, ha="left")
    label(bx, u(I2[1]) - 0.2, 0.68, r"$T_2\cap L$", size=8.6, color=C.cyan)
    label(bx, 2.52, 0.95, r"$L$", size=9.6, ha="left")
    note(bx, 1.3, 0.3, "intersect iff the intervals overlap:", size=6.9, color=C.ink)
    label(bx, 1.3, 0.05, r"$\mathrm{o3d}(q_2,p_2,p_1,q_1)\leq0\;\wedge\;\mathrm{o3d}(r_2,p_2,r_1,p_1)\leq0$", size=8.2)
    note(bx, 1.3, -0.22, "at most 8 predicates, no division, no constructed point", size=6.4)
    return fig
