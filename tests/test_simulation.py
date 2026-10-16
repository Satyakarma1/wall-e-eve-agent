"""End-to-end integration tests for the simulation runner, trace and report."""

import json
from pathlib import Path

from src.simulation import run_mission, save_mission_report, save_trace_json
from src.report import render_report_markdown


def test_simulation_default_mission_succeeds():
    result = run_mission(Path("config/default.json"), random_seed=42)

    assert result.success is True
    assert result.status == "SUCCESS"
    assert result.battery_remaining > 0
    assert result.clues_inspected >= 1
    assert len(result.action_trace) == result.total_steps
    assert len(result.belief_history) == result.total_steps
    assert result.inference["conclusion"] == "EVE_FOUND"
    assert result.inference["status_estimate"] == "DORMANT"


def test_trace_is_consistent_with_actual_path():
    result = run_mission(Path("config/hard.json"))
    trace = result.action_trace
    for current, nxt in zip(trace, trace[1:]):
        assert current["outcome"]["agent_pos"] == nxt["agent_pos"]
    moved = [tuple(trace[0]["agent_pos"])] + [
        tuple(s["outcome"]["agent_pos"])
        for s in trace
        if s["action"].startswith("MOVE") and not s["outcome"]["collision"]
    ]
    assert moved == [tuple(p) for p in result.path_taken]
    for step in trace:
        assert step["observation"] and step["reason"] and "message" in step["outcome"]


def test_scans_are_never_repeated_from_the_same_spot():
    result = run_mission(Path("config/noisy.json"))
    scan_cells = [tuple(s["agent_pos"]) for s in result.action_trace if s["action"] == "SCAN"]
    for i, a in enumerate(scan_cells):
        for b in scan_cells[i + 1:]:
            assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) >= 3


def test_unreachable_target_aborts_with_inference_instead_of_dying():
    result = run_mission(Path("config/unreachable.json"), random_seed=77)

    assert result.success is False
    assert result.status == "TERMINATED_BY_AGENT"
    assert result.battery_remaining > 0
    assert result.inference["conclusion"] == "EVE_UNREACHABLE"
    assert result.inference["map_estimate"] == [9, 9]
    assert result.inference["breach_candidates"]
    assert result.action_trace[-1]["strategy"] == "ABORT_UNREACHABLE"


def test_agent_turns_back_and_recharges():
    result = run_mission(Path("config/recharge.json"))
    strategies = [s for _, s, _ in result.strategy_transitions]
    assert "RETURN_TO_CHARGE" in strategies
    assert result.recharge_count >= 1
    assert result.success is True


def test_decoy_beacon_is_detected_and_rejected():
    result = run_mission(Path("config/decoy.json"))
    assert result.success is True
    assert result.evaluation["decoys_flagged"] == [[1, 1]]
    assert result.evaluation["genuine_flagged"] == []
    assert any("rejected as spoofed" in r for _, _, r in result.strategy_transitions)


def test_naive_agent_never_flags_decoys():
    result = run_mission(Path("config/decoy.json"), agent_type="naive", record_belief_history=False)
    assert result.inference["flagged_decoys"] == []


def test_runs_are_reproducible_for_a_seed():
    a = run_mission(Path("config/noisy.json"), random_seed=5, record_belief_history=False)
    b = run_mission(Path("config/noisy.json"), random_seed=5, record_belief_history=False)
    assert [s["action"] for s in a.action_trace] == [s["action"] for s in b.action_trace]


def test_report_has_evidence_inference_confidence_and_next_step(tmp_path):
    result = run_mission(Path("config/decoy.json"))
    text = render_report_markdown(result)
    for section in ("Evidence found", "EVE location", "EVE status", "Recommended next step",
                    "rejected as spoofed", "After-mission evaluation"):
        assert section in text

    report_path = save_mission_report(result, tmp_path / "report.md")
    trace_path = save_trace_json(result, tmp_path / "trace.json")
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    assert report_path.exists()
    assert len(data["steps"]) == result.total_steps
    assert data["inference"]["conclusion"] == "EVE_FOUND"


def test_unfound_mission_report_states_confidence():
    result = run_mission(Path("config/unreachable.json"))
    text = render_report_markdown(result)
    assert "credible region" in text and "clear the debris" in text
