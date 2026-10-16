"""Interactive HTML replay player: one self-contained file (vanilla JS + canvas, no dependencies).

Used two ways: saved as outputs/<mission>_replay.html (opens in any browser) and embedded in the
Streamlit dashboard with st.iframe. The page only learns ground truth for the optional
"evaluation view", which the player unlocks once the replay has reached the end.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from src.frames import STRATEGY_COLORS_DARK, STRATEGY_LABELS, mission_frames
from src.report import recommend_next_step
from src.simulation import SimulationResult

TEMPLATE_PATH = Path(__file__).with_name("assets") / "replay_player.html"


def _quantize(belief: Optional[np.ndarray]) -> Optional[List[int]]:
    """Belief grid -> 0..255 ints relative to the frame maximum (keeps the HTML small)."""
    if belief is None:
        return None
    peak = float(belief.max())
    if peak <= 0:
        return [0] * belief.size
    return [int(v) for v in np.rint(255.0 * belief.ravel() / peak)]


def _after(frame: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "belief": _quantize(frame["belief"]),
        "top": list(frame["top_candidate"]),
        "top_p": frame["top_probability"],
        "entropy": frame["entropy"],
        "status": frame["status_belief"],
        "flagged": [list(c) for c in frame["flagged_decoys"]],
        "reliability": {f"{r},{c}": p for (r, c), p in frame["reliability"].items() if p is not None},
    }


def build_replay_payload(result: SimulationResult, autoplay: bool = True) -> Dict[str, Any]:
    """Everything the player needs, step by step (deltas) to keep the file compact."""
    frames = mission_frames(result)
    trace = result.action_trace
    gt = result.ground_truth
    steps = []
    for k, s in enumerate(trace):
        out = s["outcome"]
        scan = out.get("scan_result")
        clue = out.get("clue_payload")
        steps.append({
            "step": s["step"],
            "action": s["action"],
            "strategy": s["strategy"],
            "reason": s["reason"],
            "events": s["events"],
            "from": s["agent_pos"],
            "to": out["agent_pos"],
            "battery": [s["battery"], out["battery"]],
            "scans_left": out["scan_budget"],
            "recharged": out["recharged"],
            "collision": out["collision"],
            "revealed": out["revealed"],
            "scan": {"pos": scan["scanner_pos"], "distance": scan["estimated_distance"],
                     "strength": scan["signal_strength"]} if scan else None,
            "decoded": {"pos": clue["clue_pos"], "distance": clue["estimated_distance"],
                        "vector": clue["bearing_vector"]} if clue else None,
            "goal": s["goal"],
            "plan": s["plan"],
            "after": _after(frames[k + 1]),
        })

    inf = result.inference
    return {
        "autoplay": autoplay,
        "mission": {
            "name": result.mission_name or result.config_name,
            "config": result.config_name,
            "agent": result.agent_type,
            "rows": gt["grid_size"][0],
            "cols": gt["grid_size"][1],
            "start": gt["start_pos"],
            "docks": gt["charging_stations"],
            "capacity": result.briefing.get("battery_capacity"),
            "scan_budget": result.briefing.get("scan_budget"),
            "initial_signal": result.briefing.get("initial_signal"),
            "signal_age": result.briefing.get("signal_age_minutes"),
        },
        "initial": {
            "pos": gt["start_pos"],
            "revealed": result.initial_revealed,
            "battery": result.briefing.get("initial_battery"),
            "scans": result.briefing.get("scan_budget"),
            "after": _after(frames[0]),
        },
        "steps": steps,
        "transitions": [list(t) for t in result.strategy_transitions],
        "outcome": {
            "status": result.status,
            "success": result.success,
            "steps": result.total_steps,
            "battery_remaining": result.battery_remaining,
            "recharges": result.recharge_count,
            "conclusion": inf["conclusion"],
            "map_estimate": inf["map_estimate"],
            "map_probability": inf["map_probability"],
            "status_estimate": inf["status_estimate"],
            "status_confidence": inf["status_confidence"],
            "recommendation": recommend_next_step(result),
        },
        "truth": {
            "eve": gt["eve_pos"],
            "eve_status": gt["eve_status"],
            "obstacles": gt["obstacles"],
            "clues": [{"pos": c["pos"], "type": c["type"]} for c in gt["clues"]],
        },
        "strategy_colors": STRATEGY_COLORS_DARK,
        "strategy_labels": STRATEGY_LABELS,
    }


def render_replay_html(result: SimulationResult, autoplay: bool = True) -> str:
    """Self-contained HTML page with the mission embedded as JSON."""
    data = json.dumps(build_replay_payload(result, autoplay), separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE_PATH.read_text(encoding="utf-8").replace("__MISSION_DATA__", data)


def save_replay_html(result: SimulationResult, output_path: Union[str, Path], autoplay: bool = True) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_replay_html(result, autoplay), encoding="utf-8")
    return path
