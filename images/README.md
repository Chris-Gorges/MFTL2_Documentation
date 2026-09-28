# images

The theory figures of the manual, as SVG. They are **generated** — by
`figures/build_figures.py`, one Python function per figure — and committed, so
building the manual needs neither matplotlib nor the generator. Do not edit an
SVG by hand; change its function in `figures/gallery/` and re-run:

```bash
python3 figures/build_figures.py                  # all figures
python3 figures/build_figures.py lbvh icosphere   # some
python3 figures/build_figures.py --list
```

The output is deterministic, so an unchanged tree re-generates byte-identical
files and a diff here is a real change to a figure.

This directory is Doxygen's `IMAGE_PATH`, and `mkdocs/gen_pages.py` publishes
every SVG in it into the web manual under `figures/`.

## Placing a figure in the prose

A figure is placed by an HTML comment, in the library's module READMEs
(`src/<module>/README.md`) and in `pages/*.md` alike:

```markdown
<!-- figure: halfedge-implicit
Implicit indexing. (a) Half-edge $3t+k$ runs from corner $k$ of triangle $t$
to corner $k+1$ ...
-->
```

- The opening line is `<!-- figure: NAME`, indented at most three spaces, where
  `NAME` (`[a-z0-9][a-z0-9-]*`) is the basename of an SVG here.
- Everything up to `-->` is the caption: Markdown with GitHub math (`$...$`),
  code spans and API names, which link as they do in the surrounding prose.
  The caption may also start on the opening line, and the whole directive may
  be one line.
- Figures are numbered per page, in order of appearance ("Figure 1.", ...).
- Inside a fenced code block the directive is left alone.

**Why a comment.** The READMEs render on GitHub next to the code, and the SVGs
live in this repository, which GitHub cannot resolve from there; a comment
renders as nothing instead of as a broken image. Both manuals expand it:

| Manual | Expanded by | Into |
|---|---|---|
| web (MkDocs) | `mkdocs/doxymd.py` | `<figure class="mftl-figure">` with the image and a `<figcaption>` |
| Doxygen | `doxygen/md_math_filter.py` | `\image html NAME.svg` plus a `<div class="mftl-caption">` (Doxygen allows no formula in an `\image` caption) |

**An unknown name fails the build**: MkDocs reports it as a warning and Doxygen
cannot find the image, so `--strict` catches a typo on either route.
