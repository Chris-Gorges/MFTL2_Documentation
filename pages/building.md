Building, testing and generating this manual {#mftl_page_building}
============================================

[TOC]

# Requirements {#build_requirements}

| | Minimum | Notes |
|---|---|---|
| CMake | 3.13 | `CONFIGURE_DEPENDS` on the source glob needs it |
| C compiler | C11 | GCC, Clang/AppleClang and MSVC are handled in `CMakeLists.txt` |
| MPI | any | found with `find_package(MPI REQUIRED)` |
| Doxygen | 1.9.7+ | documentation only; written against 1.18. Tags the installed version does not know (obsolete, newer, or not compiled in) are dropped automatically |
| Graphviz | any | documentation only; without it the graphs are simply omitted |
| Python | 3.9+ | `build_all.py` in the library; `build_docs.py`, `build_mkdocs.py` and `export_manual.py` in MFTL2_Documentation |
| MkDocs Material | see `requirements-docs.txt` | web manual only; installed into `.venv-docs/` on first use (needs network once) |
| Chrome, Chromium or Edge | any recent | only for the PDF of `export_manual.py` |

@note **Nothing needs to be built to read the manual.** `MFTL2_Documentation`
      carries a pre-built copy in `prebuilt/`: `MFTL_Manual.pdf` and an offline
      web manual, `prebuilt/html/index.html`, with the Doxygen manual and its
      call graphs at `prebuilt/html/doxygen/index.html` (see @ref build_export).

@note **The library and its documentation are two repositories.** MFTL itself
      carries no Doxyfile, no MkDocs configuration and no documentation
      toolchain — only the doc comments in its sources, its eleven module
      `README.md` files and the measurement document `docs/analysis.md`.
      Everything that *renders* those lives in **MFTL2_Documentation**, which
      reads the library from wherever it is checked out. Nothing below that
      says `build_docs.py` or `build_mkdocs.py` is run from the library
      directory; everything that says `build_all.py` is.

---

# Building the library {#build_library}

```bash
python3 build_all.py              # Release (optimized, no sanitizers) — for performance runs
python3 build_all.py --debug      # Debug WITH ASan+UBSan — default for day-to-day dev
python3 build_all.py --valgrind   # Debug WITHOUT sanitizers — required under Valgrind
python3 build_all.py --lib-only   # skip examples/
```

`build_all.py` always deletes and recreates `build/`, so flags never mix between
runs. `src/**/*.c` is globbed with `CONFIGURE_DEPENDS`, so a new `.c` is picked up
without editing `CMakeLists.txt`.

Or configure by hand:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

## Architecture flags {#build_arch}

`-march=native` is **off by default**. Cluster login nodes routinely differ in
ISA from compute nodes, which turns into `SIGILL` at run time.

```bash
cmake -S . -B build -DMFTL_ARCH_NATIVE=ON              # same-machine run
cmake -S . -B build -DMFTL_ARCH_FLAGS=-march=sapphirerapids
```

## CMake options {#build_options}

| Option | Default | Effect |
|---|---|---|
| `ENABLE_SANITIZERS` | `ON` | ASan + UBSan in Debug. **Public**, so every target linking MFTL is instrumented too — mixing is what produces bogus ASan reports |
| `BUILD_EXAMPLES` | `ON` | the benchmarks under `examples/` |
| `BUILD_TESTING` | `ON` | the CTest suite |
| `MFTL_ARCH_NATIVE` | `OFF` | `-march=native` in Release |
| `MFTL_ARCH_FLAGS` | *(empty)* | extra Release architecture flags |

The documentation has its own CMake project, in its own repository, with its own
options — see @ref build_docs. The library's build knows nothing about Doxygen.

@warning One compile flag in `CMakeLists.txt` is **correctness, not tuning**:
         `src/bvh/bvh_predicates.c` is built with `-ffp-contract=off`. The
         adaptive orientation predicate recovers the exact residue of \f$ab\f$ by
         evaluating \f$x - ab\f$ in a second rounding step; a fused multiply-add
         contracts that into one rounding, the residue comes out zero, and every
         exactness guarantee in the file silently evaporates while the numbers
         still look plausible. Do not remove it.

---

# Running the tests {#build_tests}

```bash
python3 run_local_tests.py            # rebuilds (Release) then runs the full CTest suite
cd build && ctest --output-on-failure
cd build && ctest --output-on-failure -R object    # one module
```

Sixty-eight CTest entries, built on `tests/test_utils.h` (`RUN_TEST`,
`TEST_ASSERT*`, `TEST_REPORT`).

@note **Run the suite in the `--debug` build too.** `tests/test_object.c`
      deliberately writes the last addressable element of every pool array, so an
      array that was not grown with the rest is an ASan failure rather than a
      silent corruption.

## Why a test is registered at several rank counts {#build_ranks}

The rank count is not a scaling knob in this suite — it changes which code path
is reachable:

| P | Grid | What only this count sees |
|---|---|---|
| 1 | — | the no-op path, and that every collective is still entered with nothing to exchange |
| 2 | 2×1×1 | periodic wrap maps several of the 26 neighbour offsets onto the same rank, so the neighbour list is shorter than the stencil |
| 4 | 2×2×1 | the first grid with a real diagonal neighbour — the **tube** conflict |
| 8 | 2×2×2 | every one of the 26 offsets is populated; **corner** conflicts |
| 27 | 3×3×3 | the first grid with an **interior** rank whose 26 neighbours are 26 *distinct* ranks. Below it, periodic aliasing collapses several stencil offsets onto the same rank and the de-duplication is doing half the work by accident. On a walled grid it is also the first where rank 0's opening scatter reaches non-neighbours and takes the global path |

@warning In a multi-rank test **every assertion must be made on an
         `MPI_Allreduce`d verdict** (see `agreed()` in `tests/test_utils.h`).
         `TEST_ASSERT` returns immediately, so an assertion failing on only some
         ranks leaves the rest blocked in the next collective — a hang instead of
         a clean failure.

## The source-level test {#build_source_test}

`test_remeshing_mpi_is_confined` is a CMake script, not a binary. It fails the
build if any file under `src/remeshing/` other than `remesh_comm.c` contains an
MPI call. No runtime test can see that property, and it is exactly the one that
was lost the first time round.

---

# Generating this manual {#build_docs}

Everything in this section is run from the **MFTL2_Documentation** checkout, not
from the library.

## Just looking at it — one command {#build_docs_view}

```bash
python3 view_manual.py            # check, build if anything changed, verify, serve, open the browser
python3 view_manual.py --check    # only report what is missing, with the command that installs it
python3 view_manual.py --clean    # start over from an empty build/
python3 view_manual.py --prebuilt # the committed offline copy; needs nothing installed
```

`view_manual.py` checks Python, Doxygen and Graphviz (by rendering an SVG, not
by finding `dot` on the path), finds the library, installs the MkDocs toolchain
into `.venv-docs/` once, builds the whole manual with its graphs, checks that
every part of it arrived — pages, theory figures, API reference, the embedded
Doxygen manual, graphs, search index — and serves it on `127.0.0.1`, port 8000
or the next free one. A missing system package or library checkout is offered
as the exact command for this machine, and run only on a yes. The second run
rebuilds nothing unless a source changed, and is up in about a second.

It SERVES the site rather than opening `build/site/index.html` from disk
because the site uses directory URLs (`guide/`), which a `file://` browser
cannot resolve: from disk, the landing page renders and every link on it is
dead. The export in `prebuilt/` is the variant built for `file://`.

Underneath it, the Doxygen manual has two build routes, producing identical
output. Both substitute the same placeholders into `doxygen/Doxyfile.in`.

## Finding the library {#build_docs_source}

The template carries **two** roots — `@MFTL_DOCS_SOURCE_DIR@` for the library and
`@MFTL_DOCS_DIR@` for this repository — and only the second is known without
being told. `mftl_paths.py` answers the first, once, for every entry point here,
taking the first of:

1. `--source-dir /path/to/MFTL2` on the command line;
2. the `MFTL_SOURCE_DIR` environment variable;
3. `mftl-source.txt` next to `mftl_paths.py`, holding one path;
4. a sibling directory called `MFTL2` or `MFTL`.

Every candidate is validated. It has to be checked rather than assumed: a
Doxygen `INPUT` that does not exist produces an **empty manual**, not an error.

@warning The first three routes are **stated** — someone named that path — so a
         stated path that is not a library tree is an error, not a reason to try
         the next route. Falling through to the sibling checkout would build a
         perfectly valid manual about the wrong sources, and nothing downstream
         could tell. Only route 4 is a guess and only route 4 may miss.

If the two repositories sit side by side, route 4 answers it and there is
nothing to configure at all.

## Standalone — nothing to configure {#build_docs_standalone}

```bash
python3 build_docs.py                 # -> build/docs/html/index.html
python3 build_docs.py --open          # and open it in a browser
python3 build_docs.py --strict        # any Doxygen warning is a failure
python3 build_docs.py --no-graphs     # skip Graphviz (much faster)
python3 build_docs.py --output-dir /tmp/mftl-docs
python3 build_docs.py --source-dir ~/git/MFTL2
python3 build_docs.py --clean         # delete the old output first (no stale pages)
```

This route does **not** invoke CMake and touches nothing in the library, so it
stays out of the way of a fast edit–compile–test cycle there.

## Through CMake {#build_docs_cmake}

```bash
cmake -S . -B build                   # add -DMFTL_SOURCE_DIR=... if needed
cmake --build build --target docs
```

| Option | Default | Effect |
|---|---|---|
| `MFTL_SOURCE_DIR` | *(resolved)* | path to the library checkout |
| `MFTL_DOCS_WARN_AS_ERROR` | `OFF` | a Doxygen warning fails the `docs` target |
| `MFTL_DOCS_LATEX` | `OFF` | also emit LaTeX sources for a PDF |

@note This CMake project declares `LANGUAGES NONE` and compiles nothing; it
      exists so the manual can be built by whatever already drives CMake. `docs`
      is **not** attached to `all`, so `cmake --build build` on its own runs
      nothing — adding this directory to a super-build cannot make anyone pay
      for Graphviz.

## What the generated manual contains {#build_docs_contents}

| Section | Source | Repository |
|---|---|---|
| Main page | `pages/mainpage.md` | documentation |
| Guides | `pages/*.md` | documentation |
| Modules | `doxygen/groups.dox` + `@ingroup` tags, one group per `src/` directory | documentation |
| Module theory pages | `src/*/README.md`, bound in as full pages | library |
| Analysis | `docs/analysis.md` | library |
| API reference | Doxygen comments in the public headers and `src/**/*.c` | library |
| Call / caller graphs | Graphviz, as interactive SVG | library |
| `#include` graphs | Graphviz, per file and per directory | library |

The measurement document stays with the code it measures: some fifty comments
in `src/`, `include/`, `tests/` and `examples/` cite it by section, and a reader
who follows one of those citations is in the library, not here.

Formulas are written as `\\f$ ... \\f$` / `\\f[ ... \\f]` in the sources and as
`$ ... $` / `$$ ... $$` in the Markdown pages; `doxygen/mathjax.js` enables both
delimiter sets, so a README renders correctly on GitHub **and** in the manual
from one source. Shared macros live in `doxygen/formulas.tex`.

## Warnings are the acceptance criterion {#build_docs_warnings}

The configuration turns on `WARN_IF_UNDOCUMENTED`, `WARN_IF_INCOMPLETE_DOC`,
`WARN_NO_PARAMDOC` and `WARN_IF_UNDOC_ENUM_VAL`, and writes them to
`build/docs/doxygen-warnings.log`. A clean run produces an empty log.

```bash
python3 build_docs.py --strict        # exits non-zero if the log is non-empty
```

---

# The web manual — MkDocs Material {#build_site}

The same corpus is also published as a modern static site: MkDocs with the
Material theme for the prose, [mkdoxy](https://mkdoxy.kubaandrysek.cz) for the
API reference, and the **whole Doxygen manual mounted inside it** at
`/doxygen/`, so a reader gets the call graphs and the annotated sources without
building or deploying a second thing.

```bash
python3 build_mkdocs.py                 # -> build/site/index.html
python3 build_mkdocs.py --serve --open  # live-reload dev server, first free port from :8000
python3 build_mkdocs.py --strict        # any warning, Doxygen or MkDocs, is a failure
python3 build_mkdocs.py --no-doxygen --no-graphs --serve   # fastest prose loop
```

`--serve --open` opens the browser only once the server answers with this site:
`mkdocs serve` builds everything before it listens (20 s warm, minutes cold),
and a port that is already taken — 8000 is every other development server's
default too — is replaced by the next free one before anything is built.

The first run creates `.venv-docs/` and installs `requirements-docs.txt` into
it, pinned to the versions in `requirements-docs.lock` — the exact set the
manual was last checked with, transitive dependencies included — and falls back
to the unpinned requirements where those pins cannot install (an older Python).
That environment is private to the documentation for the same reason
`build_all.py` recreates `build/` every time: a documentation dependency must
never be able to change what the library build does. Since the split it cannot
even be installed next to it — nothing in `requirements-docs.txt` is reachable
from the library checkout, and nothing in it is needed to compile, test or use
MFTL.

## There is still one source per subject {#build_site_sources}

No prose is copied. `mkdocs/gen_pages.py` reads the files Doxygen reads and
rewrites Doxygen's Markdown dialect into Material's at build time:

| Site section | Generated from | Repository |
|---|---|---|
| Overview | `pages/mainpage.md` | documentation |
| Guide | `pages/architecture.md`, `building.md`, `timestep.md`, `invariants.md` | documentation |
| Modules | `pages/modules.md` and the eleven `src/*/README.md` | both |
| Analysis | `docs/analysis.md` | library |
| API reference | Doxygen XML, via mkdoxy | library |
| `/doxygen/` | `build/docs/html`, copied in by `mkdocs/hooks.py` | documentation |

`@ref`, `@subpage`, `#MFTL_Symbol` and `MFTLFunction()` are resolved against
Doxygen's own `index.xml`, so a cross-reference in the prose lands on the exact
member anchor of the generated API page rather than on a guessed path. The
Doxyfile mkdoxy runs is itself derived from `doxygen/Doxyfile.in` by
`mkdocs/doxyfile.py` — the aliases, the `PREDEFINED` set and the extraction
policy are read from one template, so the two manuals cannot document
differently configured libraries.

@note mkdoxy's `src-dirs` assigns Doxygen's `INPUT` directly, and the trees it
      has to read are not in this repository, so `mkdocs.yml` holds a
      **placeholder** that `mkdocs/hooks.py` replaces in `on_config` with the
      resolved absolute paths. mkdoxy reads the option in `on_files`, which is
      strictly later, so the ordering is safe by construction rather than by
      declaration order. For the same reason `mkdocs.yml`'s `watch:` list covers
      only this repository: `build_mkdocs.py --serve` adds the library's trees
      with `mkdocs serve -w`, because where they are is not known when the
      configuration is read.

@note The plugin order in `mkdocs.yml` is load-bearing: **mkdoxy must run before
      `gen-files`**. mkdoxy produces the Doxygen XML that the page generator
      resolves cross-references against, and MkDocs fires plugin events in the
      order the plugins are declared. Swap the two and every API link in the
      prose silently degrades to a plain code span on the first build of a clean
      tree — the pages still build, and nothing reports it.

## Which manual answers which question {#build_site_split}

The two are generated from the same sources but they are not interchangeable,
and the split is by what the tool can produce rather than by taste:

| Question | Where |
|---|---|
| What does this function do | either — identical content |
| What is the theory behind this module | the site: the module pages, with a navigable structure and a search index over the prose |
| Who calls this, and what does it call | the Doxygen manual — Graphviz call and caller graphs |
| What does the annotated source look like | the Doxygen manual — cross-linked source browser |
| Which headers include which | the Doxygen manual — `#include` dependency graphs |

@warning `build/site/` is a **static** directory and nothing in it is generated
         at view time, so it can be served from anywhere. It does, however,
         contain the whole Doxygen manual, about 85 MB of HTML and SVG (the
         graph caches `*.md5` and `*.map` are not copied). Deploying it
         to a path other than the site root requires `site_url` in `mkdocs.yml`
         to be set — the links between the two halves are relative, but
         Material's search index and social assets are not.

---

# The pre-built manual {#build_export}

```bash
python3 export_manual.py              # -> prebuilt/html/ and prebuilt/MFTL_Manual.pdf
python3 export_manual.py --no-pdf     # only the offline HTML
python3 export_manual.py --no-doxygen # without the Doxygen manual (about 85 MB less)
python3 export_manual.py --chrome /path/to/chromium
```

`prebuilt/` is **committed**, so a reader needs no toolchain at all. The export is
the same site built with a generated configuration (`.mkdocs.export.yml`) that
INHERITs `mkdocs.yml` and changes only what an offline copy needs:

- Material's `privacy` plugin downloads the web fonts and MathJax at build time
  and serves them from the site itself, so nothing is fetched at view time;
  MathJax uses its SVG output, whose glyphs are inside the script;
- the `offline` plugin and `use_directory_urls: false` make the site work from
  `file://`, search included (instant navigation is switched off: browsers
  refuse its requests for local files);
- the Doxygen manual is rebuilt from scratch (`build_docs.py --clean`: Doxygen
  never deletes a page it stopped generating) and mounted at `doxygen/` —
  call, caller and include graphs and the source browser, about 85 MB — and
  its pages are pointed at the bundled MathJax instead of the CDN;
- `mkdocs-print-site-plugin` concatenates every page into `print_page.html`, and a
  headless Chrome/Chromium/Edge prints that page to `MFTL_Manual.pdf` with a
  bookmark outline. The navigation of the export adds one page per public header
  and per public structure, derived from the library's `include/`, so the PDF
  carries the complete API reference.

`prebuilt/README.md` records the library and documentation commits and the
Doxygen version the export was built from. Refresh it before a release.

---

# Header hygiene {#build_hygiene}

Two checks worth running after touching headers:

```bash
# every header must compile alone
for h in include/*.h; do printf '#include "%s"\n' "$(basename $h)" > /tmp/sc.c; \
  mpicc -std=c11 -fsyntax-only -Iinclude /tmp/sc.c || echo "NOT SELF-CONTAINED: $h"; done

# the library must export only MFTL* symbols, with no duplicates
nm -g build/lib/libMFTL.a | grep ' T ' | awk '{print $NF}' | grep -v _MFTL   # must be empty
nm -g build/lib/libMFTL.a | grep ' T ' | awk '{print $NF}' | sort | uniq -d  # must be empty
```
