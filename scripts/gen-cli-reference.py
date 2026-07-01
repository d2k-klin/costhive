#!/usr/bin/env python3
"""Generate the CLI command/flag reference in docs/usage.md from the Typer app.

Keeps the usage docs from drifting: the reference tables between the
`<!-- BEGIN CLI REFERENCE -->` / `<!-- END CLI REFERENCE -->` markers are rebuilt
from the live CLI definition (introspecting Typer's OptionInfo models, no click
dependency).

    python scripts/gen-cli-reference.py           # rewrite the block in place
    python scripts/gen-cli-reference.py --check   # exit 1 if the block is stale (CI)
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import typer.models

from costhive.cli import app

DOC = Path(__file__).resolve().parent.parent / "docs" / "usage.md"
BEGIN = "<!-- BEGIN CLI REFERENCE -->"
END = "<!-- END CLI REFERENCE -->"


def _escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def _type_name(annotation) -> str:
    if annotation is bool:
        return "flag"
    return getattr(annotation, "__name__", str(annotation)).replace("typing.", "")


def _default(info: typer.models.OptionInfo, annotation) -> str:
    if annotation is bool:
        return "flag"
    if info.default in (None, "", [], (), Ellipsis):
        return "—"
    return f"`{info.default}`"


def _render() -> str:
    commands = {(c.name or c.callback.__name__): c for c in app.registered_commands}
    lines: list[str] = []
    for name in sorted(commands):
        cmd = commands[name]
        lines.append(f"### `costhive {name}`\n")
        doc = (cmd.help or cmd.callback.__doc__ or "").strip()
        if doc:
            lines.append(f"{doc.splitlines()[0]}\n")
        params = [
            (p, p.default)
            for p in inspect.signature(cmd.callback).parameters.values()
            if isinstance(p.default, typer.models.OptionInfo) and p.name != "_version"
        ]
        if not params:
            lines.append("_No options._\n")
            continue
        lines.append("| Flag | Type | Default | Description |")
        lines.append("|------|------|---------|-------------|")
        for param, info in params:
            flags = ", ".join(f"`{d}`" for d in (info.param_decls or (f"--{param.name}",)))
            lines.append(
                f"| {flags} | {_type_name(param.annotation)} | "
                f"{_default(info, param.annotation)} | {_escape(info.help)} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    check = "--check" in sys.argv[1:]
    text = DOC.read_text()
    if BEGIN not in text or END not in text:
        print(f"markers not found in {DOC}", file=sys.stderr)
        return 2
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    new = f"{head}{BEGIN}\n\n{_render()}\n{END}{tail}"
    if check:
        if new != text:
            print("docs/usage.md CLI reference is stale — run: python scripts/gen-cli-reference.py")
            return 1
        print("CLI reference is up to date.")
        return 0
    DOC.write_text(new)
    print(f"Updated CLI reference in {DOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
