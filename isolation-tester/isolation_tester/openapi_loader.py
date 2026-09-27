"""Deliberately insecure for demonstration. Do not deploy.

Loads the hand-authored OpenAPI SUBSET describing tenant-api's isolation-
tested surface (SPEC.md section 3.1: "Reads an OpenAPI spec"). Each
operation carries a custom `x-tenant-isolation` vendor extension naming
which generic probe types apply to it and which SPEC.md finding id each
probe is expected to (re)discover on the baseline. Endpoints not listed
here are simply outside this harness's declared surface (see the
`excluded_findings` list in the run config for WHY, per finding id).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


@dataclass(frozen=True)
class Probe:
    type: str
    finding: str | None  # None => positive control, no known finding attached


@dataclass(frozen=True)
class Operation:
    path: str
    method: str
    operation_id: str
    resource: str
    probes: tuple[Probe, ...]
    restore: bool = False
    min_role: str | None = None

    @property
    def id(self) -> str:
        return f"{self.method.upper()} {self.path}"


def load_operations(path: str | Path) -> list[Operation]:
    spec = yaml.safe_load(Path(path).read_text())
    operations: list[Operation] = []
    for path_template, methods in spec.get("paths", {}).items():
        for method in HTTP_METHODS:
            op_raw = methods.get(method)
            if not op_raw:
                continue
            ext = op_raw.get("x-tenant-isolation")
            if not ext:
                continue
            probes = tuple(
                Probe(type=p["type"], finding=p.get("finding")) for p in ext.get("probes", [])
            )
            operations.append(
                Operation(
                    path=path_template,
                    method=method,
                    operation_id=op_raw.get("operationId", f"{method}_{path_template}"),
                    resource=ext.get("resource", "unknown"),
                    probes=probes,
                    restore=bool(ext.get("restore", False)),
                    min_role=ext.get("min_role"),
                )
            )
    return operations


def operations_with_probe(operations: list[Operation], probe_type: str) -> list[tuple[Operation, Probe]]:
    result = []
    for op in operations:
        for probe in op.probes:
            if probe.type == probe_type:
                result.append((op, probe))
    return result
