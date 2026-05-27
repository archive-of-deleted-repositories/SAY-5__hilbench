"""Scenario model and loader.

A scenario is a named sequence of steps. Each step sends one command and may
assert on the response value and on the response latency. Scenarios are written
in YAML and loaded into typed dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Step:
    """A single command and its expectations."""

    name: str
    command: str
    expect: str | None = None
    expect_contains: str | None = None
    # Maximum allowed response latency in milliseconds. None disables the check.
    max_latency_ms: float | None = None
    # Fraction by which the latency budget is widened to absorb expected jitter.
    tolerance: float = 0.0
    wait_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.expect is not None and self.expect_contains is not None:
            raise ValueError(
                f"step {self.name!r} sets both expect and expect_contains"
            )


@dataclass(frozen=True)
class Scenario:
    """A named ordered list of steps with optional parameters."""

    name: str
    steps: tuple[Step, ...]
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)


def _step_from_dict(raw: dict[str, Any]) -> Step:
    if "name" not in raw or "command" not in raw:
        raise ValueError("each step needs a name and a command")
    return Step(
        name=str(raw["name"]),
        command=str(raw["command"]),
        expect=_opt_str(raw.get("expect")),
        expect_contains=_opt_str(raw.get("expect_contains")),
        max_latency_ms=_opt_float(raw.get("max_latency_ms")),
        tolerance=float(raw.get("tolerance", 0.0)),
        wait_ms=float(raw.get("wait_ms", 0.0)),
    )


def _opt_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _opt_float(value: Any) -> float | None:
    return None if value is None else float(value)


def scenario_from_dict(raw: dict[str, Any]) -> Scenario:
    """Build a scenario from a parsed mapping."""
    if "name" not in raw or "steps" not in raw:
        raise ValueError("a scenario needs a name and steps")
    steps = tuple(_step_from_dict(s) for s in raw["steps"])
    return Scenario(
        name=str(raw["name"]),
        steps=steps,
        description=str(raw.get("description", "")),
        params=dict(raw.get("params", {})),
    )


def load_scenario(path: str | Path) -> Scenario:
    """Load a single scenario from a YAML file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level of a scenario must be a mapping")
    return scenario_from_dict(data)
