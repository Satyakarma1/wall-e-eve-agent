"""Terminal (ASCII) replay of a mission — the "ASCII" option of the visualization bonus.

Legend:  ? never sensed   . sensed free   # obstacle   W WALL-E   D dock   * beacon
         x beacon rejected as spoofed   E EVE (only once sighted)   + current goal
         path cells use the strategy that entered them: h hunt, a acquire, s scan, e explore, r return
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, TextIO

from src.frames import STRATEGY_LABELS, mission_frames
from src.simulation import SimulationResult

PATH_LETTERS = {
    "HUNT_BELIEF_TARGET": "h",
    "ACQUIRE_CLUE": "a",
    "PULSE_SCAN": "s",
    "EXPLORE_FOR_CLUES": "e",
    "RETURN_TO_CHARGE": "r",
    "MISSION_COMPLETE": "c",
    "ABORT_UNREACHABLE": "!",
}
TIMELINE_LETTERS = {**PATH_LETTERS, "PULSE_SCAN": "S", "ACQUIRE_CLUE": "A", "RETURN_TO_CHARGE": "R"}


def render_frame(frame: Dict[str, Any], result: SimulationResult) -> str:
    """One frame as text: status header, decision reason, events and the fog-of-war map."""
    rows, cols = result.ground_truth["grid_size"]
    cells = [["?" for _ in range(cols)] for _ in range(rows)]
    for (r, c), kind in frame["revealed"].items():
        cells[r][c] = "#" if kind == "OBSTACLE" else "."
    for _, (r, c), strategy in frame["segments"]:
        cells[r][c] = PATH_LETTERS.get(strategy, "o")
    for r, c in result.ground_truth["charging_stations"]:
        cells[r][c] = "D"
    for r, c in frame["clues_sighted"]:
        cells[r][c] = "x" if (r, c) in frame["flagged_decoys"] else "*"
    if frame["goal"] and not frame["is_final"]:
        gr, gc = frame["goal"]
        if cells[gr][gc] in ".?":
            cells[gr][gc] = "+"
    if frame["eve_visible"] is not None:
        er, ec = frame["eve_visible"]
        cells[er][ec] = "E"
    pr, pc = frame["pos"]
    cells[pr][pc] = "W"

    step = "START" if frame["step"] is None else f"step {frame['step']:>3}/{result.total_steps}"
    strategy = STRATEGY_LABELS.get(frame["strategy"] or "", "briefing")
    lines = [
        f"WALL-E & EVE | {result.mission_name or result.config_name}",
        f"{step} | {frame['action']:<10} | {strategy:<20} | battery {frame['battery']:6.1f} | scans {frame['scan_budget']}",
        f"why: {frame['reason'][:110]}",
        f"saw: {'; '.join(frame['events'])[:110] or '-'}",
        "    " + "".join(f"{c % 10}" for c in range(cols)),
    ]
    lines += [f"{r:>3} " + "".join(row) for r, row in enumerate(cells)]
    return "\n".join(lines)


def render_timeline(result: SimulationResult) -> str:
    """One character per step showing which strategy was active (S/A/R capitalized for emphasis)."""
    letters = "".join(TIMELINE_LETTERS.get(s["strategy"], "?") for s in result.action_trace)
    chunks = [letters[i:i + 60] for i in range(0, len(letters), 60)] or [""]
    legend = "h hunt, A acquire beacon, S pulse scan, e explore, R return to charge, c complete, ! abort"
    return "strategy timeline:\n" + "\n".join(f"  {i * 60:>4} {chunk}" for i, chunk in enumerate(chunks)) + f"\n  ({legend})"


def final_ascii_summary(result: SimulationResult) -> str:
    """Final frame + strategy timeline, suitable for saving next to the other outputs."""
    frames = mission_frames(result)
    verdict = (f"outcome: {result.status} | conclusion {result.inference['conclusion']} at "
               f"{tuple(result.inference['map_estimate'])} | EVE status {result.inference['status_estimate']}")
    return "\n\n".join([render_frame(frames[-1], result), render_timeline(result), verdict]) + "\n"


def play_ascii(result: SimulationResult, delay: float = 0.15, stream: TextIO = sys.stdout) -> None:
    """Animate the mission in the terminal (ANSI clear-screen between frames)."""
    if os.name == "nt":
        os.system("")  # enable ANSI escape processing in the Windows console
    frames: List[Dict[str, Any]] = mission_frames(result)
    for frame in frames:
        stream.write("\x1b[2J\x1b[H" + render_frame(frame, result) + "\n")
        stream.flush()
        time.sleep(delay)
    stream.write("\n" + render_timeline(result) + "\n")
