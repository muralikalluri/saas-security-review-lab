"""Deliberately insecure for demonstration. Do not deploy.

Process-wide runtime context, read from environment variables set by
`python -m isolation_tester` before pytest is invoked. Kept as plain env
vars (rather than pytest fixtures) because test files need this data at
COLLECTION time to build `pytest.mark.parametrize` tables, which runs
before any fixture is available.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from isolation_tester.config import RunConfig, load_config
from isolation_tester.expectations import load_expected
from isolation_tester.openapi_loader import Operation, load_operations

ENV_CONFIG = "ISOLATION_TESTER_CONFIG"
ENV_OPENAPI = "ISOLATION_TESTER_OPENAPI"
ENV_RUN_DIR = "ISOLATION_TESTER_RUN_DIR"
ENV_RUN_NAME = "ISOLATION_TESTER_RUN_NAME"
ENV_EXPECT = "ISOLATION_TESTER_EXPECT"


@lru_cache(maxsize=1)
def get_config() -> RunConfig:
    return load_config(os.environ[ENV_CONFIG])


@lru_cache(maxsize=1)
def get_operations() -> list[Operation]:
    return load_operations(os.environ[ENV_OPENAPI])


def get_run_dir() -> Path:
    return Path(os.environ[ENV_RUN_DIR])


def get_run_name() -> str:
    return os.environ.get(ENV_RUN_NAME, "run")


def get_expected() -> set[str] | None:
    expect_path = os.environ.get(ENV_EXPECT)
    if not expect_path:
        return None
    return load_expected(expect_path)
