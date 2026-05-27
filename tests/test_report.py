import json
import xml.etree.ElementTree as ET

from hilbench.report import render_summary, to_dict, to_junit, write_json, write_junit
from hilbench.runner import run_scenario
from hilbench.scenario import Scenario, Step
from hilbench.transport import InProcessTransport


def _sample_results():
    transport = InProcessTransport()
    scenario = Scenario(
        name="run_cycle",
        steps=(
            Step(name="arm", command="ARM", expect="OK armed"),
            Step(name="start", command="START", expect="OK running"),
            Step(name="bad", command="STATUS", expect="OK nonsense"),
        ),
    )
    return [run_scenario(transport, scenario)]


def test_json_summary_counts_failures():
    payload = to_dict(_sample_results())
    assert payload["summary"]["steps"] == 3
    assert payload["summary"]["failed_steps"] == 1
    assert payload["summary"]["passed"] is False


def test_junit_marks_failure():
    tree = to_junit(_sample_results())
    root = tree.getroot()
    suite = root.find("testsuite")
    assert suite.attrib["tests"] == "3"
    assert suite.attrib["failures"] == "1"
    failures = root.findall(".//failure")
    assert len(failures) == 1


def test_write_json_and_junit(tmp_path):
    results = _sample_results()
    json_path = tmp_path / "report.json"
    junit_path = tmp_path / "report.xml"
    write_json(results, str(json_path))
    write_junit(results, str(junit_path))
    loaded = json.loads(json_path.read_text())
    assert loaded["summary"]["scenarios"] == 1
    parsed = ET.parse(junit_path)
    assert parsed.getroot().tag == "testsuites"


def test_summary_lists_failed_step():
    text = render_summary(_sample_results())
    assert "[FAIL] run_cycle" in text
    assert "bad" in text
