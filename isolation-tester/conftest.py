"""Deliberately insecure for demonstration. Do not deploy.

Root conftest so `isolation_tester` is importable from both tests/ (the
live probes, run via `python -m isolation_tester`) and unit_tests/ (offline,
mocked, run directly via `pytest unit_tests/` in CI) without installing the
package.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
