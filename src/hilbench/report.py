"""Report writers.

Three views of a run are produced:

* a machine readable JSON document,
* a JUnit XML document that CI systems ingest as test results,
* a short human readable text summary.

The JSON writer rounds latencies to a fixed precision so a deterministic run
produces a byte stable document, which the golden report test relies on.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Sequence

from hilbench.runner import Outcome, ScenarioResult

LATENCY_PRECISION = 3


def to_dict(results: Sequence[ScenarioResult]) -> dict[str, object]:
    """Build a JSON serialisable mapping from scenario results."""
    scenarios: list[dict[str, object]] = []
    total_steps = 0
    failed_steps = 0
    for result in results:
        steps = []
        for step in result.steps:
            total_steps += 1
            if not step.passed:
                failed_steps += 1
            steps.append(
                {
                    "name": step.name,
                    "command": step.command,
                    "response": step.response,
                    "latency_ms": round(step.latency_ms, LATENCY_PRECISION),
                    "outcome": step.outcome.value,
                    "messages": list(step.messages),
                }
            )
        scenarios.append(
            {
                "name": result.name,
                "passed": result.passed,
                "steps": steps,
            }
        )
    return {
        "summary": {
            "scenarios": len(scenarios),
            "steps": total_steps,
            "failed_steps": failed_steps,
            "passed": failed_steps == 0,
        },
        "scenarios": scenarios,
    }


def write_json(results: Sequence[ScenarioResult], path: str) -> None:
    """Write the JSON report to a file."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(to_dict(results), handle, indent=2, sort_keys=True)
        handle.write("\n")


def render_json(results: Sequence[ScenarioResult], *, deterministic: bool = False) -> str:
    """Return the JSON report as a string.

    When ``deterministic`` is set, latencies are replaced with a fixed value so
    the document does not depend on measured timing. This supports a byte stable
    golden report.
    """
    payload = to_dict(results)
    if deterministic:
        scenarios: list[dict[str, object]] = payload["scenarios"]  # type: ignore[assignment]
        for scenario in scenarios:
            steps: list[dict[str, object]] = scenario["steps"]  # type: ignore[assignment]
            for step in steps:
                step["latency_ms"] = 0.0
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def to_junit(results: Sequence[ScenarioResult]) -> ET.ElementTree:
    """Build a JUnit XML element tree from scenario results.

    Each scenario maps to a testsuite and each step maps to a testcase. A failed
    step carries a failure element with the joined assertion messages.
    """
    suites = ET.Element("testsuites")
    for result in results:
        failures = sum(1 for step in result.steps if not step.passed)
        time_s = result.total_latency_ms / 1000.0
        suite = ET.SubElement(
            suites,
            "testsuite",
            name=result.name,
            tests=str(len(result.steps)),
            failures=str(failures),
            time=f"{time_s:.6f}",
        )
        for step in result.steps:
            case = ET.SubElement(
                suite,
                "testcase",
                classname=result.name,
                name=step.name,
                time=f"{step.latency_ms / 1000.0:.6f}",
            )
            if step.outcome is Outcome.FAIL:
                failure = ET.SubElement(
                    case, "failure", message="; ".join(step.messages)
                )
                failure.text = (
                    f"command: {step.command}\nresponse: {step.response}"
                )
    return ET.ElementTree(suites)


def write_junit(results: Sequence[ScenarioResult], path: str) -> None:
    """Write the JUnit XML report to a file."""
    tree = to_junit(results)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def render_summary(results: Sequence[ScenarioResult]) -> str:
    """Return a short human readable summary."""
    lines = []
    for result in results:
        mark = "PASS" if result.passed else "FAIL"
        lines.append(f"[{mark}] {result.name} ({result.total_latency_ms:.3f} ms)")
        for step in result.steps:
            if not step.passed:
                detail = "; ".join(step.messages)
                lines.append(f"    - {step.name}: {detail}")
    total_steps = sum(len(result.steps) for result in results)
    failed_steps = sum(
        1 for result in results for step in result.steps if not step.passed
    )
    lines.append(
        f"{len(results)} scenarios, {total_steps} steps, {failed_steps} failed"
    )
    return "\n".join(lines) + "\n"
