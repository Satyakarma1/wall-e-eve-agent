"""Belief state representation and Bayesian update engine for EVE localization."""

from __future__ import annotations
import math
from typing import Tuple, List, Optional, Set
import numpy as np

Coord = Tuple[int, int]


class BeliefMap:
    """
    Maintains a 2D discrete probability distribution over all grid cells
    representing the agent's belief about EVE's location: P(EVE = (r, c)).
    """

    def __init__(self, bounds: Tuple[int, int], known_obstacles: Optional[Set[Coord]] = None):
        self.rows, self.cols = bounds
        self.grid = np.zeros((self.rows, self.cols), dtype=np.float64)

        # Initialize uniform prior over all non-obstacle cells
        obstacles = known_obstacles or set()
        free_cells = []
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) not in obstacles:
                    free_cells.append((r, c))

        if free_cells:
            prior_val = 1.0 / len(free_cells)
            for r, c in free_cells:
                self.grid[r, c] = prior_val
        else:
            self.grid.fill(1.0 / (self.rows * self.cols))

    def normalize(self) -> None:
        """Normalize probabilities so they sum to 1.0."""
        total = np.sum(self.grid)
        if total > 1e-12:
            self.grid /= total
        else:
            # If all beliefs were zeroed out, reset uniform over non-zero cells or uniform fallback
            self.grid.fill(1.0 / (self.rows * self.cols))

    def mark_cell_empty(self, pos: Coord) -> None:
        """Mark that EVE is not at pos (e.g. agent visited this cell)."""
        r, c = pos
        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.grid[r, c] = 0.0
            self.normalize()

    def mark_obstacle(self, pos: Coord) -> None:
        """Mark cell as impassable obstacle; EVE cannot be inside an obstacle."""
        self.mark_cell_empty(pos)

    def mark_unreachable_set(self, unreachable_cells: Set[Coord]) -> None:
        """Zero out probabilities for cells that are proven disconnected / unreachable."""
        for r, c in unreachable_cells:
            if 0 <= r < self.rows and 0 <= c < self.cols:
                self.grid[r, c] = 0.0
        self.normalize()

    def update_with_clue(
        self,
        clue_pos: Coord,
        estimated_distance: float,
        bearing_vector: Tuple[float, float],
        noise_sigma: float = 0.0
    ) -> None:
        """
        Bayesian update given a directional signal beacon clue.
        - estimated_distance: Estimated Euclidean distance to EVE.
        - bearing_vector: Unit vector (dr, dc) pointing towards EVE.
        - noise_sigma: Standard deviation of sensor noise.
        """
        cr, cc = clue_pos
        effective_sigma = max(noise_sigma, 0.4)
        var_factor = 2.0 * (effective_sigma ** 2)

        dr_target, dc_target = bearing_vector
        has_dir = math.hypot(dr_target, dc_target) > 1e-6

        likelihood = np.zeros_like(self.grid)

        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r, c] <= 0.0:
                    continue

                dist = math.hypot(r - cr, c - cc)
                # Distance likelihood (Gaussian shell around clue)
                dist_diff = dist - estimated_distance
                l_dist = math.exp(-(dist_diff ** 2) / var_factor)

                # Directional likelihood (cosine similarity)
                l_dir = 1.0
                if has_dir and dist > 1e-6:
                    vec_r = (r - cr) / dist
                    vec_c = (c - cc) / dist
                    dot = vec_r * dr_target + vec_c * dc_target
                    # Rescale [-1, 1] to [0.01, 1.0] with quadratic sharpness
                    cos_sim = max(0.0, dot)
                    l_dir = 0.05 + 0.95 * (cos_sim ** 2)

                likelihood[r, c] = l_dist * l_dir

        self.grid *= likelihood
        self.normalize()

    def update_with_scan(
        self,
        scanner_pos: Coord,
        estimated_distance: float,
        noise_sigma: float = 1.0
    ) -> None:
        """
        Bayesian update from omnidirectional radar/radio pulse scan.
        """
        sr, sc = scanner_pos
        effective_sigma = max(noise_sigma, 0.5)
        var_factor = 2.0 * (effective_sigma ** 2)

        likelihood = np.zeros_like(self.grid)
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r, c] <= 0.0:
                    continue
                dist = math.hypot(r - sr, c - sc)
                diff = dist - estimated_distance
                likelihood[r, c] = math.exp(-(diff ** 2) / var_factor)

        self.grid *= likelihood
        self.normalize()

    def get_entropy(self) -> float:
        """Calculate Shannon entropy H = -sum(p * log2(p))."""
        nonzero = self.grid[self.grid > 1e-12]
        return float(-np.sum(nonzero * np.log2(nonzero)))

    def most_likely_position(self) -> Coord:
        """Return coordinate with maximum posterior probability."""
        idx = int(np.argmax(self.grid))
        r, c = divmod(idx, self.cols)
        return (r, c)

    def get_top_candidates(self, k: int = 5) -> List[Tuple[Coord, float]]:
        """Return top k most probable candidate coordinates and probabilities."""
        flat_indices = np.argsort(self.grid.ravel())[::-1]
        results = []
        for idx in flat_indices[:k]:
            r, c = divmod(int(idx), self.cols)
            prob = float(self.grid[r, c])
            if prob > 1e-6:
                results.append(((r, c), prob))
        return results

    def expected_target_error(self, true_pos: Coord) -> float:
        """Calculate expected Euclidean distance to true position (for evaluation/metrics)."""
        tr, tc = true_pos
        error = 0.0
        for r in range(self.rows):
            for c in range(self.cols):
                prob = self.grid[r, c]
                if prob > 0:
                    dist = math.hypot(r - tr, c - tc)
                    error += prob * dist
        return float(error)

    def get_probability(self, pos: Coord) -> float:
        """Get probability for a specific cell."""
        r, c = pos
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return float(self.grid[r, c])
        return 0.0
