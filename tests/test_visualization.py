"""Tests for the replays (frames, GIF, HTML, ASCII) and the static summary."""

import json
import re
from pathlib import Path

from PIL import Image

from src.ascii_view import final_ascii_summary, render_frame
from src.frames import mission_frames
from src.replay_player import build_replay_payload, render_replay_html
from src.simulation import run_mission
from src.visualization import create_animated_mission_gif, plot_static_mission_summary


def test_one_frame_per_step_and_positions_match_trace():
    result = run_mission(Path("config/decoy.json"))
    frames = mission_frames(result)
    assert len(frames) == result.total_steps + 1
    for frame, step in zip(frames[1:], result.action_trace):
        assert list(frame["pos"]) == step["outcome"]["agent_pos"]
        assert frame["action"] == step["action"]


def test_frames_never_reveal_unsensed_beacons_or_eve():
    result = run_mission(Path("config/decoy.json"))
    genuine_far_beacon = (5, 11)  # never sensed in this mission
    for frame in mission_frames(result):
        sensed = frame["revealed"]
        assert all(sensed.get(c) == "CLUE" for c in frame["clues_sighted"])
        assert genuine_far_beacon not in frame["clues_sighted"]
        if frame["eve_visible"] is not None:
            assert sensed[frame["eve_visible"]] == "EVE"


def test_visualizations_generate_valid_files(tmp_path):
    result = run_mission(Path("config/default.json"), random_seed=42)

    out_png = plot_static_mission_summary(result, tmp_path / "summary.png")
    assert out_png.stat().st_size > 10_000

    out_gif = create_animated_mission_gif(result, tmp_path / "animation.gif", duration_per_frame_ms=100)
    with Image.open(out_gif) as gif:
        assert gif.n_frames == result.total_steps + 1  # scans and inspections get their own frames


def test_replay_html_is_self_contained_and_parsable():
    result = run_mission(Path("config/recharge.json"))
    html = render_replay_html(result)
    assert "<canvas id=\"map\"" in html and "__MISSION_DATA__" not in html
    data = re.search(r'<script id="mission-data" type="application/json">(.*?)</script>', html, re.S).group(1)
    payload = json.loads(data.replace("<\\/", "</"))
    assert len(payload["steps"]) == result.total_steps
    assert payload["outcome"]["recharges"] == result.recharge_count
    assert payload == json.loads(json.dumps(build_replay_payload(result)))


def test_ascii_replay_marks_walle_and_fog():
    result = run_mission(Path("config/unreachable.json"))
    first = render_frame(mission_frames(result)[0], result)
    assert "W" in first and "?" in first
    summary = final_ascii_summary(result)
    assert "strategy timeline" in summary and "EVE_UNREACHABLE" in summary
