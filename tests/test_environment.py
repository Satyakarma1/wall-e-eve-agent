"""Unit tests for simulation environment and information security."""

import pytest
from src.environment import Environment, Action, Observation


@pytest.fixture
def sample_config():
    return {
        "grid_size": [6, 6],
        "start_pos": [0, 0],
        "eve_pos": [5, 5],
        "obstacles": [[1, 1], [1, 2], [2, 1]],
        "clues": [
            {"pos": [3, 3], "type": "directional_beacon", "noise_sigma": 0.0}
        ],
        "resources": {
            "initial_battery": 20.0,
            "max_steps": 30,
            "scan_budget": 2,
            "action_costs": {
                "move": 1.0,
                "inspect": 2.0,
                "scan": 4.0,
                "terminate": 0.0
            }
        },
        "random_seed": 42
    }


def test_observation_does_not_leak_eve_position(sample_config):
    """Verify that Observation object NEVER contains hidden eve_pos."""
    env = Environment(sample_config)
    obs = env.reset()

    # Verify no attribute or dict leaks eve_pos
    assert not hasattr(obs, "eve_pos")
    assert not hasattr(obs, "_eve_pos")
    assert obs.target_found is False

    # Perform a move and verify again
    obs, _, _, _ = env.step(Action.MOVE_RIGHT)
    assert not hasattr(obs, "eve_pos")
    assert not hasattr(obs, "_eve_pos")


def test_obstacle_collision_prevention(sample_config):
    """Agent cannot move into an obstacle; position is preserved, battery consumed."""
    env = Environment(sample_config)
    obs = env.reset()
    assert obs.agent_pos == (0, 0)

    # Move to (0, 1)
    obs, _, _, _ = env.step(Action.MOVE_RIGHT)
    assert obs.agent_pos == (0, 1)

    # Obstacle is at (1, 1). Attempting MOVE_DOWN should be blocked.
    obs, reward, done, info = env.step(Action.MOVE_DOWN)
    assert obs.agent_pos == (0, 1)  # Did not enter obstacle
    assert obs.collision_detected is True
    assert obs.battery < 20.0  # Battery was consumed
    assert not done


def test_boundary_collision_prevention(sample_config):
    """Agent cannot move outside grid boundaries."""
    env = Environment(sample_config)
    obs = env.reset()
    assert obs.agent_pos == (0, 0)

    # Attempt to move UP past row 0
    obs, _, done, _ = env.step(Action.MOVE_UP)
    assert obs.agent_pos == (0, 0)
    assert obs.collision_detected is True
    assert not done


def test_clue_inspection_payload(sample_config):
    """Inspecting at a clue location provides valid distance and bearing."""
    env = Environment(sample_config)
    env.reset()

    # Move to clue at (3, 3)
    for _ in range(3):
        env.step(Action.MOVE_DOWN)
    for _ in range(3):
        env.step(Action.MOVE_RIGHT)

    assert env.agent_pos == (3, 3)

    # Perform INSPECT
    obs, _, _, _ = env.step(Action.INSPECT)
    assert obs.clue_payload is not None
    payload = obs.clue_payload
    assert payload["clue_pos"] == (3, 3)
    # Target is at (5, 5). Distance from (3, 3) to (5, 5) is sqrt(4 + 4) = sqrt(8) ~ 2.828
    assert abs(payload["estimated_distance"] - 2.8284) < 1e-3
    assert len(env.discovered_clues) == 1


def test_scan_action_depletes_budget(sample_config):
    """Scan action consumes scan budget and battery."""
    env = Environment(sample_config)
    obs = env.reset()
    initial_budget = obs.scan_budget
    initial_batt = obs.battery

    obs, _, _, _ = env.step(Action.SCAN)
    assert obs.scan_budget == initial_budget - 1
    assert obs.battery == initial_batt - 4.0
    assert obs.scan_result is not None


def test_battery_exhaustion_failure(sample_config):
    """Depleting battery causes terminal FAILURE_BATTERY."""
    sample_config["resources"]["initial_battery"] = 2.0
    env = Environment(sample_config)
    env.reset()

    env.step(Action.MOVE_RIGHT)  # Cost 1.0 -> 1.0 left
    assert not env.done
    _, _, done, info = env.step(Action.MOVE_RIGHT)  # Cost 1.0 -> 0.0 left
    assert done is True
    assert info["status"] == "FAILURE_BATTERY"
    assert info["success"] is False


def test_max_steps_timeout_failure(sample_config):
    """Exceeding max steps causes terminal FAILURE_TIMEOUT."""
    sample_config["resources"]["max_steps"] = 3
    sample_config["resources"]["initial_battery"] = 100.0
    env = Environment(sample_config)
    env.reset()

    env.step(Action.MOVE_RIGHT)
    env.step(Action.MOVE_LEFT)
    _, _, done, info = env.step(Action.MOVE_RIGHT)
    assert done is True
    assert info["status"] == "FAILURE_TIMEOUT"


def test_success_reaching_eve():
    """Agent reaches EVE and succeeds."""
    config = {
        "grid_size": [3, 3],
        "start_pos": [0, 0],
        "eve_pos": [0, 1],
        "obstacles": [],
        "clues": [],
        "resources": {
            "initial_battery": 10.0,
            "max_steps": 10,
            "scan_budget": 0,
            "action_costs": {"move": 1.0, "inspect": 2.0, "scan": 4.0, "terminate": 0.0}
        }
    }
    env = Environment(config)
    env.reset()
    obs, _, done, info = env.step(Action.MOVE_RIGHT)
    assert done is True
    assert obs.target_found is True
    assert info["status"] == "SUCCESS"
    assert info["success"] is True
