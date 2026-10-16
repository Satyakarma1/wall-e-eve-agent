"""Shared signal physics used by the environment (to generate readings) and the belief (to invert them).

EVE's beacon strength decays exponentially with distance and is scaled by her hidden status:
    strength = STATUS_POWER[status] * exp(-distance / SIGNAL_DECAY_CELLS)

Bearings use compass degrees on the grid: 0 = north (row - 1), 90 = east (col + 1),
180 = south (row + 1), 270 = west (col - 1).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional, Tuple

SIGNAL_DECAY_CELLS = 8.0
STATUS_POWER = {"ACTIVE": 1.0, "DORMANT": 0.4}
STATUSES: Tuple[str, ...] = tuple(STATUS_POWER)


def expected_strength(distance: float, status: str) -> float:
    """Noise-free beacon strength at a given distance for a given EVE status."""
    return STATUS_POWER[status] * math.exp(-distance / SIGNAL_DECAY_CELLS)


def bearing_deg_from_vector(dr: float, dc: float) -> float:
    """Compass bearing (degrees) of a (row, col) displacement."""
    return math.degrees(math.atan2(dc, -dr)) % 360.0


def vector_from_bearing_deg(bearing_deg: float) -> Tuple[float, float]:
    """Unit (row, col) displacement pointing along a compass bearing."""
    rad = math.radians(bearing_deg)
    return (-math.cos(rad), math.sin(rad))


def signal_age_minutes(timestamp: Optional[str], mission_start: Optional[str]) -> float:
    """Minutes between an ISO-8601 signal timestamp and the mission start (0 if unknown)."""
    if not timestamp or not mission_start:
        return 0.0
    try:
        received = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        start = datetime.fromisoformat(mission_start.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return max(0.0, (start - received).total_seconds() / 60.0)
