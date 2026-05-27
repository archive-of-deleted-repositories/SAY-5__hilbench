"""Scenario execution throughput benchmark.

This measures how many scenario steps the runner can drive per second against the
in process DUT with service times zeroed, so the number reflects framework
overhead (assertion evaluation, latency capture, result assembly) rather than the
device's modeled delays. It builds one large scenario batch, times the run with a
monotonic clock, and prints a small JSON document.

The CI smoke gate compares the measured steps per second against a checked in
baseline and fails if throughput drops by more than a set fraction.
"""

from __future__ import annotations

import argparse
import json
import time

from hilbench.dut import MotorControllerDUT
from hilbench.runner import run_scenario
from hilbench.scenario import Scenario, Step
from hilbench.transport import InProcessTransport


def build_batch(scenarios: int, steps_per_scenario: int) -> list[Scenario]:
    batch: list[Scenario] = []
    for index in range(scenarios):
        steps = tuple(
            Step(name=f"ping_{i}", command="PING", expect="OK PONG")
            for i in range(steps_per_scenario)
        )
        batch.append(Scenario(name=f"bench_{index}", steps=steps))
    return batch


def _zero_latency_transport() -> InProcessTransport:
    # Remove modeled service time so the benchmark isolates framework overhead.
    dut = MotorControllerDUT(service_time={}, latency_offset=0.0)
    dut.service_time = {}
    dut._sleep = lambda _seconds: None
    return InProcessTransport(dut)


def measure(scenarios: int, steps_per_scenario: int, repeats: int) -> dict[str, float]:
    batch = build_batch(scenarios, steps_per_scenario)
    total_steps = scenarios * steps_per_scenario
    best = float("inf")
    for _ in range(repeats):
        transport = _zero_latency_transport()
        start = time.perf_counter()
        for scenario in batch:
            run_scenario(transport, scenario)
        elapsed = time.perf_counter() - start
        best = min(best, elapsed)
    return {
        "total_steps": float(total_steps),
        "seconds": best,
        "steps_per_second": total_steps / best,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Throughput benchmark")
    parser.add_argument("--scenarios", type=int, default=200)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    result = measure(args.scenarios, args.steps, args.repeats)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
