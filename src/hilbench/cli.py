"""Command line entry point for running scenarios.

The CLI loads one or more scenario files, runs each against a fresh in process
DUT, writes the JSON and JUnit reports, prints the human summary, and exits non
zero if any step failed so that CI fails the build.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hilbench.report import render_summary, write_json, write_junit
from hilbench.runner import ScenarioResult, run_scenario
from hilbench.scenario import load_scenario
from hilbench.transport import InProcessTransport


def _gather_scenarios(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.glob("*.yaml")))
        else:
            files.append(path)
    return files


def run(paths: list[str], json_path: str, junit_path: str) -> int:
    results: list[ScenarioResult] = []
    for file in _gather_scenarios(paths):
        scenario = load_scenario(file)
        transport = InProcessTransport()
        results.append(run_scenario(transport, scenario))
        transport.close()
    write_json(results, json_path)
    write_junit(results, junit_path)
    sys.stdout.write(render_summary(results))
    return 0 if all(result.passed for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run HILBench scenarios")
    parser.add_argument("paths", nargs="+", help="scenario files or directories")
    parser.add_argument("--json", default="report.json", help="JSON report path")
    parser.add_argument(
        "--junit", default="report.xml", help="JUnit XML report path"
    )
    args = parser.parse_args(argv)
    return run(args.paths, args.json, args.junit)


if __name__ == "__main__":
    raise SystemExit(main())
