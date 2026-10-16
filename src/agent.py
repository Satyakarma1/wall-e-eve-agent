"""Autonomous WALL-E agent with an explainable observe -> update belief -> decide -> act loop.

The agent never touches the Environment object. It only receives a public `MissionBriefing`
(map size, docks, initial signal, budgets) and the `Observation` returned after each action.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from src.belief import BeliefMap
from src.environment import Action, Coord, MissionBriefing, Observation
from src.pathfinding import a_star_search, bfs_distance_map, bfs_tree, path_from_tree
from src.signal_model import bearing_deg_from_vector


class Strategy(str, Enum):
    EXPLORE_FOR_CLUES = "EXPLORE_FOR_CLUES"
    ACQUIRE_CLUE = "ACQUIRE_CLUE"
    PULSE_SCAN = "PULSE_SCAN"
    HUNT_BELIEF_TARGET = "HUNT_BELIEF_TARGET"
    RETURN_TO_CHARGE = "RETURN_TO_CHARGE"
    ABORT_UNREACHABLE = "ABORT_UNREACHABLE"
    MISSION_COMPLETE = "MISSION_COMPLETE"


STRATEGY_DESCRIPTIONS = {
    Strategy.EXPLORE_FOR_CLUES: "Sweep the nearest unseen territory to find beacons (or EVE).",
    Strategy.ACQUIRE_CLUE: "Travel to a sighted beacon and decode its signal.",
    Strategy.PULSE_SCAN: "Fire a range/strength pulse to shrink uncertainty or arbitrate conflicting beacons.",
    Strategy.HUNT_BELIEF_TARGET: "Head for the best belief cell, trading probability against distance.",
    Strategy.RETURN_TO_CHARGE: "Turn back to a dock and recharge before the round trip becomes impossible.",
    Strategy.ABORT_UNREACHABLE: "Stop: EVE is almost surely sealed off from every reachable cell.",
    Strategy.MISSION_COMPLETE: "Rendezvous with EVE.",
}


@dataclass
class AgentConfig:
    """Tunable policy parameters (see README: Agent policy)."""
    use_signals: bool = True              # False = frontier baseline ignoring initial signal, beacons, scans
    clue_reliability_prior: float = 0.8   # prior P(beacon genuine); 1.0 = naive agent that trusts every beacon
    battery_reserve: float = 3.0          # never plan to be stranded with less than this
    scan_entropy_threshold: float = 3.0   # scan only while belief entropy (bits) exceeds this
    min_scan_spacing: int = 3             # new scan must be >= this many cells from previous scans
    hunt_min_ratio: float = 2.5           # hunt when top P >= ratio x (1 / possible cells)
    commit_probability: float = 0.5       # skip the return-trip reserve when goal P >= this
    clue_value_threshold: float = 0.6     # stop detouring for beacons once top P >= this
    abort_reachable_mass: float = 0.05    # abort when less belief than this lies in reachable cells
    decoy_threshold: float = 0.2          # flag a beacon as spoofed when P(genuine) < this
    distance_penalty: float = 0.1         # hunt score = P / (1 + penalty * moves)


@dataclass
class TraceRecord:
    """Detailed record of one decision (what was observed, believed, decided and why)."""
    step: int
    agent_pos: Coord
    action: Action
    reason: str
    strategy: Strategy
    battery: float
    belief_entropy: float
    top_candidate: Coord
    top_candidate_prob: float
    scan_budget: int = 0
    status_belief: Dict[str, float] = field(default_factory=dict)
    goal: Optional[Coord] = None
    plan: List[Coord] = field(default_factory=list)
    observation: Dict[str, Any] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)
    clue_reliability: Dict[Coord, float] = field(default_factory=dict)
    flagged_decoys: List[Coord] = field(default_factory=list)
    message: str = ""


@dataclass
class _Decision:
    action: Action
    strategy: Strategy
    reason: str
    goal: Optional[Coord] = None
    plan: List[Coord] = field(default_factory=list)
    extra_cost: float = 0.0
    goal_prob: float = 0.0


def _coord_to_action(from_pos: Coord, to_pos: Coord) -> Action:
    """Convert a 1-step move between adjacent coordinates into an action."""
    delta = (to_pos[0] - from_pos[0], to_pos[1] - from_pos[1])
    return {
        (-1, 0): Action.MOVE_UP,
        (1, 0): Action.MOVE_DOWN,
        (0, -1): Action.MOVE_LEFT,
        (0, 1): Action.MOVE_RIGHT,
    }.get(delta, Action.TERMINATE)


def _jsonable(value: Any) -> Any:
    """Tuples -> lists and rounded floats so trace entries serialize cleanly."""
    if isinstance(value, dict):
        return {str(k) if isinstance(k, tuple) else k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return round(float(value), 4)
    if isinstance(value, np.integer):
        return int(value)
    return value


class WallEAgent:
    """
    Autonomous agent: BFS-optimal navigation over its own map, a Bayesian belief over EVE's
    location and status, energy-aware turn-back/recharge decisions and an explainable trace.
    """

    def __init__(
        self,
        bounds: Tuple[int, int],
        briefing: Optional[MissionBriefing] = None,
        config: Optional[AgentConfig] = None,
        battery_reserve_safety: Optional[float] = None,
    ):
        self.bounds = (int(bounds[0]), int(bounds[1]))
        self.rows, self.cols = self.bounds
        self.briefing = briefing
        self.cfg = replace(config) if config else AgentConfig()
        if battery_reserve_safety is not None:
            self.cfg.battery_reserve = battery_reserve_safety

        costs = briefing.action_costs if briefing else {}
        self.move_cost = float(costs.get("move", 1.0))
        self.inspect_cost = float(costs.get("inspect", 2.0))
        self.scan_cost = float(costs.get("scan", 4.0))
        self.capacity: Optional[float] = briefing.battery_capacity if briefing else None
        self.max_steps: Optional[int] = briefing.max_steps if briefing else None
        self.docks: Set[Coord] = set(briefing.charging_stations) if briefing else set()

        # Internal world model, built only from observations
        self.position: Coord = briefing.start_pos if briefing else (0, 0)
        self.known_obstacles: Set[Coord] = set()
        self.known_clues: Set[Coord] = set()
        self.inspected_clues: Set[Coord] = set()
        self.visited_cells: Set[Coord] = set()
        self.seen_cells: Set[Coord] = set()
        self.flagged_decoys: Set[Coord] = set()
        self.scan_positions: List[Coord] = []
        self.eve_sighted: Optional[Coord] = None
        self.eve_status_observed: Optional[str] = None
        self.evidence_log: List[Dict[str, Any]] = []
        self.reliabilities: Dict[Coord, float] = {}

        self.belief = BeliefMap(self.bounds, clue_reliability_prior=self.cfg.clue_reliability_prior)
        if self.cfg.use_signals and briefing and briefing.initial_signal:
            self.belief.update_with_initial_signal(briefing.initial_signal, briefing.signal_age_minutes)
            self.evidence_log.append({
                "step": 0,
                "type": "initial_signal",
                **_jsonable(briefing.initial_signal),
                "age_minutes": round(briefing.signal_age_minutes, 1),
            })

        self.current_strategy: Optional[Strategy] = None
        self.current_goal: Optional[Coord] = None
        self._recharging = False
        self._last_observation: Dict[str, Any] = {}
        self.history: List[TraceRecord] = []
        self.strategy_transitions: List[Tuple[int, Strategy, str]] = []

    # ================================================================ observe
    def observe(self, obs: Observation) -> List[str]:
        """Integrate one observation into the map and belief; return notable events."""
        events: List[str] = []
        pos = obs.agent_pos
        self.position = pos
        self.visited_cells.add(pos)

        new_obstacles: List[Coord] = []
        new_clues: List[Coord] = []
        empty_cells: List[Coord] = []
        for coord, kind in obs.local_sensor.items():
            self.seen_cells.add(coord)
            if kind == "EVE":
                if self.eve_sighted is None:
                    events.append(f"EVE sighted at {coord}!")
                    self.evidence_log.append({"step": obs.step_count, "type": "eve_sighting", "pos": list(coord)})
                self.eve_sighted = coord
                continue
            empty_cells.append(coord)
            if kind == "OBSTACLE" and coord not in self.known_obstacles:
                self.known_obstacles.add(coord)
                new_obstacles.append(coord)
            elif kind == "CLUE" and coord not in self.known_clues:
                self.known_clues.add(coord)
                new_clues.append(coord)
                events.append(f"Beacon sighted at {coord}")
        self.belief.mark_cells_empty(empty_cells)

        if obs.target_found:
            self.eve_sighted = pos
        if self.eve_sighted is not None:
            self.belief.set_certain(self.eve_sighted)

        if obs.clue_payload is not None:
            p = obs.clue_payload
            c_pos: Coord = tuple(p["clue_pos"])  # type: ignore[assignment]
            self.inspected_clues.add(c_pos)
            bearing = float(p.get("bearing_deg", bearing_deg_from_vector(*p["bearing_vector"])))
            if self.cfg.use_signals:
                self.belief.update_with_clue(
                    c_pos,
                    float(p["estimated_distance"]),
                    tuple(p["bearing_vector"]),  # type: ignore[arg-type]
                    float(p.get("noise_sigma", 0.0)),
                    float(p.get("bearing_noise_deg", 0.0)),
                )
            events.append(
                f"Beacon {c_pos} decoded: EVE ~{p['estimated_distance']:.1f} cells away at bearing {bearing:.0f}°"
            )
            self.evidence_log.append({
                "step": obs.step_count, "type": "beacon", "pos": list(c_pos),
                "distance": round(float(p["estimated_distance"]), 2), "bearing_deg": round(bearing, 1),
                "noise_sigma": p.get("noise_sigma", 0.0), "bearing_noise_deg": p.get("bearing_noise_deg", 0.0),
            })

        if obs.scan_result is not None:
            s = obs.scan_result
            s_pos: Coord = tuple(s["scanner_pos"])  # type: ignore[assignment]
            self.scan_positions.append(s_pos)
            strength = s.get("signal_strength")
            if self.cfg.use_signals:
                self.belief.update_with_scan(
                    s_pos,
                    float(s["estimated_distance"]),
                    float(s.get("noise_sigma", 1.0)),
                    strength,
                    float(s.get("strength_noise_sigma", 0.02)),
                )
            events.append(
                f"Pulse scan from {s_pos}: EVE ~{s['estimated_distance']:.1f} cells away, strength {strength:.3f}"
            )
            self.evidence_log.append({
                "step": obs.step_count, "type": "scan", "pos": list(s_pos),
                "distance": round(float(s["estimated_distance"]), 2), "strength": round(float(strength), 4),
            })

        if obs.target_found and obs.eve_status_observed:
            self.eve_status_observed = obs.eve_status_observed
            self.belief.observe_status(obs.eve_status_observed)
            events.append(f"Rendezvous with EVE at {pos}: status {obs.eve_status_observed}")
            self.evidence_log.append({
                "step": obs.step_count, "type": "rendezvous", "pos": list(pos), "status": obs.eve_status_observed,
            })

        if obs.collision_detected:
            events.append("Bumped into an obstacle")
        if obs.recharged > 0:
            events.append(f"Recharged +{obs.recharged:.0f}")

        # Decoy detection: exact posterior that each decoded beacon is genuine
        self.reliabilities = self.belief.all_clue_reliabilities() if self.cfg.use_signals else {}
        for c_pos, rel in self.reliabilities.items():
            if rel < self.cfg.decoy_threshold and c_pos not in self.flagged_decoys:
                self.flagged_decoys.add(c_pos)
                events.append(f"Beacon {c_pos} rejected as spoofed (P genuine={rel:.2f})")
            elif rel >= 0.5 and c_pos in self.flagged_decoys:
                self.flagged_decoys.discard(c_pos)
                events.append(f"Beacon {c_pos} trusted again (P genuine={rel:.2f})")

        self._last_observation = _jsonable({
            "position": pos,
            "battery": obs.battery,
            "scan_budget": obs.scan_budget,
            "new_obstacles": new_obstacles,
            "new_beacons": new_clues,
            "eve_in_view": self.eve_sighted if self.eve_sighted in obs.local_sensor else None,
            "clue_payload": obs.clue_payload,
            "scan_result": obs.scan_result,
            "collision": obs.collision_detected,
            "at_dock": obs.at_charging_station,
            "recharged": obs.recharged,
            "message": obs.message,
        })
        return events

    # ================================================================= decide
    def decide(self, obs: Observation) -> _Decision:
        """Choose the next action from the current map, belief and battery."""
        pos, battery, cfg = obs.agent_pos, obs.battery, self.cfg

        if obs.target_found:
            return _Decision(Action.TERMINATE, Strategy.MISSION_COMPLETE, f"Rendezvous with EVE at {pos}: mission complete")

        dist, parent = bfs_tree(pos, self.bounds, self.known_obstacles)
        dock_dist = bfs_distance_map(self.docks, self.bounds, self.known_obstacles) if self.docks else None

        if self.eve_sighted is not None:
            path = self._route(parent, pos, self.eve_sighted)
            if path and len(path) > 1:
                return self._move_along(
                    path, Strategy.HUNT_BELIEF_TARGET,
                    f"EVE sighted at {self.eve_sighted}: closing in ({len(path) - 1} moves)", goal_prob=1.0,
                )

        if self._recharging:
            out_of_time = self.max_steps is not None and obs.step_count >= self.max_steps - 1
            if pos in self.docks and self.capacity and battery < self.capacity - 0.5 and not out_of_time:
                return _Decision(
                    Action.RECHARGE, Strategy.RETURN_TO_CHARGE,
                    f"Docked at {pos}: recharging ({battery:.0f}/{self.capacity:.0f})", goal=pos,
                )
            self._recharging = False

        if cfg.use_signals and pos in self.known_clues and pos not in self.inspected_clues and battery > self.inspect_cost:
            return _Decision(Action.INSPECT, Strategy.ACQUIRE_CLUE, f"Standing on beacon {pos}: decoding its signal", goal=pos)

        grid = self.belief.grid
        reachable_mass = float(grid[np.isfinite(dist)].sum())
        if reachable_mass < cfg.abort_reachable_mass:
            best = self.belief.most_likely_position()
            return _Decision(
                Action.TERMINATE, Strategy.ABORT_UNREACHABLE,
                f"EVE most likely at {best} (P={grid[best]:.2f}) but only {reachable_mass:.1%} of the belief lies "
                f"in cells WALL-E can reach: debris seals her off. Terminating to save resources.",
                goal=best,
            )

        decision = (
            self._plan_clue(pos, dist, parent, grid)
            or self._plan_scan(obs, dock_dist)
            or self._plan_hunt(pos, dist, parent, grid)
            or self._plan_explore(pos, dist, parent, grid)
            or self._plan_hunt(pos, dist, parent, grid, force=True)
        )
        if decision is None:
            return _Decision(
                Action.TERMINATE, Strategy.ABORT_UNREACHABLE,
                "No reachable cell can still contain EVE: search space exhausted.",
            )
        return self._apply_energy_policy(decision, obs, dist, parent, dock_dist)

    def _route(self, parent: Dict[Coord, Coord], start: Coord, goal: Coord) -> Optional[List[Coord]]:
        """Shortest route on the known map; A* tie-breaking keeps it close to the straight line."""
        return a_star_search(start, goal, self.bounds, self.known_obstacles) or path_from_tree(parent, start, goal)

    def _move_along(self, path: List[Coord], strategy: Strategy, reason: str,
                    extra_cost: float = 0.0, goal_prob: float = 0.0) -> _Decision:
        return _Decision(
            _coord_to_action(path[0], path[1]), strategy, reason,
            goal=path[-1], plan=list(path), extra_cost=extra_cost, goal_prob=goal_prob,
        )

    def _plan_clue(self, pos: Coord, dist: np.ndarray, parent: Dict[Coord, Coord], grid: np.ndarray) -> Optional[_Decision]:
        if not self.cfg.use_signals or float(grid.max()) >= self.cfg.clue_value_threshold:
            return None
        pending = [c for c in self.known_clues if c not in self.inspected_clues and np.isfinite(dist[c])]
        if not pending:
            return None
        target = min(pending, key=lambda c: (dist[c], c))
        path = self._route(parent, pos, target)
        if not path or len(path) < 2:
            return None
        return self._move_along(
            path, Strategy.ACQUIRE_CLUE,
            f"Beacon at {target} not yet decoded ({int(dist[target])} moves): going to inspect it",
            extra_cost=self.inspect_cost,
        )

    def _plan_scan(self, obs: Observation, dock_dist: Optional[np.ndarray]) -> Optional[_Decision]:
        cfg = self.cfg
        if not cfg.use_signals or obs.scan_budget <= 0:
            return None
        entropy = self.belief.get_entropy()
        conflicts = sorted((r, c) for c, r in self.reliabilities.items() if cfg.decoy_threshold <= r < 0.5)
        if entropy <= cfg.scan_entropy_threshold and not conflicts:
            return None

        pos = obs.agent_pos
        spacing = min((max(abs(pos[0] - s[0]), abs(pos[1] - s[1])) for s in self.scan_positions), default=None)
        if spacing is not None and spacing < cfg.min_scan_spacing:
            return None
        back = 0.0
        if dock_dist is not None and np.isfinite(dock_dist[pos]):
            back = float(dock_dist[pos]) * self.move_cost
        if obs.battery - self.scan_cost - back < cfg.battery_reserve:
            return None

        if conflicts:
            rel, beacon = conflicts[0]
            reason = f"Beacon {beacon} conflicts with other evidence (P genuine={rel:.2f}): scanning to arbitrate"
        elif spacing is None:
            reason = f"Belief entropy {entropy:.1f} bits: first pulse scan to measure EVE's range and signal strength"
        else:
            reason = (f"Belief entropy {entropy:.1f} bits: scanning from a new vantage point "
                      f"{spacing} cells from the last scan to triangulate")
        return _Decision(Action.SCAN, Strategy.PULSE_SCAN, reason, goal=pos)

    def _plan_hunt(self, pos: Coord, dist: np.ndarray, parent: Dict[Coord, Coord], grid: np.ndarray,
                   force: bool = False) -> Optional[_Decision]:
        cfg = self.cfg
        if not cfg.use_signals and not force:
            return None
        possible = max(1, int((grid > 1e-12).sum()))
        informative = (
            float(grid.max()) >= cfg.hunt_min_ratio / possible
            or bool(self.inspected_clues)
            or bool(self.scan_positions)
        )
        if not (informative or force):
            return None

        reachable_grid = np.where(np.isfinite(dist), grid, 0.0)
        reachable_grid[pos] = 0.0
        flat = reachable_grid.ravel()
        best: Optional[Coord] = None
        best_score = -1.0
        for i in np.argsort(-flat, kind="stable")[:12]:
            if flat[i] <= 1e-12:
                break
            cell = (int(i) // self.cols, int(i) % self.cols)
            score = flat[i] / (1.0 + cfg.distance_penalty * dist[cell])
            if score > best_score:
                best, best_score = cell, score
        if best is None:
            return None

        goal = self.current_goal
        if (goal is not None and goal != best and goal != pos and self.current_strategy == Strategy.HUNT_BELIEF_TARGET
                and np.isfinite(dist[goal]) and reachable_grid[goal] > 1e-12):
            if reachable_grid[goal] / (1.0 + cfg.distance_penalty * dist[goal]) >= 0.85 * best_score:
                best = goal  # hysteresis: avoid dithering between near-equal targets

        path = self._route(parent, pos, best)
        if not path or len(path) < 2:
            return None
        p = float(grid[best])
        return self._move_along(
            path, Strategy.HUNT_BELIEF_TARGET,
            f"Belief target {best}: P={p:.2f}, {int(dist[best])} moves away", goal_prob=p,
        )

    def _plan_explore(self, pos: Coord, dist: np.ndarray, parent: Dict[Coord, Coord], grid: np.ndarray) -> Optional[_Decision]:
        unseen = np.ones(self.bounds, dtype=bool)
        for cell in self.seen_cells:
            unseen[cell] = False
        candidate_dist = np.where(np.isfinite(dist) & unseen, dist, np.inf)
        nearest = float(candidate_dist.min())
        if not np.isfinite(nearest):
            return None
        ties = [tuple(int(v) for v in t) for t in np.argwhere(candidate_dist == nearest)]
        target: Coord = max(ties, key=lambda c: (grid[c], -c[0], -c[1]))  # type: ignore[assignment]
        path = self._route(parent, pos, target)
        if not path or len(path) < 2:
            return None
        return self._move_along(
            path, Strategy.EXPLORE_FOR_CLUES,
            f"Exploring unseen territory at {target} ({int(nearest)} moves) for beacons or EVE",
            goal_prob=float(grid[target]),
        )

    def _apply_energy_policy(self, decision: _Decision, obs: Observation, dist: np.ndarray,
                             parent: Dict[Coord, Coord], dock_dist: Optional[np.ndarray]) -> _Decision:
        """Turn back to recharge when the planned trip plus the way home no longer fits the battery."""
        if decision.action not in (Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT):
            return decision
        if dock_dist is None or self.capacity is None or decision.goal is None:
            return decision

        cfg = self.cfg
        pos, battery = obs.agent_pos, obs.battery
        cost_to_goal = (len(decision.plan) - 1) * self.move_cost + decision.extra_cost
        back = float(dock_dist[decision.goal])
        if not np.isfinite(back):
            return decision
        needed = cost_to_goal + back * self.move_cost + cfg.battery_reserve
        if battery >= needed:
            return decision
        if decision.goal_prob >= cfg.commit_probability and battery >= cost_to_goal + 0.5:
            decision.reason += f"; committing one-way (P={decision.goal_prob:.2f}), no return reserve"
            return decision

        here_back = float(dock_dist[pos])
        round_trip_from_dock = 2 * back * self.move_cost + decision.extra_cost + cfg.battery_reserve
        recharge_helps = round_trip_from_dock <= self.capacity and battery < self.capacity - 1.0
        if not (recharge_helps and np.isfinite(here_back) and battery >= here_back * self.move_cost):
            return decision  # recharging cannot make this trip safer: best effort

        shortfall = (f"battery {battery:.0f} < {needed:.0f} needed to reach {decision.goal} "
                     f"({cost_to_goal:.0f}) and return to a dock ({back:.0f}) with reserve")
        if here_back == 0:
            self._recharging = True
            return _Decision(Action.RECHARGE, Strategy.RETURN_TO_CHARGE, f"Docked: recharging first, {shortfall}", goal=pos)
        dock = min(self.docks, key=lambda d: (dist[d], d))
        path = self._route(parent, pos, dock)
        if not path or len(path) < 2:
            return decision
        return self._move_along(
            path, Strategy.RETURN_TO_CHARGE,
            f"Turning back to dock {dock} ({len(path) - 1} moves): {shortfall}",
        )

    # =================================================================== step
    def _set_strategy(self, step: int, new_strategy: Strategy, reason: str, replan_note: Optional[str] = None) -> None:
        """Record strategy transitions (and evidence-driven re-plans within the same strategy)."""
        if self.current_strategy != new_strategy:
            note = f"{replan_note} -> {reason}" if replan_note else reason
            self.strategy_transitions.append((step, new_strategy, note))
            self.current_strategy = new_strategy
        elif replan_note:
            self.strategy_transitions.append((step, new_strategy, f"Re-plan after {replan_note}: {reason}"))

    def step(self, obs: Observation) -> Action:
        """Observe, decide and record an explainable trace entry; return the chosen action."""
        events = self.observe(obs)
        decision = self.decide(obs)

        replan = next((e for e in events if "rejected as spoofed" in e or "EVE sighted" in e), None)
        self._set_strategy(obs.step_count, decision.strategy, decision.reason, replan_note=replan)
        self.current_goal = decision.goal

        top = self.belief.get_top_candidates(k=1)
        top_cand, top_prob = top[0] if top else (obs.agent_pos, 0.0)
        self.history.append(TraceRecord(
            step=obs.step_count,
            agent_pos=obs.agent_pos,
            action=decision.action,
            reason=decision.reason,
            strategy=decision.strategy,
            battery=obs.battery,
            belief_entropy=round(self.belief.get_entropy(), 3),
            top_candidate=top_cand,
            top_candidate_prob=round(top_prob, 3),
            scan_budget=obs.scan_budget,
            status_belief={k: round(v, 4) for k, v in self.belief.status_probabilities().items()},
            goal=decision.goal,
            plan=list(decision.plan),
            observation=self._last_observation,
            events=events,
            clue_reliability={k: round(v, 4) for k, v in self.reliabilities.items()},
            flagged_decoys=sorted(self.flagged_decoys),
            message=obs.message,
        ))
        return decision.action

    # ============================================================== inference
    def inference_summary(self) -> Dict[str, Any]:
        """Final conclusions for the mission report: location, status, confidence, evidence."""
        grid = self.belief.grid
        best = self.belief.most_likely_position()
        neighborhood = [(best[0] + dr, best[1] + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
        region = self.belief.credible_region(0.9)
        status_p = self.belief.status_probabilities()
        status_est = max(status_p, key=status_p.get)

        dist, _ = bfs_tree(self.position, self.bounds, self.known_obstacles)
        reachable = np.isfinite(dist)
        reachable_mass = float(grid[reachable].sum())

        if self.eve_status_observed is not None:
            conclusion = "EVE_FOUND"
        elif reachable_mass < self.cfg.abort_reachable_mass:
            conclusion = "EVE_UNREACHABLE"
        elif self.belief.mass_in(neighborhood) >= 0.8:
            conclusion = "EVE_LOCALIZED"
        else:
            conclusion = "SEARCH_INCOMPLETE"

        evidence = [dict(e) for e in self.evidence_log]
        for e in evidence:
            if e["type"] == "beacon":
                rel = self.reliabilities.get(tuple(e["pos"]))
                e["p_genuine"] = round(rel, 4) if rel is not None else None
                e["flagged_decoy"] = tuple(e["pos"]) in self.flagged_decoys

        return {
            "conclusion": conclusion,
            "map_estimate": list(best),
            "map_probability": round(float(grid[best]), 4),
            "p_within_1_cell": round(self.belief.mass_in(neighborhood), 4),
            "credible_region_90": [list(c) for c in region],
            "entropy_bits": round(self.belief.get_entropy(), 3),
            "status_probabilities": {k: round(v, 4) for k, v in status_p.items()},
            "status_estimate": self.eve_status_observed or status_est,
            "status_confidence": 1.0 if self.eve_status_observed else round(status_p[status_est], 4),
            "status_observed": self.eve_status_observed is not None,
            "reachable_mass": round(reachable_mass, 4),
            "flagged_decoys": [list(c) for c in sorted(self.flagged_decoys)],
            "evidence": evidence,
            "breach_candidates": (
                [list(c) for c in self._breach_candidates(reachable, best)] if conclusion == "EVE_UNREACHABLE" else []
            ),
            "last_position": list(self.position),
            "known_docks": [list(d) for d in sorted(self.docks)],
        }

    def _breach_candidates(self, reachable: np.ndarray, target: Coord) -> List[Coord]:
        """Known obstacles separating WALL-E's reachable area from the pocket around `target`."""
        pocket_dist = bfs_distance_map([target], self.bounds, self.known_obstacles)
        pocket = np.isfinite(pocket_dist)
        candidates = []
        for o in self.known_obstacles:
            nbrs = [(o[0] + dr, o[1] + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            nbrs = [n for n in nbrs if 0 <= n[0] < self.rows and 0 <= n[1] < self.cols]
            if any(reachable[n] for n in nbrs) and any(pocket[n] for n in nbrs):
                candidates.append(o)
        return sorted(candidates, key=lambda o: (abs(o[0] - target[0]) + abs(o[1] - target[1]), o))[:3]


class FrontierBaselineAgent(WallEAgent):
    """
    Ablation baseline: identical sensing, navigation and energy rules, but it ignores every
    signal (initial reading, beacons, scans) and simply sweeps the nearest unseen territory.
    """

    def __init__(self, bounds: Tuple[int, int], briefing: Optional[MissionBriefing] = None):
        super().__init__(bounds, briefing, AgentConfig(use_signals=False))


BaselineRandomAgent = FrontierBaselineAgent  # backward-compatible name
