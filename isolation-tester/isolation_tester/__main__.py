"""Deliberately insecure for demonstration. Do not deploy.

CLI entrypoint: `python -m isolation_tester run --config ... --openapi ... --run-name ...`

This is a thin wrapper around pytest - the probes themselves live in
isolation-tester/tests/ and are ordinary pytest tests, run serially
(no pytest-xdist), so evidence and cache-order-sensitive probes behave
deterministically. See isolation-tester/README.md.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pytest

from isolation_tester import runtime

TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# Shared repo-root results/ directory (not isolation-tester/results/): the
# root .gitignore's `results/**/raw/` rule anchors to THIS directory, and
# scanners/ (M5) and sample-deliverables/ (M7) are expected to write their
# own generated evidence under the same tree - see CLAUDE.md's "generate
# numbers from results files" rule.
DEFAULT_RESULTS_DIR = REPO_ROOT / "results" / "isolation-tester"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="isolation_tester")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the isolation probes against a live tenant-api instance")
    run.add_argument("--config", required=True, help="path to a tenants/roles/fixtures YAML config")
    run.add_argument("--openapi", required=True, help="path to the isolation-tested OpenAPI subset")
    run.add_argument("--run-name", required=True, help="name for this run; output goes to <repo>/results/isolation-tester/<run-name>/")
    run.add_argument("--expect", default=None, help="path to an expected-leaks YAML file for this profile")
    run.add_argument("--results-dir", default=None, help=f"override the results base directory (default: {DEFAULT_RESULTS_DIR})")
    run.add_argument("-v", "--verbose", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.error(f"unknown command {args.command!r}")

    results_base = Path(args.results_dir) if args.results_dir else DEFAULT_RESULTS_DIR
    run_dir = results_base / args.run_name

    os.environ[runtime.ENV_CONFIG] = str(Path(args.config).resolve())
    os.environ[runtime.ENV_OPENAPI] = str(Path(args.openapi).resolve())
    os.environ[runtime.ENV_RUN_DIR] = str(run_dir.resolve())
    os.environ[runtime.ENV_RUN_NAME] = args.run_name
    if args.expect:
        os.environ[runtime.ENV_EXPECT] = str(Path(args.expect).resolve())
    elif runtime.ENV_EXPECT in os.environ:
        del os.environ[runtime.ENV_EXPECT]

    pytest_args = [str(TESTS_DIR), "-p", "no:cacheprovider"]
    pytest_args.append("-v" if args.verbose else "-q")

    exit_code = pytest.main(pytest_args)
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
