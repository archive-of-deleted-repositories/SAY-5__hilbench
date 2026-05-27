from benchmarks.throughput import build_batch, measure


def test_build_batch_shape():
    batch = build_batch(scenarios=3, steps_per_scenario=4)
    assert len(batch) == 3
    assert all(len(scenario.steps) == 4 for scenario in batch)


def test_measure_reports_positive_throughput():
    result = measure(scenarios=5, steps_per_scenario=10, repeats=2)
    assert result["total_steps"] == 50
    assert result["steps_per_second"] > 0
    assert result["seconds"] > 0
