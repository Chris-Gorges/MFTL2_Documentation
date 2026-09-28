#!/usr/bin/env python3
"""
MFTL Manual Build Script (MkDocs / Material)
============================================

Builds the MFTL manual as a modern static site: MkDocs with the Material theme
for the prose, mkdoxy for the API reference, and the full Doxygen HTML manual
mounted inside the result at ``/doxygen/`` so there is one artefact and one URL.

This repository holds no C source. The library it documents is a separate
checkout -- found by ``mftl_paths.resolve()`` from ``--source-dir``,
``$MFTL_SOURCE_DIR``, ``mftl-source.txt`` or a sibling directory -- and the
answer is exported to every subprocess, so the Doxygen pass, the hooks and the
page generator all read the same tree.

Nothing about the site is a second copy of anything. The guide pages, the eleven
module theory chapters and the measurement document are generated at
build time from ``pages/*.md`` here and ``src/<module>/README.md`` /
``docs/analysis.md`` in the library -- the same files Doxygen reads -- by
``mkdocs/gen_pages.py``. The API reference is generated from Doxygen XML using
a Doxyfile derived from ``doxygen/Doxyfile.in``, so both manuals extract the
same symbols with the same aliases.

The Python toolchain is kept in a private virtual environment (``.venv-docs``)
rather than in the system interpreter, for the reason the library's
``build_all.py`` always recreates ``build/``: a documentation dependency must
never be able to change what the library build does. Since the split it cannot
even be installed next to it.

To just LOOK at the manual, ``python3 view_manual.py`` is the one command: it
checks every prerequisite, builds only when something changed and serves the
result. This script is the builder underneath it.

Usage:
    python3 build_mkdocs.py [options]

Options:
    --source-dir DIR Path to the MFTL library checkout.
    --serve          Run the live-reload development server instead of building.
    --port N         Port to serve on (default: 8000, or the next free one).
    --open           Open the result in the browser -- once the server answers,
                     not before. After a plain build the site is served over
                     HTTP for this, because its directory links do not work
                     from file://.
    --strict         Fail on any warning, from Doxygen and from MkDocs alike.
    --no-doxygen     Skip the Doxygen HTML pass; /doxygen/ keeps whatever is
                     already in build/docs/html (or a placeholder page).
    --no-graphs      Pass --no-graphs to the Doxygen pass. Much faster while
                     editing prose; loses the call and include graphs.
    --site-dir DIR   Write the site somewhere other than build/site.
    --reinstall      Re-install the documentation toolchain into .venv-docs.
    --quiet          Suppress progress chatter.

Examples:
    python3 build_mkdocs.py                 # build the whole site
    python3 build_mkdocs.py --serve --open  # write prose, watch it reload
    python3 build_mkdocs.py --strict        # what CI should run
    python3 build_mkdocs.py --serve --no-doxygen --no-graphs   # fastest loop
    python3 build_mkdocs.py --source-dir ~/git/MFTL2
"""

import argparse
import functools
import http.server
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import doxyconf  # noqa: E402
import mftl_paths  # noqa: E402

DOCS_ROOT = mftl_paths.docs_root()
VENV_DIR = os.path.join(DOCS_ROOT, ".venv-docs")
REQUIREMENTS = os.path.join(DOCS_ROOT, "requirements-docs.txt")
REQUIREMENTS_LOCK = os.path.join(DOCS_ROOT, "requirements-docs.lock")
CONFIG = os.path.join(DOCS_ROOT, "mkdocs.yml")
DEFAULT_SITE_DIR = os.path.join(DOCS_ROOT, "build", "site")

#: How many ports above the requested one ``--serve`` tries before giving up.
#: Port 8000 is the default of half the development servers in existence
#: (uvicorn, Django, ``python -m http.server``), so "the port is taken" is the
#: normal case on a developer machine, not an edge case.
PORT_SEARCH_SPAN = 50

#: Library trees `mkdocs serve` must watch.  They cannot go in ``mkdocs.yml``'s
#: `watch:` list, which is read before anything has resolved where the library
#: is, so they are passed as ``mkdocs serve -w`` arguments instead.
SOURCE_WATCH = (
    "include",
    "src",
    os.path.join("docs", "analysis.md"),
)

#: Import names that prove the toolchain is present, and the distribution each
#: comes from -- reported when one is missing so the fix is one pip install.
REQUIRED_IMPORTS = {
    "mkdocs": "mkdocs",
    "material": "mkdocs-material",
    "mkdoxy": "mkdoxy",
    "mkdocs_gen_files": "mkdocs-gen-files",
    "mkdocs_print_site_plugin": "mkdocs-print-site-plugin",
}

#: Oldest interpreter the pinned toolchain supports.
MIN_PYTHON = (3, 9)


def check_python():
    """Exit with a clear message on an interpreter the toolchain cannot run on.

    :returns: nothing.
    """
    if sys.version_info < MIN_PYTHON:
        want = ".".join(map(str, MIN_PYTHON))
        print(f"Error: Python {want} or newer is required (this is {sys.version.split()[0]}).", file=sys.stderr)
        sys.exit(1)


def venv_python(venv_dir):
    """Return the interpreter inside a virtual environment.

    :param venv_dir: root of the virtual environment.
    :returns: absolute path to its ``python`` executable.
    """
    if os.name == "nt":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def missing_imports(python):
    """Report which parts of the documentation toolchain an interpreter lacks.

    The probe runs in a neutral directory: ``python -c`` puts the working
    directory on ``sys.path``, and this repository's own ``mkdocs/`` folder is
    importable from here as a namespace package -- so, probed from here, MkDocs
    always looks installed.

    :param python: path to the interpreter to probe.
    :returns: list of distribution names that are not importable.
    """
    script = "import importlib.util as u,sys;print(' '.join(n for n in sys.argv[1:] if u.find_spec(n) is None))"
    try:
        out = subprocess.run(
            [python, "-c", script, *REQUIRED_IMPORTS],
            capture_output=True, text=True, check=True, cwd=tempfile.gettempdir(),
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return list(REQUIRED_IMPORTS.values())
    return [REQUIRED_IMPORTS[name] for name in out]


def interpreter_runs(python):
    """Report whether an interpreter exists and actually starts.

    A virtual environment's ``python`` is a symlink to the interpreter that
    created it, so upgrading that interpreter (``brew upgrade python``) leaves a
    dangling link behind: the file test fails, or it passes and the process
    cannot start. Only running it tells the two apart from a working one.

    :param python: path to the interpreter.
    :returns: ``True`` when ``python -c pass`` succeeds.
    """
    try:
        return subprocess.run([python, "-c", "pass"], capture_output=True).returncode == 0
    except OSError:
        return False


def create_environment():
    """Create (or re-create) ``.venv-docs``, explaining the usual failure.

    :returns: path to the new environment's interpreter.
    """
    stale = os.path.isdir(VENV_DIR)
    what = "Re-creating the broken" if stale else "Creating the"
    print(f"{what} documentation environment in {os.path.relpath(VENV_DIR, DOCS_ROOT)} ...")
    command = [sys.executable, "-m", "venv", VENV_DIR]
    if stale:
        command.insert(3, "--clear")
    try:
        subprocess.check_call(command)
    except (OSError, subprocess.CalledProcessError):
        minor = f"{sys.version_info.major}.{sys.version_info.minor}"
        print("Error: could not create a Python virtual environment.", file=sys.stderr)
        print("  Debian/Ubuntu ship `venv` separately:", file=sys.stderr)
        print(f"    sudo apt-get install python3-venv   (or python{minor}-venv)", file=sys.stderr)
        print(f"  then re-run. Or delete {VENV_DIR} and try again.", file=sys.stderr)
        sys.exit(1)
    return venv_python(VENV_DIR)


def install_toolchain(python, quiet):
    """Install ``requirements-docs.txt``, pinned to the known-good versions if possible.

    ``requirements-docs.lock`` fixes every package, transitive ones included, at
    the versions the manual was last checked with, so a new machine renders the
    same site as the last one that worked. The pins can be unsatisfiable on an
    older Python or an unusual platform, and then the looser requirements alone
    are the right answer rather than a failure.

    :param python: interpreter of the environment to install into.
    :param quiet: suppress pip's progress output.
    :returns: nothing; exits when not even the loose requirements install.
    """
    pip = [python, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check"]
    if quiet:
        pip.append("--quiet")
    try:
        subprocess.check_call(pip + ["pip"])
    except subprocess.CalledProcessError:
        pass  # an old pip still installs everything below; only its warnings differ
    if os.path.isfile(REQUIREMENTS_LOCK):
        try:
            subprocess.check_call(pip + ["-r", REQUIREMENTS, "-c", REQUIREMENTS_LOCK])
            return
        except subprocess.CalledProcessError:
            print("Note: the known-good versions in requirements-docs.lock do not install here;")
            print("      falling back to the newest compatible ones from requirements-docs.txt.")
    try:
        subprocess.check_call(pip + ["-r", REQUIREMENTS])
    except subprocess.CalledProcessError:
        print("Error: installing the documentation toolchain failed (is there network access?).", file=sys.stderr)
        print("  Behind a proxy: export HTTPS_PROXY=http://proxy:port and re-run.", file=sys.stderr)
        print(f"  Or install by hand: {python} -m pip install -r {REQUIREMENTS}", file=sys.stderr)
        sys.exit(1)


def ensure_environment(reinstall, quiet):
    """Create ``.venv-docs`` if needed and install the toolchain into it.

    The interpreter running this script is used directly when it already has
    everything, so a system-wide or Conda installation is not duplicated.

    :param reinstall: install even when the environment already satisfies the
        requirements.
    :param quiet: suppress pip's progress output.
    :returns: path to the interpreter the documentation should be built with.
    """
    if not reinstall and not missing_imports(sys.executable):
        return sys.executable

    python = venv_python(VENV_DIR)
    if not interpreter_runs(python):
        python = create_environment()

    needed = missing_imports(python)
    if reinstall or needed:
        if needed and not reinstall:
            print(f"Installing the documentation toolchain ({', '.join(needed)}) -- once, needs network ...")
        install_toolchain(python, quiet)

    still_missing = missing_imports(python)
    if still_missing:
        print(f"Error: could not install {', '.join(still_missing)}.", file=sys.stderr)
        print(f"  Try: {python} -m pip install -r {REQUIREMENTS}", file=sys.stderr)
        sys.exit(1)
    return python


def build_doxygen(source_root, strict, graphs, quiet, clean=False):
    """Run the Doxygen HTML pass that the site mounts at ``/doxygen/``.

    Delegated to ``build_docs.py`` rather than reimplemented, so the embedded
    manual is byte-for-byte the one a reader gets from that script.

    :param source_root: root of the MFTL library checkout.
    :param strict: treat Doxygen warnings as errors.
    :param graphs: generate the Graphviz call and include graphs.
    :param quiet: suppress Doxygen's progress output.
    :param clean: delete the previous output first, so no stale page survives.
    :returns: nothing; exits non-zero if the pass fails.
    """
    if doxyconf.find_doxygen() is None:
        print("Warning: Doxygen not found on PATH or in $DOXYGEN -- skipping the embedded manual.")
        print("         macOS: brew install doxygen graphviz")
        return

    command = [sys.executable, os.path.join(DOCS_ROOT, "build_docs.py"), "--source-dir", source_root]
    if strict:
        command.append("--strict")
    if not graphs:
        command.append("--no-graphs")
    if quiet:
        command.append("--quiet")
    if clean:
        command.append("--clean")
    status = subprocess.call(command, cwd=DOCS_ROOT)
    if status != 0:
        print("\nError: the Doxygen pass failed (see its output above).", file=sys.stderr)
        sys.exit(status)


def run_mkdocs(python, source_root, arguments, quiet, config=CONFIG):
    """Invoke MkDocs with the environment the site expects.

    The resolved library path is exported rather than passed: the hooks and the
    page generator run inside MkDocs, not on this command line, and they must
    not repeat the search and risk a different answer.

    :param python: interpreter to run MkDocs with.
    :param source_root: root of the MFTL library checkout.
    :param arguments: MkDocs sub-command and its options.
    :param quiet: suppress MkDocs' informational output.
    :param config: the MkDocs configuration file (default: ``mkdocs.yml``).
    :returns: the process' exit status.
    """
    env = dict(os.environ)
    # Notices about MkDocs 2.0, printed on every run by Material and by a
    # transitive dependency of mkdocs-gen-files. requirements-docs.txt keeps
    # MkDocs below 2.0, so neither applies here.
    env["NO_MKDOCS_2_WARNING"] = "true"
    env["DISABLE_MKDOCS_2_WARNING"] = "true"
    env[mftl_paths.ENV_VAR] = source_root

    command = [python, "-m", "mkdocs", *arguments, "--config-file", config]
    if quiet:
        command.append("--quiet")
    return subprocess.call(command, cwd=DOCS_ROOT, env=env)


def port_is_free(port, host="127.0.0.1"):
    """Report whether a TCP port can be bound right now.

    :param port: the port to test.
    :param host: the interface the server will bind.
    :returns: ``True`` when nothing is listening on it.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def find_free_port(preferred, host="127.0.0.1"):
    """Return ``preferred`` if it is free, else the next free port above it.

    ``mkdocs serve`` only discovers a taken port AFTER building the whole site,
    and until this check existed ``--open`` pointed the browser at whatever
    else was listening there -- on the machine this was written on, another
    project's web API. Checking first turns both into a one-line note.

    :param preferred: the port asked for.
    :param host: the interface the server will bind.
    :returns: a port that was free at the time of the check.
    :raises SystemExit: when no port in the search span is free.
    """
    for port in range(preferred, preferred + PORT_SEARCH_SPAN):
        if port_is_free(port, host):
            if port != preferred:
                print(f"Note: port {preferred} is in use by another program; using {port} instead.")
            return port
    print(f"Error: ports {preferred}-{preferred + PORT_SEARCH_SPAN - 1} are all in use; pass --port.", file=sys.stderr)
    sys.exit(1)


def open_when_ready(url, timeout=1800.0):
    """Open ``url`` in the browser as soon as the MFTL site answers there.

    Runs in a daemon thread next to ``mkdocs serve``, which builds the entire
    site before it binds its socket -- 20 s with a warm Doxygen cache, minutes
    on a first run. Opening the browser on a timer shows a connection error for
    all of that time. The page must also be OURS (MkDocs puts its name in the
    ``generator`` meta tag), not merely a 200 from something else on the port.

    :param url: the address ``mkdocs serve`` was told to listen on.
    :param timeout: seconds to keep polling before giving up silently.
    :returns: nothing.
    """
    def poll():
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if b"mkdocs" in response.read(4096).lower():
                        print(f"\n  The manual is ready: {url}\n", flush=True)
                        webbrowser.open(url)
                        return
            except OSError:
                pass
            time.sleep(0.5)

    threading.Thread(target=poll, daemon=True).start()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Static file handler that does not log every request to the terminal."""

    def log_message(self, format, *args):  # noqa: A002 -- the base class' name
        """Discard the per-request access log.

        :param format: printf-style format of the message.
        :param args: its arguments.
        :returns: nothing.
        """


def serve_static(site_dir, preferred_port=8000, open_browser=True):
    """Serve a BUILT site over HTTP until Ctrl-C, and point the browser at it.

    The site is built with ``use_directory_urls``, so every link ends in a
    directory (``guide/``), which a ``file://`` browser cannot resolve to its
    ``index.html``: opened from disk, the landing page renders and every link
    after it is dead. Material's instant navigation and search need HTTP too.
    The export in ``prebuilt/`` is the one variant made for ``file://``.

    Unlike ``mkdocs serve`` this rebuilds nothing, so it is up in well under a
    second; ``build_mkdocs.py --serve`` is the live-reload route for authors.

    :param site_dir: the directory ``mkdocs build`` wrote.
    :param preferred_port: first port to try; the next free one is used if taken.
    :param open_browser: open the default browser once the server listens.
    :returns: nothing; returns when interrupted.
    """
    handler = functools.partial(QuietHandler, directory=site_dir)
    port = find_free_port(preferred_port)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"\n  The manual is being served at  {url}")
    print("  Press Ctrl-C to stop the server.\n", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


def main():
    """Parse the command line and drive the two passes.

    :returns: nothing; exits with the status of the MkDocs run.
    """
    parser = argparse.ArgumentParser(
        description="Generate the MFTL manual as a MkDocs Material site.",
        epilog="Example: python3 build_mkdocs.py --serve --open",
    )
    mftl_paths.add_argument(parser)
    parser.add_argument("--serve", action="store_true",
                        help="run the live-reload development server instead of building")
    parser.add_argument("--port", type=int, default=8000,
                        help="port to serve on (default: 8000, or the next free one)")
    parser.add_argument("--open", dest="open_browser", action="store_true",
                        help="open the result in the browser, served over HTTP")
    parser.add_argument("--strict", action="store_true",
                        help="fail on any warning, from Doxygen and from MkDocs alike")
    parser.add_argument("--no-doxygen", dest="doxygen", action="store_false",
                        help="skip the Doxygen HTML pass mounted at /doxygen/")
    parser.add_argument("--no-graphs", dest="graphs", action="store_false",
                        help="skip Graphviz in the Doxygen pass; much faster")
    parser.add_argument("--site-dir", default=None,
                        help="output directory (default: build/site)")
    parser.add_argument("--reinstall", action="store_true",
                        help="re-install the documentation toolchain into .venv-docs")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress progress output")
    args = parser.parse_args()

    check_python()
    site_dir = os.path.abspath(args.site_dir or DEFAULT_SITE_DIR)
    source_root = mftl_paths.resolve(args.source_dir)
    python = ensure_environment(args.reinstall, args.quiet)

    if not args.quiet:
        print("-------------------------------------------------")
        print("MFTL Manual Build (MkDocs / Material)")
        print("-------------------------------------------------")
        print(f"Interpreter      : {python}")
        print(f"Library sources  : {source_root}")
        print(f"Documentation    : {DOCS_ROOT}")
        print(f"Doxygen pass     : {'yes' if args.doxygen else 'skipped'}"
              f"{'' if args.graphs else ' (no graphs)'}")
        print(f"Output Directory : {site_dir}")
        print(f"Mode             : {'serve' if args.serve else 'build'}")
        print(f"Strict           : {'yes' if args.strict else 'no'}")
        print("-------------------------------------------------", flush=True)

    if args.doxygen:
        build_doxygen(source_root, args.strict, args.graphs, args.quiet)

    if args.serve:
        port = find_free_port(args.port)
        url = f"http://127.0.0.1:{port}/"
        arguments = ["serve", "--dev-addr", f"127.0.0.1:{port}"]
        for relative in SOURCE_WATCH:
            target = os.path.join(source_root, relative)
            if os.path.exists(target):
                arguments += ["--watch", target]
        if args.strict:
            arguments.append("--strict")
        print(f"Building the site, then serving it on {url} -- Ctrl-C to stop.", flush=True)
        if args.open_browser:
            # The server blocks and builds everything before it listens, so
            # the browser is opened from a thread once the site answers.
            open_when_ready(url)
        try:
            sys.exit(run_mkdocs(python, source_root, arguments, args.quiet))
        except KeyboardInterrupt:
            sys.exit(0)

    arguments = ["build", "--site-dir", site_dir]
    if args.strict:
        arguments.append("--strict")
    status = run_mkdocs(python, source_root, arguments, args.quiet)
    if status != 0:
        print("\nError: the MkDocs build failed.", file=sys.stderr)
        sys.exit(status)

    index = os.path.join(site_dir, "index.html")
    if not args.quiet:
        print("\nManual built.")
        print(f"  Site           : {index}")
        print(f"  Doxygen manual : {os.path.join(site_dir, 'doxygen', 'index.html')}")
        if not args.open_browser:
            print("\n  Look at it with:  python3 view_manual.py --no-build")

    if args.open_browser and os.path.isfile(index):
        serve_static(site_dir, args.port)


if __name__ == "__main__":
    main()
