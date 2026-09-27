"""Deliberately insecure for demonstration. Do not deploy.

Loads a per-profile expected-leak set. The tool exits 0 only if the actual
leaked-finding set equals this set exactly - so a regression where the
baseline stops finding a known flaw (e.g. someone accidentally fixes A-01
while "just refactoring") fails the run just as loudly as a genuinely new
leak would.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def load_expected(path: str | Path) -> set[str]:
    raw = yaml.safe_load(Path(path).read_text())
    return set(raw.get("expected_leaks", []) or [])
