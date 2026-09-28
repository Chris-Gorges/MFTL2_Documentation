"""Figures for ``src/topology_change/README.md`` -- events, the reconstruction, the union field."""

from __future__ import annotations

import numpy as np
from matplotlib.patches import Circle

from mftlfig import register
from mftlfig.style import C, SIGNED_CMAP, arrow, canvas, dot, fheading, figure, lighten, note, tri

# ------------------------------------------------------------------ 2D machinery


def marching_squares(phi, xs, ys, known=None):
    """Zero level set of a node field by the face rule of marching_cubes.c, in 2D.

    Walk each cell's corners counter-clockwise; connect every crossing where
    the walk enters the inside (phi < 0) to the next one where it leaves. A
    crossing is named by its lattice edge, so neighbouring cells share it.

    :returns: dict lattice-edge -> point, and a list of (from, to) segments.
    """
    nx, ny = len(xs), len(ys)
    pts, segs = {}, []

    def edge_key(i, j, axis):
        return (i, j, axis)

    def crossing(i0, j0, i1, j1):
        a, b = phi[i0, j0], phi[i1, j1]
        t = a / (a - b)
        p = np.array([xs[i0] + t * (xs[i1] - xs[i0]), ys[j0] + t * (ys[j1] - ys[j0])])
        key = edge_key(min(i0, i1), min(j0, j1), 0 if j0 == j1 else 1)
        pts[key] = p
        return key

    for i in range(nx - 1):
        for j in range(ny - 1):
            cyc = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if known is not None and not all(known[c] for c in cyc):
                continue
            inside = [phi[c] < 0 for c in cyc]
            for k in range(4):
                if not inside[k] and inside[(k + 1) % 4]:
                    for dj in range(1, 4):
                        u = (k + dj) % 4
                        if inside[u] and not inside[(u + 1) % 4]:
                            a = crossing(*cyc[k], *cyc[(k + 1) % 4])
                            b = crossing(*cyc[u], *cyc[(u + 1) % 4])
                            segs.append((a, b))
                            break
    return pts, segs


def loops_of(segs):
    nxt = dict(segs)
    seen, loops = set(), []
    for a in nxt:
        if a in seen:
            continue
        loop, u = [], a
        while u not in seen and u in nxt:
            seen.add(u)
            loop.append(u)
            u = nxt[u]
        loops.append(loop)
    return loops


def _seg_dist(P, A, B):
    AB = B - A
    t = np.clip(((P - A) @ AB) / (AB @ AB), 0.0, 1.0)
    Q = A + t[:, None] * AB
    return np.linalg.norm(P - Q, axis=1)


def signed_distance(nodes, poly):
    """Distance to a closed polyline, negative inside (even-odd rule)."""
    d = np.full(len(nodes), np.inf)
    for k in range(len(poly)):
        d = np.minimum(d, _seg_dist(nodes, poly[k], poly[(k + 1) % len(poly)]))
    x, y = nodes[:, 0], nodes[:, 1]
    inside = np.zeros(len(nodes), bool)
    for k in range(len(poly)):
        (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % len(poly)]
        cond = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-300) + x1)
        inside ^= cond
    return np.where(inside, -d, d)


def dumbbell():
    """The input surface: two bulbs on a neck thinner than the breakup threshold (fine polyline)."""
    g = np.linspace(-1.2, 1.2, 481)
    h = np.linspace(-0.7, 0.7, 281)
    X, Y = np.meshgrid(g, h, indexing="ij")
    r1 = np.hypot(X + 0.55, Y) - 0.42
    r2 = np.hypot(X - 0.55, Y) - 0.42
    neck = np.maximum(np.abs(Y) - 0.032, np.abs(X) - 0.6)
    k = 0.06

    def smin(a, b):
        hh = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
        return b * (1 - hh) + a * hh - k * hh * (1 - hh)

    f = smin(smin(r1, r2), neck)
    pts, segs = marching_squares(f, g, h)
    loop = max(loops_of(segs), key=len)
    return np.array([pts[e] for e in loop])


def _bias_weight(r):
    t = np.clip((r - 0.5) / 0.5, 0.0, 1.0)
    return np.where(r <= 0.5, 1.0, 1.0 - t * t * (3 - 2 * t))


@register("topo-reconstruction")
def topo_reconstruction():
    fig = figure(7.0, 4.25)
    heads = [("a", r"detect: an opposing pair, gap $<\delta_b$"), ("b", r"rasterise owned triangles within $r_\mathrm{cut}$"),
             ("c", "bias the field at the event"), ("d", "extract and label: two bodies")]
    poly = dumbbell()
    dx = 0.07
    xs = np.arange(-1.1, 1.1 + 1e-9, dx)
    ys = np.arange(-0.6, 0.6 + 1e-9, dx)
    N = np.array([[x, y] for x in xs for y in ys])
    phi = signed_distance(N, poly).reshape(len(xs), len(ys))
    delta_b, beta, gamma = 0.1, 1.5, 1.5
    eps = 0.5 * beta * delta_b
    rho = gamma * max(delta_b, dx)
    r_cut = np.hypot(dx, dx) + eps + 0.5 * dx
    known = np.abs(phi) <= r_cut
    xe = np.array([0.0, 0.0])
    w = _bias_weight(np.linalg.norm(N - xe, axis=1) / rho).reshape(phi.shape)
    phib = phi + eps * w

    for k, (letter, t) in enumerate(heads):
        col_, row_ = k % 2, k // 2
        fheading(fig, col_ * 0.51, 0.965 - row_ * 0.5, letter, t)
        ax = canvas(fig, [col_ * 0.51, 0.5 - row_ * 0.5, 0.49, 0.43], (-1.18, 1.18), (-0.82, 0.68))
        if k == 0:
            tri(ax, poly, C.blue_fill, ec=C.blue, lw=1.1)
            for sgn in (1, -1):
                y0 = sgn * 0.032
                ax.plot([-0.06, 0.06], [y0, y0], color=C.coral, lw=2.4, zorder=4, solid_capstyle="butt")
                arrow(ax, (0.0, y0), (0.0, y0 + sgn * 0.26), color=C.coral, lw=1.0, head=0.07)
            dot(ax, xe, r=0.03, fc=C.ink, zorder=6)
            note(ax, 0.0, -0.74, "each triangle behind the other: the gap is liquid, a breakup", size=6.8,
                 color=C.coral)
        elif k in (1, 2):
            field = phi if k == 1 else phib
            vmax = r_cut
            GX, GY = np.meshgrid(xs, ys, indexing="ij")
            kn = known.ravel()
            vals = 0.5 + 0.5 * np.clip(field.ravel() / vmax, -1, 1)
            # one collection each, so the SVG defines the marker once
            ax.scatter(GX.ravel()[kn], GY.ravel()[kn], s=11, c=SIGNED_CMAP(vals[kn]), linewidths=0, zorder=3)
            ax.scatter(GX.ravel()[~kn], GY.ravel()[~kn], s=2.2, c=C.grey_mid, linewidths=0, zorder=2)
            ax.plot(*np.vstack([poly, poly[:1]]).T, color=C.ink_soft, lw=0.7, zorder=4, ls="-" if k == 1 else (0, (2, 1.5)))
            if k == 2:
                ax.add_patch(Circle(xe, rho, fc="none", ec=C.coral, lw=0.8, ls=(0, (2, 2)), zorder=5))
                ax.add_patch(Circle(xe, 0.5 * rho, fc=lighten(C.coral, 0.7), ec="none", zorder=1, alpha=0.8))
                note(ax, 0.0, -0.74, r"$\phi\leftarrow\phi+\varepsilon_b\,w(|\mathbf{x}-\mathbf{x}_e|/\rho)$: the neck becomes outside",
                     size=7.4, color=C.coral)
            else:
                note(ax, 0.0, -0.74, "grey: unknown beyond the cutoff (no flood fill needed)", size=6.8, color=C.ink_soft)
        else:
            pts, segs = marching_squares(phib, xs, ys, known)
            loops = loops_of(segs)
            for loop, col, fc in zip(sorted(loops, key=lambda L: np.mean([pts[e][0] for e in L])),
                                     (C.blue, C.cyan), (C.blue_fill, C.cyan_fill)):
                P = np.array([pts[e] for e in loop])
                tri(ax, P, fc, ec=col, lw=1.1)
                ax.scatter(P[:, 0], P[:, 1], s=4, c=col, linewidths=0, zorder=4)
            for x in xs:
                ax.plot([x, x], [ys[0], ys[-1]], color=C.rule, lw=0.3, zorder=0)
            for y in ys:
                ax.plot([xs[0], xs[-1]], [y, y], color=C.rule, lw=0.3, zorder=0)
            note(ax, 0.0, -0.74, f"{len(loops)} closed loops; every vertex lies on a lattice edge", size=6.8)
    return fig


# ------------------------------------------------------------------ events


def _thick_curve(center, width):
    """Outline of a thick curve (a 2D 'body' around a centreline), round-capped."""
    c = np.asarray(center, float)
    d = np.gradient(c, axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None]
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    left = c + width * nrm
    right = c - width * nrm
    cap1 = [c[-1] + width * (np.cos(t) * nrm[-1] + np.sin(t) * d[-1]) for t in np.linspace(0, -np.pi, 12)]
    cap0 = [c[0] + width * (np.cos(t) * -nrm[0] + np.sin(t) * -d[0]) for t in np.linspace(0, -np.pi, 12)]
    return np.vstack([left, cap1, right[::-1], cap0])


def _pair(ax, pa, na, pb, nb, color, L=0.3):
    for p, n in ((pa, na), (pb, nb)):
        t = np.array([-n[1], n[0]])
        ax.plot(*np.array([p - 0.07 * t, p + 0.07 * t]).T, color=color, lw=2.6, zorder=5, solid_capstyle="butt")
        arrow(ax, p, p + L * np.asarray(n), color=color, lw=1.0, head=0.07, zorder=6)


@register("topo-events")
def topo_events():
    fig = figure(7.0, 2.3)
    specs = [("a", "one body: breakup"), ("b", "two bodies: coalescence"), ("c", "one body: coalescence"),
             ("d", "two bodies: breakup")]
    verdicts = [("thread: each behind the other", C.coral), ("film: each in front of the other", C.cyan),
                ("a cap rolled onto its stem", C.cyan), ("a film around a bubble", C.coral)]
    for k, ((letter, t), (v, vc)) in enumerate(zip(specs, verdicts)):
        fheading(fig, k * 0.25, 0.94, letter, t, size=8.4)
        ax = canvas(fig, [k * 0.25 + 0.005, 0.1, 0.24, 0.78], (-1.1, 1.1), (-1.0, 1.0))
        nax = canvas(fig, [k * 0.25, 0.0, 0.25, 0.1], (0, 1), (0, 1), equal=False)
        note(nax, 0.5, 0.55, v, size=6.8, color=vc)
        if k == 0:
            x = np.linspace(-1.0, 1.0, 80)
            yt = 0.1 + 0.45 * x ** 2
            P = np.vstack([np.column_stack([x, yt]), np.column_stack([x[::-1], -yt[::-1]])])
            tri(ax, P, C.blue_fill, ec=C.blue, lw=1.1)
            _pair(ax, np.array([0.0, 0.1]), (0, 1), np.array([0.0, -0.1]), (0, -1), C.coral)
            note(ax, 0.55, 0.0, "liquid", size=6.4, color=C.blue_dark)
        elif k == 1:
            for cx in (-0.55, 0.55):
                ax.add_patch(Circle((cx, 0.0), 0.47, fc=C.blue_fill, ec=C.blue, lw=1.1))
            _pair(ax, np.array([-0.08, 0.0]), (1, 0), np.array([0.08, 0.0]), (-1, 0), C.cyan, L=0.26)
        elif k == 2:
            stem = np.column_stack([np.full(40, -0.45), np.linspace(-0.95, 0.3, 40)])
            th = np.linspace(np.pi, -0.82 * np.pi, 140)
            r = 0.5 - 0.2 * (np.pi - th) / (1.82 * np.pi)
            spiral = np.column_stack([0.05 + r * np.cos(th), 0.3 + r * np.sin(th)])
            center = np.vstack([stem, spiral[1:]])
            tri(ax, _thick_curve(center, 0.11), C.blue_fill, ec=C.blue, lw=1.1)
            tip = spiral[-1]
            ya = tip[1]
            _pair(ax, np.array([-0.34, ya]), (1, 0), np.array([tip[0] - 0.11, ya]), (-1, 0), C.cyan, L=0.22)
        else:
            ax.add_patch(Circle((0.0, 0.0), 0.9, fc=C.blue_fill, ec=C.blue, lw=1.1))
            ax.add_patch(Circle((0.25, 0.0), 0.56, fc=C.paper, ec=C.cyan, lw=1.1))
            note(ax, 0.25, 0.0, "bubble", size=6.4, color=C.cyan)
            _pair(ax, np.array([0.9, 0.0]), (1, 0), np.array([0.81, 0.0]), (-1, 0), C.coral, L=0.24)
    return fig


# ------------------------------------------------------------------ the union field


@register("union-field")
def union_field():
    fig = figure(7.0, 2.35)
    ax = fig.add_axes([0.08, 0.2, 0.62, 0.72])
    x = np.linspace(-1.3, 1.3, 2601)
    r_cut = 0.6
    phi_drop = np.abs(x) - 1.0
    # the bubble is the cavity of the liquid: its surface faces INTO the bubble,
    # so its own signed distance is positive inside the bubble, negative around it
    phi_bub = -(np.abs(x - 0.45) - 0.25)
    known = lambda f: np.where(np.abs(f) <= r_cut, f, np.nan)
    fd, fb = known(phi_drop), known(phi_bub)
    mn = np.fmin(fd, fb)
    surf = np.array([-1.0, 1.0, 0.2, 0.7])
    normal = np.array([-1, +1, +1, -1])  # outward (liquid -> other phase) along x
    dist = np.abs(x[:, None] - surf[None, :])
    near = np.argmin(dist, axis=1)
    union = np.sign((x - surf[near]) * normal[near]) * dist[np.arange(len(x)), near]
    union = known(union)
    liquid = ((x > -1) & (x < 0.2)) | ((x > 0.7) & (x < 1))
    for a, b in ((-1.0, 0.2), (0.7, 1.0)):
        ax.axvspan(a, b, color=C.blue_fill, lw=0, zorder=0)
    wrong = (np.sign(mn) < 0) != liquid
    wrong &= ~np.isnan(mn)
    ax.fill_between(x, -0.72, -0.66, where=wrong, color=C.coral, lw=0, zorder=1)
    ax.axhline(0, color=C.ink, lw=0.8, zorder=1)
    ax.plot(x, mn, color=C.coral, lw=1.6, ls=(0, (4, 2)), zorder=3)
    ax.plot(x, union, color=C.blue_dark, lw=1.8, zorder=4)
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.72, 0.5)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    for s_ in ("left", "bottom"):
        ax.spines[s_].set_color(C.ink_soft)
        ax.spines[s_].set_linewidth(0.7)
    ax.tick_params(colors=C.ink_soft, labelsize=7, width=0.6, length=3)
    ax.set_xlabel(r"$x$", fontsize=9.4, color=C.ink, labelpad=1)
    ax.set_ylabel(r"$\phi$", fontsize=9.4, color=C.ink, rotation=0, labelpad=8)
    ax.text(-0.4, 0.4, "liquid", fontsize=7, color=C.blue_dark, ha="center")
    ax.text(0.45, 0.4, "bubble", fontsize=7, color=C.ink_soft, ha="center")
    ax.text(0.85, 0.4, "liquid", fontsize=7, color=C.blue_dark, ha="center")
    lg = canvas(fig, [0.73, 0.2, 0.27, 0.72], (0, 1), (0, 1), equal=False)
    rows = [(C.blue_dark, "-", 1.8, "distance to the union,\nsigned by the nearest\nsurface"),
            (C.coral, (0, (4, 2)), 1.6, r"$\min(\phi_\mathrm{drop},\phi_\mathrm{bubble})$" + "\nof the per-body fields"),
            (C.coral, "-", 5.0, "where the minimum\nhas the wrong sign")]
    for i, (col, ls, lw, txt) in enumerate(rows):
        y = 0.9 - [0, 0.32, 0.6][i]
        lg.plot([0.02, 0.16], [y, y], color=col, ls=ls, lw=lw)
        lg.text(0.21, y, txt, fontsize=6.9, color=C.ink, va="center", linespacing=1.25)
    lg.text(0.02, 0.06, r"each field known within $r_\mathrm{cut}$ of its surface", fontsize=6.4, color=C.ink_soft)
    return fig
