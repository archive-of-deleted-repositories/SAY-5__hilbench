"""Parameterized scenario matrices.

A matrix is one scenario template expanded over many parameter sets (cases).
Template fields use ``{name}`` placeholders that are filled from each case's
parameters. Each case runs as its own scenario, so the JUnit report carries a
testsuite per case and the JSON report carries a scenario per case. A consolidated
view reports the per case pass/fail breakdown.

A matrix file looks like:

    name: speed_sweep
    template:
      steps:
        - name: arm
          command: ARM
          expect: OK armed
        - name: set_speed
          command: "SETSPEED {speed}"
          expect: "OK speed={speed}"
          max_latency_ms: 50
    cases:
      - name: low
        params: {speed: 100}
      - name: high
        params: {speed: 9000}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from hilbench.runner import ScenarioResult, run_scenario
from hilbench.scenario import Scenario, scenario_from_dict
from hilbench.transport import InProcessTransport


@dataclass(frozen=True)
class MatrixCase:
    name: str
    params: dict[str, Any]


@dataclass(frozen=True)
class ScenarioMatrix:
    name: str
    template: dict[str, Any]
    cases: tuple[MatrixCase, ...]
    description: str = ""


def _fill(value: Any, params: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return value.format(**params)
    if isinstance(value, dict):
        return {key: _fill(item, params) for key, item in value.items()}
    if isinstance(value, list):
        return [_fill(item, params) for item in value]
    return value


def expand_case(matrix: ScenarioMatrix, case: MatrixCase) -> Scenario:
    """Build a concrete scenario for one case by filling template placeholders."""
    filled = _fill(matrix.template, case.params)
    raw: dict[str, Any] = {
        "name": f"{matrix.name}[{case.name}]",
        "description": matrix.description,
        "steps": filled["steps"],
        "params": case.params,
    }
    return scenario_from_dict(raw)


def expand(matrix: ScenarioMatrix) -> list[Scenario]:
    """Expand a matrix into one scenario per case."""
    return [expand_case(matrix, case) for case in matrix.cases]


def matrix_from_dict(raw: dict[str, Any]) -> ScenarioMatrix:
    if "name" not in raw or "template" not in raw or "cases" not in raw:
        raise ValueError("a matrix needs a name, a template, and cases")
    cases = tuple(
        MatrixCase(name=str(c["name"]), params=dict(c.get("params", {})))
        for c in raw["cases"]
    )
    return ScenarioMatrix(
        name=str(raw["name"]),
        template=dict(raw["template"]),
        cases=cases,
        description=str(raw.get("description", "")),
    )


def load_matrix(path: str | Path) -> ScenarioMatrix:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level of a matrix must be a mapping")
    return matrix_from_dict(data)


@dataclass
class MatrixResult:
    name: str
    cases: list[ScenarioResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(case.passed for case in self.cases)

    def breakdown(self) -> dict[str, bool]:
        """Map each case scenario name to its pass/fail."""
        return {case.name: case.passed for case in self.cases}


def run_matrix(matrix: ScenarioMatrix) -> MatrixResult:
    """Run every case of a matrix against a fresh DUT and collect results."""
    result = MatrixResult(name=matrix.name)
    for scenario in expand(matrix):
        transport = InProcessTransport()
        result.cases.append(run_scenario(transport, scenario))
        transport.close()
    return result
