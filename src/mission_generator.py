"""Seeded random mission generator (generalization benchmark + dashboard "random mission").

Separate random streams are used for the map, the signals and the decoys, so a given seed keeps
the same map, EVE position and genuine beacons under every experimental condition; only the
evidence quality (noise) or the presence of a decoy changes.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from src.pathfinding import bfs_distance_map
from src.signal_model import STATUSES, bearing_deg_from_vector, expected_strength

Coord = Tuple[int, int]
MISSION_START = "2805-07-14T06:00:00Z"
SIZES = ((12, 12), (14, 14), (16, 16))


def _place_debris(rng: np.random.Generator, rows: int, cols: int, density: float, protected: Set[Coord]) -> Set[Coord]:
    """Random straight debris walls (length 2-5) until the target density is reached."""
    obstacles: Set[Coord] = set()
    target = int(density * rows * cols)
    for _ in range(600):
        if len(obstacles) >= target:
            break
        length = int(rng.integers(2, 6))
        r, c = int(rng.integers(0, rows)), int(rng.integers(0, cols))
        horizontal = bool(rng.random() < 0.5)
        cells = [(r, c + k) if horizontal else (r + k, c) for k in range(length)]
        cells = [p for p in cells if 0 <= p[0] < rows and 0 <= p[1] < cols]
        if not any(p in protected for p in cells):
            obstacles.update(cells)
    return obstacles


def _pick(rng: np.random.Generator, cells: List[Coord]) -> Coord:
    return cells[int(rng.integers(0, len(cells)))]


def generate_mission(
    seed: int,
    size: Optional[Tuple[int, int]] = None,
    obstacle_density: float = 0.14,
    n_beacons: int = 2,
    n_decoys: int = 0,
    noisy: bool = False,
) -> Dict[str, Any]:
    """Build a solvable random mission config (EVE is always reachable from the start)."""
    rng_map = np.random.default_rng([seed, 0])
    rng_sig = np.random.default_rng([seed, 1])
    rng_decoy = np.random.default_rng([seed, 2])

    rows, cols = size or SIZES[int(rng_map.integers(0, len(SIZES)))]
    corners = [(0, 0), (0, cols - 1), (rows - 1, 0), (rows - 1, cols - 1)]
    start = corners[int(rng_map.integers(0, 4))]
    protected = {(start[0] + dr, start[1] + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
    obstacles: Set[Coord] = set()
    for _ in range(25):  # redraw debris until most of the map is connected to the start
        candidate = _place_debris(rng_map, rows, cols, obstacle_density, protected)
        dist = bfs_distance_map([start], (rows, cols), candidate)
        if np.isfinite(dist).sum() >= 0.7 * (rows * cols - len(candidate)):
            obstacles = candidate
            break

    dist = bfs_distance_map([start], (rows, cols), obstacles)
    reachable = [(int(r), int(c)) for r, c in np.argwhere(np.isfinite(dist))]
    far = max(dist[p] for p in reachable)
    eve_pool = [p for p in reachable if dist[p] >= 0.6 * far] or reachable
    eve = _pick(rng_map, eve_pool)
    status = STATUSES[int(rng_map.integers(0, len(STATUSES)))]

    taken = {start, eve}
    beacons: List[Coord] = []
    pool = [p for p in reachable if p not in taken and math.dist(p, eve) >= 3 and dist[p] >= 2]
    while pool and len(beacons) < n_beacons:
        b = _pick(rng_map, pool)
        beacons.append(b)
        pool = [p for p in pool if math.dist(p, b) >= 3]
    taken.update(beacons)

    beacon_noise = (1.5, 20.0) if noisy else (0.0, 0.0)
    clues = [
        {"pos": list(b), "type": "directional_beacon", "noise_sigma": beacon_noise[0], "bearing_noise_deg": beacon_noise[1]}
        for b in beacons
    ]
    free = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in obstacles]
    decoy_pool = [p for p in reachable if p not in taken and dist[p] >= 2]
    spoof_pool = [p for p in free if math.dist(p, eve) >= 0.4 * max(rows, cols)]
    for _ in range(n_decoys):
        if not decoy_pool or not spoof_pool:
            break
        d = _pick(rng_decoy, decoy_pool)
        decoy_pool.remove(d)
        clues.append({"pos": list(d), "type": "decoy", "spoof_pos": list(_pick(rng_decoy, spoof_pool)),
                      "noise_sigma": beacon_noise[0], "bearing_noise_deg": beacon_noise[1]})

    true_d = math.dist(start, eve)
    strength_noise = 0.04 if noisy else 0.02
    signal: Dict[str, Any] = {
        "received_at": list(start),
        "strength": round(float(np.clip(expected_strength(true_d, status) + rng_sig.normal(0, strength_noise), 0.005, 1.0)), 3),
    }
    if rng_sig.random() < 0.7:  # 30% of missions only have an omnidirectional strength reading
        bearing = bearing_deg_from_vector(eve[0] - start[0], eve[1] - start[1])
        signal["bearing_deg"] = round(float((bearing + rng_sig.normal(0, 25.0 if noisy else 12.0)) % 360), 1)
    age = int(rng_sig.integers(5, 121))
    start_time = datetime.fromisoformat(MISSION_START.replace("Z", "+00:00"))
    signal["timestamp"] = (start_time - timedelta(minutes=age)).strftime("%Y-%m-%dT%H:%M:%SZ")

    capacity = float(max(40, round(1.8 * (rows + cols) + 1.2 * dist[eve])))
    return {
        "config_name": f"random_{seed}",
        "mission_name": f"Random mission #{seed} ({rows}x{cols}{', noisy' if noisy else ''}{', decoy' if n_decoys else ''})",
        "grid_size": [rows, cols],
        "start_pos": list(start),
        "charging_stations": [list(start)],
        "eve": {"pos": list(eve), "status": status},
        "obstacles": sorted([list(o) for o in obstacles]),
        "clues": clues,
        "initial_signal": signal,
        "mission_start": MISSION_START,
        "sensors": {
            "sensor_radius": 1,
            "scan_noise_sigma": 1.5 if noisy else 1.0,
            "strength_noise_sigma": strength_noise,
        },
        "resources": {
            "initial_battery": capacity,
            "battery_capacity": capacity,
            "max_steps": int(3 * capacity),
            "scan_budget": 3,
            "recharge_per_action": 25.0,
            "action_costs": {"move": 1.0, "inspect": 2.0, "scan": 4.0, "recharge": 0.0, "terminate": 0.0},
        },
        "random_seed": int(seed),
    }
