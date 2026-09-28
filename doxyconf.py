"""Adapt the Doxyfile template to the Doxygen that is actually installed.

``doxygen/Doxyfile.in`` is written against one Doxygen release, and Doxygen's
configuration is not stable across releases: tags become obsolete
(``DOT_TRANSPARENT``, ``DOT_MULTI_TARGETS``), new tags appear
(``WARN_IF_UNDOC_ENUM_VAL``), and some exist only when Doxygen was compiled
with a feature (``CLANG_ASSISTED_PARSING``). An unsupported tag produces a
configuration warning on every run, so a template that is clean on one machine
is noisy on the next.

The installed binary knows exactly which tags it supports: ``doxygen -g``
writes a fresh configuration listing all of them. Every configuration this
repository generates is filtered against that list before Doxygen reads it, so
the template can name every tag it wants and each machine silently drops the
ones its Doxygen does not have.

Used by ``build_docs.py`` (the Doxygen manual) and ``mkdocs/doxyfile.py`` (the
configuration mkdoxy runs for the site's API reference).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile

#: Oldest Doxygen the template is known to work with. Older releases are not
#: refused, only warned about: most of the manual still builds.
MIN_VERSION = (1, 9, 7)

_TAG_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*\+?=")
_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def find_doxygen() -> str | None:
    """Locate the Doxygen executable.

    :returns: its path, from ``$DOXYGEN`` or ``PATH``, or ``None``.
    """
    explicit = os.environ.get("DOXYGEN")
    if explicit and os.path.isfile(explicit):
        return explicit
    return shutil.which("doxygen")


def version(doxygen: str) -> tuple[int, int, int] | None:
    """Report the version of a Doxygen executable.

    :param doxygen: path to the executable.
    :returns: ``(major, minor, patch)``, or ``None`` if it cannot be determined.
    """
    try:
        out = subprocess.run([doxygen, "--version"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    match = _VERSION_RE.search(out)
    return tuple(int(g) for g in match.groups()) if match else None


def version_note(doxygen: str) -> str | None:
    """Explain an outdated Doxygen, if it is one.

    :param doxygen: path to the executable.
    :returns: a one-line warning, or ``None`` when the version is recent enough
        or unknown.
    """
    found = version(doxygen)
    if found is None or found >= MIN_VERSION:
        return None
    want = ".".join(map(str, MIN_VERSION))
    have = ".".join(map(str, found))
    return f"Doxygen {have} is older than {want}; the manual may render with gaps. Upgrade if you can."


def supported_tags(doxygen: str) -> set[str] | None:
    """The configuration tags this Doxygen binary accepts.

    :param doxygen: path to the executable.
    :returns: the tag names, or ``None`` if ``doxygen -g`` could not be run (the
        caller then leaves the configuration untouched).
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "Doxyfile")
        try:
            subprocess.run([doxygen, "-g", path], capture_output=True, check=True)
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except (OSError, subprocess.CalledProcessError):
            return None
    tags = {m.group(1) for m in map(_TAG_RE.match, text.splitlines()) if m}
    return tags or None


def drop_unsupported(text: str, tags: set[str] | None) -> tuple[str, list[str]]:
    """Remove every assignment to a tag the installed Doxygen does not know.

    Continuation lines (a trailing backslash) are removed with their tag.

    :param text: a Doxyfile.
    :param tags: the supported tags, or ``None`` to leave ``text`` unchanged.
    :returns: the filtered text and the names of the removed tags.
    """
    if not tags:
        return text, []
    kept: list[str] = []
    removed: list[str] = []
    skipping = False
    for line in text.splitlines(keepends=True):
        if skipping:
            skipping = line.rstrip().endswith("\\")
            continue
        match = _TAG_RE.match(line)
        if match and match.group(1) not in tags:
            removed.append(match.group(1))
            skipping = line.rstrip().endswith("\\")
            continue
        kept.append(line)
    return "".join(kept), sorted(set(removed))
