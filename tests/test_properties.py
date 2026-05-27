"""Property tests for the assertion engine.

These check invariants that must hold for any step the runner evaluates:

* a step whose expectation matches the response and whose latency is within
  budget always passes,
* a value mismatch always fails,
* a latency above the budget always fails.

The DUT response is fixed so the properties isolate the evaluation logic from
device behavior. A stub transport returns a chosen response with a chosen
latency by spending time before replying.
"""

from __future__ import annotations

import time

from hypothesis import given, settings
from hypothesis import strategies as st

from hilbench.runner import Outcome, run_step
from hilbench.scenario import Step


class _StubTransport:
    def __init__(self, response: str) -> None:
        self.response = response

    def send(self, command: str) -> str:
        return self.response

    def close(self) -> None:
        return None


tokens = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789=_ ", min_size=1, max_size=24
)


@given(response=tokens, budget=st.floats(min_value=100.0, max_value=5000.0))
@settings(max_examples=50, deadline=None)
def test_matching_value_within_budget_passes(response, budget):
    transport = _StubTransport(response)
    step = Step(name="s", command="X", expect=response, max_latency_ms=budget)
    result = run_step(transport, step)
    assert result.outcome is Outcome.PASS


@given(
    response=tokens,
    expected=tokens,
)
@settings(max_examples=50, deadline=None)
def test_value_mismatch_always_fails(response, expected):
    if response == expected:
        return
    transport = _StubTransport(response)
    step = Step(name="s", command="X", expect=expected)
    result = run_step(transport, step)
    assert result.outcome is Outcome.FAIL


class _SlowTransport:
    def __init__(self, response: str, delay_s: float) -> None:
        self.response = response
        self.delay_s = delay_s

    def send(self, command: str) -> str:
        time.sleep(self.delay_s)
        return self.response

    def close(self) -> None:
        return None


@given(budget=st.floats(min_value=1.0, max_value=20.0))
@settings(max_examples=20, deadline=None)
def test_latency_over_budget_always_fails(budget):
    # Spend at least twice the budget so the step must breach it.
    transport = _SlowTransport("OK", delay_s=(budget / 1000.0) * 2)
    step = Step(name="s", command="X", expect="OK", max_latency_ms=budget)
    result = run_step(transport, step)
    assert result.outcome is Outcome.FAIL
    assert any("budget" in m for m in result.messages)
