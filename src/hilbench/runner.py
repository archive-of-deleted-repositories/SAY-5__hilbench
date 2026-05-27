"""Scenario runner with per step timing capture and assertions.

The runner drives a transport through a scenario. For each step it sends the
command, measures the round trip latency with a monotonic clock, and evaluates
value and timing assertions. Results are collected into structured objects that
the report writers consume.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from hilbench.scenario import Scenario, Step
from hilbench.transport import Transport


class Outcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass
class StepResult:
    name: str
    command: str
    response: str
    latency_ms: float
    outcome: Outcome
    messages: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.outcome is Outcome.PASS


@dataclass
class ScenarioResult:
    name: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(step.passed for step in self.steps)

    @property
    def total_latency_ms(self) -> float:
        return sum(step.latency_ms for step in self.steps)


def _evaluate(step: Step, response: str, latency_ms: float) -> tuple[Outcome, list[str]]:
    messages: list[str] = []
    if step.expect is not None and response != step.expect:
        messages.append(f"expected {step.expect!r} but got {response!r}")
    if step.expect_contains is not None and step.expect_contains not in response:
        messages.append(
            f"expected response to contain {step.expect_contains!r} "
            f"but got {response!r}"
        )
    if step.max_latency_ms is not None and latency_ms > step.max_latency_ms:
        messages.append(
            f"latency {latency_ms:.3f} ms exceeded budget "
            f"{step.max_latency_ms:.3f} ms"
        )
    outcome = Outcome.PASS if not messages else Outcome.FAIL
    return outcome, messages


def run_step(transport: Transport, step: Step) -> StepResult:
    """Send one step, measure latency, and evaluate assertions."""
    if step.wait_ms > 0:
        time.sleep(step.wait_ms / 1000.0)
    start = time.perf_counter()
    response = transport.send(step.command)
    latency_ms = (time.perf_counter() - start) * 1000.0
    outcome, messages = _evaluate(step, response, latency_ms)
    return StepResult(
        name=step.name,
        command=step.command,
        response=response,
        latency_ms=latency_ms,
        outcome=outcome,
        messages=messages,
    )


def run_scenario(transport: Transport, scenario: Scenario) -> ScenarioResult:
    """Run every step of a scenario in order and collect results."""
    result = ScenarioResult(name=scenario.name)
    for step in scenario.steps:
        result.steps.append(run_step(transport, step))
    return result
