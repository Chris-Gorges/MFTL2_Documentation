#!/usr/bin/env python3
"""
MFTL Manual Export -- a pre-built manual nobody has to compile
==============================================================

Builds the complete manual into ``prebuilt/``, as two artefacts meant to be
committed so that a reader needs no toolchain at all:

``prebuilt/html/index.html``
    An offline copy of the web manual. It opens straight from the file system
    (``file://``): fonts, scripts and MathJax are bundled by Material's
    ``privacy`` plugin, search works through the ``offline`` plugin, and nothing
    is fetched from the network at view time. It contains the guides, the module
    theory chapters, the measurements, the API reference, and the complete
    Doxygen manual at ``html/doxygen/index.html``: call and caller graphs,
    include graphs and the annotated source browser. Doxygen's graph caches
    (``*.md5``, ``*.map``) are left out, and its MathJax is pointed at the copy
    the privacy plugin bundled.

``prebuilt/MFTL_Manual.pdf``
    The same content as one PDF -- guides, module theory, measurements, and the
    reference of every public header and every public structure -- printed from
    a single print page (``mkdocs-print-site-plugin``) by a headless Chrome,
    Chromium or Edge.

The export uses a configuration generated next to ``mkdocs.yml``
(``.mkdocs.export.yml``, git-ignored) that INHERITs it and changes only what an
offline copy needs, so the site and the export cannot drift apart. The API
section of its navigation is derived from the library's public headers, so a
new header or structure appears in the PDF without editing anything here.

Requirements: those of ``build_mkdocs.py`` (Python 3.9+, Doxygen, network access
on the first run to install the toolchain and to fetch fonts and MathJax),
Graphviz for the graphs, plus a Chromium-based browser for the PDF (found
automatically, or ``--chrome``, or ``$CHROME``).

Usage:
    python3 export_manual.py [options]

Options:
    --source-dir DIR  Path to the MFTL library checkout.
    --output-dir DIR  Where to write the export (default: prebuilt/).
    --no-pdf          Skip the PDF.
    --no-doxygen      Leave the Doxygen manual (call graphs, source browser)
                      out of the HTML: about 100 MB smaller.
    --no-html         Do not copy the offline HTML into the output directory
                      (it is still built, because the PDF is printed from it).
    --chrome PATH     The browser used to print the PDF.
    --quiet           Suppress progress chatter.

Examples:
    python3 export_manual.py                  # refresh prebuilt/ before a release
    python3 export_manual.py --no-pdf         # only the offline HTML
"""

import argparse
import datetime
import glob
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_mkdocs  # noqa: E402
import doxyconf  # noqa: E402
import mftl_paths  # noqa: E402

DOCS_ROOT = mftl_paths.docs_root()
BASE_CONFIG = os.path.join(DOCS_ROOT, "mkdocs.yml")
EXPORT_CONFIG = os.path.join(DOCS_ROOT, ".mkdocs.export.yml")
EXPORT_SITE = os.path.join(DOCS_ROOT, "build", "export")
DEFAULT_OUTPUT = os.path.join(DOCS_ROOT, "prebuilt")
PDF_NAME = "MFTL_Manual.pdf"

#: MathJax for the export: the SVG output carries its glyphs inside the script,
#: so no font file is loaded at run time and the bundled copy works offline.
#: Pinned, because the privacy plugin downloads exactly this file.
MATHJAX_OFFLINE = "https://unpkg.com/mathjax@3.2.2/es5/tex-svg-full.js"

#: How Doxygen's pages load MathJax (``MATHJAX_RELPATH`` in ``Doxyfile.in``,
#: a CDN). Rewritten to the bundled copy, which includes every TeX extension.
DOXYGEN_MATHJAX = re.compile(r'src="https?://[^"]*mathjax[^"]*/tex-[a-z-]+\.js"')

#: Pages left out of the PDF: the landing page, the API index pages and the
#: Doxygen-manual page are link lists (the last into the HTML's ``doxygen/``).
PDF_EXCLUDE = (
    "index.md",
    "api/modules.md",
    "api/annotated.md",
    "api/class_members.md",
    "api/files.md",
    "api/functions.md",
    "api/macros.md",
    "api/variables.md",
    "api/doxygen-manual.md",
)

#: Browsers able to print a page to PDF headlessly, most likely first.
BROWSER_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
    "msedge",
    "microsoft-edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


def doxygen_escape(name):
    """Spell a name the way Doxygen spells it in file names and compound ids.

    With ``CASE_SENSE_NAMES = NO`` (pinned in ``Doxyfile.in``) an upper-case
    letter becomes ``_`` plus its lower case, ``_`` becomes ``__`` and ``.``
    becomes ``_8``.

    :param name: a file or type name.
    :returns: the escaped name.
    """
    out = []
    for char in name:
        if char.isupper():
            out.append("_" + char.lower())
        elif char == "_":
            out.append("__")
        elif char == ".":
            out.append("_8")
        else:
            out.append(char)
    return "".join(out)


def public_reference(source_root):
    """The API pages of the public headers and of the structures they define.

    :param source_root: root of the MFTL library checkout.
    :returns: ``(headers, structs)``, each a list of ``(title, page)`` pairs.
    """
    headers, structs = [], []
    for path in sorted(glob.glob(os.path.join(source_root, "include", "*.h"))):
        name = os.path.basename(path)
        if name == "mftl_core.h":
            continue  # the umbrella header documents nothing of its own
        headers.append((name, f"api/{doxygen_escape(name)}.md"))

        kind = None
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                opened = re.match(r"typedef\s+(struct|enum|union)\b", line)
                if opened:
                    kind = opened.group(1)
                    continue
                closed = re.match(r"\}\s*(MFTL_\w+)\s*;", line)
                if closed and kind is not None:
                    if kind == "struct":
                        structs.append((closed.group(1), f"api/struct{doxygen_escape(closed.group(1))}.md"))
                    kind = None
    structs.sort()
    return headers, structs


def top_level_block(text, key):
    """Return one top-level block of a YAML file, verbatim.

    :param text: the file.
    :param key: the top-level key, e.g. ``"plugins"``.
    :returns: the block's lines after the key line, as text.
    """
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            break
    else:
        raise SystemExit(f"Error: no top-level '{key}:' in {BASE_CONFIG}")
    body = []
    for line in lines[start + 1:]:
        if re.match(r"[A-Za-z_]", line):
            break
        body.append(line)
    while body and not body[-1].strip():
        body.pop()
    return "\n".join(body) + "\n"


def drop_plugin(block, name):
    """Remove one plugin entry, with its options, from a ``plugins:`` block.

    :param block: the block, as returned by :func:`top_level_block`.
    :param name: the plugin's name.
    :returns: the block without it.
    """
    out, skipping = [], False
    for line in block.splitlines():
        if re.match(r"  - ", line):
            skipping = re.match(rf"  - {re.escape(name)}\b", line) is not None
        if not skipping:
            out.append(line)
    return "\n".join(out) + "\n"


def theme_features(text):
    """The theme features of ``mkdocs.yml`` minus instant navigation.

    Instant navigation loads pages with XHR, which a browser refuses for
    ``file://`` URLs.

    :param text: contents of ``mkdocs.yml``.
    :returns: the feature names to keep.
    """
    block = top_level_block(text, "theme")
    match = re.search(r"^  features:\n((?:    - .+\n)+)", block, re.MULTILINE)
    features = re.findall(r"^    - (\S+)", match.group(1), re.MULTILINE) if match else []
    return [f for f in features if not f.startswith("navigation.instant")]


def offline_scripts(text):
    """The ``extra_javascript`` of ``mkdocs.yml`` with every network URL replaced.

    Derived rather than restated: a script the site gains (the settings
    reference's filter, say) must reach the offline copy too, and a fixed list
    here would drop it without a word. Local scripts keep their order; the
    MathJax the site loads from a CDN becomes the bundled
    :data:`MATHJAX_OFFLINE`, after them, so its configuration still loads first.

    :param text: contents of ``mkdocs.yml``.
    :returns: the script entries for the export configuration.
    """
    entries = re.findall(r"^  - (\S+)", top_level_block(text, "extra_javascript"), re.MULTILINE)
    local = [e for e in entries if not re.match(r"https?://", e)]
    return local + [MATHJAX_OFFLINE]


def write_export_config(source_root, site_dir, mount_doxygen):
    """Generate ``.mkdocs.export.yml``.

    :param source_root: root of the MFTL library checkout.
    :param site_dir: where the offline site is built.
    :param mount_doxygen: whether ``mkdocs/hooks.py`` copies the Doxygen manual
        into the site.
    :returns: the path written.
    """
    with open(BASE_CONFIG, encoding="utf-8") as handle:
        base = handle.read()

    headers, structs = public_reference(source_root)
    reference = ["  - Reference:", "      - Public headers:"]
    reference += [f"          - {title}: {page}" for title, page in headers]
    reference += ["      - Public types:"]
    reference += [f"          - {title}: {page}" for title, page in structs]

    features = "\n".join(f"    - {f}" for f in theme_features(base))
    # glightbox re-serialises every page body as a whole HTML document, which
    # makes the print page run its table-of-contents script once per page. The
    # offline copy loses only click-to-zoom on the theory figures; they are
    # vector graphics, so the PDF prints them sharp without it.
    plugins = drop_plugin(top_level_block(base, "plugins"), "glightbox")
    exclude = "\n".join(f"        - {page}" for page in PDF_EXCLUDE)
    scripts = "\n".join(f"  - {script}" for script in offline_scripts(base))

    text = f"""# Generated by export_manual.py -- do not edit, edit mkdocs.yml instead.
INHERIT: mkdocs.yml

site_dir: {site_dir}
use_directory_urls: false

theme:
  features:
{features}

extra:
  mftl_mount_doxygen: {"true" if mount_doxygen else "false"}

extra_javascript:
{scripts}

plugins:
{plugins.rstrip()}
  - privacy
  - offline
  - print-site:
      add_to_navigation: false
      print_page_title: "MFTL -- the complete manual"
      add_print_site_banner: false
      add_table_of_contents: true
      toc_title: Contents
      toc_depth: 1
      add_full_urls: false
      enumerate_headings: true
      enumerate_headings_depth: 2
      enumerate_figures: false
      add_cover_page: true
      include_css: true
      exclude:
{exclude}

nav:
{top_level_block(base, "nav").rstrip()}
{chr(10).join(reference)}
"""
    with open(EXPORT_CONFIG, "w", encoding="utf-8") as handle:
        handle.write(text)
    return EXPORT_CONFIG


def localise_doxygen_mathjax(site_dir):
    """Point the Doxygen pages at the MathJax the privacy plugin bundled.

    Doxygen loads MathJax from a CDN, which an offline copy cannot reach. The
    bundled ``tex-svg-full.js`` carries its fonts and every TeX extension, so
    the configuration Doxygen writes into each page works unchanged.

    :param site_dir: the built site, with the Doxygen manual under ``doxygen/``.
    :returns: the number of pages rewritten.
    """
    doxygen_dir = os.path.join(site_dir, "doxygen")
    bundled = glob.glob(os.path.join(site_dir, "assets", "external", "**", "tex-svg-full.js"), recursive=True)
    if not bundled:
        raise SystemExit("Error: the privacy plugin did not bundle MathJax; the Doxygen pages would need network.")
    rewritten = 0
    for page in glob.glob(os.path.join(doxygen_dir, "**", "*.html"), recursive=True):
        with open(page, encoding="utf-8") as handle:
            text = handle.read()
        relative = os.path.relpath(bundled[0], os.path.dirname(page)).replace(os.sep, "/")
        new_text, n = DOXYGEN_MATHJAX.subn(f'src="{relative}"', text)
        if n:
            with open(page, "w", encoding="utf-8") as handle:
                handle.write(new_text)
            rewritten += 1
    if rewritten == 0:
        raise SystemExit("Error: no Doxygen page loads MathJax the expected way; check MATHJAX_RELPATH.")
    return rewritten


def find_browser(explicit):
    """Locate a Chromium-based browser that can print to PDF.

    :param explicit: a path given on the command line, or ``None``.
    :returns: the executable, or ``None``.
    """
    for candidate in (explicit, os.environ.get("CHROME"), *BROWSER_CANDIDATES):
        if not candidate:
            continue
        if os.path.isfile(candidate):
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def print_pdf(browser, page, pdf):
    """Print a page to PDF with a headless browser.

    ``--virtual-time-budget`` lets MathJax finish typesetting before the page
    is printed, the page is forced into the light colour scheme (the theme
    follows the system's by default, which would print dark page margins), and
    the PDF gets a bookmark outline from the headings. Older browsers ignore
    the flags they do not know. The new headless mode is tried first and the old
    one second.

    :param browser: the browser executable.
    :param page: the HTML file to print.
    :param pdf: the PDF to write.
    :returns: ``True`` on success.
    """
    url = "file://" + os.path.abspath(page).replace(os.sep, "/")
    common = [
        "--disable-gpu",
        "--no-first-run",
        "--no-pdf-header-footer",
        "--blink-settings=preferredColorScheme=1",
        "--generate-pdf-document-outline",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=180000",
        f"--print-to-pdf={pdf}",
        url,
    ]
    if os.path.exists(pdf):
        os.remove(pdf)
    for mode in ("--headless=new", "--headless"):
        try:
            subprocess.run([browser, mode, *common], capture_output=True, timeout=900, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if os.path.isfile(pdf) and os.path.getsize(pdf) > 0:
            return True
    return False


def git_describe(path):
    """Name the commit a checkout is at.

    :param path: a directory inside a git repository.
    :returns: ``<short hash>`` (with ``+local changes`` when dirty), or ``None``.
    """
    try:
        head = subprocess.run(["git", "-C", path, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", path, "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return head + (" + local changes" if dirty else "")


def write_readme(output_dir, source_root, have_html, have_pdf, have_doxygen, have_measurements):
    """Describe the export, and what it was built from, in ``prebuilt/README.md``.

    :param output_dir: the export directory.
    :param source_root: root of the MFTL library checkout.
    :param have_html: whether the offline HTML is part of the export.
    :param have_pdf: whether the PDF is part of the export.
    :param have_doxygen: whether the HTML carries the Doxygen manual.
    :param have_measurements: whether the Analysis section (``docs/analysis.md``) is in it.
    :returns: nothing.
    """
    doxygen = doxyconf.find_doxygen()
    found = doxyconf.version(doxygen) if doxygen else None
    lines = [
        "# MFTL manual -- pre-built",
        "",
        "Generated by `export_manual.py`; do not edit. Rebuild it after the library's",
        "documentation changes:",
        "",
        "```bash",
        "python3 export_manual.py",
        "```",
        "",
        "| File | What it is |",
        "|---|---|",
    ]
    if have_pdf:
        lines.append(f"| [`{PDF_NAME}`]({PDF_NAME}) | the whole manual as one PDF: guides, module theory, "
                     f"{'measurements, ' if have_measurements else ''}and the reference of every public header "
                     "and type |")
    if have_html:
        lines.append("| [`html/index.html`](html/index.html) | the web manual for offline use: open it in a "
                     "browser straight from disk; search and formulas work without network |")
    if have_doxygen:
        lines += [
            "",
            "The HTML includes the Doxygen manual at [`html/doxygen/index.html`](html/doxygen/index.html):",
            "call and caller graphs, include graphs and the annotated source browser.",
        ]
    else:
        lines += [
            "",
            "Not included: the Doxygen manual with call graphs and the annotated source",
            "browser. Build it with `python3 build_docs.py --open`.",
        ]
    lines += [
        "",
        "| Built from | |",
        "|---|---|",
        f"| MFTL version | {mftl_paths.project_version(source_root)} |",
        f"| MFTL commit | {git_describe(source_root) or 'unknown'} |",
        f"| MFTL2_Documentation commit | {git_describe(DOCS_ROOT) or 'unknown'} |",
        f"| Measurements (`docs/analysis.md`) | {'included' if have_measurements else 'left out: local to the library'} |",
        f"| Doxygen | {'.'.join(map(str, found)) if found else 'unknown'} |",
        f"| Date | {datetime.date.today().isoformat()} |",
        "",
    ]
    with open(os.path.join(output_dir, "README.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def directory_size(path):
    """Total size of a directory tree.

    :param path: the directory.
    :returns: the size in bytes.
    """
    return sum(os.path.getsize(os.path.join(root, name)) for root, _, names in os.walk(path) for name in names)


def main():
    """Build the offline site, copy it, print the PDF.

    :returns: nothing; exits non-zero on failure.
    """
    parser = argparse.ArgumentParser(description="Export the MFTL manual as offline HTML and PDF.")
    mftl_paths.add_argument(parser)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, help="export directory (default: prebuilt/)")
    parser.add_argument("--no-pdf", dest="pdf", action="store_false", help="skip the PDF")
    parser.add_argument("--no-doxygen", dest="doxygen", action="store_false",
                        help="leave the Doxygen manual (call graphs, source browser) out of the HTML")
    parser.add_argument("--no-html", dest="html", action="store_false",
                        help="do not copy the offline HTML into the export directory")
    parser.add_argument("--with-measurements", action="store_true",
                        help="include the Analysis section (docs/analysis.md); left out by default, "
                             "because prebuilt/ is published and the measurements stay local")
    parser.add_argument("--chrome", default=None, help="browser used to print the PDF")
    parser.add_argument("--quiet", action="store_true", help="suppress progress output")
    args = parser.parse_args()

    build_mkdocs.check_python()
    if not args.with_measurements:
        # Exported, so read by every subprocess: Doxygen's configuration, the
        # MkDocs hooks and the page generator all ask mftl_paths.has_measurements().
        os.environ[mftl_paths.MEASUREMENTS_ENV] = "0"
    source_root = mftl_paths.resolve(args.source_dir)
    have_measurements = mftl_paths.has_measurements(source_root)
    output_dir = os.path.abspath(args.output_dir)
    browser = find_browser(args.chrome) if args.pdf else None
    if args.pdf and browser is None:
        print("Error: no Chrome, Chromium or Edge found to print the PDF.", file=sys.stderr)
        print("  Pass --chrome /path/to/browser, set $CHROME, or use --no-pdf.", file=sys.stderr)
        sys.exit(1)

    python = build_mkdocs.ensure_environment(False, args.quiet)
    config = write_export_config(source_root, EXPORT_SITE, args.doxygen)

    if not args.quiet:
        print("-------------------------------------------------")
        print("MFTL Manual Export")
        print("-------------------------------------------------")
        print(f"Library sources  : {source_root}")
        print(f"Offline site     : {EXPORT_SITE}")
        print(f"Export directory : {output_dir}")
        print(f"PDF              : {browser if args.pdf else 'skipped'}")
        print(f"Doxygen manual   : {'included' if args.doxygen else 'skipped'}")
        print(f"Measurements     : {'included' if have_measurements else 'left out (--with-measurements includes them)'}")
        print("-------------------------------------------------", flush=True)

    if args.doxygen:
        if doxyconf.find_doxygen() is None:
            print("Error: Doxygen not found (PATH or $DOXYGEN); install it, or pass --no-doxygen.", file=sys.stderr)
            sys.exit(1)
        if shutil.which("dot") is None:
            print("Warning: Graphviz (dot) not found -- the Doxygen manual will have no call graphs.", file=sys.stderr)
        build_mkdocs.build_doxygen(source_root, False, True, args.quiet, clean=True)

    if os.path.isdir(EXPORT_SITE):
        shutil.rmtree(EXPORT_SITE)
    status = build_mkdocs.run_mkdocs(python, source_root, ["build"], args.quiet, config=config)
    if status != 0:
        print("\nError: the MkDocs build of the export failed.", file=sys.stderr)
        sys.exit(status)
    if args.doxygen:
        pages = localise_doxygen_mathjax(EXPORT_SITE)
        if not args.quiet:
            print(f"Doxygen manual: MathJax bundled for {pages} pages.")

    os.makedirs(output_dir, exist_ok=True)
    have_html = False
    if args.html:
        target = os.path.join(output_dir, "html")
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(EXPORT_SITE, target)
        have_html = True

    have_pdf = False
    if args.pdf:
        pdf = os.path.join(output_dir, PDF_NAME)
        print("Printing the PDF (this takes a minute) ...", flush=True)
        have_pdf = print_pdf(browser, os.path.join(EXPORT_SITE, "print_page.html"), pdf)
        if not have_pdf:
            print(f"Error: {browser} did not produce {pdf}.", file=sys.stderr)
            sys.exit(1)

    write_readme(output_dir, source_root, have_html, have_pdf, have_html and args.doxygen, have_measurements)

    print("\nManual exported.")
    if have_html:
        html = os.path.join(output_dir, "html")
        print(f"  HTML : {os.path.join(html, 'index.html')}  ({directory_size(html) / 1e6:.1f} MB)")
    if have_pdf:
        pdf = os.path.join(output_dir, PDF_NAME)
        print(f"  PDF  : {pdf}  ({os.path.getsize(pdf) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
