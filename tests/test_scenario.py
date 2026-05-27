import pytest

from hilbench.scenario import Step, load_scenario, scenario_from_dict


def test_step_rejects_both_expect_forms():
    with pytest.raises(ValueError):
        Step(name="s", command="X", expect="a", expect_contains="b")


def test_scenario_requires_name_and_steps():
    with pytest.raises(ValueError):
        scenario_from_dict({"steps": []})


def test_step_requires_command():
    with pytest.raises(ValueError):
        scenario_from_dict({"name": "s", "steps": [{"name": "only"}]})


def test_load_scenario_rejects_non_mapping(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("- just\n- a list\n")
    with pytest.raises(ValueError):
        load_scenario(path)


def test_scenario_carries_params():
    scenario = scenario_from_dict(
        {
            "name": "s",
            "params": {"speed": 1000},
            "steps": [{"name": "ping", "command": "PING"}],
        }
    )
    assert scenario.params["speed"] == 1000
