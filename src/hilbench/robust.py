"""Timing tolerance, retry, and flake detection.

A real bench is noisy. A single slow response can be a genuine regression or a
one off scheduling hiccup. This module adds three controls on top of the plain
runner so timing assertions stay meaningful under noise without hiding real
failures.

Timing tolerance
    A step's latency budget can carry a tolerance fraction. The effective budget
    is ``max_latency_ms * (1 + tolerance)``. This absorbs small, expected jitter
    without widening the budget itself, which keeps the documented intent
    separate from the noise allowance.

Retry on transient
    A step may be retried a bounded number of times. Only failures classed as
    transient are retried: a timing breach, or a response that matches a caller
    supplied transient pattern. A value mismatch is never retried, because a
    wrong value is a real defect, not noise. The policy is documented in
    ``RetryPolicy`` and surfaced in the result so a passing retry is visible.

Flake detection
    Running a step ``repeats`` times and recording how many pass classes the step
    as stable (all pass), failing (all fail), or flaky (a mix). A flaky step is
    reported as a distinct outcome so it is surfaced rather than silently passing
    on a lucky run or silently failing on an unlucky one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from hilbench.runner import StepResult, run_step
from hilbench.scenario import Step
from hilbench.transport import Transport


@dataclass(frozen=True)
class RetryPolicy:
    """How a step may be retried.

    Only transient failures are retried. A timing budget breach is transient by
    default. A response is also transient if it matches ``transient_pattern``. A
    value mismatch is never transient.
    """

    max_attempts: int = 1
    retry_on_timing: bool = True
    transient_pattern: str | None = None

    def is_transient(self, result: StepResult) -> bool:
        if result.passed:
            return False
        timing_only = all("budget" in message for message in result.messages)
        if self.retry_on_timing and result.messages and timing_only:
            return True
        if self.transient_pattern is not None:
            if re.search(self.transient_pattern, result.response):
                return True
        return False


def apply_tolerance(step: Step) -> Step:
    """Return a step whose budget is widened by its tolerance fraction.

    A step with no budget or no tolerance is returned unchanged.
    """
    if step.max_latency_ms is None or not step.tolerance:
        return step
    widened = step.max_latency_ms * (1.0 + step.tolerance)
    return Step(
        name=step.name,
        command=step.command,
        expect=step.expect,
        expect_contains=step.expect_contains,
        max_latency_ms=widened,
        tolerance=0.0,
        wait_ms=step.wait_ms,
    )


def run_step_with_retry(
    transport: Transport, step: Step, policy: RetryPolicy
) -> StepResult:
    """Run a step, retrying transient failures up to the policy limit."""
    effective = apply_tolerance(step)
    attempts = max(1, policy.max_attempts)
    last: StepResult | None = None
    for attempt in range(1, attempts + 1):
        result = run_step(transport, effective)
        last = result
        if result.passed:
            if attempt > 1:
                result.messages.append(f"passed on attempt {attempt}")
            return result
        if attempt < attempts and policy.is_transient(result):
            continue
        return result
    assert last is not None
    return last


class FlakeOutcome(str, Enum):
    STABLE_PASS = "stable_pass"
    STABLE_FAIL = "stable_fail"
    FLAKY = "flaky"


@dataclass
class FlakeReport:
    name: str
    repeats: int
    passes: int
    outcome: FlakeOutcome
    samples: list[StepResult] = field(default_factory=list)

    @property
    def is_flaky(self) -> bool:
        return self.outcome is FlakeOutcome.FLAKY


def detect_flake(
    transport_factory: object,
    step: Step,
    repeats: int,
    policy: RetryPolicy | None = None,
) -> FlakeReport:
    """Run a step ``repeats`` times and classify it as stable or flaky.

    ``transport_factory`` is a callable returning a fresh transport per repeat so
    each run starts from a clean device state. A step that passes on some runs and
    fails on others is reported as flaky.
    """
    if repeats < 2:
        raise ValueError("flake detection needs at least two repeats")
    policy = policy or RetryPolicy()
    samples: list[StepResult] = []
    passes = 0
    for _ in range(repeats):
        transport = transport_factory()  # type: ignore[operator]
        try:
            result = run_step_with_retry(transport, step, policy)
        finally:
            close = getattr(transport, "close", None)
            if callable(close):
                close()
        samples.append(result)
        if result.passed:
            passes += 1
    if passes == repeats:
        outcome = FlakeOutcome.STABLE_PASS
    elif passes == 0:
        outcome = FlakeOutcome.STABLE_FAIL
    else:
        outcome = FlakeOutcome.FLAKY
    return FlakeReport(
        name=step.name,
        repeats=repeats,
        passes=passes,
        outcome=outcome,
        samples=samples,
    )
