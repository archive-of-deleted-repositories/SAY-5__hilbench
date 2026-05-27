"""Command line entry point for running scenarios.

The CLI loads one or more scenario files, runs each against a fresh in process
DUT, writes the JSON and JUnit reports, prints the human summary, and exits non
zero if any step failed so that CI fails the build.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hilbench.matrix import load_matrix, run_matrix
from hilbench.report import render_summary, write_json, write_junit
from hilbench.runner import ScenarioResult, run_scenario
from hilbench.scenario import load_scenario
from hilbench.transport import InProcessTransport


def _gather_scenarios(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(
                sorted(
                    f for f in path.glob("*.yaml") if not f.name.endswith(".matrix.yaml")
                )
            )
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


def run_matrix_file(path: str, json_path: str, junit_path: str) -> int:
    matrix = load_matrix(path)
    result = run_matrix(matrix)
    # Each case is a scenario, so the report writers emit a testsuite and a JSON
    # scenario per case, giving a per case pass/fail breakdown.
    write_json(result.cases, json_path)
    write_junit(result.cases, junit_path)
    sys.stdout.write(render_summary(result.cases))
    breakdown = result.breakdown()
    passed = sum(1 for ok in breakdown.values() if ok)
    sys.stdout.write(
        f"matrix {result.name}: {passed}/{len(breakdown)} cases passed\n"
    )
    return 0 if result.passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run HILBench scenarios")
    parser.add_argument("paths", nargs="+", help="scenario files or directories")
    parser.add_argument("--json", default="report.json", help="JSON report path")
    parser.add_argument(
        "--junit", default="report.xml", help="JUnit XML report path"
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="treat the single path as a scenario matrix file",
    )
    args = parser.parse_args(argv)
    if args.matrix:
        if len(args.paths) != 1:
            parser.error("--matrix takes exactly one matrix file")
        return run_matrix_file(args.paths[0], args.json, args.junit)
    return run(args.paths, args.json, args.junit)


if __name__ == "__main__":
    raise SystemExit(main())
