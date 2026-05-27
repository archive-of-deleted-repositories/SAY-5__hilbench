"""Golden report test.

Running the fixed run_cycle scenario through the deterministic JSON writer must
reproduce a checked in report byte for byte. This guards the report schema and
serialization against accidental changes.
"""

from pathlib import Path

from hilbench.report import render_json
from hilbench.runner import run_scenario
from hilbench.scenario import load_scenario
from hilbench.transport import InProcessTransport

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).resolve().parent / "golden" / "run_cycle.json"


def test_run_cycle_report_matches_golden():
    scenario = load_scenario(ROOT / "scenarios" / "run_cycle.yaml")
    result = run_scenario(InProcessTransport(), scenario)
    rendered = render_json([result], deterministic=True)
    assert rendered == GOLDEN.read_text(encoding="utf-8")
