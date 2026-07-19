#!/usr/bin/env python3
"""Re-apply fork-local wrangler.toml overrides after syncing upstream.

Preserves:
  - run_worker_first = false
  - no [[r2_buckets]] bindings (attachments / R2 not used on this fork)

Everything else is left as upstream (or the merge result) provided it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WRANGLER = Path("wrangler.toml")


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def force_run_worker_first_false(text: str) -> str:
    # Only match horizontal trailing whitespace — do not let \s eat newlines.
    pattern = re.compile(
        r"^([ \t]*run_worker_first[ \t]*=[ \t]*)(true|false)[ \t]*$",
        re.MULTILINE | re.IGNORECASE,
    )

    def repl(match: re.Match[str]) -> str:
        if match.group(2).lower() == "false":
            return match.group(0)
        return f"{match.group(1)}false"

    if pattern.search(text):
        return pattern.sub(repl, text)

    # Upstream usually has this under [assets]; insert if missing.
    assets = re.compile(r"(^\[assets\][ \t]*\n(?:.*\n)*?)(?=^\[|\Z)", re.MULTILINE)
    match = assets.search(text)
    if not match:
        return text
    block = match.group(1)
    if "run_worker_first" in block:
        return text
    insertion = block.rstrip("\n") + "\nrun_worker_first = false\n\n"
    return text[: match.start(1)] + insertion + text[match.end(1) :]


def strip_r2_buckets(text: str) -> str:
    # Remove each [[r2_buckets]] table (header + following key/blank lines until next section).
    pattern = re.compile(
        r"(?m)^\[\[r2_buckets\]\][ \t]*\n(?:^[^\n\[][^\n]*\n|^[ \t]*\n)*"
    )
    cleaned, n = pattern.subn("", text)
    if n:
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def main() -> int:
    if not WRANGLER.is_file():
        print(f"error: {WRANGLER} not found", file=sys.stderr)
        return 1

    original = normalize_newlines(WRANGLER.read_text(encoding="utf-8"))
    updated = force_run_worker_first_false(original)
    updated = strip_r2_buckets(updated)

    if updated == original:
        print("wrangler.toml already matches fork overrides")
        return 0

    WRANGLER.write_text(updated, encoding="utf-8", newline="\n")
    print("applied fork overrides to wrangler.toml:")
    print("  - run_worker_first = false")
    print("  - removed [[r2_buckets]] sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
