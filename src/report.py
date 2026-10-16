"""Final mission report: evidence found, inferred location/status, confidence and recommended next step."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from src.pathfinding import bfs_distance_map
from src.simulation import SimulationResult


def _fmt(pos: Any) -> str:
    return f"({pos[0]}, {pos[1]})"


def _known_obstacles(result: SimulationResult) -> set:
    """Obstacles WALL-E actually sensed during the mission (its own map, not ground truth)."""
    known = {(r, c) for r, c, kind in result.initial_revealed if kind == "OBSTACLE"}
    for step in result.action_trace:
        known.update((r, c) for r, c, kind in step["outcome"]["revealed"] if kind == "OBSTACLE")
    return known


def recommend_next_step(result: SimulationResult) -> str:
    """Rule-based recommendation built only from the agent's own conclusions and map."""
    inf = result.inference
    est = tuple(inf["map_estimate"])
    docks = [tuple(d) for d in inf.get("known_docks", [])]
    rows, cols = result.ground_truth["grid_size"]
    decoys = inf.get("flagged_decoys", [])
    decoy_note = f" Ignore beacon(s) {', '.join(_fmt(d) for d in decoys)}: judged spoofed." if decoys else ""

    if inf["conclusion"] == "EVE_FOUND":
        dock_note = ""
        if docks:
            dist = bfs_distance_map(docks, (rows, cols), _known_obstacles(result))
            moves = dist[est]
            if np.isfinite(moves):
                enough = "enough" if result.battery_remaining >= moves else "NOT enough"
                dock_note = (f" Nearest dock is {int(moves)} moves away; battery left "
                             f"{result.battery_remaining:.0f} is {enough} to escort her back.")
        if inf["status_estimate"] == "DORMANT":
            return (f"EVE is DORMANT at {_fmt(est)}: stay with her, shield her and keep her beacon logged until "
                    f"pickup.{dock_note}{decoy_note}")
        return f"EVE is ACTIVE at {_fmt(est)}: hand over the plant and escort her to the dock.{dock_note}{decoy_note}"

    if inf["conclusion"] == "EVE_UNREACHABLE":
        breach = inf.get("breach_candidates") or []
        breach_note = (f"clear the debris at {_fmt(breach[0])} (the thinnest wall between WALL-E's area and the pocket)"
                       if breach else "clear a path through the surrounding debris")
        return (f"EVE is almost certainly sealed inside debris near {_fmt(est)} "
                f"(P={inf['map_probability']:.2f}). Next: {breach_note}, or send an aerial unit.{decoy_note}")

    region = inf["credible_region_90"]
    dock_note = f"Recharge at dock {_fmt(docks[0])}, then " if docks else "Then "
    return (f"{dock_note}search the {len(region)}-cell 90% credible region, starting at the most likely cell "
            f"{_fmt(est)} (P={inf['map_probability']:.2f}).{decoy_note}")


def _evidence_lines(result: SimulationResult) -> List[str]:
    lines = []
    for e in result.inference["evidence"]:
        step = f"Step {e['step']}"
        if e["type"] == "initial_signal":
            parts = []
            if e.get("bearing_deg") is not None:
                parts.append(f"bearing {e['bearing_deg']:.0f}°")
            if e.get("approx_pos") is not None:
                parts.append(f"approx. coordinates {_fmt(e['approx_pos'])}")
            if e.get("strength") is not None:
                parts.append(f"strength {e['strength']:.2f}")
            lines.append(f"{step} — **Initial signal** received at {_fmt(e.get('received_at', [0, 0]))}: "
                         f"{', '.join(parts)}; {e['age_minutes']:.0f} min old at mission start "
                         f"(timestamp {e.get('timestamp', 'n/a')}).")
        elif e["type"] == "beacon":
            verdict = ""
            if e.get("p_genuine") is not None:
                verdict = (f" → **rejected as spoofed** (P genuine = {e['p_genuine']:.2f})" if e.get("flagged_decoy")
                           else f" → P(genuine) = {e['p_genuine']:.2f}")
            lines.append(f"{step} — **Beacon** {_fmt(e['pos'])} decoded: EVE ~{e['distance']:.1f} cells away "
                         f"at bearing {e['bearing_deg']:.0f}°{verdict}.")
        elif e["type"] == "scan":
            lines.append(f"{step} — **Pulse scan** from {_fmt(e['pos'])}: range ~{e['distance']:.1f} cells, "
                         f"beacon strength {e['strength']:.3f}.")
        elif e["type"] == "eve_sighting":
            lines.append(f"{step} — **EVE sighted** at {_fmt(e['pos'])} by the local camera.")
        elif e["type"] == "rendezvous":
            lines.append(f"{step} — **Rendezvous** at {_fmt(e['pos'])}: EVE status observed as {e['status']}.")
    return lines or ["No evidence was gathered."]


def render_report_markdown(result: SimulationResult, trace_rows: int = 12) -> str:
    """Human-readable mission report (markdown)."""
    inf, ev = result.inference, result.evaluation
    est = inf["map_estimate"]
    status_p = inf["status_probabilities"]

    if inf["conclusion"] == "EVE_FOUND":
        location = f"{_fmt(est)} — **observed directly at rendezvous**"
        status = f"{inf['status_estimate']} — **observed directly**"
    else:
        location = (f"{_fmt(est)} — P = {inf['map_probability']:.2f}, P(within 1 cell) = {inf['p_within_1_cell']:.2f}, "
                    f"90% credible region = {len(inf['credible_region_90'])} cell(s)")
        status = f"{inf['status_estimate']} — confidence {inf['status_confidence']:.0%}"

    lines = [
        f"# WALL-E Mission Report — {result.mission_name or result.config_name}",
        "",
        f"Config `{result.config_name}` · agent `{result.agent_type}` · outcome **{result.status}** "
        f"after {result.total_steps} steps",
        "",
        "## 1. Verdict",
        "| Item | Inference |",
        "| :--- | :--- |",
        f"| Conclusion | `{inf['conclusion']}` |",
        f"| EVE location | {location} |",
        f"| EVE status | {status} (P(ACTIVE) = {status_p.get('ACTIVE', 0):.2f}, P(DORMANT) = {status_p.get('DORMANT', 0):.2f}) |",
        f"| Remaining uncertainty | {inf['entropy_bits']:.2f} bits of entropy over EVE's location |",
        f"| Recommended next step | {recommend_next_step(result)} |",
        "",
        "## 2. Evidence found",
    ]
    lines += [f"{i}. {line}" for i, line in enumerate(_evidence_lines(result), start=1)]

    lines += [
        "",
        "## 3. Resources and performance",
        f"- Steps: {result.total_steps} (path length {result.path_length} cells)",
        f"- Battery: {result.battery_used:.1f} consumed, {result.battery_remaining:.1f} remaining, "
        f"{result.energy_recharged:.1f} recharged over {result.recharge_count} dock action(s)",
        f"- Pulse scans: {result.scan_count} · beacons inspected: {result.clues_inspected} · "
        f"beacons sighted: {result.clues_discovered} of {result.total_clues}",
        f"- Coverage: {result.exploration_coverage_pct:.1f}% of free cells visited, "
        f"{result.sensor_coverage_pct:.1f}% of the map sensed",
        "",
        "## 4. Strategy changes",
    ]
    lines += [f"- **Step {s}** → `{strat}`: {reason}" for s, strat, reason in result.strategy_transitions] or ["- None."]

    lines += [
        "",
        "## 5. Decision trace",
        f"Full trace with every observation, decision and outcome: `{result.config_name}_trace.json`.",
        "",
        "| Step | Position | Action | Strategy | Battery | Top candidate | Reason |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    trace = result.action_trace
    shown = trace if len(trace) <= trace_rows + 4 else trace[:trace_rows] + trace[-4:]
    for i, e in enumerate(shown):
        if len(trace) > trace_rows + 4 and i == trace_rows:
            lines.append(f"| … | | | | | | *{len(trace) - trace_rows - 4} steps omitted* |")
        lines.append(
            f"| {e['step']} | {_fmt(e['agent_pos'])} | `{e['action']}` | `{e['strategy']}` | {e['battery']:.1f} | "
            f"{_fmt(e['top_candidate'])} P={e['top_candidate_prob']:.2f} | {e['reason']} |"
        )

    lines += [
        "",
        "## 6. After-mission evaluation (ground truth, never visible to the agent)",
        f"- True EVE position {_fmt(ev['true_eve_pos'])}, true status {ev['true_eve_status']}",
        f"- Localization error of the final estimate: {ev['localization_error']:.2f} cells "
        f"(expected error under the belief: {ev['expected_error']:.2f})",
        f"- Status inference correct: {'yes' if ev['status_correct'] else 'no'} · "
        f"true position inside 90% credible region: {'yes' if ev['true_pos_in_credible_region'] else 'no'}",
    ]
    if ev["decoys"]:
        lines.append(
            f"- Decoy beacons: {', '.join(_fmt(d) for d in ev['decoys'])} · inspected: "
            f"{', '.join(_fmt(d) for d in ev['decoys_inspected']) or 'none'} · flagged as spoofed: "
            f"{', '.join(_fmt(d) for d in ev['decoys_flagged']) or 'none'}"
        )
    if ev["genuine_flagged"]:
        lines.append(f"- Genuine beacons wrongly flagged: {', '.join(_fmt(g) for g in ev['genuine_flagged'])}")
    return "\n".join(lines) + "\n"
