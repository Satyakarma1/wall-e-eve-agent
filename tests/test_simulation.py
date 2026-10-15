"""End-to-end integration tests for simulation runner."""

from pathlib import Path
from src.simulation import run_mission, save_mission_report


def test_simulation_default_mission_succeeds():
    config_path = Path("config/default.json")
    result = run_mission(config_path, random_seed=42)

    assert result.success is True
    assert result.status == "SUCCESS"
    assert result.total_steps > 0
    assert result.battery_remaining > 0
    assert result.clues_discovered >= 1
    assert len(result.action_trace) == result.total_steps
    assert len(result.belief_history) > 0


def test_simulation_unreachable_target_terminates_gracefully():
    config_path = Path("config/unreachable.json")
    result = run_mission(config_path, random_seed=77)

    # Mission should terminate cleanly without infinite loop or unhandled exception
    assert result.success is False
    assert result.status in ("TERMINATED_BY_AGENT", "FAILURE_BATTERY", "FAILURE_TIMEOUT")
    assert len(result.action_trace) > 0


def test_save_mission_report(tmp_path):
    config_path = Path("config/default.json")
    result = run_mission(config_path, random_seed=42)

    report_path = tmp_path / "test_report.md"
    save_mission_report(result, report_path)

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "WALL-E Mission Report" in content
    assert "SUCCESS" in content
