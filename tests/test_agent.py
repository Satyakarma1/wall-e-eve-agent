"""Unit tests for WallEAgent and Bayesian Belief system."""

import pytest
import math
from src.belief import BeliefMap
from src.agent import WallEAgent, Strategy, BaselineRandomAgent
from src.environment import Action, Observation


def test_belief_initialization():
    bounds = (4, 4)
    obstacles = {(0, 1), (1, 0)}
    belief = BeliefMap(bounds, obstacles)

    # 16 total - 2 obstacles = 14 free cells
    assert belief.get_probability((0, 1)) == 0.0
    assert belief.get_probability((1, 0)) == 0.0
    assert abs(belief.get_probability((0, 0)) - (1.0 / 14.0)) < 1e-4

    # Entropy should be positive
    assert belief.get_entropy() > 0.0


def test_belief_update_with_clue_reduces_entropy():
    bounds = (10, 10)
    belief = BeliefMap(bounds)
    initial_entropy = belief.get_entropy()

    # Suppose clue at (2, 2) signals target at (8, 8)
    clue_pos = (2, 2)
    dist = math.hypot(8 - 2, 8 - 2)
    dr = (8 - 2) / dist
    dc = (8 - 2) / dist

    belief.update_with_clue(clue_pos, dist, (dr, dc), noise_sigma=0.1)

    updated_entropy = belief.get_entropy()
    # Clue should concentrate probability and sharply reduce entropy
    assert updated_entropy < initial_entropy

    # Target (8, 8) must have the highest or near-highest probability
    top_pos, top_prob = belief.get_top_candidates(k=1)[0]
    assert top_pos == (8, 8)
    assert top_prob > 0.15


def test_agent_observe_decide_act_loop():
    bounds = (10, 10)
    agent = WallEAgent(bounds)

    obs = Observation(
        agent_pos=(0, 0),
        local_sensor={(0, 0): "FREE", (0, 1): "FREE", (1, 0): "FREE", (1, 1): "FREE"},
        battery=50.0,
        scan_budget=3,
        step_count=0
    )

    action = agent.step(obs)
    assert action in (Action.MOVE_DOWN, Action.MOVE_RIGHT, Action.SCAN, Action.TERMINATE)
    assert len(agent.history) == 1
    assert agent.history[0].step == 0
    assert agent.history[0].agent_pos == (0, 0)
    assert agent.history[0].reason != ""


def test_agent_clue_acquisition_strategy():
    bounds = (6, 6)
    agent = WallEAgent(bounds)

    # Agent sees a clue at (0, 1)
    obs = Observation(
        agent_pos=(0, 0),
        local_sensor={(0, 0): "FREE", (0, 1): "CLUE", (1, 0): "FREE"},
        battery=50.0,
        scan_budget=2,
        step_count=1
    )

    action = agent.step(obs)
    # Agent should choose to move to the clue at (0, 1)
    assert action == Action.MOVE_RIGHT
    assert agent.current_strategy == Strategy.ACQUIRE_CLUE


def test_baseline_random_agent():
    bounds = (5, 5)
    agent = BaselineRandomAgent(bounds)
    obs = Observation(
        agent_pos=(0, 0),
        local_sensor={(0, 0): "FREE", (0, 1): "FREE", (1, 0): "FREE"},
        battery=20.0,
        scan_budget=0,
        step_count=0
    )
    action = agent.step(obs)
    assert action in (Action.MOVE_RIGHT, Action.MOVE_DOWN)
