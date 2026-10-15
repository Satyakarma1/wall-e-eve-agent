"""Autonomous AI exploration agent with explainable Observe-Decide-Act loop."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple, Dict, Any

from src.environment import Action, Observation, Coord
from src.pathfinding import a_star_search, find_nearest_frontier, get_reachable_cells
from src.belief import BeliefMap


class Strategy(str, Enum):
    EXPLORE_FOR_CLUES = "EXPLORE_FOR_CLUES"
    ACQUIRE_CLUE = "ACQUIRE_CLUE"
    HUNT_BELIEF_TARGET = "HUNT_BELIEF_TARGET"
    PULSE_SCAN = "PULSE_SCAN"
    ABORT_UNREACHABLE = "ABORT_UNREACHABLE"


@dataclass
class TraceRecord:
    """Detailed record of an agent decision at a specific step."""
    step: int
    agent_pos: Coord
    action: Action
    reason: str
    strategy: Strategy
    battery: float
    belief_entropy: float
    top_candidate: Coord
    top_candidate_prob: float
    message: str = ""


class WallEAgent:
    """
    Autonomous agent using A* pathfinding and Bayesian belief updates.
    Operates strictly within permitted observations without access to hidden state.
    """

    def __init__(self, bounds: Tuple[int, int], battery_reserve_safety: float = 2.0):
        self.bounds = bounds
        self.rows, self.cols = bounds
        self.battery_reserve_safety = battery_reserve_safety

        # Internal world model constructed strictly through observations
        self.known_obstacles: Set[Coord] = set()
        self.known_clues: Set[Coord] = set()
        self.inspected_clues: Set[Coord] = set()
        self.visited_cells: Set[Coord] = set()

        # Belief state distribution
        self.belief = BeliefMap(bounds)

        # Navigation state
        self.current_strategy: Strategy = Strategy.EXPLORE_FOR_CLUES
        self.planned_path: List[Coord] = []
        self.current_target: Optional[Coord] = None
        self.history: List[TraceRecord] = []
        self.strategy_transitions: List[Tuple[int, Strategy, str]] = []

    def _update_internal_map(self, obs: Observation) -> None:
        """Integrate new local sensor readings into agent's internal map."""
        self.visited_cells.add(obs.agent_pos)
        self.belief.mark_cell_empty(obs.agent_pos)

        for coord, cell_type in obs.local_sensor.items():
            if cell_type == "OBSTACLE":
                if coord not in self.known_obstacles:
                    self.known_obstacles.add(coord)
                    self.belief.mark_obstacle(coord)
            elif cell_type == "CLUE":
                self.known_clues.add(coord)

        # Process clue inspection payload if received
        if obs.clue_payload is not None:
            c_pos = tuple(obs.clue_payload["clue_pos"])  # type: ignore
            est_dist = float(obs.clue_payload["estimated_distance"])
            bearing = tuple(obs.clue_payload["bearing_vector"])  # type: ignore
            sigma = float(obs.clue_payload.get("noise_sigma", 0.0))

            self.inspected_clues.add(c_pos)
            self.belief.update_with_clue(c_pos, est_dist, bearing, sigma)

        # Process scan payload if received
        if obs.scan_result is not None:
            s_pos = tuple(obs.scan_result["scanner_pos"])  # type: ignore
            est_dist = float(obs.scan_result["estimated_distance"])
            sigma = float(obs.scan_result.get("noise_sigma", 1.0))
            self.belief.update_with_scan(s_pos, est_dist, sigma)

    def _set_strategy(self, step: int, new_strategy: Strategy, reason: str) -> None:
        """Record and update strategy transition."""
        if self.current_strategy != new_strategy:
            self.strategy_transitions.append((step, new_strategy, reason))
            self.current_strategy = new_strategy

    def _coord_to_action(self, from_pos: Coord, to_pos: Coord) -> Action:
        """Convert a 1-step move from one coordinate to an adjacent coordinate."""
        dr = to_pos[0] - from_pos[0]
        dc = to_pos[1] - from_pos[1]
        if dr == -1 and dc == 0:
            return Action.MOVE_UP
        if dr == 1 and dc == 0:
            return Action.MOVE_DOWN
        if dr == 0 and dc == -1:
            return Action.MOVE_LEFT
        if dr == 0 and dc == 1:
            return Action.MOVE_RIGHT
        return Action.TERMINATE

    def decide_action(self, obs: Observation) -> Tuple[Action, str]:
        """
        Main decision-making function implementing Observe-Decide-Act loop.
        """
        # 1. Update internal state from observations
        self._update_internal_map(obs)

        # 2. Check if already reached target or finished
        if obs.target_found:
            return Action.TERMINATE, "Target reached! Mission complete."

        # 3. Check for immediate Clue Inspection opportunity
        if obs.agent_pos in self.known_clues and obs.agent_pos not in self.inspected_clues:
            if obs.battery >= 2.0:
                self._set_strategy(obs.step_count, Strategy.ACQUIRE_CLUE, "Arrived at clue; inspecting beacon signal")
                return Action.INSPECT, f"Inspecting clue at {obs.agent_pos}"

        # 4. Strategy Evaluation & Planning
        # Check uninspected discovered clues
        uninspected = [c for c in self.known_clues if c not in self.inspected_clues]
        top_candidates = self.belief.get_top_candidates(k=5)
        top_cand_pos, top_cand_prob = top_candidates[0] if top_candidates else (obs.agent_pos, 0.0)

        # Decision tree for strategy selection
        # Priority A: If an uninspected clue is known and reachable, acquire it
        if uninspected:
            # Pick closest uninspected clue
            uninspected.sort(key=lambda c: abs(c[0] - obs.agent_pos[0]) + abs(c[1] - obs.agent_pos[1]))
            target_clue = uninspected[0]
            path = a_star_search(obs.agent_pos, target_clue, self.bounds, self.known_obstacles)
            if path and len(path) > 1:
                # Check battery sufficiency: path cost + inspect cost
                estimated_cost = (len(path) - 1) * 1.0 + 2.0
                if obs.battery >= estimated_cost:
                    self._set_strategy(obs.step_count, Strategy.ACQUIRE_CLUE, f"Navigating to clue at {target_clue}")
                    self.planned_path = path[1:]
                    next_pos = self.planned_path.pop(0)
                    action = self._coord_to_action(obs.agent_pos, next_pos)
                    return action, f"Moving along path to clue {target_clue}"

        # Priority B: If we have acquired clue(s) or belief has a high-probability candidate
        if self.inspected_clues or top_cand_prob >= 0.15:
            # Find the best reachable candidate
            best_path = None
            selected_cand = None

            for cand_pos, prob in top_candidates:
                if cand_pos == obs.agent_pos:
                    continue
                path = a_star_search(obs.agent_pos, cand_pos, self.bounds, self.known_obstacles)
                if path and len(path) > 1:
                    cost = (len(path) - 1) * 1.0
                    if obs.battery >= cost:
                        best_path = path
                        selected_cand = cand_pos
                        break
                else:
                    # Candidate is unreachable through known obstacles
                    # Zero out probability of unreachable candidate
                    self.belief.mark_obstacle(cand_pos)

            if best_path and selected_cand:
                self._set_strategy(
                    obs.step_count,
                    Strategy.HUNT_BELIEF_TARGET,
                    f"Belief indicates EVE candidate at {selected_cand} (P={self.belief.get_probability(selected_cand):.3f})"
                )
                self.planned_path = best_path[1:]
                next_pos = self.planned_path.pop(0)
                action = self._coord_to_action(obs.agent_pos, next_pos)
                return action, f"Advancing toward top candidate {selected_cand} via A*"

        # Priority C: High entropy, multiple clues inspected, or uncertain -> Trigger SCAN if budget permits
        if obs.scan_budget > 0 and obs.battery >= 6.0 and self.belief.get_entropy() > 3.0:
            self._set_strategy(obs.step_count, Strategy.PULSE_SCAN, "Entropy high; firing deep radar scan pulse")
            return Action.SCAN, "Emitting omnidirectional pulse scan to resolve candidate ambiguity"

        # Priority D: Explore nearest frontier to discover clues or locate EVE
        frontier = find_nearest_frontier(obs.agent_pos, self.bounds, self.known_obstacles, self.visited_cells)
        if frontier:
            path = a_star_search(obs.agent_pos, frontier, self.bounds, self.known_obstacles)
            if path and len(path) > 1 and obs.battery >= (len(path) - 1) * 1.0:
                self._set_strategy(obs.step_count, Strategy.EXPLORE_FOR_CLUES, f"Exploring toward frontier {frontier}")
                self.planned_path = path[1:]
                next_pos = self.planned_path.pop(0)
                action = self._coord_to_action(obs.agent_pos, next_pos)
                return action, f"Exploring unmapped territory at {frontier}"

        # Priority E: Unreachable or battery exhausted
        self._set_strategy(
            obs.step_count,
            Strategy.ABORT_UNREACHABLE,
            "No reachable candidates or frontiers remain within battery budget"
        )
        return Action.TERMINATE, "Mission abort: Target unreachable or battery reserve exhausted"

    def step(self, obs: Observation) -> Action:
        """Wrapper combining decision and explainable trace recording."""
        action, reason = self.decide_action(obs)

        top_candidates = self.belief.get_top_candidates(k=1)
        top_cand, top_prob = top_candidates[0] if top_candidates else (obs.agent_pos, 0.0)

        record = TraceRecord(
            step=obs.step_count,
            agent_pos=obs.agent_pos,
            action=action,
            reason=reason,
            strategy=self.current_strategy,
            battery=obs.battery,
            belief_entropy=round(self.belief.get_entropy(), 3),
            top_candidate=top_cand,
            top_candidate_prob=round(top_prob, 3),
            message=obs.message
        )
        self.history.append(record)
        return action


class BaselineRandomAgent:
    """
    Baseline agent for comparative benchmarking:
    Explores using random traversable moves without utilizing Bayesian belief updates or clue directives.
    """

    def __init__(self, bounds: Tuple[int, int]):
        self.bounds = bounds
        self.known_obstacles: Set[Coord] = set()
        self.visited: Set[Coord] = set()

    def step(self, obs: Observation) -> Action:
        self.visited.add(obs.agent_pos)
        for coord, cell_type in obs.local_sensor.items():
            if cell_type == "OBSTACLE":
                self.known_obstacles.add(coord)

        if obs.target_found:
            return Action.TERMINATE

        # Look for nearest unvisited frontier
        frontier = find_nearest_frontier(obs.agent_pos, self.bounds, self.known_obstacles, self.visited)
        if frontier:
            path = a_star_search(obs.agent_pos, frontier, self.bounds, self.known_obstacles)
            if path and len(path) > 1:
                next_pos = path[1]
                dr = next_pos[0] - obs.agent_pos[0]
                dc = next_pos[1] - obs.agent_pos[1]
                if dr == -1: return Action.MOVE_UP
                if dr == 1: return Action.MOVE_DOWN
                if dc == -1: return Action.MOVE_LEFT
                if dc == 1: return Action.MOVE_RIGHT

        return Action.TERMINATE
