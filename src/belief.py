"""Bayesian belief over EVE's hidden location AND status, robust to spoofed (decoy) beacons.

The belief is a joint distribution P(status, row, col) stored as two grids (ACTIVE, DORMANT).
Everything is kept in log space so many multiplicative updates never underflow.

Evidence handled:
- Negative evidence: sensed cells without EVE, obstacles             -> probability 0
- Initial signal reading (bearing or approximate coordinates, strength, age)
- Beacon clues (distance + bearing) as a reliability MIXTURE:
      L_j(x) = p * L_clue(x) + (1 - p) * uniform
  so a decoy can never erase the true location, and the posterior probability that each
  beacon is genuine can be computed exactly (see `clue_reliability`).
- Pulse scans: time-of-flight distance (status-independent) and beacon strength
  (status-dependent via src/signal_model.py), which is how EVE's status is inferred.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np

from src.signal_model import SIGNAL_DECAY_CELLS, STATUS_POWER, STATUSES

Coord = Tuple[int, int]

_TINY = 1e-300


def _wrap_angle(rad: np.ndarray) -> np.ndarray:
    return (rad + np.pi) % (2 * np.pi) - np.pi


class BeliefMap:
    """Joint posterior P(EVE status, EVE location) with a location marginal in `self.grid`."""

    def __init__(
        self,
        bounds: Tuple[int, int],
        known_obstacles: Optional[Set[Coord]] = None,
        clue_reliability_prior: float = 0.8,
        status_prior: Optional[Dict[str, float]] = None,
    ):
        self.rows, self.cols = bounds
        self.n_cells = self.rows * self.cols
        self._rr, self._cc = np.indices((self.rows, self.cols), dtype=float)
        self.statuses: Tuple[str, ...] = STATUSES
        prior = status_prior or {s: 1.0 / len(STATUSES) for s in STATUSES}
        self._log_status_prior = np.log(np.array([prior[s] for s in STATUSES], dtype=float))
        self.clue_reliability_prior = float(clue_reliability_prior)

        self._mask = np.ones((self.rows, self.cols), dtype=bool)          # False = EVE ruled out
        self._loc_loglik = np.zeros((self.rows, self.cols))               # status-independent evidence
        self._status_loglik = np.zeros((len(STATUSES), self.rows, self.cols))
        self._clues: Dict[Coord, np.ndarray] = {}                         # normalized clue likelihoods
        self._certain_cell: Optional[Coord] = None
        self._observed_status: Optional[str] = None

        for r, c in known_obstacles or set():
            if self._in_bounds((r, c)):
                self._mask[r, c] = False
        self._recompute()

    # ----------------------------------------------------------- composition
    def _in_bounds(self, pos: Coord) -> bool:
        return 0 <= pos[0] < self.rows and 0 <= pos[1] < self.cols

    def _clue_mixture(self, likelihood: np.ndarray) -> np.ndarray:
        p = self.clue_reliability_prior
        return p * likelihood + (1.0 - p) / self.n_cells

    def _compose(self, exclude_clue: Optional[Coord] = None) -> np.ndarray:
        """Normalized joint posterior, optionally leaving one clue out (used for reliability)."""
        with np.errstate(divide="ignore"):
            log_joint = (
                self._log_status_prior[:, None, None]
                + self._status_loglik
                + self._loc_loglik[None, :, :]
                + np.log(self._mask.astype(float))[None, :, :]
            )
            for pos, lik in self._clues.items():
                if pos != exclude_clue:
                    log_joint = log_joint + np.log(np.maximum(self._clue_mixture(lik), _TINY))[None, :, :]

        if self._observed_status is not None:
            for i, s in enumerate(self.statuses):
                if s != self._observed_status:
                    log_joint[i] = -np.inf
        if self._certain_cell is not None:
            keep = np.full((self.rows, self.cols), -np.inf)
            keep[self._certain_cell] = 0.0
            log_joint = log_joint + keep[None, :, :]

        finite = np.isfinite(log_joint)
        if not finite.any():
            # Every hypothesis ruled out (contradictory evidence): fall back to the mask only.
            base = np.broadcast_to(self._mask, log_joint.shape).astype(float)
            total = base.sum()
            return base / total if total > 0 else np.full(log_joint.shape, 1.0 / log_joint.size)

        joint = np.exp(log_joint - log_joint[finite].max())
        return joint / joint.sum()

    def _recompute(self) -> None:
        self.joint = self._compose()
        self.grid = self.joint.sum(axis=0)

    # -------------------------------------------------------- hard evidence
    def mark_cell_empty(self, pos: Coord) -> None:
        """EVE is not at pos (sensed or visited without finding her)."""
        self.mark_cells_empty([pos])

    def mark_cells_empty(self, cells: Iterable[Coord]) -> None:
        changed = False
        for pos in cells:
            if self._in_bounds(pos) and self._mask[pos] and pos != self._certain_cell:
                self._mask[pos] = False
                changed = True
        if changed:
            self._recompute()

    def mark_obstacle(self, pos: Coord) -> None:
        """EVE cannot be inside an obstacle."""
        self.mark_cell_empty(pos)

    def set_certain(self, pos: Coord) -> None:
        """EVE was directly sighted at pos."""
        self._certain_cell = pos
        self._mask[pos] = True
        self._recompute()

    def observe_status(self, status: str) -> None:
        """EVE's status was directly observed (on rendezvous)."""
        self._observed_status = status
        self._recompute()

    # ------------------------------------------------------- soft evidence
    def update_with_initial_signal(self, signal: Dict, age_minutes: float = 0.0) -> None:
        """
        Prior from the mission's initial signal reading. Older readings are trusted less:
        every uncertainty is inflated by (1 + age / 60 min). A floor keeps the prior soft.
        """
        age_factor = 1.0 + max(0.0, age_minutes) / 60.0
        origin = tuple(signal.get("received_at", (0, 0)))
        d = np.hypot(self._rr - origin[0], self._cc - origin[1])
        floor = 0.05

        loc = np.ones((self.rows, self.cols))
        if signal.get("bearing_deg") is not None:
            cell_bearing = np.arctan2(self._cc - origin[1], -(self._rr - origin[0]))
            delta = _wrap_angle(cell_bearing - math.radians(float(signal["bearing_deg"])))
            sigma = math.radians(15.0 * age_factor)
            cone = np.exp(-(delta ** 2) / (2 * sigma ** 2))
            cone[d < 1e-9] = 1.0
            loc *= floor + (1 - floor) * cone
        if signal.get("approx_pos") is not None:
            ar, ac = signal["approx_pos"]
            sigma = float(signal.get("pos_sigma", 2.0)) * age_factor
            blob = np.exp(-((self._rr - ar) ** 2 + (self._cc - ac) ** 2) / (2 * sigma ** 2))
            loc *= floor + (1 - floor) * blob
        self._loc_loglik += np.log(loc)

        if signal.get("strength") is not None:
            sigma_s = 0.03 * age_factor
            for i, status in enumerate(self.statuses):
                expected = STATUS_POWER[status] * np.exp(-d / SIGNAL_DECAY_CELLS)
                lik = np.exp(-((float(signal["strength"]) - expected) ** 2) / (2 * sigma_s ** 2))
                self._status_loglik[i] += np.log(floor + (1 - floor) * lik)
        self._recompute()

    def update_with_clue(
        self,
        clue_pos: Coord,
        estimated_distance: float,
        bearing_vector: Tuple[float, float],
        noise_sigma: float = 0.0,
        bearing_sigma_deg: float = 0.0,
    ) -> None:
        """
        Beacon clue: Gaussian shell at the decoded distance times a Gaussian cone around the
        decoded bearing. Stored as a normalized likelihood and applied as a reliability mixture.
        """
        cr, cc = clue_pos
        d = np.hypot(self._rr - cr, self._cc - cc)
        sigma_d = max(noise_sigma, 0.5)
        lik = np.exp(-((d - estimated_distance) ** 2) / (2 * sigma_d ** 2))

        br, bc = bearing_vector
        if math.hypot(br, bc) > 1e-6:
            cell_bearing = np.arctan2(self._cc - cc, -(self._rr - cr))
            delta = _wrap_angle(cell_bearing - math.atan2(bc, -br))
            sigma_t = math.radians(max(bearing_sigma_deg, 10.0))
            cone = np.exp(-(delta ** 2) / (2 * sigma_t ** 2))
            cone[d < 1e-9] = 1.0
            lik = lik * cone

        total = lik.sum()
        self._clues[tuple(clue_pos)] = lik / total if total > 0 else np.full_like(lik, 1.0 / self.n_cells)
        self._recompute()

    def update_with_scan(
        self,
        scanner_pos: Coord,
        estimated_distance: float,
        noise_sigma: float = 1.0,
        signal_strength: Optional[float] = None,
        strength_sigma: float = 0.02,
    ) -> None:
        """Pulse scan: distance ring (location) and, if given, beacon strength (location x status)."""
        sr, sc = scanner_pos
        d = np.hypot(self._rr - sr, self._cc - sc)
        sigma = max(noise_sigma, 0.5)
        self._loc_loglik += -((d - estimated_distance) ** 2) / (2 * sigma ** 2)

        if signal_strength is not None:
            sigma_s = max(strength_sigma, 0.01)
            for i, status in enumerate(self.statuses):
                expected = STATUS_POWER[status] * np.exp(-d / SIGNAL_DECAY_CELLS)
                self._status_loglik[i] += -((signal_strength - expected) ** 2) / (2 * sigma_s ** 2)
        self._recompute()

    # -------------------------------------------------------------- queries
    def clue_reliability(self, clue_pos: Coord) -> float:
        """
        Exact posterior probability that the beacon at clue_pos is genuine, given ALL other evidence:
            P(genuine) = p*A / (p*A + (1-p)/N),  A = sum_x L_clue(x) * P_without_this_clue(x)
        """
        lik = self._clues.get(tuple(clue_pos))
        if lik is None:
            return self.clue_reliability_prior
        p = self.clue_reliability_prior
        if p >= 1.0:
            return 1.0
        others = self._compose(exclude_clue=tuple(clue_pos)).sum(axis=0)
        agreement = float((lik * others).sum())
        genuine = p * agreement
        return genuine / (genuine + (1.0 - p) / self.n_cells)

    def all_clue_reliabilities(self) -> Dict[Coord, float]:
        return {pos: self.clue_reliability(pos) for pos in self._clues}

    def status_probabilities(self) -> Dict[str, float]:
        totals = self.joint.sum(axis=(1, 2))
        return {s: float(totals[i]) for i, s in enumerate(self.statuses)}

    def get_entropy(self) -> float:
        """Shannon entropy (bits) of the location marginal."""
        nonzero = self.grid[self.grid > 1e-12]
        return float(-np.sum(nonzero * np.log2(nonzero)))

    def most_likely_position(self) -> Coord:
        r, c = divmod(int(np.argmax(self.grid)), self.cols)
        return (r, c)

    def get_top_candidates(self, k: int = 5) -> List[Tuple[Coord, float]]:
        flat = self.grid.ravel()
        order = np.argsort(-flat, kind="stable")[:k]
        return [
            ((int(i) // self.cols, int(i) % self.cols), float(flat[i]))
            for i in order
            if flat[i] > 1e-6
        ]

    def credible_region(self, mass: float = 0.9) -> List[Coord]:
        """Smallest set of cells (highest probability first) holding at least `mass` probability."""
        flat = self.grid.ravel()
        order = np.argsort(-flat, kind="stable")
        cumulative = np.cumsum(flat[order])
        n = int(np.searchsorted(cumulative, mass) + 1)
        return [(int(i) // self.cols, int(i) % self.cols) for i in order[:n]]

    def mass_in(self, cells: Iterable[Coord]) -> float:
        return float(sum(self.grid[pos] for pos in cells if self._in_bounds(pos)))

    def expected_target_error(self, true_pos: Coord) -> float:
        """Expected Euclidean distance between belief and the true position (evaluation only)."""
        d = np.hypot(self._rr - true_pos[0], self._cc - true_pos[1])
        return float((self.grid * d).sum())

    def get_probability(self, pos: Coord) -> float:
        return float(self.grid[pos]) if self._in_bounds(pos) else 0.0
