"""Locate the MFTL library tree that this documentation describes.

This repository holds no C source. Both manuals are generated from a *separate*
checkout of the library -- its headers, its sources, its doc comments, its twelve
module ``README.md`` files and its measurement document -- so every entry
point here needs one answer to one question: where is that checkout?

The answer is resolved once, in this module, rather than spelled as a relative
path in each of ``build_docs.py``, ``build_mkdocs.py``, ``mkdocs/hooks.py`` and
``mkdocs/gen_pages.py``. Four independently-guessed relative paths are four
places to get it wrong, and three of them would fail *quietly*: a Doxygen INPUT
that does not exist produces an empty manual, not an error.

Resolution order, first hit wins:

1. an explicit path passed on the command line (``--source-dir``);
2. the ``MFTL_SOURCE_DIR`` environment variable;
3. ``mftl-source.txt`` next to this file, holding one path (git-ignored, so a
   machine with an unusual layout can be configured once and never again);
4. a sibling directory of this repository named ``MFTL2`` or ``MFTL``.

Every candidate is *validated* before it is accepted. The first three are
STATED -- someone named that path -- so a stated path that is not a library
tree is an ERROR, not a reason to try the next route: falling through would
build a perfectly valid manual about the wrong sources, and nothing downstream
could tell. Only route 4 is a guess and only route 4 may miss. When nothing
survives, the failure names all four, because the fix depends on which one the
reader intended.
"""

from __future__ import annotations

import os
import re
import shutil
import sys

#: Environment variable naming the library checkout.
ENV_VAR = "MFTL_SOURCE_DIR"

#: Optional one-line file next to this module holding the same path.
CONFIG_FILE = "mftl-source.txt"

#: Sibling directory names tried when nothing else says where the library is.
SIBLING_NAMES = ("MFTL2", "MFTL")

#: Files that must exist for a directory to be the MFTL library and not, say,
#: this repository or an empty checkout. ``mftl_core.h`` is the umbrella header
#: and ``mftl_types.h`` the one place the structs are defined; a tree missing
#: either cannot produce an API reference.
SIGNATURE = (
    os.path.join("include", "mftl_core.h"),
    os.path.join("include", "mftl_types.h"),
    "CMakeLists.txt",
)

#: The library's measurement document, the source of the manual's Analysis
#: section. OPTIONAL: MFTL2 keeps ``docs/`` out of its repository, so a fresh
#: clone does not have it, while the checkout it was written in does.
MEASUREMENTS = os.path.join("docs", "analysis.md")

#: Set to ``0`` to leave the measurements out even where the file exists.
#: ``export_manual.py`` does, because ``prebuilt/`` is published and the
#: measurements are not.
MEASUREMENTS_ENV = "MFTL_DOCS_MEASUREMENTS"


def docs_root() -> str:
    """Return the root of this documentation repository.

    :returns: absolute path of the directory holding this module.
    """
    return os.path.dirname(os.path.abspath(__file__))


def is_source_tree(path: str) -> bool:
    """Report whether a directory looks like the MFTL library checkout.

    :param path: directory to test.
    :returns: ``True`` when every file in :data:`SIGNATURE` is present.
    """
    if not path or not os.path.isdir(path):
        return False
    return all(os.path.isfile(os.path.join(path, name)) for name in SIGNATURE)


def _why_not(path: str) -> str:
    """Explain why a candidate was rejected, naming the first missing file.

    :param path: the rejected candidate.
    :returns: a short phrase for the diagnostic.
    """
    if not os.path.isdir(path):
        return "not a directory"
    for name in SIGNATURE:
        if not os.path.isfile(os.path.join(path, name)):
            return f"no {name}"
    return "rejected"


def _configured() -> str | None:
    """Read the path out of :data:`CONFIG_FILE`, if that file exists.

    :returns: the configured path, or ``None``.
    """
    path = os.path.join(docs_root(), CONFIG_FILE)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.split("#", 1)[0].strip()
            if line:
                return os.path.expanduser(line)
    return None


def candidates(explicit: str | None = None) -> list[tuple[str, str, bool]]:
    """Assemble the ``(route, path, stated)`` triples to try, in resolution order.

    ``stated`` separates the three routes on which someone has NAMED a path from
    the sibling scan, which is a guess.  The distinction is what
    :func:`resolve` refuses to paper over.

    :param explicit: path given on the command line, or ``None``.
    :returns: every candidate, whether or not it exists.
    """
    root = docs_root()
    parent = os.path.dirname(root)

    found: list[tuple[str, str, bool]] = []
    if explicit:
        found.append(("--source-dir", os.path.expanduser(explicit), True))
    if os.environ.get(ENV_VAR):
        found.append((f"${ENV_VAR}", os.path.expanduser(os.environ[ENV_VAR]), True))
    configured = _configured()
    if configured:
        found.append((CONFIG_FILE, configured, True))
    found += [(f"sibling {name}/", os.path.join(parent, name), False) for name in SIBLING_NAMES]
    return [(route, os.path.abspath(path), stated) for route, path, stated in found]


def resolve(explicit: str | None = None) -> str:
    """Find the library checkout, or explain every route that was tried.

    A STATED path -- ``--source-dir``, ``$MFTL_SOURCE_DIR``, ``mftl-source.txt``
    -- is authoritative: if it is not a library tree this fails, rather than
    quietly documenting a different checkout that happens to sit next door.
    Falling through would be the worst of both worlds, because the manual it
    produced would be perfectly valid and about the wrong sources.  Only the
    sibling scan is allowed to miss.

    :param explicit: path given on the command line, or ``None``.
    :returns: absolute path of the MFTL library root.
    :raises SystemExit: when no candidate is a usable library tree.
    """
    tried = candidates(explicit)
    for route, path, stated in tried:
        if is_source_tree(path):
            return path
        if stated:
            print(f"Error: {route} names {path},", file=sys.stderr)
            print(f"  which is not an MFTL library checkout ({_why_not(path)}).", file=sys.stderr)
            raise SystemExit(1)

    print("Error: could not find the MFTL library sources.", file=sys.stderr)
    print("  This repository documents a checkout of MFTL that lives elsewhere.", file=sys.stderr)
    print("  Tried, in order:", file=sys.stderr)
    for route, path, _ in tried:
        print(f"    {route:<18} {path}  ({_why_not(path)})", file=sys.stderr)
    print("", file=sys.stderr)
    print("  Point it at the library with any one of:", file=sys.stderr)
    print("    python3 build_mkdocs.py --source-dir /path/to/MFTL2", file=sys.stderr)
    print(f"    export {ENV_VAR}=/path/to/MFTL2", file=sys.stderr)
    print(f"    echo /path/to/MFTL2 > {os.path.join(docs_root(), CONFIG_FILE)}", file=sys.stderr)
    raise SystemExit(1)


def project_version(source_root: str, fallback: str = "2.0") -> str:
    """Read the library version out of its ``CMakeLists.txt``.

    Taken from the library rather than repeated here, so the two repositories
    cannot report different version numbers for the same manual.

    :param source_root: root of the MFTL library checkout.
    :param fallback: value to use when the ``project()`` call cannot be read.
    :returns: the version string, e.g. ``"2.0"``.
    """
    path = os.path.join(source_root, "CMakeLists.txt")
    try:
        with open(path, encoding="utf-8") as handle:
            match = re.search(r"^project\s*\([^)]*VERSION\s+([0-9][0-9.]*)", handle.read(), re.MULTILINE)
    except OSError:
        return fallback
    return match.group(1) if match else fallback


def has_measurements(source_root: str) -> bool:
    """Decide whether the manual includes the Analysis section.

    Every place that includes or leaves it out asks this one function -- the
    Doxyfile for both Doxygen routes, the MkDocs navigation, the landing page
    and the page generator -- so a checkout without the file gets a manual with
    no Analysis section rather than one with dead links into it.

    :param source_root: root of the MFTL library checkout.
    :returns: ``True`` when :data:`MEASUREMENTS` exists and
        :data:`MEASUREMENTS_ENV` is not ``0``.
    """
    if os.environ.get(MEASUREMENTS_ENV, "").strip() == "0":
        return False
    return os.path.isfile(os.path.join(source_root, MEASUREMENTS))


def invalidate_on_measurement_change(directory: str, source_root: str) -> bool:
    """Delete generated output that was made with the other measurement setting.

    Doxygen never deletes a page it stops generating, and mkdoxy re-runs
    Doxygen only when a file under its ``src-dirs`` changes -- neither notices
    that the measurements came or went. So the setting of the last run is
    recorded next to each output tree (``<directory>.measurements``, outside it
    so it survives the delete), and a tree made with the other setting is
    removed before the next run. Without this, a build that leaves the Analysis
    section out still ships its pages, orphaned, from the previous build.

    :param directory: a generated tree, e.g. ``build/docs/html``.
    :param source_root: root of the MFTL library checkout.
    :returns: ``True`` when the tree was deleted.
    """
    want = "1" if has_measurements(source_root) else "0"
    marker = directory.rstrip("/\\") + ".measurements"
    try:
        with open(marker, encoding="utf-8") as handle:
            had = handle.read().strip()
    except OSError:
        had = None  # unknown: made before this check existed, so assume the worst
    changed = os.path.isdir(directory) and had != want
    if changed:
        shutil.rmtree(directory)
    os.makedirs(os.path.dirname(os.path.abspath(marker)), exist_ok=True)
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write(want + "\n")
    return changed


def measurement_substitutions(source_root: str, docs_root_dir: str) -> dict[str, str]:
    """Values for the two ``Doxyfile.in`` placeholders that include or drop the measurements.

    Without the document, Doxygen must neither be told to read it (a missing
    ``INPUT`` is a warning) nor read the Analysis page that introduces it (its
    references to the missing page are four more).

    :param source_root: root of the MFTL library checkout.
    :param docs_root_dir: root of this documentation repository.
    :returns: ``MFTL_DOCS_MEASUREMENTS_INPUT`` and ``MFTL_DOCS_MEASUREMENTS_EXCLUDE``.
    """
    if has_measurements(source_root):
        return {
            "MFTL_DOCS_MEASUREMENTS_INPUT": os.path.join(source_root, MEASUREMENTS),
            "MFTL_DOCS_MEASUREMENTS_EXCLUDE": "",
        }
    return {
        "MFTL_DOCS_MEASUREMENTS_INPUT": "",
        "MFTL_DOCS_MEASUREMENTS_EXCLUDE": os.path.join(docs_root_dir, "pages", "analysis.md"),
    }


def add_argument(parser) -> None:
    """Add the ``--source-dir`` option to an ``argparse`` parser.

    Kept here so the two build scripts spell the option, its default and its
    help text identically.

    :param parser: the parser to extend.
    :returns: nothing.
    """
    parser.add_argument(
        "--source-dir", default=None,
        help=f"path to the MFTL library checkout (default: ${ENV_VAR}, {CONFIG_FILE}, "
             f"or a sibling {'/'.join(SIBLING_NAMES)} directory)",
    )
