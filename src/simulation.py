"""Simulation orchestrator: runs a mission and captures the full explainable trace."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from src.agent import AgentConfig, FrontierBaselineAgent, TraceRecord, WallEAgent, _jsonable
from src.environment import Coord, Environment, MissionBriefing, Observation

AGENT_TYPES = ("walle", "naive", "baseline")


@dataclass
class SimulationResult:
    """Everything one mission produced: metrics, trace, beliefs, conclusions and ground truth."""
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
    belief_history: List[np.ndarray]          # belief used for the decision at each step
    mission_name: str = ""
    agent_type: str = "walle"
    energy_recharged: float = 0.0
    recharge_count: int = 0
    inspect_count: int = 0
    clues_inspected: int = 0
    sensor_coverage_pct: float = 0.0
    briefing: Dict[str, Any] = field(default_factory=dict)
    inference: Dict[str, Any] = field(default_factory=dict)
    evaluation: Dict[str, Any] = field(default_factory=dict)
    initial_revealed: List[List[Any]] = field(default_factory=list)
    belief_prior: Optional[np.ndarray] = None
    belief_final: Optional[np.ndarray] = None


def make_agent(
    agent_type: str,
    briefing: MissionBriefing,
    agent_config: Optional[AgentConfig] = None,
) -> WallEAgent:
    """walle = robust Bayesian agent, naive = trusts every beacon, baseline = signal-blind sweep."""
    if agent_type == "walle":
        return WallEAgent(briefing.grid_size, briefing, agent_config)
    if agent_type == "naive":
        return WallEAgent(briefing.grid_size, briefing, AgentConfig(clue_reliability_prior=1.0))
    if agent_type == "baseline":
        return FrontierBaselineAgent(briefing.grid_size, briefing)
    raise ValueError(f"Unknown agent type '{agent_type}'. Choose from {AGENT_TYPES}.")


def _serialize_step(record: TraceRecord, outcome: Observation, revealed: List[List[Any]], status: str) -> Dict[str, Any]:
    return {
        "step": record.step,
        "agent_pos": list(record.agent_pos),
        "action": record.action.value,
        "strategy": record.strategy.value,
        "reason": record.reason,
        "battery": round(record.battery, 2),
        "scan_budget": record.scan_budget,
        "belief_entropy": record.belief_entropy,
        "top_candidate": list(record.top_candidate),
        "top_candidate_prob": record.top_candidate_prob,
        "status_belief": record.status_belief,
        "goal": list(record.goal) if record.goal is not None else None,
        "plan": [list(p) for p in record.plan],
        "events": list(record.events),
        "clue_reliability": {f"{k[0]},{k[1]}": v for k, v in record.clue_reliability.items()},
        "flagged_decoys": [list(c) for c in record.flagged_decoys],
        "observation": record.observation,
        "outcome": {
            "agent_pos": list(outcome.agent_pos),
            "battery": round(outcome.battery, 2),
            "scan_budget": outcome.scan_budget,
            "collision": outcome.collision_detected,
            "recharged": round(outcome.recharged, 2),
            "message": outcome.message,
            "revealed": revealed,
            "scan_result": _jsonable(outcome.scan_result),
            "clue_payload": _jsonable(outcome.clue_payload),
            "status": status,
        },
    }


def _status_before_contact(trace: List[Dict[str, Any]]) -> Optional[str]:
    """Status WALL-E had inferred from signals alone, at the moment EVE was first sighted (or at the end)."""
    if not trace:
        return None
    step = next((s for s in trace if any("EVE sighted" in e for e in s["events"])), trace[-1])
    belief = step["status_belief"]
    return max(belief, key=belief.get) if belief else None


def _evaluate(inference: Dict[str, Any], truth: Dict[str, Any], agent: WallEAgent,
              trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """After-mission comparison with ground truth (never visible to the agent)."""
    eve = tuple(truth["eve_pos"])
    est = tuple(inference["map_estimate"])
    decoys = sorted(pos for pos, c in truth["clues"].items() if c["type"] == "decoy")
    genuine = sorted(pos for pos, c in truth["clues"].items() if c["type"] != "decoy")
    inferred_status = _status_before_contact(trace)
    return {
        "true_eve_pos": list(eve),
        "true_eve_status": truth["eve_status"],
        "localization_error": round(math.hypot(est[0] - eve[0], est[1] - eve[1]), 3),
        "expected_error": round(agent.belief.expected_target_error(eve), 3),
        "status_correct": inference["status_estimate"] == truth["eve_status"],
        "status_inferred_before_contact": inferred_status,
        "status_inference_correct": inferred_status == truth["eve_status"],
        "true_pos_in_credible_region": list(eve) in inference["credible_region_90"],
        "decoys": [list(d) for d in decoys],
        "decoys_inspected": [list(d) for d in decoys if d in agent.inspected_clues],
        "decoys_flagged": [list(d) for d in decoys if d in agent.flagged_decoys],
        "genuine_flagged": [list(g) for g in genuine if g in agent.flagged_decoys],
    }


def run_mission(
    config_data_or_path: Union[Dict[str, Any], str, Path],
    random_seed: Optional[int] = None,
    record_belief_history: bool = True,
    agent_type: str = "walle",
    agent_config: Optional[AgentConfig] = None,
) -> SimulationResult:
    """Run one autonomous mission to completion and collect its trace, beliefs and conclusions."""
    env = Environment(config_data_or_path)
    obs = env.reset(new_seed=random_seed)
    briefing = env.get_briefing()
    agent = make_agent(agent_type, briefing, agent_config)

    belief_prior = agent.belief.grid.copy()
    seen = set(obs.local_sensor)
    initial_revealed = [[r, c, kind] for (r, c), kind in obs.local_sensor.items()]
    belief_history: List[np.ndarray] = []
    trace: List[Dict[str, Any]] = []

    done = env.done
    while not done:
        action = agent.step(obs)
        if record_belief_history:
            belief_history.append(agent.belief.grid.copy())
        next_obs, _, done, info = env.step(action)
        revealed = [[r, c, kind] for (r, c), kind in next_obs.local_sensor.items() if (r, c) not in seen]
        seen.update(next_obs.local_sensor)
        trace.append(_serialize_step(agent.history[-1], next_obs, revealed, info["status"]))
        obs = next_obs

    agent.observe(obs)  # integrate the final observation (last scan, rendezvous) before concluding

    summary = env.get_summary_info()
    truth = env.get_ground_truth_for_eval()
    inference = agent.inference_summary()
    evaluation = _evaluate(inference, truth, agent, trace)

    ground_truth = {
        "eve_pos": list(truth["eve_pos"]),
        "eve_status": truth["eve_status"],
        "obstacles": sorted([list(o) for o in truth["obstacles"]]),
        "clues": [
            {"pos": list(pos), **{k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}}
            for pos, cfg in sorted(truth["clues"].items())
        ],
        "grid_size": list(truth["grid_size"]),
        "start_pos": list(truth["start_pos"]),
        "charging_stations": [list(p) for p in truth["charging_stations"]],
    }

    return SimulationResult(
        config_name=env.config_name,
        mission_name=env.mission_name,
        agent_type=agent_type,
        status=summary["status"],
        success=summary["success"],
        total_steps=summary["step_count"],
        path_length=summary["path_length"],
        battery_used=summary["battery_used"],
        battery_remaining=summary["battery_remaining"],
        energy_recharged=summary["energy_recharged"],
        recharge_count=summary["recharge_count"],
        scan_count=summary["scan_count"],
        inspect_count=summary["inspect_count"],
        cells_visited=summary["cells_visited"],
        exploration_coverage_pct=summary["exploration_coverage_pct"],
        sensor_coverage_pct=summary["sensor_coverage_pct"],
        clues_discovered=summary["clues_discovered"],
        clues_inspected=summary["clues_inspected"],
        total_clues=summary["total_clues"],
        path_taken=list(env.path_taken),
        action_trace=trace,
        strategy_transitions=[(s, strat.value, r) for s, strat, r in agent.strategy_transitions],
        ground_truth=ground_truth,
        belief_history=belief_history,
        briefing=json.loads(json.dumps(asdict(briefing))),
        inference=inference,
        evaluation=evaluation,
        initial_revealed=initial_revealed,
        belief_prior=belief_prior,
        belief_final=agent.belief.grid.copy(),
    )


def outcome_metrics(result: SimulationResult) -> Dict[str, Any]:
    """Flat dictionary of the mission's quantitative outcome."""
    return {
        "status": result.status,
        "success": result.success,
        "total_steps": result.total_steps,
        "path_length": result.path_length,
        "battery_used": result.battery_used,
        "battery_remaining": result.battery_remaining,
        "energy_recharged": result.energy_recharged,
        "recharge_count": result.recharge_count,
        "scan_count": result.scan_count,
        "inspect_count": result.inspect_count,
        "cells_visited": result.cells_visited,
        "exploration_coverage_pct": result.exploration_coverage_pct,
        "sensor_coverage_pct": result.sensor_coverage_pct,
        "clues_discovered": result.clues_discovered,
        "clues_inspected": result.clues_inspected,
        "total_clues": result.total_clues,
    }


def save_trace_json(result: SimulationResult, output_path: Union[str, Path]) -> Path:
    """Save the complete machine-readable mission log (every observation, decision and outcome)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mission": {"config_name": result.config_name, "mission_name": result.mission_name, "agent_type": result.agent_type},
        "briefing": result.briefing,
        "outcome": outcome_metrics(result),
        "inference": result.inference,
        "strategy_transitions": [list(t) for t in result.strategy_transitions],
        "steps": result.action_trace,
        "evaluation_ground_truth": {**result.evaluation, "ground_truth": result.ground_truth},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    return path


def save_mission_report(result: SimulationResult, output_path: Union[str, Path]) -> Path:
    """Save the human-readable markdown mission report."""
    from src.report import render_report_markdown

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report_markdown(result), encoding="utf-8")
    return path
