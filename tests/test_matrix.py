"""Tests for parameterized scenario matrices.

The breakdown proof uses a mix of in range and out of range speeds. An out of
range speed faults the controller, so the matching case fails while the in range
cases pass. The test asserts the consolidated breakdown reports the right per
case result, and that the JUnit report carries one testsuite per case.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from hilbench.matrix import (
    MatrixCase,
    ScenarioMatrix,
    expand,
    matrix_from_dict,
    run_matrix,
)
from hilbench.report import to_junit

ROOT = Path(__file__).resolve().parents[1]


def _template():
    return {
        "steps": [
            {"name": "arm", "command": "ARM", "expect": "OK armed"},
            {"name": "start", "command": "START", "expect": "OK running"},
            {
                "name": "set_speed",
                "command": "SETSPEED {speed}",
                "expect": "OK speed={speed}",
            },
        ]
    }


def test_expand_fills_placeholders():
    matrix = ScenarioMatrix(
        name="sweep",
        template=_template(),
        cases=(MatrixCase(name="one", params={"speed": 1234}),),
    )
    scenarios = expand(matrix)
    assert scenarios[0].name == "sweep[one]"
    assert scenarios[0].steps[2].command == "SETSPEED 1234"
    assert scenarios[0].steps[2].expect == "OK speed=1234"


def test_breakdown_reports_per_case_pass_and_fail():
    matrix = ScenarioMatrix(
        name="sweep",
        template=_template(),
        cases=(
            MatrixCase(name="ok", params={"speed": 500}),
            MatrixCase(name="too_fast", params={"speed": 99999}),
        ),
    )
    result = run_matrix(matrix)
    breakdown = result.breakdown()
    assert breakdown["sweep[ok]"] is True
    assert breakdown["sweep[too_fast]"] is False
    assert result.passed is False


def test_junit_has_one_suite_per_case():
    matrix = ScenarioMatrix(
        name="sweep",
        template=_template(),
        cases=(
            MatrixCase(name="a", params={"speed": 100}),
            MatrixCase(name="b", params={"speed": 200}),
        ),
    )
    tree = to_junit(run_matrix(matrix).cases)
    suites = tree.getroot().findall("testsuite")
    names = {suite.attrib["name"] for suite in suites}
    assert names == {"sweep[a]", "sweep[b]"}


def test_matrix_from_dict_requires_fields():
    with pytest.raises(ValueError):
        matrix_from_dict({"name": "x", "cases": []})


def test_bundled_matrix_file_runs():
    from hilbench.matrix import load_matrix

    matrix = load_matrix(ROOT / "scenarios" / "speed_sweep.matrix.yaml")
    result = run_matrix(matrix)
    assert len(result.cases) == 3
    assert result.passed
    parsed = ET.ElementTree(to_junit(result.cases).getroot())
    assert len(parsed.getroot().findall("testsuite")) == 3
