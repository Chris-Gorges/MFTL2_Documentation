"""MkDocs hooks that bind this site to the library and to the Doxygen manual.

Two manuals are generated from the MFTL sources and they answer different
questions.  The Material site is the *manual*: prose, guides, module theory and
a browsable API index.  The Doxygen manual is the *machine-generated reference*:
call graphs, caller graphs, ``#include`` dependency graphs and a fully
cross-linked source browser -- artefacts mkdoxy does not reproduce because they
come out of Graphviz, not out of the XML.

Rather than ask the reader to build and open a second site, the whole Doxygen
HTML tree is copied into the published site under ``/doxygen/``.  One deploy
target, one URL, both manuals.

The other job is locating the library.  This repository holds no C source, so
``mkdocs.yml`` cannot name the trees mkdoxy has to read; ``on_config`` resolves
them through :mod:`mftl_paths` and writes them into the plugin's configuration
before mkdoxy looks at it.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import doxyconf  # noqa: E402
import doxyfile  # noqa: E402
import mftl_paths  # noqa: E402

log = logging.getLogger("mkdocs.hooks.mftl")

#: Where ``build_docs.py`` (and the ``docs`` CMake target) leave the manual.
DOXYGEN_HTML = os.path.join("build", "docs", "html")

#: Where it is mounted inside the published site.
MOUNT_POINT = "doxygen"

#: Files in the Doxygen HTML tree that only Doxygen reads (graph caches).
DOXYGEN_CACHE_FILES = ("*.md5", "*.map")

#: Doxyfile handed to mkdoxy, generated from ``doxygen/Doxyfile.in``.
API_DOXYFILE = os.path.join("build", "mkdocs", "Doxyfile.api")

#: Library sub-trees the API reference is extracted from, in Doxygen's INPUT
#: order.  ``doxygen/`` is this repository's own and carries ``groups.dox``,
#: which is where every ``@defgroup`` is defined.
SOURCE_SUBDIRS = ("include", "src")


def _mkdoxy_projects(config):
    """Return mkdoxy's per-project configuration dictionaries.

    :param config: the MkDocs configuration.
    :returns: list of the project dicts, empty when mkdoxy is not enabled.
    """
    plugin = config["plugins"].get("mkdoxy")
    if plugin is None:
        return []
    projects = plugin.config.get("projects") or {}
    return list(projects.values())


def on_config(config, **kwargs):
    """Point mkdoxy at the library and derive its Doxygen configuration.

    Two things happen here, and both have to happen before any plugin's
    ``on_files`` -- which is the only event mkdoxy implements, so ``on_config``
    is unconditionally early enough:

    * ``src-dirs`` is replaced with absolute paths into the resolved library
      checkout.  mkdoxy assigns that value straight to Doxygen's ``INPUT``, and
      a wrong one produces an *empty* API reference rather than an error, so it
      is resolved rather than written down.
    * ``build/mkdocs/Doxyfile.api`` is generated from the project's own template,
      so the API reference is extracted with the same aliases, the same
      ``PREDEFINED`` set and the same extraction policy as the Doxygen manual.

    :param config: the MkDocs configuration.
    :param kwargs: further MkDocs event arguments, unused.
    :returns: the configuration, unchanged apart from the two writes above.
    """
    docs_root = os.path.dirname(os.path.abspath(config["config_file_path"]))
    source_root = mftl_paths.resolve()

    inputs = [os.path.join(source_root, name) for name in SOURCE_SUBDIRS]
    inputs.append(os.path.join(docs_root, "doxygen"))
    for project in _mkdoxy_projects(config):
        project["src-dirs"] = " ".join(inputs)
    log.info("MFTL: reading the library from %s", source_root)

    # The Doxygen mkdoxy runs is the one build_docs.py would run ($DOXYGEN or PATH).
    plugin = config["plugins"].get("mkdoxy")
    doxygen = doxyconf.find_doxygen()
    if plugin is not None and doxygen:
        plugin.config["doxygen-bin-path"] = doxygen

    try:
        doxyfile.write_api_doxyfile(docs_root, source_root, os.path.join(docs_root, API_DOXYFILE))
    except OSError as error:
        log.warning("MFTL: could not generate %s (%s); mkdoxy will fall back to its defaults.", API_DOXYFILE, error)

    measurements = mftl_paths.has_measurements(source_root)
    config["extra"]["mftl_measurements"] = measurements
    if plugin is not None and plugin.config.get("save-api"):
        # mkdoxy re-runs Doxygen only when its src-dirs change, and would keep
        # serving the XML of the other setting -- its file list included.
        cache = os.path.join(docs_root, plugin.config["save-api"])
        if mftl_paths.invalidate_on_measurement_change(cache, source_root):
            log.info("MFTL: the measurements came or went; cleared mkdoxy's cache %s.", plugin.config["save-api"])
    if not measurements:
        config["nav"] = [entry for entry in (config["nav"] or []) if not _points_into_analysis(entry)]
        log.info("MFTL: no %s in the library (or %s=0) -- the Analysis section is left out.",
                 mftl_paths.MEASUREMENTS, mftl_paths.MEASUREMENTS_ENV)
    return config


#: Site directory of the Analysis section (``mkdocs/gen_pages.py`` generates it).
ANALYSIS_DIR = "analysis/"

#: A block of a hand-written page that exists only with the measurements.
MEASUREMENTS_BLOCK = re.compile(
    r"^[ \t]*<!-- measurements -->[ \t]*\n(.*?)^[ \t]*<!-- /measurements -->[ \t]*\n", re.DOTALL | re.MULTILINE
)


def _points_into_analysis(entry) -> bool:
    """Report whether a navigation entry leads into the Analysis section.

    :param entry: one item of ``nav``: a path, a ``{title: ...}`` mapping or a list.
    :returns: ``True`` when any page under it lies in :data:`ANALYSIS_DIR`.
    """
    if isinstance(entry, str):
        return entry.startswith(ANALYSIS_DIR)
    if isinstance(entry, dict):
        return any(_points_into_analysis(value) for value in entry.values())
    if isinstance(entry, list):
        return any(_points_into_analysis(value) for value in entry)
    return False


def on_page_markdown(markdown, page, config, files, **kwargs):
    """Keep or drop the ``<!-- measurements -->`` blocks of a hand-written page.

    The landing page links into the Analysis section from a card; without the
    measurements that card would be a dead link. The markers themselves always
    go, so they cannot interrupt the Markdown list they sit in.

    :param markdown: the page source.
    :param page: the page being built, unused.
    :param config: the MkDocs configuration.
    :param files: the site's files, unused.
    :param kwargs: further MkDocs event arguments, unused.
    :returns: the page source with every block kept or dropped.
    """
    if "<!-- measurements -->" not in markdown:
        return markdown
    keep = config["extra"].get("mftl_measurements", True)
    return MEASUREMENTS_BLOCK.sub(lambda match: match.group(1) if keep else "", markdown)


def on_post_build(config, **kwargs) -> None:
    """Copy the Doxygen HTML manual into the built site.

    Silent about a missing manual beyond one informational line: a prose-only
    rebuild is a legitimate thing to do while editing, and failing it would make
    the fast path depend on Graphviz.

    :param config: the MkDocs configuration.
    :param kwargs: further MkDocs event arguments, unused.
    :returns: nothing.
    """
    # A prose-only site (``extra.mftl_mount_doxygen: false``) keeps the
    # placeholder pages, which say how to build the manual.
    if not config["extra"].get("mftl_mount_doxygen", True):
        return

    root = os.path.dirname(os.path.abspath(config["config_file_path"]))
    source = os.path.join(root, DOXYGEN_HTML)
    target = os.path.join(config["site_dir"], MOUNT_POINT)

    if not os.path.isdir(source):
        log.info(
            "MFTL: no Doxygen manual at %s -- the '%s/' section of the site will 404. "
            "Run `python3 build_docs.py` (or `python3 build_mkdocs.py`, which does it for you).",
            DOXYGEN_HTML,
            MOUNT_POINT,
        )
        return

    if os.path.isdir(target):
        shutil.rmtree(target)
    # *.md5 and *.map are Doxygen's graph caches (a quarter of the tree); no page
    # loads them.
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*DOXYGEN_CACHE_FILES))
    log.info("MFTL: embedded the Doxygen manual at /%s/ (%d files).", MOUNT_POINT, sum(len(f) for _, _, f in os.walk(target)))
