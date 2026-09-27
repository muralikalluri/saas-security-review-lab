"""Deliberately insecure for demonstration. Do not deploy.

Aggregates probe results into isolation-matrix.md + isolation-matrix.json
(SPEC.md section 3.4/3.5), and decides the process exit code.

Exit code policy (see isolation-tester/README.md for the rationale):
  0 - actual leaked-finding set matches what was expected for this profile
      (or, with no expectations file, simply no leaks and no errors).
  1 - a leak was found that wasn't expected, or an expected leak went
      missing (a regression - baseline stopped finding something).
  2 - the run itself is not trustworthy: a positive control failed, an
      actor's login failed, or any probe errored. Never conflate this with
      "0 leaks found".
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from isolation_tester.oracle import Verdict


@dataclass
class ProbeResult:
    probe_id: str
    probe_type: str
    finding: str | None
    actor: str
    method: str
    path: str
    verdict: str
    detail: str
    evidence_path: str | None = None


@dataclass
class RunResult:
    run_name: str
    base_url: str
    started_at: str
    results: list[ProbeResult] = field(default_factory=list)
    controls_ok: bool = True
    preflight_ok: bool = True


class MatrixCollector:
    def __init__(self, run_name: str, base_url: str):
        self.run = RunResult(
            run_name=run_name,
            base_url=base_url,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

    def record(self, result: ProbeResult) -> None:
        self.run.results.append(result)

    def mark_control_failed(self) -> None:
        self.run.controls_ok = False

    def mark_preflight_failed(self) -> None:
        self.run.preflight_ok = False

    def leaked_findings(self) -> set[str]:
        return {r.finding for r in self.run.results if r.verdict == Verdict.LEAK.value and r.finding}

    def unattributed_leaks(self) -> list[ProbeResult]:
        """LEAKs on a `finding: null` probe (a positive control such as
        GET /customers/{id} or /invoices/search) have no finding id to add
        to leaked_findings(), so they could never move actual != expected
        and would silently exit 0. These endpoints are declared exactly
        BECAUSE they must always be denied - a leak here is never expected
        under any profile, so it must always fail the run on its own.
        """
        return [r for r in self.run.results if r.verdict == Verdict.LEAK.value and not r.finding]

    def has_errors(self) -> bool:
        return any(r.verdict == Verdict.ERROR.value for r in self.run.results) or not self.run.controls_ok or not self.run.preflight_ok

    def compute_exit_code(self, expected: set[str] | None) -> int:
        if self.has_errors():
            return 2
        if self.unattributed_leaks():
            return 1
        actual = self.leaked_findings()
        if expected is None:
            return 1 if actual else 0
        return 0 if actual == expected else 1

    def write(
        self,
        out_dir: Path,
        expected: set[str] | None,
        excluded_findings: list | None = None,
    ) -> tuple[Path, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "isolation-matrix.json"
        md_path = out_dir / "isolation-matrix.md"

        exit_code = self.compute_exit_code(expected)
        excluded_rows = [
            ProbeResult(
                probe_id=f"excluded:{ex.id}",
                probe_type="excluded",
                finding=ex.id,
                actor="-",
                method="-",
                path="-",
                verdict=Verdict.EXCLUDED.value,
                detail=ex.reason.strip(),
            )
            for ex in (excluded_findings or [])
        ]
        payload = {
            "run_name": self.run.run_name,
            "base_url": self.run.base_url,
            "started_at": self.run.started_at,
            "preflight_ok": self.run.preflight_ok,
            "controls_ok": self.run.controls_ok,
            "expected_leaks": sorted(expected) if expected is not None else None,
            "actual_leaks": sorted(self.leaked_findings()),
            "exit_code": exit_code,
            "results": [asdict(r) for r in self.run.results] + [asdict(r) for r in excluded_rows],
        }
        json_path.write_text(json.dumps(payload, indent=2))
        md_path.write_text(self._render_markdown(payload))
        return md_path, json_path

    def _render_markdown(self, payload: dict) -> str:
        lines = [
            "# Isolation matrix",
            "",
            "> Deliberately insecure for demonstration. Do not deploy. Run locally only.",
            "",
            f"- Run: `{payload['run_name']}`",
            f"- Target: `{payload['base_url']}`",
            f"- Started: {payload['started_at']}",
            f"- Preflight OK: {payload['preflight_ok']}",
            f"- Positive controls OK: {payload['controls_ok']}",
            f"- Expected leaked findings: {payload['expected_leaks']}",
            f"- Actual leaked findings: {payload['actual_leaks']}",
            f"- Exit code: **{payload['exit_code']}** "
            f"({'PASS' if payload['exit_code'] == 0 else ('LEAK/REGRESSION' if payload['exit_code'] == 1 else 'RUN ERROR - not trustworthy')})",
            "",
            "This file, its sibling `isolation-matrix.json`, and the "
            "per-probe evidence in `raw/` are all generated by "
            "`python -m isolation_tester`. See CLAUDE.md: never hand-edit "
            "the numbers below.",
            "",
            "## Endpoint x actor matrix",
            "",
            "| Finding | Probe | Method & Path | Actor | Verdict | Detail | Evidence |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in payload["results"]:
            evidence = f"`{r['evidence_path']}`" if r["evidence_path"] else ""
            finding = r["finding"] or "(control)"
            verdict_badge = {
                "DENIED": "PASS (denied)",
                "LEAK": "**LEAK**",
                "ERROR": "ERROR",
                "EXCLUDED": "excluded",
                "NOT_RUN": "not run",
                "ALLOWED": "PASS (owner allowed)",
            }.get(r["verdict"], r["verdict"])
            lines.append(
                f"| {finding} | {r['probe_type']} | `{r['method']} {r['path']}` | "
                f"{r['actor']} | {verdict_badge} | {r['detail']} | {evidence} |"
            )
        return "\n".join(lines) + "\n"
