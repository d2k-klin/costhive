#!/usr/bin/env python3
"""Check that relative links in Markdown docs resolve to real files.

Scans README.md, CHANGELOG.md, CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md and
everything under docs/. Ignores external (http/https/mailto) links and pure anchors.

    python scripts/check-doc-links.py     # exit 1 if any relative link is broken
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _md_files() -> list[Path]:
    roots = ["README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md"]
    files = [ROOT / name for name in roots if (ROOT / name).exists()]
    files += sorted((ROOT / "docs").rglob("*.md"))
    return files


def _check(md: Path) -> list[str]:
    problems: list[str] = []
    for lineno, line in enumerate(md.read_text().splitlines(), 1):
        for target in LINK_RE.findall(line):
            target = target.strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0].strip()
            if not path_part:
                continue
            resolved = (md.parent / path_part).resolve()
            if not resolved.exists():
                problems.append(f"{md.relative_to(ROOT)}:{lineno}: broken link -> {target}")
    return problems


def main() -> int:
    problems: list[str] = []
    for md in _md_files():
        problems.extend(_check(md))
    if problems:
        print("Broken relative links found:")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"All relative doc links resolve ({len(_md_files())} files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
