"""Simulation environment with strictly separated hidden ground truth."""

from __future__ import annotations
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import numpy as np

Coord = Tuple[int, int]


class Action(str, Enum):
    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    INSPECT = "INSPECT"
    SCAN = "SCAN"
    TERMINATE = "TERMINATE"


@dataclass
class Observation:
    """Information visible to the agent at a single step. Hidden world state is omitted."""
    agent_pos: Coord
    local_sensor: Dict[Coord, str]  # {(r, c): "FREE" | "OBSTACLE" | "CLUE"}
    battery: float
    scan_budget: int
    step_count: int
    clue_payload: Optional[Dict[str, Any]] = None
    scan_result: Optional[Dict[str, Any]] = None
    collision_detected: bool = False
    target_found: bool = False
    message: str = ""


class Environment:
    """
    Grid-world simulation environment.
    EVE's true position and unobserved obstacle layouts are kept strictly private (_eve_pos).
    """

    def __init__(self, config_data_or_path: Union[Dict[str, Any], str, Path]):
        if isinstance(config_data_or_path, (str, Path)):
            with open(config_data_or_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = config_data_or_path

        self.rows, self.cols = self.config.get("grid_size", [12, 12])
        self.bounds: Tuple[int, int] = (self.rows, self.cols)
        self.start_pos: Coord = tuple(self.config.get("start_pos", [0, 0]))  # type: ignore

        # Hidden ground truth
        self._eve_pos: Coord = tuple(self.config.get("eve_pos", [10, 10]))  # type: ignore
        self._obstacles: Set[Coord] = {
            tuple(obs) for obs in self.config.get("obstacles", [])  # type: ignore
        }

        # Clue configurations
        self._clue_configs: Dict[Coord, Dict[str, Any]] = {}
        for c_entry in self.config.get("clues", []):
            c_pos = tuple(c_entry["pos"])
            self._clue_configs[c_pos] = {  # type: ignore
                "type": c_entry.get("type", "directional_beacon"),
                "noise_sigma": float(c_entry.get("noise_sigma", 0.0)),
            }

        # Resource configuration
        res = self.config.get("resources", {})
        self.initial_battery: float = float(res.get("initial_battery", 100.0))
        self.max_steps: int = int(res.get("max_steps", 150))
        self.initial_scan_budget: int = int(res.get("scan_budget", 5))

        costs = res.get("action_costs", {})
        self.cost_move: float = float(costs.get("move", 1.0))
        self.cost_inspect: float = float(costs.get("inspect", 2.0))
        self.cost_scan: float = float(costs.get("scan", 4.0))
        self.cost_terminate: float = float(costs.get("terminate", 0.0))

        # Random number generator
        seed = self.config.get("random_seed", 42)
        self._rng = np.random.default_rng(seed)

        # Dynamic state
        self.agent_pos: Coord = self.start_pos
        self.battery: float = self.initial_battery
        self.scan_budget: int = self.initial_scan_budget
        self.step_count: int = 0
        self.scan_count: int = 0
        self.visited_cells: Set[Coord] = {self.start_pos}
        self.path_taken: List[Coord] = [self.start_pos]
        self.discovered_clues: Set[Coord] = set()
        self.done: bool = False
        self.status: str = "IN_PROGRESS"

    def reset(self, new_seed: Optional[int] = None) -> Observation:
        """Reset the environment to its starting state."""
        if new_seed is not None:
            self._rng = np.random.default_rng(new_seed)

        self.agent_pos = self.start_pos
        self.battery = self.initial_battery
        self.scan_budget = self.initial_scan_budget
        self.step_count = 0
        self.scan_count = 0
        self.visited_cells = {self.start_pos}
        self.path_taken = [self.start_pos]
        self.discovered_clues = set()
        self.done = False
        self.status = "IN_PROGRESS"

        target_found = (self.agent_pos == self._eve_pos)
        if target_found:
            self.done = True
            self.status = "SUCCESS"

        obs = Observation(
            agent_pos=self.agent_pos,
            local_sensor=self._sense_local_neighborhood(self.agent_pos),
            battery=self.battery,
            scan_budget=self.scan_budget,
            step_count=self.step_count,
            target_found=target_found,
            message="Environment initialized at starting position."
        )
        return obs

    def _sense_local_neighborhood(self, pos: Coord, radius: int = 1) -> Dict[Coord, str]:
        """Sense surrounding cells within Chebyshev radius (Chebyshev radius 1 = 3x3 local window)."""
        r, c = pos
        sensor_data: Dict[Coord, str] = {}
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    n_coord = (nr, nc)
                    if n_coord in self._obstacles:
                        sensor_data[n_coord] = "OBSTACLE"
                    elif n_coord in self._clue_configs:
                        sensor_data[n_coord] = "CLUE"
                    else:
                        sensor_data[n_coord] = "FREE"
        return sensor_data

    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        """
        Execute an agent action and return (observation, reward, done, info).
        """
        if self.done:
            info = self.get_summary_info()
            obs = Observation(
                agent_pos=self.agent_pos,
                local_sensor=self._sense_local_neighborhood(self.agent_pos),
                battery=self.battery,
                scan_budget=self.scan_budget,
                step_count=self.step_count,
                target_found=(self.agent_pos == self._eve_pos),
                message="Mission already completed."
            )
            return obs, 0.0, True, info

        self.step_count += 1
        collision = False
        clue_payload: Optional[Dict[str, Any]] = None
        scan_payload: Optional[Dict[str, Any]] = None
        message = ""

        # Action execution
        if action in (Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT):
            self.battery -= self.cost_move
            delta = {
                Action.MOVE_UP: (-1, 0),
                Action.MOVE_DOWN: (1, 0),
                Action.MOVE_LEFT: (0, -1),
                Action.MOVE_RIGHT: (0, 1),
            }[action]

            target_pos = (self.agent_pos[0] + delta[0], self.agent_pos[1] + delta[1])

            # Collision check: boundary or obstacle
            if not (0 <= target_pos[0] < self.rows and 0 <= target_pos[1] < self.cols):
                collision = True
                message = f"Movement blocked: Out of bounds at {target_pos}."
            elif target_pos in self._obstacles:
                collision = True
                message = f"Movement blocked: Collision with obstacle at {target_pos}."
            else:
                self.agent_pos = target_pos
                self.visited_cells.add(self.agent_pos)
                self.path_taken.append(self.agent_pos)
                message = f"Moved to {self.agent_pos}."

                if self.agent_pos in self._clue_configs:
                    self.discovered_clues.add(self.agent_pos)
                    message += " Discovered a signal beacon!"

        elif action == Action.INSPECT:
            self.battery -= self.cost_inspect
            if self.agent_pos in self._clue_configs:
                clue_cfg = self._clue_configs[self.agent_pos]
                noise_sigma = clue_cfg["noise_sigma"]

                # Ground truth calculation (done securely in environment)
                true_dist = math.hypot(
                    self._eve_pos[0] - self.agent_pos[0],
                    self._eve_pos[1] - self.agent_pos[1]
                )
                noise = float(self._rng.normal(0.0, noise_sigma)) if noise_sigma > 0 else 0.0
                est_dist = max(0.0, true_dist + noise)

                # Direction vector towards EVE
                dr = self._eve_pos[0] - self.agent_pos[0]
                dc = self._eve_pos[1] - self.agent_pos[1]
                mag = math.hypot(dr, dc)
                if mag > 1e-6:
                    unit_dir = (dr / mag, dc / mag)
                else:
                    unit_dir = (0.0, 0.0)

                clue_payload = {
                    "clue_pos": self.agent_pos,
                    "estimated_distance": est_dist,
                    "bearing_vector": unit_dir,
                    "noise_sigma": noise_sigma,
                }
                self.discovered_clues.add(self.agent_pos)
                message = f"Inspected clue at {self.agent_pos}: Beacon signal decoded."
            else:
                message = f"Inspect action executed at {self.agent_pos}, but no clue was found."

        elif action == Action.SCAN:
            if self.scan_budget > 0:
                self.scan_budget -= 1
                self.scan_count += 1
                self.battery -= self.cost_scan

                true_dist = math.hypot(
                    self._eve_pos[0] - self.agent_pos[0],
                    self._eve_pos[1] - self.agent_pos[1]
                )
                scan_noise_sigma = 1.0
                noise = float(self._rng.normal(0.0, scan_noise_sigma))
                est_dist = max(0.0, true_dist + noise)

                scan_payload = {
                    "scanner_pos": self.agent_pos,
                    "estimated_distance": est_dist,
                    "noise_sigma": scan_noise_sigma,
                }
                message = f"Deep pulse scan performed at {self.agent_pos}."
            else:
                message = "Scan action failed: Scan budget exhausted."

        elif action == Action.TERMINATE:
            self.battery -= self.cost_terminate
            self.done = True
            self.status = "TERMINATED_BY_AGENT"
            message = "Mission terminated by agent."

        # Check success condition
        target_found = (self.agent_pos == self._eve_pos)
        if target_found:
            self.done = True
            self.status = "SUCCESS"
            message += " Target EVE reached! Mission Accomplished!"

        # Check resource failure conditions
        if not self.done:
            if self.battery <= 0.0:
                self.done = True
                self.status = "FAILURE_BATTERY"
                message += " Battery fully depleted! Mission Failed."
            elif self.step_count >= self.max_steps:
                self.done = True
                self.status = "FAILURE_TIMEOUT"
                message += " Maximum step limit reached! Mission Failed."

        obs = Observation(
            agent_pos=self.agent_pos,
            local_sensor=self._sense_local_neighborhood(self.agent_pos),
            battery=max(0.0, self.battery),
            scan_budget=self.scan_budget,
            step_count=self.step_count,
            clue_payload=clue_payload,
            scan_result=scan_payload,
            collision_detected=collision,
            target_found=target_found,
            message=message
        )

        reward = 100.0 if target_found else (-1.0 if collision else -0.1)
        info = self.get_summary_info()
        return obs, reward, self.done, info

    def get_summary_info(self) -> Dict[str, Any]:
        """Generate mission summary metrics."""
        total_cells = self.rows * self.cols
        obstacle_count = len(self._obstacles)
        traversable_cells = total_cells - obstacle_count
        coverage_pct = (len(self.visited_cells) / max(1, traversable_cells)) * 100.0

        return {
            "status": self.status,
            "success": (self.status == "SUCCESS"),
            "step_count": self.step_count,
            "path_length": len(self.path_taken) - 1,
            "battery_used": round(self.initial_battery - max(0.0, self.battery), 2),
            "battery_remaining": round(max(0.0, self.battery), 2),
            "scan_count": self.scan_count,
            "cells_visited": len(self.visited_cells),
            "exploration_coverage_pct": round(coverage_pct, 2),
            "clues_discovered": len(self.discovered_clues),
            "total_clues": len(self._clue_configs),
        }

    # Debug / Visualization / Evaluation helpers (NOT for agent direct use)
    def get_ground_truth_for_eval(self) -> Dict[str, Any]:
        """Provides ground truth data strictly for test evaluation, visualizer, and reporting."""
        return {
            "eve_pos": self._eve_pos,
            "obstacles": set(self._obstacles),
            "clues": dict(self._clue_configs),
            "grid_size": (self.rows, self.cols),
            "start_pos": self.start_pos,
        }
