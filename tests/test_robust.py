"""Tests for timing tolerance, retry, and flake detection.

The flake proof injects a deterministic jitter sequence into the DUT so that a
step lands above its budget on some repeats and below it on others. The test
asserts that detection reports the step as flaky rather than letting a lucky run
pass or an unlucky run fail it outright.
"""

from hilbench.dut import MotorControllerDUT
from hilbench.robust import (
    FlakeOutcome,
    RetryPolicy,
    apply_tolerance,
    detect_flake,
    run_step_with_retry,
)
from hilbench.scenario import Step
from hilbench.transport import InProcessTransport


def test_tolerance_widens_budget():
    step = Step(name="s", command="PING", max_latency_ms=10.0, tolerance=0.5)
    widened = apply_tolerance(step)
    assert widened.max_latency_ms == 15.0
    assert widened.tolerance == 0.0


def test_value_mismatch_is_not_transient():
    policy = RetryPolicy(max_attempts=3)
    transport = InProcessTransport()
    step = Step(name="s", command="PING", expect="OK WRONG")
    result = run_step_with_retry(transport, step, policy)
    assert not result.passed
    assert not any("attempt" in m for m in result.messages)


class _JitterTransport:
    """A transport whose command latency follows a fixed jitter sequence."""

    def __init__(self, delays_ms):
        self._delays = list(delays_ms)
        self._index = 0
        dut = MotorControllerDUT(service_time={})
        dut.service_time = {}
        dut._sleep = lambda _s: None
        self._dut = dut

    def send(self, command: str) -> str:
        import time

        delay = self._delays[self._index % len(self._delays)]
        self._index += 1
        time.sleep(delay / 1000.0)
        return self._dut.send(command)

    def close(self) -> None:
        return None


def test_retry_recovers_a_transient_timing_breach():
    # First attempt is slow, second is fast, so a retry should pass.
    transport = _JitterTransport([40.0, 0.0])
    step = Step(name="s", command="PING", expect="OK PONG", max_latency_ms=10.0)
    policy = RetryPolicy(max_attempts=2, retry_on_timing=True)
    result = run_step_with_retry(transport, step, policy)
    assert result.passed
    assert any("attempt 2" in m for m in result.messages)


def test_flake_is_surfaced_under_injected_jitter():
    # Alternating slow and fast responses straddle the budget, so the step passes
    # on some repeats and fails on others. With no retry, detection must call it
    # flaky rather than report a single stable outcome.
    delays = [40.0, 0.0, 40.0, 0.0, 40.0, 0.0]
    sequence = iter([_JitterTransport([d]) for d in delays])

    def factory():
        return next(sequence)

    step = Step(name="ping", command="PING", expect="OK PONG", max_latency_ms=10.0)
    report = detect_flake(factory, step, repeats=6, policy=RetryPolicy(max_attempts=1))
    assert report.outcome is FlakeOutcome.FLAKY
    assert report.is_flaky
    assert 0 < report.passes < report.repeats


def test_stable_pass_is_not_flagged():
    def factory():
        return InProcessTransport()

    step = Step(name="ping", command="PING", expect="OK PONG", max_latency_ms=500.0)
    report = detect_flake(factory, step, repeats=4)
    assert report.outcome is FlakeOutcome.STABLE_PASS


def test_flake_detection_requires_two_repeats():
    import pytest

    with pytest.raises(ValueError):
        detect_flake(InProcessTransport, Step(name="s", command="PING"), repeats=1)
