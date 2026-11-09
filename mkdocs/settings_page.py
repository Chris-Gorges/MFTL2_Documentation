"""Generate the manual's settings reference from the library's key table.

Every runtime option of MFTL is declared once, as one ``KEY(...)`` line in the
library's ``src/settings/settings_keys.c`` -- type, struct member, default,
admissible range, keyword choices, unit and a one-line summary.  The parser,
the range checks, ``MFTLSettingsDefaults()`` and the annotated template the
library prints are all derived from that table, and so is this page: nothing
about a setting is written down twice, and a key added to the table appears
here on the next build.

The table is C, and this module reads it as text.  The format it relies on is
stated in the header comment of ``settings_keys.c`` -- one ``SECTION``,
``CHOICE`` or ``KEY`` per entry, text arguments as string literals -- and a
table this parser cannot read is reported through the MkDocs logger, which
``--strict`` turns into a failure rather than a page with holes.

The generated Markdown is written in the same Doxygen dialect as every other
page (``@ref``, ``Function()``, ``#MFTL_Symbol``) and goes through
:func:`doxymd.convert` like them, so its cross-references resolve exactly as
theirs do.  One consequence: a literal ``#name`` in prose would be taken for a
symbol, so in-page links are written as ``@ref label "text"``.

The C member path of every key is walked through ``include/mftl_settings.h``
to find the struct that documents it, which is where the page links for the
full rationale of a field.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field

log = logging.getLogger("mkdocs.plugins.mftl.settings")

#: The key table, relative to the library root.
KEYS_SOURCE = os.path.join("src", "settings", "settings_keys.c")

#: The header declaring the section structs, relative to the library root.
HEADER_SOURCE = os.path.join("include", "mftl_settings.h")

#: Site path of the generated page.
PAGE = "settings.md"

#: How a type is named on the page.
TYPE_NAMES = {
    "INT": "integer",
    "REAL": "real",
    "BOOL": "true / false",
    "KEYWORD": "keyword",
    "STRING": "string",
    "INT3": "3 integers",
    "REAL3": "3 reals",
    "BOOL3": "3 × true / false",
}


@dataclass
class Choice:
    """One admissible name of a keyword key."""

    name: str
    summary: str


@dataclass
class Key:
    """One ``KEY(...)`` entry of the table."""

    section: str
    name: str
    type: str
    member: str
    default: str
    range: str
    choices: list[Choice]
    unit: str
    advanced: bool
    summary: str
    owner: str = ""  #: The struct whose field this is, e.g. ``MFTL_RemeshParameters``.


@dataclass
class Section:
    """One ``SECTION(...)`` entry of the table."""

    name: str
    title: str
    summary: str
    keys: list[Key] = field(default_factory=list)


# --------------------------------------------------------------------------
# Reading C
# --------------------------------------------------------------------------

_STRING_RE = re.compile(r'"(?:[^"\\\n]|\\.)*"')


def _strip_comments_and_directives(text: str) -> str:
    """Remove comments and preprocessor lines, leaving string literals intact.

    :param text: C source.
    :returns: the source without ``/* */``, ``//`` and ``#`` lines.
    """
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            match = _STRING_RE.match(text, i)
            end = match.end() if match else n
            out.append(text[i:end])
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            out.append(" ")
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end < 0 else end
        else:
            out.append(c)
            i += 1
    lines, keep, continued = "".join(out).split("\n"), [], False
    for line in lines:
        directive = continued or line.lstrip().startswith("#")
        continued = directive and line.rstrip().endswith("\\")
        keep.append("" if directive else line)
    return "\n".join(keep)


def _split_args(text: str, start: int) -> tuple[list[str], int]:
    """Split the argument list of a macro call at top-level commas.

    :param text: the source.
    :param start: index just past the opening parenthesis.
    :returns: ``(raw arguments, index past the closing parenthesis)``.
    """
    args, depth, i, begin = [], 0, start, start
    while i < len(text):
        c = text[i]
        if c == '"':
            match = _STRING_RE.match(text, i)
            i = match.end() if match else i + 1
            continue
        if c in "({[":
            depth += 1
        elif c in ")}]":
            if depth == 0:
                args.append(text[begin:i].strip())
                return args, i + 1
            depth -= 1
        elif c == "," and depth == 0:
            args.append(text[begin:i].strip())
            begin = i + 1
        i += 1
    raise ValueError("unterminated macro call")


def _c_string(arg: str) -> str:
    """Decode one argument made of adjacent C string literals.

    :param arg: e.g. ``"a" "b\\"c"``.
    :returns: the concatenated, unescaped text.
    """
    parts = _STRING_RE.findall(arg)
    if not parts or _STRING_RE.sub("", arg).strip():
        raise ValueError(f"expected string literals, got {arg!r}")
    escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "'": "'"}
    out: list[str] = []
    for part in parts:
        body, i = part[1:-1], 0
        while i < len(body):
            if body[i] == "\\" and i + 1 < len(body):
                out.append(escapes.get(body[i + 1], body[i + 1]))
                i += 2
            else:
                out.append(body[i])
                i += 1
    return "".join(out)


def _calls(text: str, macro: str):
    """Yield the argument lists of every call of ``macro`` in ``text``.

    :param text: comment-free source.
    :param macro: macro name.
    :returns: generator of ``(argument list, end index)``.
    """
    for match in re.finditer(rf"(?<![\w]){macro}\s*\(", text):
        yield _split_args(text, match.end())


def read_table(source_root: str) -> list[Section]:
    """Read the sections and keys of the library's key table.

    :param source_root: the library checkout.
    :returns: the sections in file order, each with its keys.
    :raises ValueError: when the table does not have the documented form.
    """
    with open(os.path.join(source_root, KEYS_SOURCE), encoding="utf-8") as handle:
        text = _strip_comments_and_directives(handle.read())

    choices: dict[str, list[Choice]] = {}
    for match in re.finditer(r"MFTL_SettingChoice\s+(\w+)\s*\[\s*\]\s*=\s*\{", text):
        end = text.index("};", match.end())
        body = text[match.end():end]
        choices[match.group(1)] = [Choice(_c_string(a[0]), _c_string(a[2])) for a, _ in _calls(body, "CHOICE")]

    sections = [Section(_c_string(a[0]), _c_string(a[1]), _c_string(a[2])) for a, _ in _calls(text, "SECTION")]
    by_name = {s.name: s for s in sections}

    for args, _ in _calls(text, "KEY"):
        if len(args) != 10:
            raise ValueError(f"KEY with {len(args)} arguments instead of 10: {args[:2]}")
        section, name = _c_string(args[0]), _c_string(args[1])
        if section not in by_name:
            raise ValueError(f"key {section}.{name} names an undeclared section")
        choice_list = [] if args[6] == "NO_CHOICES" else choices.get(args[6])
        if choice_list is None:
            raise ValueError(f"key {section}.{name} names an unknown choice list {args[6]}")
        by_name[section].keys.append(
            Key(section=section, name=name, type=args[2], member=args[3], default=_c_string(args[4]), range=_c_string(args[5]),
                choices=choice_list, unit=_c_string(args[7]), advanced=args[8].strip() not in ("0", "false"), summary=_c_string(args[9])))
    if not any(s.keys for s in sections):
        raise ValueError("no KEY(...) entries found")
    return sections


def read_struct_members(source_root: str) -> dict[str, dict[str, str]]:
    """Map every struct of ``mftl_settings.h`` to ``{member: type}``.

    :param source_root: the library checkout.
    :returns: e.g. ``{"MFTL_Settings": {"remesh": "MFTL_RemeshSettings", ...}}``.
    """
    with open(os.path.join(source_root, HEADER_SOURCE), encoding="utf-8") as handle:
        text = _strip_comments_and_directives(handle.read())
    structs: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"typedef\s+struct\s+(\w+)\s*\{(.*?)\}\s*(\w+)\s*;", text, re.DOTALL):
        members: dict[str, str] = {}
        for decl in match.group(2).split(";"):
            m = re.match(r"\s*(?:const\s+)?([A-Za-z_]\w*)\s*\**\s*([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*$", decl)
            if m:
                members[m.group(2)] = m.group(1)
        structs[match.group(3)] = members
    return structs


def _owner(member: str, structs: dict[str, dict[str, str]]) -> str:
    """The struct whose field the last component of ``member`` is.

    :param member: path in ``MFTL_Settings``, e.g. ``remesh.params.target_length``.
    :param structs: from :func:`read_struct_members`.
    :returns: the owning struct's name, or ``""`` if the path cannot be walked.
    """
    owner = "MFTL_Settings"
    for part in member.split(".")[:-1]:
        owner = structs.get(owner, {}).get(part, "")
        if not owner:
            return ""
    return owner


# --------------------------------------------------------------------------
# Writing Markdown
# --------------------------------------------------------------------------


def _prose(text: str) -> str:
    """Make a summary safe for a table cell; code spans are left alone.

    :param text: summary from the table.
    :returns: text with ``*``, ``|`` and ``<`` escaped outside backticks.
    """
    parts = re.split(r"(`[^`]*`)", text)
    for i in range(0, len(parts), 2):
        parts[i] = parts[i].replace("|", r"\|").replace("*", r"\*").replace("<", "&lt;")
    return "".join(parts)


def _code(text: str) -> str:
    """A code span that survives any content, including backticks and pipes.

    :param text: literal text.
    :returns: a Markdown code span.
    """
    text = text.replace("|", r"\|")
    fence = "``" if "`" in text else "`"
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _allowed(key: Key) -> str:
    """The "allowed values" cell.

    :param key: the key.
    :returns: Markdown.
    """
    if key.choices:
        return "<br>".join(_code(f'"{c.name}"') for c in key.choices)
    if key.type in ("BOOL", "BOOL3"):
        return "`true`, `false`"
    if key.type == "STRING":
        return "text, up to 255 bytes"
    return _code(key.range) if key.range else "any"


def _meaning(key: Key) -> str:
    """The "what it does" cell: the summary, plus what each keyword choice means.

    :param key: the key.
    :returns: Markdown.
    """
    text = _prose(key.summary)
    for choice in key.choices:
        text += f"<br>{_code(choice.name)}: {_prose(choice.summary)}"
    return text


def _row(key: Key) -> str:
    """One table row, with an anchor, and the key's C path under its description.

    :param key: the key.
    :returns: a Markdown table row.
    """
    anchor = f"key-{key.section}-{key.name}"
    kind = TYPE_NAMES.get(key.type, key.type.lower())
    if key.unit:
        kind += f"<br><small>{key.unit}</small>"
    name = f'<span id="{anchor}"></span>**{_code(key.name)}**'
    where = f'<br><small class="mftl-settings-cpath">C: {_code("cfg." + key.member)}</small>'
    return f"| {name} | {kind} | {_code(key.default)} | {_allowed(key)} | {_meaning(key)}{where} |"


_TABLE_HEAD = ["| Key | Type | Default | Allowed | What it does |", "|---|---|---|---|---|"]


def _template(sections: list[Section]) -> list[str]:
    """Every key at its default, in file syntax, as a TOML code block.

    :param sections: the table.
    :returns: Markdown lines of one fenced block.
    """
    lines = ["```toml", "# Every MFTL setting at its default.", "# `mftl_settings template` prints the same with every key documented."]
    for sec in sections:
        lines += ["", f"[{sec.name}]"]
        width = max(len(k.name) for k in sec.keys)
        common = [k for k in sec.keys if not k.advanced]
        advanced = [k for k in sec.keys if k.advanced]
        for k in common:
            lines.append(f"{k.name.ljust(width)} = {k.default}")
        if advanced:
            lines.append("# advanced")
            for k in advanced:
                lines.append(f"{k.name.ljust(width)} = {k.default}")
    lines.append("```")
    return lines


def render(sections: list[Section], structs: dict[str, dict[str, str]]) -> str:
    """The whole page, in the Doxygen Markdown dialect the other pages use.

    :param sections: from :func:`read_table`.
    :param structs: from :func:`read_struct_members`.
    :returns: Markdown for :func:`doxymd.convert`.
    """
    for sec in sections:
        for key in sec.keys:
            key.owner = _owner(key.member, structs)
    n_keys = sum(len(s.keys) for s in sections)
    n_advanced = sum(k.advanced for s in sections for k in s.keys)

    out = [
        "# Settings reference {#mftl_page_settings}",
        "",
        f"Every runtime option of MFTL — {n_keys} keys in {len(sections)} sections — "
        "is set from **one settings file per simulation**, overridable on the command "
        "line, and ends up in one struct, #MFTL_Settings, whose sections are the parameter "
        "blocks the library's calls already take. Unknown keys, wrong types and values "
        "outside the range below are errors that name the file, the line and the key "
        "that was probably meant.",
        "",
        '@ref settings_quickstart "Quick start"{ .md-button .md-button--primary } '
        '@ref settings_template "Every key at its default"{ .md-button } '
        '@ref mftl_mod_settings "How it works"{ .md-button }',
        "",
        "## Quick start {#settings_quickstart}",
        "",
        "**1. Write a file** with only what differs from the defaults. A subset of TOML: "
        "`[section]` headers, `key = value`, `#` comments, `[x, y, z]` for three-vectors "
        "(one value sets all three).",
        "",
        "```toml",
        "# run.toml",
        "[domain]",
        "global_max = [2.0, 1.0, 1.0]",
        "periodic   = [true, false, false]",
        "",
        "[remesh]",
        "every         = 1",
        "target_length = 0.0          # 0: hold the mesh's starting resolution",
        "",
        "[topology]",
        "every = 5                    # breakup and coalescence every 5 steps",
        "",
        "[output]",
        "every  = 10",
        'prefix = "out/run"',
        "```",
        "",
        "**2. Check it before the job is queued** — the same code the run uses, every "
        "problem at once, and the process grid it will get:",
        "",
        "```bash",
        "build/mftl_settings check run.toml --np 64",
        "build/mftl_settings template > run.toml     # or start from every key, documented",
        "```",
        "",
        "**3. Load it** in the solver, and take each call's block from the struct:",
        "",
        "```c",
        "MFTL_Settings cfg;",
        "MFTLSettingsDefaults(&cfg);",
        'MFTLSettingsLoad(&cfg, "run.toml", MPI_COMM_WORLD);        /* rank 0 reads, every rank parses */',
        "MFTLSettingsLoadArgs(&cfg, argc, argv, MPI_COMM_WORLD);    /* section.key=value overrides */",
        "",
        "MFTL_Ensemble *ens = MFTLSettingsCreateEnsemble(&cfg, MPI_COMM_WORLD);",
        "/* ... create the bodies ... */",
        "MFTLSettingsResolve(&cfg, ens);                            /* lengths left at 0, from the mesh */",
        "",
        "if (MFTLSettingsDue(cfg.remesh.every, step))   MFTLRemeshEnsemble(ens, &cfg.remesh.params, &st);",
        "if (MFTLSettingsDue(cfg.topology.every, step)) MFTLEnsembleApplyTopologyChanges(ens, &cfg.topology.options, &ts);",
        "if (MFTLSettingsDue(cfg.output.every, step))   MFTLWriteVtu(ens, name, &cfg.output.vtk);",
        "```",
        "",
        "**4. Override on the command line** for one run, without editing the file:",
        "",
        "```bash",
        "mpirun -np 64 ./solver run.toml remesh.every=2 output.prefix=out/run2 domain.cuts=0,0,1",
        "```",
        "",
        "`examples/settings_driven_run.c` is a complete program built this way, with its "
        "file in `examples/settings/`.",
        "",
        '!!! tip "Lengths are in your units, and 0 means *derive it*"',
        "",
        "    MFTL has no length unit of its own. A few lengths are best stated relative to "
        "the mesh, so `0` means: `remesh.target_length` = the mesh's mean edge length, the "
        "edge-length band = 4/5 and 4/3 of it, and the three topology lengths = their "
        "`*_factor` times it. MFTLSettingsResolve() computes them once the bodies exist, "
        "and MFTLSettingsWrite() then prints the numbers the run actually used.",
        "",
        "## Find a key {#settings_find}",
        "",
        '<div class="mftl-settings-filter">',
        '<input type="search" id="mftl-settings-filter" placeholder="Filter the keys: remesh, length, strategy, ghost ..." '
        'aria-label="Filter the settings keys" autocomplete="off">',
        '<span class="mftl-settings-filter-count" aria-live="polite"></span>',
        "</div>",
        "",
        "| Section | What it configures | Keys |",
        "|---|---|---|",
    ]
    for sec in sections:
        out.append(f'| @ref settings_{sec.name} "`[{sec.name}]`" | {_prose(sec.title)} | {len(sec.keys)} |')
    out += [
        "",
        f"Each section lists the keys most runs touch first; the {n_advanced} advanced keys — "
        "tuning, testing and diagnostics — are folded away below them. The C path under each "
        "description is where the key lands in #MFTL_Settings, and the struct named in the "
        "section header documents every field in full.",
        "",
    ]

    for sec in sections:
        owners: list[str] = []
        for key in sec.keys:
            if key.owner and key.owner not in owners:
                owners.append(key.owner)
        common = [k for k in sec.keys if not k.advanced]
        advanced = [k for k in sec.keys if k.advanced]

        out += [
            f'<div class="mftl-settings-section" markdown="1">',
            "",
            f"## `[{sec.name}]` {_prose(sec.title)} {{#settings_{sec.name}}}",
            "",
            _prose(sec.summary),
            "",
        ]
        if owners:
            out += ["Fields documented on " + ", ".join(f"#{o}" for o in owners) + ".", ""]
        if common:
            out += _TABLE_HEAD + [_row(k) for k in common] + [""]
        if advanced:
            out += [f'??? note "Advanced [{sec.name}] keys ({len(advanced)})"', ""]
            out += ["    " + line for line in _TABLE_HEAD + [_row(k) for k in advanced]]
            out.append("")
        out += ["</div>", ""]

    out += [
        '<p class="mftl-settings-empty" hidden>No key matches the filter.</p>',
        "",
        "## Every key at its default {#settings_template}",
        "",
        "A complete settings file equal to the defaults. Copy it as a starting point and delete "
        "what you do not change — or run `mftl_settings template`, which prints the same with "
        "every key documented.",
        "",
        '??? example "The complete default settings file"',
        "",
    ]
    out += ["    " + line if line else "" for line in _template(sections)]
    out.append("")
    return "\n".join(out)


def generate(source_root: str) -> str | None:
    """Read the library and render the page.

    :param source_root: the library checkout.
    :returns: the Markdown source, or ``None`` when the checkout has no settings
        module (an older library), in which case the page is left out.
    """
    if not os.path.isfile(os.path.join(source_root, KEYS_SOURCE)):
        log.info("MFTL: no %s in the library -- the settings reference is left out.", KEYS_SOURCE)
        return None
    try:
        sections = read_table(source_root)
        structs = read_struct_members(source_root)
    except (OSError, ValueError) as error:
        log.warning("MFTL: cannot read the settings table %s: %s", KEYS_SOURCE, error)
        return None
    return render(sections, structs)
