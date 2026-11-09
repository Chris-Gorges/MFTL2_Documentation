"""Generate the manual's prose pages from Markdown that already exists.

Run by ``mkdocs-gen-files`` during every build (and every ``mkdocs serve``
reload), this script is the single seam between the two documentation
backends.  It reads the files Doxygen reads and writes the same prose into the
MkDocs site as virtual pages, rewritten by :mod:`doxymd`.

The sources come from TWO repositories and the split is deliberate:

* this one contributes the guide prose, ``pages/*.md``;
* the LIBRARY contributes what belongs next to the code -- the fourteen
  ``src/<module>/README.md`` theory chapters and the ``docs/analysis.md``
  measurement document, which some fifty source comments cite by path;
* and one page is GENERATED rather than converted: the settings reference, from
  the library's key table ``src/settings/settings_keys.c`` (see
  :mod:`settings_page`), which is also what the library's parser, defaults and
  template are derived from.

Nothing is copied on disk.  There is one source of truth per subject, and both
manuals are built from it, which is the same rule the Doxyfile template follows
for its two build routes.

Figures are drawn by ``figures/build_figures.py`` into this repository's
``images/``, which is also Doxygen's ``IMAGE_PATH``; every SVG there is
published into the site under ``figures/``, and ``<!-- figure: name -->``
directives in the prose become numbered figures (see ``images/README.md``).

Cross-references are resolved in two passes because the corpus is a graph: the
first pass records every ``{#label}`` and where it will live, the second
converts.  A reference into the API reference is resolved against Doxygen's
``index.xml`` (see :mod:`doxyxml`), so it can only ever point at a page mkdoxy
has generated.
"""

from __future__ import annotations

import glob
import os
import sys

import mkdocs_gen_files

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import doxymd  # noqa: E402
import doxyxml  # noqa: E402
import mftl_paths  # noqa: E402
import settings_page  # noqa: E402

#: Root of this documentation repository.
DOCS_ROOT = mftl_paths.docs_root()

#: Root of the MFTL library checkout these pages describe.
SOURCE_ROOT = mftl_paths.resolve()

#: How a page's origin is named in its footer, per root.
REPOSITORIES = {
    DOCS_ROOT: "the MFTL2_Documentation repository",
    SOURCE_ROOT: "the MFTL library repository",
}

#: ``(source file, site page)`` for the guide pages, in nav order.  Relative to
#: THIS repository.
GUIDE_PAGES: list[tuple[str, str]] = [
    ("pages/mainpage.md", "overview.md"),
    ("pages/architecture.md", "guide/architecture.md"),
    ("pages/building.md", "guide/building.md"),
    ("pages/timestep.md", "guide/timestep.md"),
    ("pages/invariants.md", "guide/invariants.md"),
    ("pages/modules.md", "modules/index.md"),
    ("pages/analysis.md", "analysis/index.md"),
]

#: The module theory pages, in the layer order ``pages/modules.md``
#: presents them.  Each is one ``src/<dir>/README.md`` in the LIBRARY.
MODULE_DIRS: list[str] = [
    "arrayfunctions",
    "object",
    "topology",
    "geometry",
    "mesh_creation",
    "ensemble",
    "communication",
    "remeshing",
    "bvh",
    "topology_change",
    "correction",
    "coupling",
    "io",
    "settings",
]

#: The measurement document.  Relative to the LIBRARY, where it stays: it is
#: the engineering record the code comments point at.
ANALYSIS_PAGES: list[tuple[str, str]] = [
    ("docs/analysis.md", "analysis/measurements.md"),
]

#: Site directory of the Analysis section.  The whole section -- the index page
#: from ``pages/analysis.md`` included, which is mostly links into the
#: measurements -- exists only when ``mftl_paths.has_measurements()`` says so.
ANALYSIS_DIR = "analysis/"

#: Where mkdoxy's Doxygen XML may be found, most likely location first.  The
#: plugin writes it under ``save-api`` when that is configured and under the
#: site directory otherwise; a standalone ``build_docs.py`` run leaves a third
#: copy.  Any of them answers the same questions.
XML_CANDIDATES = [
    os.path.join(DOCS_ROOT, "build", "mkdocs", ".doxy", "mftl", "xml"),
    os.path.join(DOCS_ROOT, "build", "site", "assets", ".doxy", "mftl", "xml"),
    os.path.join(DOCS_ROOT, "build", "docs", "xml"),
]


def _source_note(root: str, source: str) -> str:
    """Footer marking a page as generated, and naming the file to edit instead.

    :param root: repository the source document lives in.
    :param source: path of the source document, relative to ``root``.
    :returns: a Markdown fragment.
    """
    where = REPOSITORIES.get(root, "the repository")
    return (
        '\n\n!!! abstract "Where this page comes from"\n\n'
        f"    This page is generated from `{source}` in {where}, which is also\n"
        "    what the Doxygen manual reads. Edit that file, not this page.\n"
    )


def _publish_figures() -> set[str]:
    """Copy every ``images/*.svg`` into the site under ``doxymd.FIGURE_DIR``.

    :returns: the names (basenames without ``.svg``) that were published.
    """
    names: set[str] = set()
    for path in sorted(glob.glob(os.path.join(DOCS_ROOT, "images", "*.svg"))):
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path, "rb") as src, mkdocs_gen_files.open(f"{doxymd.FIGURE_DIR}/{name}.svg", "wb") as dst:
            dst.write(src.read())
        names.add(name)
    return names


def _pages() -> list[tuple[str, str, str]]:
    """Assemble the full ``(root, source, site page)`` list.

    :returns: every page this script generates, in a stable order.
    """
    pages = [(DOCS_ROOT, source, page) for source, page in GUIDE_PAGES]
    pages += [(SOURCE_ROOT, f"src/{d}/README.md", f"modules/{d}.md") for d in MODULE_DIRS]
    pages += [(SOURCE_ROOT, source, page) for source, page in ANALYSIS_PAGES]
    if not mftl_paths.has_measurements(SOURCE_ROOT):
        pages = [entry for entry in pages if not entry[2].startswith(ANALYSIS_DIR)]
    return pages


def main() -> None:
    """Harvest anchors, then convert and emit every page.

    :returns: nothing.
    """
    index = doxymd.LinkIndex(api_path="api")

    xml_dir = doxyxml.find_xml_dir(XML_CANDIDATES)
    if xml_dir:
        index.compounds, index.members = doxyxml.load_index(xml_dir)

    figures = _publish_figures()
    pages = _pages()
    sources: dict[str, str] = {}
    for root, source, page in pages:
        path = os.path.join(root, source)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as handle:
            sources[path] = handle.read()
        doxymd.harvest_anchors(sources[path], page, index)

    # The settings reference has no Markdown source: it is rendered from the key
    # table, and from then on is a page like the others.
    settings_md = settings_page.generate(SOURCE_ROOT)
    if settings_md is not None:
        settings_source = settings_page.KEYS_SOURCE.replace(os.sep, "/")
        path = os.path.join(SOURCE_ROOT, settings_page.KEYS_SOURCE)
        sources[path] = settings_md
        pages.append((SOURCE_ROOT, settings_source, settings_page.PAGE))
        doxymd.harvest_anchors(settings_md, settings_page.PAGE, index)

    for root, source, page in pages:
        path = os.path.join(root, source)
        if path not in sources:
            continue
        body = doxymd.convert(sources[path], page, index, figures)
        with mkdocs_gen_files.open(page, "w") as handle:
            handle.write(body)
            handle.write(_source_note(root, source))
        mkdocs_gen_files.set_edit_path(page, source)


main()
