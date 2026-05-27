"""Compare a fresh throughput measurement against a checked in baseline.

The gate fails if measured throughput drops below the baseline by more than the
allowed drift fraction. It does not fail when throughput improves. This is a
smoke gate, not a precise benchmark, so the drift allowance is generous to absorb
shared CI runner noise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmarks.throughput import measure


def main() -> int:
    parser = argparse.ArgumentParser(description="Throughput regression gate")
    parser.add_argument("--baseline", default="benchmarks/baseline.json")
    parser.add_argument("--drift", type=float, default=0.30)
    parser.add_argument("--scenarios", type=int, default=200)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    gate_floor = float(baseline["gate_floor_steps_per_second"])
    floor = gate_floor * (1.0 - args.drift)

    result = measure(args.scenarios, args.steps, args.repeats)
    measured = result["steps_per_second"]

    print(
        f"gate floor {gate_floor:.0f} steps/s, drift band floor {floor:.0f} "
        f"steps/s, measured {measured:.0f} steps/s"
    )
    if measured < floor:
        print("FAIL: throughput regressed beyond the allowed drift")
        return 1
    print("OK: throughput within the allowed drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
