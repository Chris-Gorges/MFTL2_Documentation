# MFTL2_Documentation

The manual of **MFTL2** (MultiFlow Triangulation Library), and the tooling that
builds it. This repository contains no C source: it reads the library from a
separate checkout of [MFTL2](https://github.com/Chris-Gorges/MFTL2), normally
the sibling directory `../MFTL2`.

**Read it online: <https://chris-gorges.github.io/MFTL2/>** — rebuilt from MFTL2's
`main` and this repository by MFTL2's `Docs` workflow, with `--strict`, so the
published manual is also the proof that both build with zero warnings.

## View the manual in your browser

**You need** — once per machine:

| | macOS | Debian / Ubuntu | Fedora | Windows |
|---|---|---|---|---|
| Python ≥ 3.9 | preinstalled, or `brew install python` | `sudo apt-get install python3 python3-venv` | `sudo dnf install python3` | [python.org](https://www.python.org/downloads/) |
| Doxygen ≥ 1.9.7 and Graphviz | `brew install doxygen graphviz` | `sudo apt-get install doxygen graphviz` | `sudo dnf install doxygen graphviz` | `winget install DimitriVanHeesch.Doxygen` and `winget install Graphviz.Graphviz` |
| git | preinstalled | `sudo apt-get install git` | `sudo dnf install git` | [git-scm.com](https://git-scm.com/) |

plus network access on the first run (to install the MkDocs toolchain into a
private `.venv-docs/`; nothing is installed system-wide).

**Steps**

1. Put the library and this repository **side by side** in one folder:

   ```bash
   mkdir mftl && cd mftl
   git clone --branch christian https://git.multiflow.org/software/MFTL2.git MFTL2
   git clone https://github.com/Chris-Gorges/MFTL2_Documentation.git MFTL2_Documentation
   ```

   Both repositories are private: you need an account on git.multiflow.org with
   access to `software/MFTL2`, and to be added as a collaborator on
   `Chris-Gorges/MFTL2_Documentation`. (Already have `MFTL2` elsewhere? Skip the
   first clone and add `--source-dir /path/to/MFTL2` to the command in step 2.)

2. Run the one script:

   ```bash
   cd MFTL2_Documentation
   python3 view_manual.py
   ```

3. Your browser opens the manual at <http://127.0.0.1:8000/> (or the next free
   port, which the script prints). Press **Ctrl-C** in the terminal to stop it.

`view_manual.py` checks everything first and says exactly what to type for
anything missing — offering to install Doxygen/Graphviz or to clone `MFTL2`
for you (only on a yes). Then it builds the whole manual — guides, module
theory with all figures, API reference, and the Doxygen manual with every call,
caller and include graph — verifies that every part arrived, and serves it.
The first run takes a few minutes; afterwards it rebuilds only when a source
changed and is up in about a second.

**The Analysis section is optional.** The measurements it shows,
`docs/analysis.md`, are kept out of the MFTL2 repository, so a fresh clone has
none and the manual leaves the section out cleanly — no menu entry, no dead
links, zero warnings. A checkout that does have the file gets the section.
The published site and an export to `prebuilt/` always leave it out
(`python3 export_manual.py --with-measurements` for a private export).

```bash
python3 view_manual.py --check      # only report what is present and what is missing
python3 view_manual.py --clean      # something looks stale: delete build/ and start over
python3 view_manual.py --no-graphs  # much faster, without the Graphviz graphs
python3 view_manual.py --live       # live reload while editing prose
python3 view_manual.py --prebuilt   # the offline copy export_manual.py wrote (below)
python3 view_manual.py --help       # all options
```

**Nothing installed at all?** Read the [online manual](https://chris-gorges.github.io/MFTL2/).
For reading offline, `python3 export_manual.py` writes `prebuilt/html/index.html`
(search and formulas work from disk; the Doxygen manual with its graphs is at
`prebuilt/html/doxygen/index.html`) and `prebuilt/MFTL_Manual.pdf`, and
`prebuilt/README.md` says which library commit it was built from. `prebuilt/` is
not versioned: the published site replaced the committed copy.

**Troubleshooting**

| Symptom | Fix |
|---|---|
| `MISSING  Doxygen` / `MISSING  Graphviz` | run the install command printed under it, or `export DOXYGEN=/path/to/doxygen` |
| `Graphviz is installed but broken` | `sudo dot -c` (registers its plugins), or reinstall Graphviz |
| `no library checkout next to this repository` | clone it as in step 1, or pass `--source-dir /path/to/MFTL2` |
| `... is a git checkout ... but not of the branch this manual documents` | `git -C ../MFTL2 fetch origin && git -C ../MFTL2 switch christian` |
| `could not create a Python virtual environment` | Debian/Ubuntu: `sudo apt-get install python3-venv` |
| `installing the documentation toolchain failed` | no network or a proxy: `export HTTPS_PROXY=http://proxy:port` and re-run |
| a page, figure or graph is missing | `python3 view_manual.py --clean --verbose` |
| running on a remote machine over SSH | `ssh -L 8000:127.0.0.1:8000 host`, then `python3 view_manual.py --no-open` there and open <http://127.0.0.1:8000/> locally |

## Build it — the individual tools

`view_manual.py` drives these; call them directly to build without serving, for
CI, or to refresh `prebuilt/`. All run from this directory.

```bash
python3 build_mkdocs.py                  # -> build/site/index.html, Doxygen manual at /doxygen/
python3 build_mkdocs.py --serve --open   # live reload; first free port from :8000
python3 build_docs.py --open             # the Doxygen manual alone -> build/docs/html/index.html
python3 export_manual.py                 # refresh prebuilt/ (offline HTML with call graphs + PDF; needs Chrome/Chromium/Edge)

python3 build_docs.py --strict           # any Doxygen warning is a failure
python3 build_mkdocs.py --strict         # any warning, Doxygen or MkDocs, is a failure (CI)
python3 build_mkdocs.py --serve --no-doxygen --no-graphs   # fastest loop while writing prose
python3 build_docs.py --clean            # drop pages Doxygen no longer generates
python3 figures/build_figures.py         # redraw the theory figures into images/ (needs matplotlib)
```

`cmake -S . -B build && cmake --build build --target docs` builds the Doxygen
manual through CMake (`LANGUAGES NONE`, it compiles nothing).

The MkDocs toolchain (`requirements-docs.txt`) is installed into `.venv-docs/`
pinned to `requirements-docs.lock`, the exact versions the manual was last
checked with; where those pins cannot install (an older Python), the looser
requirements are used instead. Doxygen is found on `PATH` or through
`$DOXYGEN`. Configuration tags your Doxygen does not know are dropped
automatically, so any version from 1.9.7 on builds without configuration
warnings.

**Finding the library.** Every entry point resolves it once, through
`mftl_paths.py`, taking the first of: `--source-dir DIR`; `$MFTL_SOURCE_DIR`;
a git-ignored `mftl-source.txt` here holding one path; a sibling directory named
`MFTL2` or `MFTL`. A stated path that is not a library tree is an error rather
than a reason to try the next route, because a wrong tree produces a valid
manual about the wrong sources.

## Zero warnings is the acceptance criterion

`WARN_IF_UNDOCUMENTED`, `WARN_IF_INCOMPLETE_DOC`, `WARN_NO_PARAMDOC` and
`WARN_IF_UNDOC_ENUM_VAL` are on, so a new library function without
`@param`/`@return` fails `build_docs.py --strict`. Run it after touching any
header in the library.

## Why a separate repository

The library is read and edited far more often than its manual is built, so every
file that only exists to *render* documentation lives here:

| Stays with the library | Lives here |
|---|---|
| Doxygen comments in `include/` and `src/**` | `doxygen/Doxyfile.in` and everything that runs it |
| the fourteen `src/<module>/README.md` theory chapters | `pages/*.md`, the guide prose |
| the measurement document `docs/analysis.md` | `mkdocs/`, `manual/`, `mkdocs.yml`, `prebuilt/` |
| where a figure goes: `<!-- figure: name ... -->` in the chapter | the figure itself: `figures/` draws it, `images/` holds it |

The module READMEs render on GitHub next to the code, and about fifty source
comments cite `docs/analysis.md §N`, so those stay in the library.

## How it is put together

| Path | What it is |
|---|---|
| `view_manual.py` | the one command: checks prerequisites, builds when stale, verifies, serves, opens the browser |
| `mftl_paths.py` | where is the library? |
| `doxyconf.py` | adapts the Doxyfile to the installed Doxygen (drops unsupported tags, checks the version) |
| `build_docs.py` | the Doxygen manual |
| `build_mkdocs.py` | the web manual (runs the Doxygen pass first); also the toolchain installer and the local server |
| `requirements-docs.txt`, `requirements-docs.lock` | the MkDocs toolchain, and the exact versions last checked to build it |
| `export_manual.py` | the offline HTML and the PDF in `prebuilt/` |
| `CMakeLists.txt` | the CMake route to the Doxygen manual |
| `mkdocs.yml` | site configuration: nav, theme, plugin order |
| `doxygen/` | `Doxyfile.in`, layout, CSS, MathJax macros, `groups.dox`, the Markdown math filter |
| `pages/` | guide prose: main page, architecture, building, timestep, invariants, modules, analysis |
| `mkdocs/` | site machinery: `gen_pages.py`, `doxymd.py`, `doxyxml.py`, `doxyfile.py`, `hooks.py`, theme overrides |
| `manual/` | the site's own pages: landing page, guide index, API overview, assets |
| `figures/` | the generator of the theory figures (Python + matplotlib; `figures/README.md`) |
| `images/` | the generated figures, committed as SVG; placed in the prose by `<!-- figure: name -->` (`images/README.md`) |

The web manual is MkDocs + Material for the prose, [mkdoxy](https://mkdoxy.kubaandrysek.cz)
for the API reference, and the whole Doxygen HTML manual mounted at `/doxygen/`.
No prose is copied: `mkdocs/gen_pages.py` reads the files Doxygen reads and
rewrites Doxygen's Markdown dialect at build time, resolving `@ref`,
`#MFTL_Symbol` and `MFTLFunction()` against Doxygen's own `index.xml`.

### Things that are easy to break, and silent when broken

- **Plugin order in `mkdocs.yml`.** mkdoxy writes the Doxygen XML in `on_files`;
  `gen-files` resolves cross-references against it. Swap them and every API link
  in the prose degrades to a plain code span, on a clean tree only.
- **mkdoxy's `src-dirs` is a placeholder**, replaced by `mkdocs/hooks.py` in
  `on_config` with the resolved library paths (mkdoxy reads it later, in
  `on_files`). For the same reason `watch:` covers only this repository;
  `build_mkdocs.py --serve` adds the library's trees.
- **mkdoxy's Doxyfile is derived from `doxygen/Doxyfile.in`** by
  `mkdocs/doxyfile.py`, which flattens Doxygen's `+=` accumulation. Without it
  the MFTL aliases (`@collective`, `@rank_local`, …) appear as literal text in
  the API reference.
- **`manual/doxygen/*.html` are placeholders** that make links into `/doxygen/`
  valid at build time; `on_post_build` replaces the directory with the real
  manual. Delete them and `--strict` fails.
- **Member anchors are computed**: `doxymd.slugify` must reproduce
  `pymdownx.slugs.slugify(case="lower")`, pinned by the `toc` extension in
  `mkdocs.yml`. `CASE_SENSE_NAMES = NO` is pinned in `Doxyfile.in` so compound
  ids are spelled the same on every platform.
- **`smartsymbols`, `tilde`, `caret`, `mark` and `critic` are deliberately off**:
  each claims a character the prose uses literally (`~128 KB`, `a^2`,
  `ops == 0`).
- **The export leaves out `glightbox`**: it re-serialises every page body as a
  whole HTML document, which makes the print page run its table-of-contents
  script once per page.
- **The export rewrites the Doxygen pages' MathJax `src`** (a CDN URL from
  `MATHJAX_RELPATH`) to the copy the privacy plugin bundled, and fails if it
  finds no such page: a changed Doxygen output format would otherwise ship an
  offline manual whose formulas need network.
- **`STRIP_FROM_INC_PATH` lists both `include/` and `src/`.** Without the
  second, the page of a type declared in an internal header shows the absolute
  path of the machine that built the manual.

## License

Copyright 2025–2026 Christian Gorges and Berend van Wachem. Licensed under the
[Apache License 2.0](LICENSE), like [MFTL2](https://github.com/Chris-Gorges/MFTL2) itself.
