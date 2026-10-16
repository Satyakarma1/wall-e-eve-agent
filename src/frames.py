"""Per-step snapshots of WALL-E's knowledge, shared by the GIF, ASCII and HTML replays.

Frame 0 is the start of the mission; frame k (k >= 1) is the world right after trace step k-1
was executed. Every frame only contains what WALL-E had sensed by then (fog of war), so no
replay can reveal undiscovered beacons or EVE early. The belief shown in frame k is the one
WALL-E held after observing that outcome (i.e. the belief used for its next decision).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.simulation import SimulationResult

Coord = Tuple[int, int]

# Fixed categorical order (reference palette slots 1-7) so a strategy always keeps its color.
STRATEGY_ORDER = (
    "HUNT_BELIEF_TARGET",
    "ACQUIRE_CLUE",
    "PULSE_SCAN",
    "EXPLORE_FOR_CLUES",
    "RETURN_TO_CHARGE",
    "MISSION_COMPLETE",
    "ABORT_UNREACHABLE",
)
STRATEGY_COLORS_LIGHT = dict(zip(STRATEGY_ORDER, ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6")))
STRATEGY_COLORS_DARK = dict(zip(STRATEGY_ORDER, ("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9")))
STRATEGY_LABELS = {
    "HUNT_BELIEF_TARGET": "Hunt belief target",
    "ACQUIRE_CLUE": "Acquire beacon",
    "PULSE_SCAN": "Pulse scan",
    "EXPLORE_FOR_CLUES": "Explore",
    "RETURN_TO_CHARGE": "Return to charge",
    "MISSION_COMPLETE": "Mission complete",
    "ABORT_UNREACHABLE": "Abort: unreachable",
}


def _parse_key(key: str) -> Coord:
    r, c = key.split(",")
    return (int(r), int(c))


def mission_frames(result: SimulationResult) -> List[Dict[str, Any]]:
    """Build one knowledge snapshot per frame (len = total_steps + 1)."""
    trace = result.action_trace
    start: Coord = tuple(result.ground_truth["start_pos"])  # type: ignore[assignment]
    beliefs: List[Optional[np.ndarray]] = list(result.belief_history) + [result.belief_final]
    if len(beliefs) < len(trace) + 1:  # belief history disabled
        beliefs = [None] * (len(trace) + 1)

    revealed: Dict[Coord, str] = {(r, c): kind for r, c, kind in result.initial_revealed}
    path: List[Coord] = [start]
    segments: List[Tuple[Coord, Coord, str]] = []
    inspected: List[Coord] = []
    scans: List[Dict[str, Any]] = []
    decoded: List[Dict[str, Any]] = []

    def snapshot(index: int, pos: Coord, step: Optional[Dict[str, Any]], nxt: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # Decision-time beliefs for this frame come from the NEXT trace step (or the final inference).
        if nxt is not None:
            top, top_p = tuple(nxt["top_candidate"]), nxt["top_candidate_prob"]
            entropy, status_p = nxt["belief_entropy"], nxt["status_belief"]
            flagged = [tuple(c) for c in nxt.get("flagged_decoys", [])]
            reliability = {_parse_key(k): v for k, v in nxt.get("clue_reliability", {}).items()}
        else:
            inf = result.inference
            top, top_p = tuple(inf["map_estimate"]), inf["map_probability"]
            entropy, status_p = inf["entropy_bits"], inf["status_probabilities"]
            flagged = [tuple(c) for c in inf["flagged_decoys"]]
            reliability = {tuple(e["pos"]): e.get("p_genuine") for e in inf["evidence"] if e["type"] == "beacon"}
        battery = step["outcome"]["battery"] if step else result.briefing.get("initial_battery", 0.0)
        scans_left = step["outcome"]["scan_budget"] if step else result.briefing.get("scan_budget", 0)
        return {
            "index": index,
            "step": step["step"] if step else None,
            "pos": pos,
            "action": step["action"] if step else "START",
            "strategy": step["strategy"] if step else None,
            "reason": step["reason"] if step else "Mission briefing received: initial signal, docks and budgets.",
            "events": list(step["events"]) if step else [],
            "battery": battery,
            "scan_budget": scans_left,
            "path": list(path),
            "segments": list(segments),
            "revealed": dict(revealed),
            "clues_sighted": sorted(c for c, k in revealed.items() if k == "CLUE"),
            "clues_inspected": list(inspected),
            "decoded": list(decoded),
            "scans": list(scans),
            "eve_visible": next((c for c, k in revealed.items() if k == "EVE"), None),
            "flagged_decoys": flagged,
            "reliability": reliability,
            "top_candidate": top,
            "top_probability": top_p,
            "entropy": entropy,
            "status_belief": status_p,
            "goal": tuple(step["goal"]) if step and step.get("goal") else None,
            "plan": [tuple(p) for p in step["plan"]] if step else [],
            "belief": beliefs[index],
            "is_final": nxt is None and step is not None,
        }

    frames = [snapshot(0, start, None, trace[0] if trace else None)]
    for k, step in enumerate(trace):
        out = step["outcome"]
        before: Coord = tuple(step["agent_pos"])  # type: ignore[assignment]
        after: Coord = tuple(out["agent_pos"])  # type: ignore[assignment]
        if after != before:
            path.append(after)
            segments.append((before, after, step["strategy"]))
        for r, c, kind in out["revealed"]:
            revealed[(r, c)] = kind
        if out.get("clue_payload"):
            p = out["clue_payload"]
            inspected.append(tuple(p["clue_pos"]))
            decoded.append({"pos": tuple(p["clue_pos"]), "distance": p["estimated_distance"], "vector": tuple(p["bearing_vector"])})
        if out.get("scan_result"):
            s = out["scan_result"]
            scans.append({"pos": tuple(s["scanner_pos"]), "distance": s["estimated_distance"], "strength": s["signal_strength"]})
        nxt = trace[k + 1] if k + 1 < len(trace) else None
        frames.append(snapshot(k + 1, after, step, nxt))
    return frames
