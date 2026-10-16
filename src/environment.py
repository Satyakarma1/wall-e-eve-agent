"""Simulation environment with strictly separated hidden ground truth.

Hidden (environment only): EVE's position and status, obstacle layout, clue placements,
which clues are decoys and where they point. The agent only ever receives a public
`MissionBriefing` and per-step `Observation` objects.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from src.signal_model import (
    STATUS_POWER,
    bearing_deg_from_vector,
    expected_strength,
    signal_age_minutes,
    vector_from_bearing_deg,
)

Coord = Tuple[int, int]


class Action(str, Enum):
    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    INSPECT = "INSPECT"
    SCAN = "SCAN"
    RECHARGE = "RECHARGE"
    TERMINATE = "TERMINATE"


MOVE_DELTAS: Dict[Action, Coord] = {
    Action.MOVE_UP: (-1, 0),
    Action.MOVE_DOWN: (1, 0),
    Action.MOVE_LEFT: (0, -1),
    Action.MOVE_RIGHT: (0, 1),
}

CLUE_TYPES = ("directional_beacon", "decoy")


@dataclass(frozen=True)
class MissionBriefing:
    """Public mission information the agent may know before it starts (no hidden state)."""
    grid_size: Tuple[int, int]
    start_pos: Coord
    charging_stations: Tuple[Coord, ...]
    initial_signal: Optional[Dict[str, Any]]
    signal_age_minutes: float
    battery_capacity: float
    initial_battery: float
    max_steps: int
    scan_budget: int
    recharge_per_action: float
    action_costs: Dict[str, float]
    sensor_radius: int
    scan_noise_sigma: float
    strength_noise_sigma: float


@dataclass
class Observation:
    """Information visible to the agent at a single step. Hidden world state is omitted."""
    agent_pos: Coord
    local_sensor: Dict[Coord, str]  # {(r, c): "FREE" | "OBSTACLE" | "CLUE" | "EVE"}
    battery: float
    scan_budget: int
    step_count: int
    clue_payload: Optional[Dict[str, Any]] = None
    scan_result: Optional[Dict[str, Any]] = None
    collision_detected: bool = False
    target_found: bool = False
    eve_status_observed: Optional[str] = None
    at_charging_station: bool = False
    recharged: float = 0.0
    message: str = ""


def load_config(config_data_or_path: Union[Dict[str, Any], str, Path]) -> Tuple[Dict[str, Any], str]:
    """Return (config dict, config name) from a dict or a JSON file path."""
    if isinstance(config_data_or_path, (str, Path)):
        path = Path(config_data_or_path)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), path.stem
    cfg = config_data_or_path
    return cfg, str(cfg.get("config_name", cfg.get("mission_name", "custom")))


class Environment:
    """
    Grid-world simulation environment.
    EVE's true position/status, obstacles and clue truth are kept private (underscore attributes);
    the agent only receives `get_briefing()` and the observations returned by `reset()` / `step()`.
    """

    def __init__(self, config_data_or_path: Union[Dict[str, Any], str, Path]):
        self.config, self.config_name = load_config(config_data_or_path)
        cfg = self.config

        self.mission_name: str = str(cfg.get("mission_name", self.config_name))
        self.rows, self.cols = (int(v) for v in cfg.get("grid_size", [12, 12]))
        self.bounds: Tuple[int, int] = (self.rows, self.cols)
        self.start_pos: Coord = tuple(cfg.get("start_pos", [0, 0]))  # type: ignore[assignment]

        # Hidden ground truth ("eve": {...} preferred; legacy "eve_pos" still accepted)
        eve_cfg = cfg.get("eve", {})
        self._eve_pos: Coord = tuple(eve_cfg.get("pos", cfg.get("eve_pos", [self.rows - 1, self.cols - 1])))  # type: ignore[assignment]
        self._eve_status: str = str(eve_cfg.get("status", cfg.get("eve_status", "ACTIVE"))).upper()
        self._obstacles: Set[Coord] = {tuple(o) for o in cfg.get("obstacles", [])}  # type: ignore[misc]

        self._clue_configs: Dict[Coord, Dict[str, Any]] = {}
        for entry in cfg.get("clues", []):
            pos: Coord = tuple(entry["pos"])  # type: ignore[assignment]
            clue = {
                "type": entry.get("type", "directional_beacon"),
                "noise_sigma": float(entry.get("noise_sigma", 0.0)),
                "bearing_noise_deg": float(entry.get("bearing_noise_deg", 0.0)),
            }
            if clue["type"] == "decoy":
                clue["spoof_pos"] = tuple(entry["spoof_pos"])
            self._clue_configs[pos] = clue

        # Public mission infrastructure and briefing
        self.charging_stations: Tuple[Coord, ...] = tuple(
            tuple(p) for p in cfg.get("charging_stations", [])  # type: ignore[misc]
        )
        self.initial_signal: Optional[Dict[str, Any]] = cfg.get("initial_signal")
        self.mission_start: Optional[str] = cfg.get("mission_start")

        sensors = cfg.get("sensors", {})
        self.sensor_radius: int = int(sensors.get("sensor_radius", 1))
        self.scan_noise_sigma: float = float(sensors.get("scan_noise_sigma", 1.0))
        self.strength_noise_sigma: float = float(sensors.get("strength_noise_sigma", 0.02))

        res = cfg.get("resources", {})
        self.initial_battery: float = float(res.get("initial_battery", 100.0))
        self.battery_capacity: float = float(res.get("battery_capacity", self.initial_battery))
        self.max_steps: int = int(res.get("max_steps", 150))
        self.initial_scan_budget: int = int(res.get("scan_budget", 5))
        self.recharge_per_action: float = float(res.get("recharge_per_action", 25.0))

        costs = res.get("action_costs", {})
        self.cost_move: float = float(costs.get("move", 1.0))
        self.cost_inspect: float = float(costs.get("inspect", 2.0))
        self.cost_scan: float = float(costs.get("scan", 4.0))
        self.cost_recharge: float = float(costs.get("recharge", 0.0))
        self.cost_terminate: float = float(costs.get("terminate", 0.0))

        self._validate()

        self._seed = cfg.get("random_seed", 42)
        self._rng = np.random.default_rng(self._seed)
        self._reset_state()

    # ------------------------------------------------------------------ setup
    def _in_bounds(self, pos: Coord) -> bool:
        return 0 <= pos[0] < self.rows and 0 <= pos[1] < self.cols

    def _validate(self) -> None:
        """Reject configs that would make the simulation meaningless."""
        named = [("start_pos", self.start_pos), ("EVE position", self._eve_pos)]
        named += [(f"charging station {p}", p) for p in self.charging_stations]
        named += [(f"clue {p}", p) for p in self._clue_configs]
        for label, pos in named:
            if not self._in_bounds(pos):
                raise ValueError(f"Config error: {label} {pos} is outside the {self.rows}x{self.cols} grid.")
            if pos in self._obstacles:
                raise ValueError(f"Config error: {label} {pos} is inside an obstacle.")
        for pos, clue in self._clue_configs.items():
            if clue["type"] not in CLUE_TYPES:
                raise ValueError(f"Config error: clue {pos} has unknown type '{clue['type']}'.")
            if clue["type"] == "decoy" and not self._in_bounds(clue["spoof_pos"]):
                raise ValueError(f"Config error: decoy {pos} points outside the grid.")
        if self._eve_status not in STATUS_POWER:
            raise ValueError(f"Config error: EVE status must be one of {list(STATUS_POWER)}.")
        if self.battery_capacity < self.initial_battery:
            raise ValueError("Config error: battery_capacity cannot be lower than initial_battery.")

    def _reset_state(self) -> None:
        self.agent_pos: Coord = self.start_pos
        self.battery: float = self.initial_battery
        self.scan_budget: int = self.initial_scan_budget
        self.step_count: int = 0
        self.scan_count: int = 0
        self.inspect_count: int = 0
        self.recharge_count: int = 0
        self.energy_recharged: float = 0.0
        self.collisions: int = 0
        self.visited_cells: Set[Coord] = {self.start_pos}
        self.seen_cells: Set[Coord] = set()
        self.path_taken: List[Coord] = [self.start_pos]
        self.discovered_clues: Set[Coord] = set()  # clues the agent's sensor has detected
        self.inspected_clues: Set[Coord] = set()
        self.done: bool = False
        self.status: str = "IN_PROGRESS"

    def get_briefing(self) -> MissionBriefing:
        """Public pre-mission information: map size, docks, initial signal reading, budgets, sensor specs."""
        signal_ts = (self.initial_signal or {}).get("timestamp")
        return MissionBriefing(
            grid_size=(self.rows, self.cols),
            start_pos=self.start_pos,
            charging_stations=self.charging_stations,
            initial_signal=dict(self.initial_signal) if self.initial_signal else None,
            signal_age_minutes=signal_age_minutes(signal_ts, self.mission_start),
            battery_capacity=self.battery_capacity,
            initial_battery=self.initial_battery,
            max_steps=self.max_steps,
            scan_budget=self.initial_scan_budget,
            recharge_per_action=self.recharge_per_action,
            action_costs={
                "move": self.cost_move,
                "inspect": self.cost_inspect,
                "scan": self.cost_scan,
                "recharge": self.cost_recharge,
                "terminate": self.cost_terminate,
            },
            sensor_radius=self.sensor_radius,
            scan_noise_sigma=self.scan_noise_sigma,
            strength_noise_sigma=self.strength_noise_sigma,
        )

    def reset(self, new_seed: Optional[int] = None) -> Observation:
        """Reset the environment to its starting state."""
        if new_seed is not None:
            self._rng = np.random.default_rng(new_seed)
        self._reset_state()

        target_found = self.agent_pos == self._eve_pos
        if target_found:
            self.done = True
            self.status = "SUCCESS"

        return self._observation(
            message="Environment initialized at starting position.",
            target_found=target_found,
        )

    # ---------------------------------------------------------------- sensing
    def _sense_local_neighborhood(self, pos: Coord) -> Dict[Coord, str]:
        """Sense cells within the Chebyshev sensor radius (radius 1 = 3x3 window)."""
        r, c = pos
        rad = self.sensor_radius
        sensor_data: Dict[Coord, str] = {}
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                cell = (r + dr, c + dc)
                if not self._in_bounds(cell):
                    continue
                if cell in self._obstacles:
                    sensor_data[cell] = "OBSTACLE"
                elif cell == self._eve_pos:
                    sensor_data[cell] = "EVE"
                elif cell in self._clue_configs:
                    sensor_data[cell] = "CLUE"
                    self.discovered_clues.add(cell)
                else:
                    sensor_data[cell] = "FREE"
        self.seen_cells.update(sensor_data)
        return sensor_data

    def _observation(self, **kwargs: Any) -> Observation:
        return Observation(
            agent_pos=self.agent_pos,
            local_sensor=self._sense_local_neighborhood(self.agent_pos),
            battery=max(0.0, self.battery),
            scan_budget=self.scan_budget,
            step_count=self.step_count,
            at_charging_station=self.agent_pos in self.charging_stations,
            eve_status_observed=self._eve_status if kwargs.get("target_found") else None,
            **kwargs,
        )

    def _decode_clue(self, clue_pos: Coord) -> Dict[str, Any]:
        """Signal decoded from a beacon. Decoys report a spoofed source in the same format."""
        clue = self._clue_configs[clue_pos]
        source = clue["spoof_pos"] if clue["type"] == "decoy" else self._eve_pos
        dr = source[0] - clue_pos[0]
        dc = source[1] - clue_pos[1]
        true_dist = math.hypot(dr, dc)

        sigma = clue["noise_sigma"]
        est_dist = max(0.0, true_dist + (float(self._rng.normal(0.0, sigma)) if sigma > 0 else 0.0))

        if true_dist > 1e-9:
            bearing = bearing_deg_from_vector(dr, dc)
            if clue["bearing_noise_deg"] > 0:
                bearing = (bearing + float(self._rng.normal(0.0, clue["bearing_noise_deg"]))) % 360.0
            unit = vector_from_bearing_deg(bearing)
        else:
            bearing, unit = 0.0, (0.0, 0.0)

        return {
            "clue_pos": clue_pos,
            "estimated_distance": est_dist,
            "bearing_vector": unit,
            "bearing_deg": bearing,
            "noise_sigma": sigma,
            "bearing_noise_deg": clue["bearing_noise_deg"],
        }

    def _pulse_scan(self) -> Dict[str, Any]:
        """Omnidirectional scan: noisy time-of-flight distance plus noisy beacon strength."""
        true_dist = math.hypot(self._eve_pos[0] - self.agent_pos[0], self._eve_pos[1] - self.agent_pos[1])
        est_dist = max(0.0, true_dist + float(self._rng.normal(0.0, self.scan_noise_sigma)))
        strength = expected_strength(true_dist, self._eve_status)
        strength += float(self._rng.normal(0.0, self.strength_noise_sigma))
        return {
            "scanner_pos": self.agent_pos,
            "estimated_distance": est_dist,
            "noise_sigma": self.scan_noise_sigma,
            "signal_strength": float(min(1.0, max(0.0, strength))),
            "strength_noise_sigma": self.strength_noise_sigma,
        }

    # ------------------------------------------------------------------- step
    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        """Execute an agent action and return (observation, reward, done, info)."""
        if self.done:
            obs = self._observation(message="Mission already completed.", target_found=self.agent_pos == self._eve_pos)
            return obs, 0.0, True, self.get_summary_info()

        self.step_count += 1
        collision = False
        clue_payload: Optional[Dict[str, Any]] = None
        scan_payload: Optional[Dict[str, Any]] = None
        recharged = 0.0
        message = ""

        if action in MOVE_DELTAS:
            self.battery -= self.cost_move
            dr, dc = MOVE_DELTAS[action]
            target = (self.agent_pos[0] + dr, self.agent_pos[1] + dc)
            if not self._in_bounds(target):
                collision = True
                message = f"Movement blocked: out of bounds at {target}."
            elif target in self._obstacles:
                collision = True
                message = f"Movement blocked: collision with obstacle at {target}."
            else:
                self.agent_pos = target
                self.visited_cells.add(target)
                self.path_taken.append(target)
                message = f"Moved to {target}."
            if collision:
                self.collisions += 1

        elif action == Action.INSPECT:
            self.battery -= self.cost_inspect
            if self.agent_pos in self._clue_configs:
                clue_payload = self._decode_clue(self.agent_pos)
                self.discovered_clues.add(self.agent_pos)
                self.inspected_clues.add(self.agent_pos)
                self.inspect_count += 1
                message = f"Inspected beacon at {self.agent_pos}: signal decoded."
            else:
                message = f"Inspect at {self.agent_pos} found no beacon."

        elif action == Action.SCAN:
            if self.scan_budget > 0:
                self.scan_budget -= 1
                self.scan_count += 1
                self.battery -= self.cost_scan
                scan_payload = self._pulse_scan()
                message = f"Deep pulse scan performed at {self.agent_pos}."
            else:
                message = "Scan failed: scan budget exhausted."

        elif action == Action.RECHARGE:
            self.battery -= self.cost_recharge
            if self.agent_pos in self.charging_stations:
                recharged = max(0.0, min(self.recharge_per_action, self.battery_capacity - self.battery))
                self.battery += recharged
                self.energy_recharged += recharged
                if recharged > 0:
                    self.recharge_count += 1
                message = (
                    f"Docked at {self.agent_pos}: recharged +{recharged:.1f} "
                    f"(battery {self.battery:.1f}/{self.battery_capacity:.1f})."
                )
            else:
                message = f"Recharge failed: no charging dock at {self.agent_pos}."

        elif action == Action.TERMINATE:
            self.battery -= self.cost_terminate
            self.done = True
            self.status = "TERMINATED_BY_AGENT"
            message = "Mission terminated by agent."

        target_found = self.agent_pos == self._eve_pos
        if target_found:
            self.done = True
            self.status = "SUCCESS"
            message += " Target EVE reached! Mission accomplished!"

        if not self.done:
            if self.battery <= 0.0:
                self.done = True
                self.status = "FAILURE_BATTERY"
                message += " Battery fully depleted! Mission failed."
            elif self.step_count >= self.max_steps:
                self.done = True
                self.status = "FAILURE_TIMEOUT"
                message += " Maximum step limit reached! Mission failed."

        obs = self._observation(
            clue_payload=clue_payload,
            scan_result=scan_payload,
            collision_detected=collision,
            target_found=target_found,
            recharged=recharged,
            message=message.strip(),
        )
        reward = 100.0 if target_found else (-1.0 if collision else -0.1)
        return obs, reward, self.done, self.get_summary_info()

    # ---------------------------------------------------------------- metrics
    def get_summary_info(self) -> Dict[str, Any]:
        """Mission outcome metrics (no hidden information about EVE)."""
        traversable = self.rows * self.cols - len(self._obstacles)
        battery_left = max(0.0, self.battery)
        return {
            "status": self.status,
            "success": self.status == "SUCCESS",
            "step_count": self.step_count,
            "path_length": len(self.path_taken) - 1,
            "battery_used": round(self.initial_battery + self.energy_recharged - battery_left, 2),
            "battery_remaining": round(battery_left, 2),
            "energy_recharged": round(self.energy_recharged, 2),
            "recharge_count": self.recharge_count,
            "scan_count": self.scan_count,
            "inspect_count": self.inspect_count,
            "collisions": self.collisions,
            "cells_visited": len(self.visited_cells),
            "exploration_coverage_pct": round(100.0 * len(self.visited_cells) / max(1, traversable), 2),
            "sensor_coverage_pct": round(100.0 * len(self.seen_cells) / (self.rows * self.cols), 2),
            "clues_discovered": len(self.discovered_clues),
            "clues_inspected": len(self.inspected_clues),
            "total_clues": len(self._clue_configs),
        }

    # Debug / visualization / evaluation helper (NEVER passed to the agent)
    def get_ground_truth_for_eval(self) -> Dict[str, Any]:
        """Ground truth for tests, visualizations and after-mission evaluation only."""
        return {
            "eve_pos": self._eve_pos,
            "eve_status": self._eve_status,
            "obstacles": set(self._obstacles),
            "clues": {pos: dict(cfg) for pos, cfg in self._clue_configs.items()},
            "grid_size": (self.rows, self.cols),
            "start_pos": self.start_pos,
            "charging_stations": list(self.charging_stations),
        }
