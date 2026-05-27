from hilbench.runner import Outcome, run_scenario, run_step
from hilbench.scenario import Scenario, Step
from hilbench.transport import InProcessTransport


def test_passing_step_records_latency():
    transport = InProcessTransport()
    step = Step(name="ping", command="PING", expect="OK PONG", max_latency_ms=500)
    result = run_step(transport, step)
    assert result.outcome is Outcome.PASS
    assert result.latency_ms >= 0


def test_value_mismatch_fails():
    transport = InProcessTransport()
    step = Step(name="ping", command="PING", expect="OK NOPE")
    result = run_step(transport, step)
    assert result.outcome is Outcome.FAIL
    assert any("expected" in m for m in result.messages)


def test_timing_budget_breach_fails():
    transport = InProcessTransport()
    step = Step(name="ping", command="PING", expect="OK PONG", max_latency_ms=0.0)
    result = run_step(transport, step)
    assert result.outcome is Outcome.FAIL
    assert any("budget" in m for m in result.messages)


def test_expect_contains():
    transport = InProcessTransport()
    step = Step(name="status", command="STATUS", expect_contains="state=IDLE")
    result = run_step(transport, step)
    assert result.outcome is Outcome.PASS


def test_run_scenario_aggregates():
    transport = InProcessTransport()
    scenario = Scenario(
        name="cycle",
        steps=(
            Step(name="arm", command="ARM", expect="OK armed"),
            Step(name="start", command="START", expect="OK running"),
        ),
    )
    result = run_scenario(transport, scenario)
    assert result.passed
    assert len(result.steps) == 2
