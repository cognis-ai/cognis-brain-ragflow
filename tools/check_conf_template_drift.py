#!/usr/bin/env python3
"""Gate the Cognis service-conf template against upstream drift (B3.1).

Gate 2 (2026-06-10) condition on theming-spec item B3.1: the in-image shadow
copy `cognis-brand-assets/service_conf.cognis.yaml.template` may differ from
upstream's `docker/service_conf.yaml.template` ONLY inside explicitly marked
Cognis regions (the header + the smtp block). The two files WILL drift at
upstream rebases; this script turns the spec's "diff the two templates at
every rebase" prose into a hard CI failure.

Mechanics:
  - From the Cognis template, drop every region delimited (inclusive) by
    lines starting with `# === COGNIS BEGIN` / `# === COGNIS END`.
  - From the upstream template, drop its commented-out smtp block: the line
    exactly `# smtp:` plus the contiguous run of `#  <indented>` lines that
    follow it (that block is what the Cognis smtp region replaces).
  - The remainders must be byte-identical. Anything else = upstream changed
    shape → re-derive the Cognis template and re-run the branding e2e gate.

Exit codes: 0 = in sync; 1 = drift or structural failure (message on stderr).

Stdlib only; runs anywhere (CI: .github/workflows/brand-guard.yml and
publish-ghcr.yml; locally: `python tools/check_conf_template_drift.py`).
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = REPO_ROOT / "docker" / "service_conf.yaml.template"
COGNIS = REPO_ROOT / "cognis-brand-assets" / "service_conf.cognis.yaml.template"

BEGIN = "# === COGNIS BEGIN"
END = "# === COGNIS END"
SMTP_HEAD = "# smtp:"
SMTP_BODY = re.compile(r"^#\s{2,}\S")  # commented, nested-indented keys


def fail(msg: str) -> "NoReturn":  # noqa: F821 - py3.8-friendly annotation
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def strip_cognis_regions(lines: list[str]) -> list[str]:
    out: list[str] = []
    depth = 0
    regions = 0
    for i, line in enumerate(lines, start=1):
        if line.startswith(BEGIN):
            if depth:
                fail(f"nested COGNIS BEGIN at {COGNIS.name}:{i}")
            depth = 1
            regions += 1
            continue
        if line.startswith(END):
            if not depth:
                fail(f"COGNIS END without BEGIN at {COGNIS.name}:{i}")
            depth = 0
            continue
        if not depth:
            out.append(line)
    if depth:
        fail(f"unterminated COGNIS BEGIN region in {COGNIS.name}")
    if regions < 2:
        fail(
            f"expected >=2 marked Cognis regions (header + smtp) in {COGNIS.name}, "
            f"found {regions} — markers were edited or removed"
        )
    return out


def strip_upstream_smtp(lines: list[str]) -> list[str]:
    try:
        start = next(i for i, line in enumerate(lines) if line == SMTP_HEAD)
    except StopIteration:
        fail(
            f"upstream smtp block ('{SMTP_HEAD}') not found in {UPSTREAM.name} — "
            "upstream template changed shape; re-derive the Cognis template"
        )
    end = start + 1
    while end < len(lines) and SMTP_BODY.match(lines[end]):
        end += 1
    return lines[:start] + lines[end:]


def main() -> int:
    for p in (UPSTREAM, COGNIS):
        if not p.is_file():
            fail(f"missing template: {p}")
    cognis = strip_cognis_regions(COGNIS.read_text(encoding="utf-8").splitlines())
    upstream = strip_upstream_smtp(UPSTREAM.read_text(encoding="utf-8").splitlines())
    if cognis == upstream:
        print(
            "OK: cognis service-conf template matches upstream outside the "
            "marked Cognis regions"
        )
        return 0
    diff = difflib.unified_diff(
        upstream,
        cognis,
        fromfile=f"{UPSTREAM.relative_to(REPO_ROOT)} (minus smtp block)",
        tofile=f"{COGNIS.relative_to(REPO_ROOT)} (minus COGNIS regions)",
        lineterm="",
    )
    print("\n".join(diff), file=sys.stderr)
    fail(
        "service-conf template drift OUTSIDE the marked Cognis regions — "
        "re-derive cognis-brand-assets/service_conf.cognis.yaml.template from "
        "docker/service_conf.yaml.template (keep only the marked regions "
        "different), then re-run this check"
    )
    return 1  # unreachable


if __name__ == "__main__":
    sys.exit(main())
