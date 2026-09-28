#!/usr/bin/env python3
"""
MFTL Documentation Build Script
===============================

Generates the Doxygen manual from a checkout of the MFTL library, WITHOUT going
through CMake -- so documentation can be regenerated without touching either
repository's build directory and without any risk of slowing down the library's
edit-compile-test cycle.

This script lives in MFTL2_Documentation and the sources live in MFTL2, so
there are two roots. ``mftl_paths.resolve()`` finds the library (``--source-dir``,
``$MFTL_SOURCE_DIR``, ``mftl-source.txt``, or a sibling checkout) and both are
substituted into the single template ``doxygen/Doxyfile.in``. The CMake route
(``cmake -S . -B build && cmake --build build --target docs``, from THIS
repository) exists too and substitutes the same two placeholders into the same
template, so the routes cannot drift apart.

Usage:
    python3 build_docs.py [options]

Options:
    --source-dir DIR Path to the MFTL library checkout.
    --open           Open the generated index.html in the default browser.
    --strict         Fail (non-zero exit) if Doxygen emitted any warning.
    --no-graphs      Skip Graphviz. Much faster; loses the call/caller graphs.
    --latex          Additionally emit LaTeX sources for a PDF.
    --output-dir DIR Write the manual somewhere other than build/docs.
    --clean          Delete the previous output first. Doxygen never removes a
                     page it no longer generates, so a renamed symbol leaves its
                     old page behind; incremental runs are faster (the graph
                     cache survives). export_manual.py always cleans.
    --quiet          Suppress Doxygen's progress chatter.

Examples:
    python3 build_docs.py                 # build the HTML manual
    python3 build_docs.py --open          # ... and look at it
    python3 build_docs.py --strict        # treat documentation warnings as errors
    python3 build_docs.py --no-graphs     # quick pass while editing prose
    python3 build_docs.py --source-dir ~/git/MFTL2
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import doxyconf  # noqa: E402
import mftl_paths  # noqa: E402

#: Root of THIS repository -- the documentation machinery and prose.
DOCS_ROOT = mftl_paths.docs_root()

#: The one template both build routes substitute into.
DOXYFILE_IN = os.path.join(DOCS_ROOT, "doxygen", "Doxyfile.in")


INSTALL_HINT = (
    "  macOS  : brew install doxygen graphviz\n"
    "  Debian : sudo apt-get install doxygen graphviz\n"
    "  Fedora : sudo dnf install doxygen graphviz\n"
    "  Windows: winget install DimitriVanHeesch.Doxygen Graphviz.Graphviz\n"
    "  or set $DOXYGEN to the executable."
)


def find_doxygen():
    """Locate Doxygen, or explain how to get it and exit.

    :returns: absolute path to the executable.
    """
    path = doxyconf.find_doxygen()
    if path:
        return path
    print("Error: Doxygen not found (looked at $DOXYGEN and PATH).", file=sys.stderr)
    print(INSTALL_HINT, file=sys.stderr)
    sys.exit(1)


def configure_doxyfile(doxygen, source_root, output_dir, have_dot, dot_path, want_latex):
    """Substitute the @PLACEHOLDER@ tokens of Doxyfile.in and write the result.

    This is deliberately the same substitution CMake's configure_file() performs,
    so the two build routes cannot drift apart. Tags the installed Doxygen does
    not support are then dropped (see :mod:`doxyconf`), so an obsolete or a
    not-compiled-in option costs no configuration warning.

    :param doxygen: the Doxygen executable the file is written for.
    :param source_root: root of the MFTL library checkout.
    :param output_dir: where the manual is written.
    :param have_dot: whether Graphviz is available.
    :param dot_path: directory holding ``dot``, or ``""``.
    :param want_latex: also emit LaTeX sources.
    :returns: path of the generated Doxyfile.
    """
    if not os.path.isfile(DOXYFILE_IN):
        print(f"Error: template not found: {DOXYFILE_IN}", file=sys.stderr)
        sys.exit(1)

    with open(DOXYFILE_IN, encoding="utf-8") as fh:
        text = fh.read()

    substitutions = {
        "MFTL_VERSION": mftl_paths.project_version(source_root),
        "MFTL_DOCS_SOURCE_DIR": source_root,
        "MFTL_DOCS_DIR": DOCS_ROOT,
        "MFTL_DOCS_OUTPUT_DIR": output_dir,
        "MFTL_DOCS_HAVE_DOT": "YES" if have_dot else "NO",
        "MFTL_DOCS_DOT_PATH": dot_path or "",
        **mftl_paths.measurement_substitutions(source_root, DOCS_ROOT),
    }
    for key, value in substitutions.items():
        text = text.replace(f"@{key}@", value)

    leftovers = re.findall(r"@[A-Z_][A-Z0-9_]*@", text)
    if leftovers:
        print(f"Error: unsubstituted placeholders: {sorted(set(leftovers))}", file=sys.stderr)
        sys.exit(1)

    if want_latex:
        text = text.replace("GENERATE_LATEX         = NO", "GENERATE_LATEX         = YES")

    text, dropped = doxyconf.drop_unsupported(text, doxyconf.supported_tags(doxygen))
    if dropped:
        print(f"Note: this Doxygen does not support {', '.join(dropped)}; dropped from the configuration.")

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "Doxyfile")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return out_path


def summarise_warnings(log_path):
    """Return (count, first_lines) for the Doxygen warning log.

    :param log_path: path of ``doxygen-warnings.log``.
    :returns: the number of warning lines and the lines themselves.
    """
    if not os.path.isfile(log_path):
        return 0, []
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    return len(lines), lines


def main():
    """Parse the command line and run the Doxygen pass.

    :returns: nothing; exits non-zero on failure or on ``--strict`` warnings.
    """
    parser = argparse.ArgumentParser(
        description="Generate the MFTL Doxygen manual.",
        epilog="Example: python3 build_docs.py --open",
    )
    mftl_paths.add_argument(parser)
    parser.add_argument("--open", dest="open_browser", action="store_true",
                        help="open the generated manual when it is ready")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero if Doxygen emitted any warning")
    parser.add_argument("--no-graphs", dest="graphs", action="store_false",
                        help="skip Graphviz; much faster, loses the call graphs")
    parser.add_argument("--latex", action="store_true",
                        help="also emit LaTeX sources for a PDF")
    parser.add_argument("--output-dir", default=None,
                        help="output directory (default: build/docs)")
    parser.add_argument("--clean", action="store_true",
                        help="delete the previous HTML/LaTeX output first (no stale pages)")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress Doxygen's progress output")
    args = parser.parse_args()

    source_root = mftl_paths.resolve(args.source_dir)

    output_dir = args.output_dir or os.path.join(DOCS_ROOT, "build", "docs")
    output_dir = os.path.abspath(output_dir)

    doxygen = find_doxygen()
    note = doxyconf.version_note(doxygen)
    if note:
        print(f"Warning: {note}")

    dot_path = ""
    have_dot = False
    if args.graphs:
        dot_exe = shutil.which("dot")
        if dot_exe:
            have_dot = True
            dot_path = os.path.dirname(dot_exe)
        else:
            print("Warning: Graphviz 'dot' not found -- call graphs will be omitted.")
            print("         brew install graphviz   /   sudo apt-get install graphviz")

    print("-------------------------------------------------")
    print("MFTL Documentation Build")
    print("-------------------------------------------------")
    found = doxyconf.version(doxygen)
    print(f"Doxygen          : {doxygen} ({'.'.join(map(str, found)) if found else 'version unknown'})")
    print(f"Library sources  : {source_root}")
    print(f"Documentation    : {DOCS_ROOT}")
    print(f"Graphviz (dot)   : {'yes -- ' + dot_path if have_dot else 'no (graphs disabled)'}")
    print(f"Output Directory : {output_dir}")
    print(f"LaTeX            : {'yes' if args.latex else 'no'}")
    print(f"Strict           : {'yes' if args.strict else 'no'}")
    print("-------------------------------------------------", flush=True)

    if args.clean:
        for generated in ("html", "latex"):
            shutil.rmtree(os.path.join(output_dir, generated), ignore_errors=True)
    for generated in ("html", "latex"):
        if mftl_paths.invalidate_on_measurement_change(os.path.join(output_dir, generated), source_root):
            print(f"Note: the measurements came or went since the last run; cleared {generated}/ so no stale page survives.")

    doxyfile = configure_doxyfile(doxygen, source_root, output_dir, have_dot, dot_path, args.latex)

    stdout = subprocess.DEVNULL if args.quiet else None
    try:
        subprocess.check_call([doxygen, doxyfile], cwd=DOCS_ROOT, stdout=stdout)
    except subprocess.CalledProcessError as exc:
        print(f"\nError: Doxygen failed with exit code {exc.returncode}.", file=sys.stderr)
        sys.exit(1)

    log_path = os.path.join(output_dir, "doxygen-warnings.log")
    n_warnings, warning_lines = summarise_warnings(log_path)

    index = os.path.join(output_dir, "html", "index.html")
    print("\nDocumentation built.")
    print(f"  Manual   : {index}")
    print(f"  Warnings : {n_warnings}" + (f"  ({log_path})" if n_warnings else ""))

    if n_warnings:
        for line in warning_lines[:25]:
            print(f"    {line}")
        if n_warnings > 25:
            print(f"    ... and {n_warnings - 25} more, see {log_path}")

    if args.open_browser and os.path.isfile(index):
        webbrowser.open(f"file://{index}")

    if args.strict and n_warnings:
        print(f"\nError: --strict and {n_warnings} Doxygen warning(s).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
