"""Figures for ``pages/timestep.md`` -- what is valid after each call of the loop."""

from __future__ import annotations

from mftlfig import register
from mftlfig.style import C, box, canvas, code, figure, note

VALID, STALE, UNSPEC, INVALID = "valid", "stale", "unspecified", "invalid"
STYLE = {
    VALID: (C.blue_fill, C.blue, C.blue_dark, r"$\checkmark$"),
    STALE: (C.amber_fill, C.amber, "#8a5a00", "stale"),
    UNSPEC: (C.coral_fill, C.coral, C.coral, "unspec."),
    INVALID: (C.coral, C.coral, C.paper, "invalid"),
}


@register("timestep-validity")
def timestep_validity():
    steps = ["1  move owned\nvertices", "2  ghost\nsync", "3  triangle geometry,\nghosts included", "4  redistribute",
             "5  ensemble\nupdate", "6  ensemble\nvertex normals"]
    rows = [
        ("verts.pos  owned", [VALID, VALID, VALID, VALID, VALID, VALID]),
        ("verts.pos  ghosts", [STALE, VALID, VALID, VALID, VALID, VALID]),
        ("tris.verts, tris.neighbors", [VALID, VALID, VALID, VALID, VALID, VALID]),
        ("tris.area/normal/center  owned", [STALE, STALE, VALID, UNSPEC, VALID, VALID]),
        ("tris.area/normal/center  ghosts", [STALE, STALE, VALID, UNSPEC, UNSPEC, UNSPEC]),
        ("verts.normal  owned", [STALE, STALE, STALE, UNSPEC, UNSPEC, VALID]),
        ("verts.normal  ghosts", [STALE, STALE, STALE, UNSPEC, UNSPEC, VALID]),
        ("MFTL_Object* handles", [VALID, VALID, VALID, INVALID, INVALID, INVALID]),
    ]
    W, H = 7.0, 3.15
    fig = figure(W, H)
    ax = canvas(fig, [0, 0, 1, 1], (0, W), (0, H), equal=False)
    x0, cw, ch, y_top = 2.05, 0.8, 0.265, 2.55
    for j, s in enumerate(steps):
        note(ax, x0 + j * cw + cw / 2, y_top + 0.28, s, size=6.1, color=C.ink, linespacing=1.15)
    for i, (name, states) in enumerate(rows):
        y = y_top - (i + 1) * ch
        code(ax, x0 - 0.1, y + ch / 2 - 0.02, name, size=6.3, ha="right")
        for j, st in enumerate(states):
            fc, ec, tc, txt = STYLE[st]
            box(ax, x0 + j * cw + 0.02, y + 0.02, cw - 0.04, ch - 0.04, fc=fc, ec=ec, lw=0.6, r=0.03)
            note(ax, x0 + j * cw + cw / 2, y + ch / 2 - 0.005, txt, size=6.3, color=tc)
    note(ax, x0 + 3.5 * cw, 0.12,
         "after step 4 keep the body id and re-fetch with MFTLEnsembleFindLocalObject();  "
         "MFTLComputeVertexNormals alone leaves ghost normals partial", size=6.2, color=C.ink_soft)
    return fig
