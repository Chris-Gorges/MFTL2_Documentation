#!/usr/bin/env python3
"""
View the MFTL2 manual -- one command, from a fresh clone to the browser
=======================================================================

    python3 view_manual.py

does everything below in order, and stops at the first thing it cannot fix
with a message that says exactly what to type:

1. Python     3.9 or newer -- the interpreter running this script.
2. Doxygen    1.9.7 or newer, on PATH or in $DOXYGEN; and Graphviz's ``dot``,
   Graphviz   proven able to render SVG (the call, caller and include graphs).
3. Library    the MFTL2 checkout the manual is generated from, normally the
              sibling directory ../MFTL2. Offers to clone it when missing.
4. Toolchain  MkDocs, Material and mkdoxy, installed ONCE into the private
              .venv-docs (network needed that one time).
5. Build      the Doxygen manual with all graphs, then the site around it.
              Skipped when nothing has changed since the last build, so the
              second run is up in a second.
6. Verify     that the result is complete: pages, theory figures, API
              reference, Doxygen manual, graphs, search index.
7. Serve      over HTTP on 127.0.0.1 -- port 8000, or the next free one -- and
              open the browser. Ctrl-C stops it.

Doxygen and Graphviz are system packages. When one is missing, the script
names the install command for this machine and offers to run it; nothing is
installed without a yes (or ``--yes``).

Usage:
    python3 view_manual.py [options]

Options:
    --check          Only report what is present and what is missing; change nothing.
    --no-build       Serve the site that is already in build/site.
    --rebuild        Build even when the site looks up to date.
    --clean          Delete build/ first and build everything from scratch.
    --no-graphs      Skip Graphviz: much faster, no call/include graphs.
    --live           Live-reload server for writing prose (build_mkdocs.py --serve).
    --prebuilt       Open the committed offline copy in prebuilt/ -- needs nothing.
    --port N         First port to try (default: 8000).
    --no-open        Do not open the browser; just print the address.
    --source-dir DIR The MFTL2 checkout, if it is not the sibling ../MFTL2.
    --yes            Answer yes to every offer (install a package, clone the library).
    --verbose        Show the full Doxygen and MkDocs output.

Examples:
    python3 view_manual.py                # the whole manual, in the browser
    python3 view_manual.py --check        # what would I have to install?
    python3 view_manual.py --clean        # something looks stale: start over
    python3 view_manual.py --prebuilt     # no toolchain at all
"""

import sys

MIN_PYTHON = (3, 9)
if sys.version_info < MIN_PYTHON:  # before anything a newer Python is needed for
    sys.stderr.write(
        "Error: Python %d.%d or newer is required; this is %s.\n"
        "  Install a newer Python (python.org, Homebrew, apt, conda) and run it as\n"
        "  python3.X view_manual.py\n" % (MIN_PYTHON + (sys.version.split()[0],))
    )
    sys.exit(1)

import argparse  # noqa: E402
import glob  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import webbrowser  # noqa: E402
from pathlib import Path  # noqa: E402

DOCS_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DOCS_ROOT)

import build_mkdocs  # noqa: E402
import doxyconf  # noqa: E402
import mftl_paths  # noqa: E402

#: Where the library lives, for the clone offer. The manual documents the
#: layout on this branch; switch the default to ``main`` once it is merged.
LIBRARY_URL = "https://git.multiflow.org/software/MFTL2.git"
LIBRARY_BRANCH = "christian"
LIBRARY_DIRNAME = mftl_paths.SIBLING_NAMES[0]

BUILD_DIR = os.path.join(DOCS_ROOT, "build")
SITE_DIR = build_mkdocs.DEFAULT_SITE_DIR
PREBUILT_INDEX = os.path.join(DOCS_ROOT, "prebuilt", "html", "index.html")

#: Written into the site after a successful build; what the next run compares
#: against to decide whether anything has to be rebuilt.
STAMP = os.path.join(SITE_DIR, ".view-manual-stamp.json")

#: Everything a build reads, per repository. A file newer than the stamp in
#: any of these means the site is stale.
DOCS_INPUTS = (
    "mkdocs.yml", "requirements-docs.txt", "requirements-docs.lock", "mftl_paths.py", "doxyconf.py",
    "build_docs.py", "build_mkdocs.py", "pages", "manual", "mkdocs", "doxygen", "images",
)
LIBRARY_INPUTS = ("CMakeLists.txt", "include", "src", "docs")

#: Doxygen's graph files: call, caller, include, included-by and directory graphs.
GRAPH_FILE = re.compile(r"(_cgraph|_icgraph|__incl|__dep__incl|_dep)(_org)?\.svg$")

#: Package names per package manager, and whether its install needs sudo.
INSTALLERS = {
    "brew": ("brew install {}", {"doxygen": "doxygen", "graphviz": "graphviz"}),
    "apt-get": ("sudo apt-get install -y {}", {"doxygen": "doxygen", "graphviz": "graphviz"}),
    "dnf": ("sudo dnf install -y {}", {"doxygen": "doxygen", "graphviz": "graphviz"}),
    "yum": ("sudo yum install -y {}", {"doxygen": "doxygen", "graphviz": "graphviz"}),
    "pacman": ("sudo pacman -S --needed {}", {"doxygen": "doxygen", "graphviz": "graphviz"}),
    "zypper": ("sudo zypper install -y {}", {"doxygen": "doxygen", "graphviz": "graphviz"}),
    "winget": ("winget install --exact --id {}", {"doxygen": "DimitriVanHeesch.Doxygen", "graphviz": "Graphviz.Graphviz"}),
}

TOTAL_STEPS = 7


# ──────────────────────────────────────────────────────────────────────────────
#  Output
# ──────────────────────────────────────────────────────────────────────────────

def step(number, title):
    """Print the heading of one numbered step.

    :param number: the step's position, 1-based.
    :param title: what the step checks or does.
    :returns: nothing.
    """
    print(f"\n[{number}/{TOTAL_STEPS}] {title}", flush=True)


def good(text):
    """Print a line reporting something that is in order.

    :param text: the finding.
    :returns: nothing.
    """
    print(f"      ok       {text}", flush=True)


def bad(text):
    """Print a line reporting something that is missing or wrong.

    :param text: the finding.
    :returns: nothing.
    """
    print(f"      MISSING  {text}", flush=True)


def note(text):
    """Print an indented explanatory line.

    :param text: the explanation.
    :returns: nothing.
    """
    print(f"               {text}", flush=True)


def die(message, *hints):
    """Stop with an error and the commands that fix it.

    :param message: what went wrong.
    :param hints: lines to print under it, typically commands.
    :returns: never; exits with status 1.
    """
    print(f"\nError: {message}", file=sys.stderr)
    for hint in hints:
        print(f"  {hint}", file=sys.stderr)
    sys.exit(1)


def confirm(question, assume_yes):
    """Ask a yes/no question; default yes. Never blocks a non-interactive run.

    :param question: the question, without the ``[Y/n]`` suffix.
    :param assume_yes: answer yes without asking (``--yes``).
    :returns: ``True`` for yes.
    """
    if assume_yes:
        print(f"      {question} [Y/n] y   (--yes)")
        return True
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(f"      {question} [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("", "y", "yes", "j", "ja")


def run_visible(command, cwd=None):
    """Run a command the user agreed to, showing its output.

    :param command: argument list.
    :param cwd: working directory, or ``None``.
    :returns: ``True`` when it exited with status 0.
    """
    print(f"      $ {' '.join(command)}", flush=True)
    try:
        return subprocess.call(command, cwd=cwd) == 0
    except OSError as error:
        print(f"      could not run it: {error}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
#  System packages: Doxygen and Graphviz
# ──────────────────────────────────────────────────────────────────────────────

def package_manager():
    """Name the package manager this machine installs Doxygen and Graphviz with.

    :returns: a key of :data:`INSTALLERS`, or ``None`` when none is found.
    """
    system = platform.system()
    if system == "Darwin":
        return "brew" if shutil.which("brew") else None
    if system == "Windows":
        return "winget" if shutil.which("winget") else None
    for name in ("apt-get", "dnf", "yum", "pacman", "zypper"):
        if shutil.which(name):
            return name
    return None


def install_command(packages):
    """The command that installs the given system packages on this machine.

    :param packages: subset of ``("doxygen", "graphviz")``.
    :returns: the command as a string, or ``None`` when no package manager is known.
    """
    manager = package_manager()
    if manager is None:
        return None
    template, names = INSTALLERS[manager]
    if manager == "winget":  # one package per call
        return " && ".join(template.format(names[p]) for p in packages)
    return template.format(" ".join(names[p] for p in packages))


def print_install_help(packages):
    """Explain how to install missing system packages when no command can be offered.

    :param packages: subset of ``("doxygen", "graphviz")``.
    :returns: nothing.
    """
    command = install_command(packages)
    if command:
        note(f"install:  {command}")
    elif platform.system() == "Darwin":
        note("install Homebrew from https://brew.sh, then:  brew install " + " ".join(packages))
    else:
        note("Doxygen:  https://www.doxygen.nl/download.html")
        note("Graphviz: https://graphviz.org/download/")
    if os.environ.get("CONDA_PREFIX"):
        note("or, in this conda environment:  conda install -c conda-forge " + " ".join(packages))


def offer_install(packages, assume_yes):
    """Offer to install missing system packages, and do it on a yes.

    :param packages: subset of ``("doxygen", "graphviz")``.
    :param assume_yes: answer yes without asking.
    :returns: ``True`` when the installation ran and succeeded.
    """
    command = install_command(packages)
    if command is None or not confirm(f"Install {' and '.join(packages)} now with `{command}`?", assume_yes):
        return False
    return all(run_visible(part.split()) for part in command.split(" && "))


def check_doxygen():
    """Find Doxygen and judge its version.

    :returns: ``(path, version string)``, or ``(None, None)`` when not found.
    """
    path = doxyconf.find_doxygen()
    if path is None:
        return None, None
    found = doxyconf.version(path)
    return path, ".".join(map(str, found)) if found else "unknown version"


def check_graphviz():
    """Find Graphviz and prove it can render the format Doxygen asks for.

    ``dot`` being on PATH is not enough: a Graphviz whose plugin registry was
    never initialised (some conda and source installs) answers ``dot -V`` and
    then refuses ``-Tsvg``, and Doxygen reports that as thousands of warnings.

    :returns: ``(path, problem)`` -- ``problem`` is ``None`` when it works;
        ``(None, None)`` when ``dot`` is not found at all.
    """
    dot = shutil.which("dot")
    if dot is None:
        return None, None
    try:
        result = subprocess.run([dot, "-Tsvg"], input="digraph { a -> b }", capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return dot, str(error)
    if result.returncode != 0 or "<svg" not in result.stdout:
        return dot, (result.stderr.strip().splitlines() or ["cannot render SVG"])[0] + "  (try: sudo dot -c)"
    return dot, None


# ──────────────────────────────────────────────────────────────────────────────
#  The library checkout
# ──────────────────────────────────────────────────────────────────────────────

def git(*arguments, cwd):
    """Run a read-only git query and return its output.

    :param arguments: git arguments.
    :param cwd: the repository to ask.
    :returns: stripped standard output, or ``""`` on any failure.
    """
    try:
        result = subprocess.run(["git", *arguments], cwd=cwd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def describe_checkout(path):
    """Name the branch and commit of a checkout, for the report and the stamp.

    :param path: a directory that may be a git checkout.
    :returns: e.g. ``"branch christian, commit 1a2b3c4"``, or ``"not a git checkout"``.
    """
    commit = git("rev-parse", "--short", "HEAD", cwd=path)
    if not commit:
        return "not a git checkout"
    branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=path) or "detached"
    dirty = " + local changes" if git("status", "--porcelain", "--untracked-files=no", cwd=path) else ""
    return f"branch {branch}, commit {commit}{dirty}"


def find_library(explicit):
    """Resolve the library checkout without exiting, when that is possible.

    A path someone STATED (``--source-dir``, ``$MFTL_SOURCE_DIR``,
    ``mftl-source.txt``) that is not a library tree is left to
    :func:`mftl_paths.resolve`, which explains it and exits -- that answer is
    never second-guessed. Only the sibling scan may come back empty.

    :param explicit: ``--source-dir``, or ``None``.
    :returns: the library root, or ``None`` when only the sibling scan ran and missed.
    """
    for _, path, stated in mftl_paths.candidates(explicit):
        if mftl_paths.is_source_tree(path):
            return path
        if stated:
            return mftl_paths.resolve(explicit)  # prints why, exits
    return None


def library_fix(assume_yes, check_only):
    """Explain -- and on a yes, perform -- what gets the library into place.

    Two situations: the sibling is missing (clone it), or it exists but is a
    checkout of a branch with a different layout (switch it).

    :param assume_yes: answer yes without asking.
    :param check_only: report only; offer nothing.
    :returns: ``True`` when something was done that may have fixed it.
    """
    sibling = os.path.join(os.path.dirname(DOCS_ROOT), LIBRARY_DIRNAME)
    rel = os.path.relpath(sibling, os.getcwd())

    if os.path.isdir(os.path.join(sibling, ".git")):
        where = describe_checkout(sibling)
        bad(f"{sibling} is a git checkout ({where}),")
        note(f"but not of the branch this manual documents ({LIBRARY_BRANCH}).")
        note(f"switch it:  git -C {rel} fetch origin && git -C {rel} switch {LIBRARY_BRANCH}")
        note("or point at another checkout:  python3 view_manual.py --source-dir /path/to/MFTL2")
        if check_only or not confirm(f"Switch {rel} to branch {LIBRARY_BRANCH} now?", assume_yes):
            return False
        return run_visible(["git", "-C", sibling, "fetch", "origin"]) and \
            run_visible(["git", "-C", sibling, "switch", LIBRARY_BRANCH])

    if os.path.exists(sibling):
        bad(f"{sibling} exists but is not an MFTL2 checkout.")
        note("point at the right one:  python3 view_manual.py --source-dir /path/to/MFTL2")
        return False

    bad(f"no library checkout next to this repository (looked for {sibling}).")
    note(f"clone it:  git clone --branch {LIBRARY_BRANCH} {LIBRARY_URL} {rel}")
    note("or point at one elsewhere:  python3 view_manual.py --source-dir /path/to/MFTL2")
    if check_only:
        return False
    if shutil.which("git") is None:
        note("git is not installed, so this script cannot clone it for you.")
        return False
    if not confirm(f"Clone {LIBRARY_URL} (branch {LIBRARY_BRANCH}) into {rel} now?", assume_yes):
        return False
    return run_visible(["git", "clone", "--branch", LIBRARY_BRANCH, LIBRARY_URL, sibling])


# ──────────────────────────────────────────────────────────────────────────────
#  The MkDocs toolchain
# ──────────────────────────────────────────────────────────────────────────────

def toolchain_state():
    """Report whether the Python toolchain is ready, without installing anything.

    :returns: ``(ready, description)``.
    """
    if not build_mkdocs.missing_imports(sys.executable):
        return True, f"in this interpreter ({sys.executable})"
    python = build_mkdocs.venv_python(build_mkdocs.VENV_DIR)
    if build_mkdocs.interpreter_runs(python):
        missing = build_mkdocs.missing_imports(python)
        if not missing:
            return True, f"in {os.path.relpath(build_mkdocs.VENV_DIR, DOCS_ROOT)}/"
        return False, f"{', '.join(missing)} missing from .venv-docs/"
    return False, "not installed yet"


# ──────────────────────────────────────────────────────────────────────────────
#  Build, freshness and verification
# ──────────────────────────────────────────────────────────────────────────────

def newest_input(source_root):
    """Modification time of the most recently changed file a build reads.

    :param source_root: the library checkout.
    :returns: a POSIX timestamp.
    """
    newest = 0.0
    for root, names in ((DOCS_ROOT, DOCS_INPUTS), (source_root, LIBRARY_INPUTS)):
        for name in names:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                newest = max(newest, os.path.getmtime(path))
                continue
            for folder, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
                for file in files:
                    if not file.endswith(".pyc"):
                        newest = max(newest, os.path.getmtime(os.path.join(folder, file)))
    return newest


def read_stamp():
    """Load what the last successful build recorded.

    :returns: the stamp dictionary, or ``{}``.
    """
    try:
        with open(STAMP, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def site_is_current(source_root, graphs):
    """Decide whether build/site already shows the current sources.

    :param source_root: the library checkout.
    :param graphs: whether the build has to include the Graphviz graphs.
    :returns: ``(current, reason)`` -- the reason is printed either way.
    """
    stamp = read_stamp()
    if not stamp or not os.path.isfile(os.path.join(SITE_DIR, "index.html")):
        return False, "no complete build yet"
    if stamp.get("library") != source_root:
        return False, f"last build read a different library ({stamp.get('library')})"
    if graphs and not stamp.get("graphs"):
        return False, "last build had no graphs"
    if stamp.get("measurements") != mftl_paths.has_measurements(source_root):
        return False, f"{mftl_paths.MEASUREMENTS} appeared or disappeared since the last build"
    if newest_input(source_root) > stamp.get("built", 0):
        return False, "sources changed since the last build"
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(stamp["built"]))
    return True, f"up to date (built {when} from {stamp.get('checkout', '?')})"


def build_site(source_root, graphs, verbose):
    """Run the full build (Doxygen, then MkDocs), with a heartbeat while it is silent.

    :param source_root: the library checkout.
    :param graphs: generate the Graphviz graphs.
    :param verbose: show Doxygen's and MkDocs' own output.
    :returns: nothing; exits when the build fails.
    """
    command = [sys.executable, os.path.join(DOCS_ROOT, "build_mkdocs.py"),
               "--source-dir", source_root, "--site-dir", SITE_DIR]
    if not graphs:
        command.append("--no-graphs")
    if not verbose:
        command.append("--quiet")

    started = time.monotonic()
    done = threading.Event()

    def heartbeat():
        while not done.wait(20.0):
            minutes, seconds = divmod(int(time.monotonic() - started), 60)
            print(f"      ... still building ({minutes}m{seconds:02d}s)", flush=True)

    if not verbose:
        threading.Thread(target=heartbeat, daemon=True).start()
    try:
        status = subprocess.call(command, cwd=DOCS_ROOT,
                                 stdout=None if verbose else subprocess.DEVNULL)
    finally:
        done.set()
    if status != 0:
        die("the build failed (see the messages above).",
            "Re-run with --verbose for the full output, or with --clean to start from scratch.")

    with open(STAMP, "w", encoding="utf-8") as handle:
        json.dump({"library": source_root, "checkout": describe_checkout(source_root), "graphs": graphs,
                   "measurements": mftl_paths.has_measurements(source_root), "built": time.time()}, handle, indent=2)
    minutes, seconds = divmod(int(time.monotonic() - started), 60)
    good(f"built in {minutes}m{seconds:02d}s -> {os.path.relpath(SITE_DIR, DOCS_ROOT)}/")


def is_real_doxygen_page(path):
    """Tell the embedded Doxygen manual apart from its placeholder page.

    :param path: ``doxygen/index.html`` inside the site.
    :returns: ``True`` when Doxygen generated it.
    """
    try:
        with open(path, "rb") as handle:
            return b'content="Doxygen' in handle.read(4096)
    except OSError:
        return False


def verify_site(graphs):
    """Check that the built site contains every part of the manual.

    :param graphs: whether call and include graphs are expected.
    :returns: the number of problems found.
    """
    def count(pattern):
        return len(glob.glob(os.path.join(SITE_DIR, pattern), recursive=True))

    pages = count("**/index.html") - count("doxygen/**/index.html")
    figures_expected = len(glob.glob(os.path.join(DOCS_ROOT, "images", "*.svg")))
    figures = count("figures/*.svg")
    api_pages = count("api/**/index.html")
    doxygen_ok = is_real_doxygen_page(os.path.join(SITE_DIR, "doxygen", "index.html"))
    graph_files = sum(1 for p in glob.glob(os.path.join(SITE_DIR, "doxygen", "*.svg")) if GRAPH_FILE.search(p))

    checks = [
        ("landing page and guides", pages >= 20, f"{pages} pages"),
        ("theory figures", figures_expected > 0 and figures == figures_expected, f"{figures} of {figures_expected}"),
        ("API reference", api_pages >= 50, f"{api_pages} pages"),
        ("Doxygen manual at /doxygen/", doxygen_ok, "embedded" if doxygen_ok else "placeholder only"),
        ("search index", os.path.isfile(os.path.join(SITE_DIR, "search", "search_index.json")), "search/search_index.json"),
    ]
    if graphs:
        checks.append(("call, caller and include graphs", graph_files > 0, f"{graph_files} graphs"))
    problems = 0
    for label, passed, detail in checks:
        (good if passed else bad)(f"{label:<34} {detail}")
        problems += not passed
    return problems


# ──────────────────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_arguments():
    """Define and parse the command line.

    :returns: the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Check, build and open the MFTL2 manual -- one command.",
        epilog="Example: python3 view_manual.py        (the first run takes a few minutes)",
    )
    mftl_paths.add_argument(parser)
    parser.add_argument("--check", action="store_true", help="only report what is present and what is missing")
    parser.add_argument("--no-build", dest="build", action="store_false", help="serve the site already in build/site")
    parser.add_argument("--rebuild", action="store_true", help="build even when the site looks up to date")
    parser.add_argument("--clean", action="store_true", help="delete build/ first and build everything from scratch")
    parser.add_argument("--no-graphs", dest="graphs", action="store_false", help="skip Graphviz: faster, no graphs")
    parser.add_argument("--live", action="store_true", help="live-reload server for writing prose")
    parser.add_argument("--prebuilt", action="store_true", help="open the committed offline copy in prebuilt/")
    parser.add_argument("--port", type=int, default=8000, help="first port to try (default: 8000)")
    parser.add_argument("--no-open", dest="open_browser", action="store_false", help="do not open the browser")
    parser.add_argument("--yes", action="store_true", help="answer yes to every offer (install, clone)")
    parser.add_argument("--verbose", action="store_true", help="show the full Doxygen and MkDocs output")
    return parser.parse_args()


def open_prebuilt(open_browser):
    """Open the committed offline manual straight from disk.

    :param open_browser: open it, rather than only print where it is.
    :returns: nothing.
    """
    if not os.path.isfile(PREBUILT_INDEX):
        die("prebuilt/html/index.html is not in this checkout.", "Build the manual instead: python3 view_manual.py")
    uri = Path(PREBUILT_INDEX).as_uri()
    print(f"The offline manual (no toolchain, no network):\n  {uri}")
    print(f"  PDF: {os.path.join(DOCS_ROOT, 'prebuilt', 'MFTL_Manual.pdf')}")
    if open_browser:
        webbrowser.open(uri)


def main():
    """Run the checks, build if needed, verify, and serve.

    :returns: nothing; exits non-zero on the first problem that cannot be fixed.
    """
    args = parse_arguments()
    if args.prebuilt:
        open_prebuilt(args.open_browser)
        return

    print("MFTL2 manual" + (" -- checking prerequisites only" if args.check else ""))
    print(f"documentation: {DOCS_ROOT}")
    problems = []
    ready, where = toolchain_state()

    # 1. Python
    step(1, "Python")
    good(f"{platform.python_version()}  ({sys.executable})")
    if not ready and importlib.util.find_spec("ensurepip") is None:
        bad("this Python cannot create virtual environments (no ensurepip)")
        note(f"Debian/Ubuntu:  sudo apt-get install python3-venv   (or python{sys.version_info[0]}.{sys.version_info[1]}-venv)")
        problems.append("python3-venv")

    # 2. Doxygen and Graphviz -- offered as ONE install when both are missing
    step(2, "Doxygen and Graphviz")
    doxygen, doxygen_version = check_doxygen()
    dot, dot_problem = check_graphviz() if args.graphs else (None, None)
    missing = [name for name, found in (("doxygen", doxygen), ("graphviz", dot or not args.graphs)) if not found]
    if missing and not args.check and offer_install(missing, args.yes):
        doxygen, doxygen_version = check_doxygen()
        dot, dot_problem = check_graphviz() if args.graphs else (None, None)

    if doxygen:
        good(f"Doxygen {doxygen_version}  ({doxygen})")
        advice = doxyconf.version_note(doxygen)
        if advice:
            note(advice)
    else:
        bad("Doxygen -- generates the API reference and the Doxygen manual")
        print_install_help(["doxygen"])
        problems.append("doxygen")
    if not args.graphs:
        good("Graphviz skipped (--no-graphs)")
    elif dot and not dot_problem:
        good(f"Graphviz renders SVG  ({dot})")
    elif dot:
        bad(f"Graphviz is installed but broken: {dot_problem}")
        problems.append("graphviz")
    else:
        bad("Graphviz -- draws the call, caller and include graphs (or pass --no-graphs)")
        print_install_help(["graphviz"])
        problems.append("graphviz")

    # 3. The library
    step(3, "MFTL2 library sources")
    source_root = find_library(args.source_dir)
    if source_root is None and library_fix(args.yes, args.check):
        source_root = find_library(args.source_dir)
    if source_root:
        good(f"{source_root}  ({describe_checkout(source_root)})")
        note(f"version {mftl_paths.project_version(source_root)}")
        if mftl_paths.has_measurements(source_root):
            note(f"{mftl_paths.MEASUREMENTS} present -- the Analysis section is included")
        else:
            note(f"no {mftl_paths.MEASUREMENTS} (kept local to the library) -- the Analysis section is left out")
    else:
        problems.append("library")

    # 4. Toolchain
    step(4, "MkDocs toolchain")
    if ready:
        good(where)
    elif args.check:
        good(f"{where} -- the first real run installs it into .venv-docs/ (network needed once)")

    if args.check:
        print()
        if problems:
            print(f"Missing: {', '.join(problems)}. Fix the lines marked MISSING above, then run  python3 view_manual.py")
            sys.exit(1)
        print("Everything is in place. Run  python3 view_manual.py")
        return
    if problems:
        die(f"cannot build the manual yet -- missing: {', '.join(problems)}.",
            "Fix the lines marked MISSING above, then run this again.",
            "Or, with nothing installed at all:  python3 view_manual.py --prebuilt")

    if not ready:
        build_mkdocs.ensure_environment(False, quiet=not args.verbose)
        good("installed into .venv-docs/")

    if args.live:
        command = [sys.executable, os.path.join(DOCS_ROOT, "build_mkdocs.py"), "--serve",
                   "--source-dir", source_root, "--port", str(args.port)]
        if args.open_browser:
            command.append("--open")
        if not args.graphs:
            command.append("--no-graphs")
        try:
            sys.exit(subprocess.call(command, cwd=DOCS_ROOT))
        except KeyboardInterrupt:
            sys.exit(0)

    # 5. Build
    step(5, "Build")
    if args.clean and os.path.isdir(BUILD_DIR):
        print(f"      deleting {os.path.relpath(BUILD_DIR, DOCS_ROOT)}/ (--clean)")
        shutil.rmtree(BUILD_DIR)
    current, reason = site_is_current(source_root, args.graphs)
    if not args.build:
        if not os.path.isfile(os.path.join(SITE_DIR, "index.html")):
            die("--no-build, but there is no site in build/site yet.", "Run: python3 view_manual.py")
        good(f"skipped (--no-build); {reason}")
    elif current and not args.rebuild:
        good(f"{reason}; --rebuild forces one")
    else:
        first = not os.path.isdir(os.path.join(BUILD_DIR, "docs", "html"))
        print(f"      {reason} -- building " + ("with" if args.graphs else "without") + " graphs"
              + ("; a first build takes a few minutes" if first else ""), flush=True)
        build_site(source_root, args.graphs, args.verbose)

    # 6. Verify
    step(6, "Verify the result")
    if verify_site(args.graphs):
        print("      Some parts are missing. The site is served anyway; to rebuild from scratch:")
        print("      python3 view_manual.py --clean --verbose")

    # 7. Serve
    step(7, "Serve")
    print("      pages:  /  (manual)   /api/  (API reference)   /doxygen/  (Doxygen manual, graphs)")
    build_mkdocs.serve_static(SITE_DIR, args.port, args.open_browser)


if __name__ == "__main__":
    main()
