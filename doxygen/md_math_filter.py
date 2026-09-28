#!/usr/bin/env python3
"""Doxygen INPUT_FILTER for Markdown pages: `$...$` math -> `\\f$...\\f$`, and
figure directives -> `\\image`.

Why this exists
---------------
The module READMEs under `src/*/` are read in two places: on GitHub, and in the
generated manual. GitHub renders LaTeX with `$ ... $` and `$$ ... $$`; Doxygen
recognises only `\\f$ ... \\f$` and `\\f[ ... \\f]`, and treats everything else
beginning with a backslash as an unknown command.

Rather than pick one dialect and lose the other reader, the sources stay in the
GitHub dialect and this filter rewrites them on the way into Doxygen. One source,
both renderings, and no duplicated prose.

What it must NOT touch
----------------------
A `$` is only math when it is not in code. Three contexts are skipped:

  * fenced code blocks (``` or ~~~), which hold shell snippets full of `$(...)`
    and `${...}`;
  * indented code blocks (four spaces), same reason;
  * inline code spans (`` `...` ``), which is where `$PATH` and `\\f$` appear in
    prose about the formatting itself.

Figures
-------
A figure is placed in the prose by an HTML comment, so that GitHub shows nothing
where it cannot resolve the image (the SVGs live in this repository's `images/`,
not next to the README):

    <!-- figure: halfedge-implicit
    Caption, in Markdown with GitHub math.
    -->

Here it becomes `\\image html halfedge-implicit.svg`, found through
`IMAGE_PATH`, followed by the numbered caption as a block of prose (Doxygen
allows no formula in an `\\image` caption); an unknown name is a Doxygen
warning, so `--strict` fails on it. Figures are numbered per page in order of appearance. The consumed lines
are replaced by blank ones so Doxygen's line numbers still match the source.
`mkdocs/doxymd.py` expands the same directive for the web manual; the grammar
is specified once, in `images/README.md`.

Doxygen invokes a filter as `<command> <file>` and reads the result from stdout,
so this script takes one argument and prints. It never fails the build: on any
unexpected input it falls back to emitting the file unchanged.
"""

import re
import sys

# ── Inline code spans ────────────────────────────────────────────────────────
# Backtick runs of any length, matched with an equal-length closer, as CommonMark
# specifies. Non-greedy so adjacent spans do not merge into one.
CODE_SPAN = re.compile(r"(`+)(?:.*?)\1")

FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
DISPLAY_ONLY = re.compile(r"^\s*\$\$\s*$")

# Text that is ALREADY in the Doxygen dialect. The pages under pages/ are
# written for Doxygen directly, and `\f$ ... \f$` contains dollar signs that must
# not be re-interpreted -- without this the inline rule below would pair the `$`
# of an opening `\f$` with the `$` of the closing one and emit `\f\f$`.
DOXY_INLINE = re.compile(r"\\f\$.*?\\f\$")
DOXY_OPEN = re.compile(r"^\s*\\f\[\s*$")
DOXY_CLOSE = re.compile(r"^\s*\\f\]\s*$")

# `<!-- figure: name` opens a figure directive; the caption runs to `-->`.
FIGURE_OPEN = re.compile(r"^ {0,3}<!--\s*figure:\s*([a-z0-9][a-z0-9-]*)\s*(.*)$")

# `$ ... $` on one line. The opening `$` must not be followed by whitespace and
# the closing one must not be preceded by it -- the same rule GitHub applies, and
# what keeps a bare "costs $5 to $9" out of math mode. A `\$` is left alone.
INLINE = re.compile(r"(?<!\\)\$(?!\s)((?:[^$\\\n]|\\.)+?)(?<!\s)(?<!\\)\$")


def protect_spans(line):
    """Replace inline code spans and existing \\f$ formulas with placeholders."""
    spans = []

    def stash(m):
        spans.append(m.group(0))
        return "\x00%d\x00" % (len(spans) - 1)

    line = CODE_SPAN.sub(stash, line)
    line = DOXY_INLINE.sub(stash, line)
    return line, spans


def restore_spans(line, spans):
    for i, original in enumerate(spans):
        line = line.replace("\x00%d\x00" % i, original)
    return line


def figure_command(name, caption_lines, number, n_lines):
    """The lines replacing one figure directive of ``n_lines`` source lines.

    Doxygen accepts no formula in an `\\image` caption, so the image is
    emitted without one and the caption follows as an ordinary block of prose
    (`<div class="mftl-caption">`), where formulas, code spans and references
    all work. The output is padded to ``n_lines`` so line numbers still match.
    """
    caption = " ".join(part.strip() for part in caption_lines if part.strip())
    stripped, spans = protect_spans(caption)
    stripped = INLINE.sub(lambda mm: "\\f$" + mm.group(1) + "\\f$", stripped)
    caption = restore_spans(stripped, spans)
    lines = ["\\image html %s.svg" % name,
             '<div class="mftl-caption"><b>Figure %d.</b> %s</div>' % (number, caption)]
    return lines + [""] * max(n_lines - len(lines), 0)


def convert(text):
    out = []
    in_fence = False
    fence_marker = ""
    in_display = False
    in_doxy_display = False
    in_indent_code = False
    prev_blank = True
    figure = None          # [name, caption lines, consumed line count] while open
    figures_seen = 0

    for line in text.split("\n"):
        # --- an open figure directive swallows lines up to `-->` --------------
        if figure is not None:
            end = line.find("-->")
            figure[1].append(line if end < 0 else line[:end])
            figure[2] += 1
            if end >= 0:
                figures_seen += 1
                out.extend(figure_command(figure[0], figure[1], figures_seen, figure[2]))
                figure = None
                prev_blank = True
            continue

        # --- fenced code: pass through verbatim -----------------------------
        m = FENCE.match(line)
        if in_fence:
            out.append(line)
            if m and line.strip().startswith(fence_marker):
                in_fence = False
            continue
        if m:
            in_fence = True
            fence_marker = m.group(1)
            out.append(line)
            continue

        # --- a `\f[ ... \f]` block is already Doxygen: pass it through -------
        if in_doxy_display:
            out.append(line)
            if DOXY_CLOSE.match(line):
                in_doxy_display = False
            continue
        if DOXY_OPEN.match(line):
            in_doxy_display = True
            out.append(line)
            continue

        # --- a figure directive -------------------------------------------
        # (at most three spaces of indent, so it also ends an indented code block)
        m = None if in_display else FIGURE_OPEN.match(line)
        if m:
            in_indent_code = False
            rest = m.group(2)
            end = rest.find("-->")
            if end >= 0:
                figures_seen += 1
                out.extend(figure_command(m.group(1), [rest[:end]], figures_seen, 1))
                prev_blank = True
            else:
                figure = [m.group(1), [rest], 1]
            continue

        # --- display math: a line that is exactly `$$` toggles --------------
        if DISPLAY_ONLY.match(line):
            out.append("\\f]" if in_display else "\\f[")
            in_display = not in_display
            continue
        if in_display:
            out.append(line)
            continue

        # --- indented code: pass through verbatim ---------------------------
        #
        # CommonMark only starts an indented code block after a BLANK line. That
        # distinction matters here: a Doxygen `@warning` or `@note` continuation,
        # and the second and later lines of a list item, are both indented and are
        # both prose. Requiring the blank line keeps their inline math working.
        if in_indent_code:
            if line.strip() == "" or line.startswith("    "):
                out.append(line)
                continue
            in_indent_code = False
        elif prev_blank and line.startswith("    ") and line.strip():
            in_indent_code = True
            out.append(line)
            continue

        # --- inline math, with code spans held back -------------------------
        stripped, spans = protect_spans(line)
        stripped = INLINE.sub(lambda mm: "\\f$" + mm.group(1) + "\\f$", stripped)
        out.append(restore_spans(stripped, spans))
        prev_blank = (line.strip() == "")

    if figure is not None:  # unterminated directive: emit it rather than lose the page
        out.extend(figure_command(figure[0], figure[1], figures_seen + 1, figure[2]))
    if in_display:  # unbalanced `$$`; better to close it than to swallow the page
        out.append("\\f]")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        return 0
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print("<!-- md_math_filter: %s -->" % exc)
        return 0
    try:
        sys.stdout.write(convert(text))
    except Exception:  # never fail the documentation build over a filter
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
