"""Unit tests for the joint location/status belief, initial signal prior and decoy robustness."""

import math

from src.belief import BeliefMap
from src.signal_model import expected_strength, vector_from_bearing_deg


def _clue_towards(belief, clue, target, sigma=0.1):
    dist = math.hypot(target[0] - clue[0], target[1] - clue[1])
    vec = ((target[0] - clue[0]) / dist, (target[1] - clue[1]) / dist)
    belief.update_with_clue(clue, dist, vec, noise_sigma=sigma)


def test_initial_signal_bearing_concentrates_belief_in_the_cone():
    belief = BeliefMap((12, 12))
    belief.update_with_initial_signal({"received_at": [0, 0], "bearing_deg": 135.0}, age_minutes=0)
    best = belief.most_likely_position()
    assert abs(best[0] - best[1]) <= 1  # along the south-east diagonal


def test_older_signal_is_trusted_less():
    fresh, stale = BeliefMap((12, 12)), BeliefMap((12, 12))
    signal = {"received_at": [0, 0], "bearing_deg": 135.0, "strength": 0.17}
    fresh.update_with_initial_signal(signal, age_minutes=0)
    stale.update_with_initial_signal(signal, age_minutes=180)
    assert stale.get_entropy() > fresh.get_entropy()


def test_scan_strength_infers_dormant_status():
    belief = BeliefMap((12, 12))
    d = math.hypot(10, 10)
    belief.update_with_scan((0, 0), d, noise_sigma=0.5, signal_strength=expected_strength(d, "DORMANT"))
    assert belief.status_probabilities()["DORMANT"] > 0.95


def test_decoy_cannot_erase_true_location_and_gets_flagged():
    belief = BeliefMap((12, 12), clue_reliability_prior=0.8)
    true_pos, spoof = (10, 10), (10, 1)
    _clue_towards(belief, (2, 9), true_pos)      # genuine beacon
    _clue_towards(belief, (1, 1), spoof)         # decoy beacon
    assert belief.get_probability(true_pos) > 0.0

    # WALL-E searches the spoofed area and finds nothing
    belief.mark_cells_empty([(r, c) for r in range(8, 12) for c in range(0, 4)])
    assert belief.most_likely_position() == true_pos
    assert belief.clue_reliability((1, 1)) < 0.2
    assert belief.clue_reliability((2, 9)) > 0.5  # uncorroborated, so it stays near its 0.8 prior


def test_naive_belief_trusts_every_beacon():
    belief = BeliefMap((12, 12), clue_reliability_prior=1.0)
    _clue_towards(belief, (1, 1), (10, 1))
    assert belief.clue_reliability((1, 1)) == 1.0


def test_sighting_makes_belief_certain():
    belief = BeliefMap((6, 6))
    belief.set_certain((3, 4))
    assert belief.get_probability((3, 4)) == 1.0
    assert belief.get_entropy() == 0.0


def test_vector_and_bearing_conventions_agree():
    dr, dc = vector_from_bearing_deg(90.0)  # east
    assert abs(dr) < 1e-9 and abs(dc - 1.0) < 1e-9
