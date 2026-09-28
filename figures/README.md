# figures

The generator of the manual's theory figures. Its output, `../images/*.svg`,
is committed; see `../images/README.md` for how a figure is placed in the prose.

```bash
pip install -r figures/requirements.txt           # numpy, scipy, matplotlib
python3 figures/build_figures.py                  # -> images/*.svg
python3 figures/build_figures.py --png /tmp/prev  # also PNG previews (needs rsvg-convert)
```

## Layout

| Path | What it is |
|---|---|
| `build_figures.py` | the driver: renders every registered figure deterministically (fixed hash salt, no timestamp, text as outlines) and writes the SVG's intrinsic size at `DISPLAY_SCALE` |
| `mftlfig/style.py` | the house style: palette, typography, headings, stealth arrowheads, labels |
| `mftlfig/scene3d.py` | an orthographic 3D renderer on a 2D axes: camera, Lambert shading, per-face painter's order |
| `mftlfig/meshes.py` | meshes built with the library's conventions: the icosphere of `sphere_creation.c`, jittered planar triangulations |
| `gallery/<chapter>.py` | one module per manual chapter; each function decorated `@register("name")` draws `images/name.svg` |

## Conventions

**Computed, not sketched.** Where a figure shows what an algorithm produces, it
runs the algorithm: the icosphere is the library's face table subdivided and
projected once; the halo, the ghost clauses and the frozen band come from the
ownership and halo rules applied to a real triangulation; the marching-cubes
case comes from a port of `build_case`; the LBVH is the radix split over real
Morton keys; the reconstruction runs signed distance, cutoff, bias and the face
rule on a lattice. A figure that reads like a textbook sketch but disagrees with
the code is worse than none.

**One palette, one meaning per colour** (`mftlfig/style.py`): blue is "this
rank / owned / the object described", cyan the second party (the other rank,
the twin, the neighbour), coral the one thing the eye should land on (the edge
being operated on, the wrong answer, the event), amber derived or replicated
state (ghosts, frozen, caches), grey context. Mathematics is Computer Modern
(mathtext); annotation text is a sans serif.

**Legible at column width.** Figures are composed at 7 in, shown at about the
width of the manual's text column. Annotation text below 8 pt is enlarged
automatically; keep panel headings at `fheading`'s default.

**Theme.** The SVGs have a transparent ground; both manuals show them on a white
plate in the light and the dark scheme (`manual/stylesheets/mftl.css`,
`doxygen/mftl.css`), so the colours are exactly as drawn.

## Adding a figure

1. Write a function in the chapter's `gallery/` module, decorated with
   `@register("my-figure")`, returning the matplotlib figure.
2. `python3 figures/build_figures.py my-figure --png /tmp/prev` and look at it.
3. Place `<!-- figure: my-figure ... -->` in the prose (`../images/README.md`).
4. `python3 build_mkdocs.py --strict` — an unknown name fails it.
