"""Simulation orchestrator for running missions and capturing action traces."""

from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Union
import numpy as np

from src.environment import Environment, Action, Observation, Coord
from src.agent import WallEAgent, TraceRecord, Strategy


@dataclass
class SimulationResult:
    """Complete summary of a simulation run including metrics, trace, and belief states."""
    config_name: str
    status: str
    success: bool
    total_steps: int
    path_length: int
    battery_used: float
    battery_remaining: float
    scan_count: int
    cells_visited: int
    exploration_coverage_pct: float
    clues_discovered: int
    total_clues: int
    path_taken: List[Coord]
    action_trace: List[Dict[str, Any]]
    strategy_transitions: List[Tuple[int, str, str]]
    ground_truth: Dict[str, Any]
    belief_history: List[np.ndarray]


def run_mission(
    config_data_or_path: Union[Dict[str, Any], str, Path],
    random_seed: Optional[int] = None,
    record_belief_history: bool = True
) -> SimulationResult:
    """
    Run an autonomous mission to completion using WallEAgent.
    """
    env = Environment(config_data_or_path)
    obs = env.reset(new_seed=random_seed)

    agent = WallEAgent(bounds=env.bounds)
    belief_history: List[np.ndarray] = []

    if record_belief_history:
        belief_history.append(agent.belief.grid.copy())

    done = env.done
    while not done:
        action = agent.step(obs)
        obs, reward, done, info = env.step(action)

        if record_belief_history:
            belief_history.append(agent.belief.grid.copy())

    # Compile trace records to serializable dictionaries
    serialized_trace = [
        {
            "step": r.step,
            "agent_pos": list(r.agent_pos),
            "action": r.action.value,
            "reason": r.reason,
            "strategy": r.strategy.value,
            "battery": r.battery,
            "belief_entropy": r.belief_entropy,
            "top_candidate": list(r.top_candidate),
            "top_candidate_prob": r.top_candidate_prob,
            "message": r.message
        }
        for r in agent.history
    ]

    config_name = "custom"
    if isinstance(config_data_or_path, (str, Path)):
        config_name = Path(config_data_or_path).stem

    summary = env.get_summary_info()
    ground_truth = env.get_ground_truth_for_eval()

    # Convert sets in ground_truth to lists for serialization safety
    ground_truth["obstacles"] = [list(o) for o in ground_truth["obstacles"]]
    ground_truth["clues"] = {str(k): v for k, v in ground_truth["clues"].items()}

    return SimulationResult(
        config_name=config_name,
        status=summary["status"],
        success=summary["success"],
        total_steps=summary["step_count"],
        path_length=summary["path_length"],
        battery_used=summary["battery_used"],
        battery_remaining=summary["battery_remaining"],
        scan_count=summary["scan_count"],
        cells_visited=summary["cells_visited"],
        exploration_coverage_pct=summary["exploration_coverage_pct"],
        clues_discovered=summary["clues_discovered"],
        total_clues=summary["total_clues"],
        path_taken=list(env.path_taken),
        action_trace=serialized_trace,
        strategy_transitions=[(s, strat.value, r) for s, strat, r in agent.strategy_transitions],
        ground_truth=ground_truth,
        belief_history=belief_history
    )


def save_mission_report(result: SimulationResult, output_path: Union[str, Path]) -> None:
    """Save formatted markdown summary report of the mission."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    status_icon = "SUCCESS" if result.success else "FAILED"

    lines = [
        f"# WALL-E Mission Report — {result.config_name.upper()}",
        f"**Outcome**: `{result.status}` [{status_icon}]",
        "",
        "## Quantitative Performance Metrics",
        f"- **Mission Succeeded**: {'Yes' if result.success else 'No'}",
        f"- **Total Steps**: {result.total_steps}",
        f"- **Path Length Travelled**: {result.path_length} cells",
        f"- **Battery Consumed**: {result.battery_used} units",
        f"- **Battery Remaining**: {result.battery_remaining} units",
        f"- **Pulse Scans Executed**: {result.scan_count}",
        f"- **Cells Visited**: {result.cells_visited}",
        f"- **Exploration Coverage**: {result.exploration_coverage_pct}%",
        f"- **Clues Discovered**: {result.clues_discovered} / {result.total_clues}",
        "",
        "## Key Strategy Changes",
    ]

    if result.strategy_transitions:
        for step, strat, reason in result.strategy_transitions:
            lines.append(f"- **Step {step}** -> `{strat}`: {reason}")
    else:
        lines.append("- No strategy transitions recorded.")

    lines.extend([
        "",
        "## Action Trace (First 15 Steps)",
        "| Step | Position | Action | Strategy | Battery | Top Belief Candidate | Reason |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ])

    for entry in result.action_trace[:15]:
        pos = f"({entry['agent_pos'][0]}, {entry['agent_pos'][1]})"
        cand = f"({entry['top_candidate'][0]}, {entry['top_candidate'][1]}) P={entry['top_candidate_prob']}"
        lines.append(
            f"| {entry['step']} | {pos} | `{entry['action']}` | `{entry['strategy']}` | "
            f"{entry['battery']:.1f} | {cand} | {entry['reason']} |"
        )

    if len(result.action_trace) > 15:
        lines.append(f"*(... and {len(result.action_trace) - 15} more recorded steps)*")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
