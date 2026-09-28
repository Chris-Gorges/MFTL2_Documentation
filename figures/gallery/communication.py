"""Figures for ``src/communication/README.md`` -- the halo rule and the spatial halo."""

from __future__ import annotations

import numpy as np

from mftlfig import register
from mftlfig.meshes import edges_of, jittered_patch, triangle_neighbours
from mftlfig.style import C, box, canvas, dot, fheading, figure, label, lighten, note, tri


def partitioned_patch(nx=11, ny=9, seed=18, cut_frac=0.45):
    """A planar open patch split between two ranks by the plane x = cut.

    Ownership follows the library: a vertex belongs to the rank whose cell
    contains it, a triangle to the rank whose cell contains its centre.

    :returns: dict with positions, triangles, owners, rank 0's pool and the
        replicated (frozen) owned triangles of rank 0.
    """
    P, F = jittered_patch(nx, ny, jitter=0.2, seed=seed)
    cut = P[:, 0].min() + cut_frac * (P[:, 0].max() - P[:, 0].min())
    vown = (P[:, 0] >= cut).astype(int)
    cen = P[F].mean(axis=1)
    town = (cen[:, 0] >= cut).astype(int)
    nb = triangle_neighbours(F)

    # the halo rule: an owned triangle goes to its owner, the owner of each corner
    # and the owner of each edge neighbour
    def destinations(t):
        d = {town[t]}
        d |= {vown[v] for v in F[t]}
        d |= {town[s] for s in nb[t] if s >= 0}
        return d

    dest = [destinations(t) for t in range(len(F))]
    local0 = np.array([0 in d for d in dest])
    corner_clause = np.array([town[t] == 1 and any(vown[v] == 0 for v in F[t]) for t in range(len(F))])
    replicated0 = np.array([town[t] == 0 and 1 in dest[t] for t in range(len(F))])
    return dict(P=P, F=F, cut=cut, vown=vown, town=town, nb=nb, local0=local0, corner=corner_clause,
                frozen=replicated0)


def _draw_tris(ax, P, F, mask, fc, ec=C.ink, lw=0.6, zorder=2, hatch=None, alpha=1.0):
    for t in np.nonzero(mask)[0]:
        p = tri(ax, P[F[t]], fc, ec=ec, lw=lw, zorder=zorder, alpha=alpha)
        if hatch:
            p.set_hatch(hatch)


@register("halo-rule")
def halo_rule():
    d = partitioned_patch()
    P, F, cut, vown, town, nb = d["P"], d["F"], d["cut"], d["vown"], d["town"], d["nb"]
    local, corner, frozen = d["local0"], d["corner"], d["frozen"]
    fig = figure(7.0, 2.75)
    fheading(fig, 0.0, 0.95, "a", "ownership")
    fheading(fig, 0.335, 0.95, "b", "rank 0 holds: owned + halo")
    fheading(fig, 0.67, 0.95, "c", "read backwards: frozen")
    lo, hi = P.min(0) - 0.3, P.max(0) + 0.3

    for k in range(3):
        ax = canvas(fig, [k * 0.335, 0.06, 0.325, 0.83], (lo[0], hi[0]), (lo[1] - 0.6, hi[1]))
        if k == 0:
            _draw_tris(ax, P, F, town == 0, C.blue_fill, lw=0.5)
            _draw_tris(ax, P, F, town == 1, C.cyan_fill, lw=0.5)
            for v in range(len(P)):
                dot(ax, P[v], r=0.085, fc=C.blue if vown[v] == 0 else C.cyan, ec=C.paper, lw=0.5)
            note(ax, (lo[0] + cut) / 2, lo[1] - 0.3, "rank 0", size=7.2, color=C.blue_dark)
            note(ax, (hi[0] + cut) / 2, lo[1] - 0.3, "rank 1", size=7.2, color=C.cyan)
        elif k == 1:
            _draw_tris(ax, P, F, ~local, "#ffffff", ec=C.rule, lw=0.4, zorder=1)
            _draw_tris(ax, P, F, local & (town == 0), C.blue_fill, lw=0.5)
            _draw_tris(ax, P, F, local & corner, C.amber_fill, lw=0.5)
            _draw_tris(ax, P, F, local & (town == 1) & ~corner, C.amber_fill, ec=C.amber, lw=0.5, hatch="//////")
            # twin-less half-edges of the local pool: the halo rim, and the mesh boundary
            E = edges_of(F)
            for (a, b), ts in E.items():
                loc = [t for t in ts if local[t]]
                if len(loc) == 1:
                    real = len(ts) == 1
                    ax.plot(*P[[a, b]].T, color=C.ink if real else C.amber, lw=1.6 if real else 1.5,
                            ls="-" if real else (0, (2.2, 1.4)), zorder=4, solid_capstyle="round")
            # one owned vertex on the cut, and its complete fan
            cand = [v for v in range(len(P)) if vown[v] == 0 and abs(P[v, 0] - cut) < 0.55
                    and 2.0 < P[v, 1] < 5.0]
            v = cand[0]
            fan = [t for t in range(len(F)) if v in F[t]]
            for t in fan:
                tri(ax, P[F[t]], "none", ec=C.coral, lw=1.2, zorder=5)
            dot(ax, P[v], r=0.11, fc=C.coral)
        else:
            _draw_tris(ax, P, F, ~local, "#ffffff", ec=C.rule, lw=0.4, zorder=1)
            _draw_tris(ax, P, F, local & (town == 1), lighten(C.amber_fill, 0.3), ec=C.ink_faint, lw=0.4)
            _draw_tris(ax, P, F, (town == 0) & ~frozen, C.blue_fill, lw=0.5)
            _draw_tris(ax, P, F, frozen, C.coral_fill, ec=C.ink, lw=0.5)
            fv = {v for t in np.nonzero(frozen)[0] for v in F[t] if vown[v] == 0}
            for v in fv:
                dot(ax, P[v], r=0.075, fc=C.coral, ec=C.paper, lw=0.4)
        ax.plot([cut, cut], [lo[1] - 0.1, hi[1] - 0.1], color=C.ink, lw=0.9, ls=(0, (4, 2)), zorder=6)

    # legends under panels (b) and (c)
    lg = canvas(fig, [0.335, 0.0, 0.665, 0.1], (0, 6.65), (0, 1), equal=False)
    items = [(C.blue_fill, None, "owned"), (C.amber_fill, None, "ghost: corner clause"),
             (C.amber_fill, "//////", "ghost: neighbour clause only")]
    x = 0.05
    for fc, hatch, text in items:
        p = box(lg, x, 0.3, 0.2, 0.42, fc=fc, ec=C.amber if hatch else C.ink, lw=0.5, r=0.02)
        if hatch:
            p.set_hatch(hatch)
        note(lg, x + 0.27, 0.51, text, ha="left", size=6.5, color=C.ink)
        x += 0.45 + 0.085 * len(text)
    box(lg, x, 0.3, 0.2, 0.42, fc=C.coral_fill, ec=C.ink, lw=0.5, r=0.02)
    note(lg, x + 0.27, 0.51, "frozen (replicated)", ha="left", size=6.5, color=C.ink)
    return fig


@register("halo-boundary")
def halo_boundary():
    """The two meanings of a missing twin, on rank 0's pool."""
    d = partitioned_patch()
    P, F, cut, town, local = d["P"], d["F"], d["cut"], d["town"], d["local0"]
    fig = figure(4.6, 2.55)
    lo, hi = P.min(0) - 0.3, P.max(0) + 0.3
    ax = canvas(fig, [0.0, 0.0, 0.64, 1.0], (lo[0], hi[0]), (lo[1], hi[1]))
    _draw_tris(ax, P, F, ~local, "#ffffff", ec=C.rule, lw=0.4, zorder=1)
    _draw_tris(ax, P, F, local & (town == 0), C.blue_fill, lw=0.5)
    _draw_tris(ax, P, F, local & (town == 1), C.amber_fill, lw=0.5)
    E = edges_of(F)
    for (a, b), ts in E.items():
        loc = [t for t in ts if local[t]]
        if len(loc) == 1:
            real = len(ts) == 1
            ax.plot(*P[[a, b]].T, color=C.ink if real else C.amber, lw=1.8 if real else 1.2,
                    ls="-" if real else (0, (2.2, 1.4)), zorder=4, solid_capstyle="round")
    ax.plot([cut, cut], [lo[1] + 0.1, hi[1] - 0.1], color=C.ink, lw=0.9, ls=(0, (4, 2)), zorder=6)
    lg = canvas(fig, [0.66, 0.1, 0.34, 0.8], (0, 3), (0, 3), equal=False)
    rows = [(C.ink, "-", 1.8, "twin_idx == MFTL_ERROR\nand MFTL_FLAG_BOUNDARY:\nthe surface ends here"),
            (C.amber, (0, (2.2, 1.4)), 1.2, "twin_idx == MFTL_ERROR\nonly: the halo ends here,\nthe surface does not")]
    for i, (col, ls, lw, text) in enumerate(rows):
        y = 2.35 - 1.3 * i
        lg.plot([0.05, 0.45], [y, y], color=col, ls=ls, lw=lw, solid_capstyle="round")
        note(lg, 0.6, y, text, ha="left", size=6.6, color=C.ink, linespacing=1.3)
    return fig


# ------------------------------------------------------------------ periodic extents


def circular_extent(pieces):
    """Centre and half-width of a set of intervals on [0, 1), measured the way the halo does.

    The extent is taken in the raw frame and in one shifted by half a period,
    keeping the tighter; exact while the share is narrower than half the period.
    """
    best = None
    for shift in (0.0, 0.5):
        ends = [(u + shift) % 1.0 for p in pieces for u in (p[0], p[1] - 1e-9)]
        lo, hi = min(ends), max(ends)
        if best is None or hi - lo < best[1] - best[0]:
            best = (lo, hi, shift)
    lo, hi, shift = best
    return ((lo + hi) / 2 - shift) % 1.0, (hi - lo) / 2


@register("halo-extents")
def halo_extents():
    fig = figure(7.0, 3.0)
    ax = canvas(fig, [0, 0, 1, 1], (0, 7.0), (0, 3.0), equal=False)
    fheading(fig, 0.0, 0.94, "a", "a contact across the seam")
    fheading(fig, 0.0, 0.43, "b", "a share that straddles the seam")
    for yy, col, txt in ((2.87, C.blue, "share of body A"), (2.67, C.cyan, "share of body B")):
        ax.plot([5.15, 5.35], [yy, yy], color=col, lw=5.0, solid_capstyle="butt")
        label(ax, 5.42, yy, txt, size=6.9, color=C.ink, ha="left")
    X0, X1 = 1.45, 4.55  # the unrolled periodic axis [0, L)
    Lx = X1 - X0

    def at(u):
        return X0 + u * Lx

    def bar(y, u0, u1, col, lw=5.0, alpha=1.0):
        ax.plot([at(u0), at(u1)], [y, y], color=col, lw=lw, solid_capstyle="butt", zorder=3, alpha=alpha)

    def axis_line(y, name):
        ax.plot([X0, X1], [y, y], color=C.ink, lw=0.9, zorder=1)
        for x in (X0, X1):
            ax.plot([x, x], [y - 0.06, y + 0.06], color=C.ink, lw=0.9)
        note(ax, X0 - 0.12, y, name, ha="right", size=6.8, color=C.ink)

    rows = [
        (2.3, [(0.86, 0.97)], [(0.03, 0.11)], r"boxes disjoint $\Rightarrow$ contact missed",
         r"$|\Delta^{\min} c|\leq h_A+h_B+m$: near"),
        (0.9, [(0.95, 1.0), (0.0, 0.05)], [(0.46, 0.56)], r"box spans the domain $\Rightarrow$ ships all",
         r"$|\Delta^{\min} c|>h_A+h_B+m$: far"),
    ]
    for y, A, B, bad, good in rows:
        axis_line(y, r"stored, $(\mathrm{lo},\mathrm{hi})$")
        axis_line(y - 0.5, "centre ± half-width")
        for yy in (y, y - 0.5):
            note(ax, X0, yy - 0.17, "0", size=6.4, color=C.ink_soft)
            note(ax, X1, yy - 0.17, r"$L\equiv 0$", size=7.2, color=C.ink_soft)
        for pieces, col in ((A, C.blue), (B, C.cyan)):
            for u0, u1 in pieces:
                bar(y, u0, u1, col)
            lo, hi = min(p[0] for p in pieces), max(p[1] for p in pieces)
            box(ax, at(lo), y + 0.08, (hi - lo) * Lx, 0.13, fc="none", ec=col, lw=0.9, r=0.01)
            c, h = circular_extent(pieces)
            yy = y - 0.5
            u0, u1 = c - h, c + h
            spans = [(u0 + 1, 1.0), (0.0, u1)] if u0 < 0 else ([(u0, 1.0), (0.0, u1 - 1)] if u1 > 1 else [(u0, u1)])
            for a, b in spans:
                bar(yy, a, b, col, lw=5.0, alpha=0.5)
            dot(ax, (at(c), yy), r=0.05, fc=col, ec=C.paper)
        note(ax, 4.85, y + 0.02, bad, ha="left", size=7.0, color=C.coral)
        note(ax, 4.85, y - 0.5, good, ha="left", size=7.4, color=C.blue_dark)
    return fig
