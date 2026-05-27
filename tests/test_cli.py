from pathlib import Path

from hilbench.cli import main

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


def test_cli_runs_scenarios_clean(tmp_path):
    json_path = tmp_path / "report.json"
    junit_path = tmp_path / "report.xml"
    code = main(
        [
            str(SCENARIOS / "smoke.yaml"),
            str(SCENARIOS / "run_cycle.yaml"),
            "--json",
            str(json_path),
            "--junit",
            str(junit_path),
        ]
    )
    assert code == 0
    assert json_path.exists()
    assert junit_path.exists()


def test_cli_fails_on_bad_expectation(tmp_path):
    scenario = tmp_path / "bad.yaml"
    scenario.write_text(
        "name: bad\nsteps:\n  - name: ping\n    command: PING\n    expect: WRONG\n"
    )
    code = main(
        [
            str(scenario),
            "--json",
            str(tmp_path / "r.json"),
            "--junit",
            str(tmp_path / "r.xml"),
        ]
    )
    assert code == 1
