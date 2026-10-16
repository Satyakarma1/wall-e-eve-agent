"""Tests for the random mission generator and the generalization benchmark statistics."""

import math

from src.environment import Environment
from src.metrics import aggregate, run_benchmark, wilson_interval
from src.mission_generator import generate_mission
from src.pathfinding import bfs_distance_map


def test_generated_missions_are_valid_and_solvable():
    for seed in range(40):
        cfg = generate_mission(seed, n_decoys=1)
        env = Environment(cfg)  # validates bounds, obstacles, clue types
        truth = env.get_ground_truth_for_eval()
        dist = bfs_distance_map([env.start_pos], env.bounds, truth["obstacles"])
        assert math.isfinite(dist[truth["eve_pos"]]), f"seed {seed}: EVE unreachable"
        reachable = sum(math.isfinite(v) for v in dist.ravel())
        assert reachable >= 0.7 * (env.rows * env.cols - len(truth["obstacles"])), f"seed {seed}: start boxed in"
        assert sum(c["type"] == "decoy" for c in cfg["clues"]) == 1
        assert sum(c["type"] != "decoy" for c in cfg["clues"]) == 2


def test_generator_is_deterministic_and_conditions_share_the_map():
    clean, noisy = generate_mission(42), generate_mission(42, noisy=True, n_decoys=1)
    assert clean == generate_mission(42)
    assert clean["obstacles"] == noisy["obstacles"]
    assert clean["eve"] == noisy["eve"]
    assert clean["clues"][0]["pos"] == noisy["clues"][0]["pos"]


def test_wilson_interval_is_sane():
    lo, hi = wilson_interval(20, 20)
    assert hi == 1.0 and 0.8 < lo < 1.0
    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0 and hi > 0.0


def test_small_benchmark_aggregates_every_condition_and_agent():
    records = run_benchmark(n_missions=3)
    assert len(records) == 4 * 3 * 3
    agg = aggregate(records)
    assert set(agg) == {"clean", "noisy", "decoy", "noisy+decoy"}
    for by_agent in agg.values():
        assert set(by_agent) == {"walle", "naive", "baseline"}
        for cell in by_agent.values():
            assert cell["missions"] == 3
            assert cell["success_ci95"][0] <= cell["success_rate"] <= cell["success_ci95"][1]
