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


def _dock_config():
    return {
        "grid_size": [5, 5],
        "start_pos": [0, 0],
        "charging_stations": [[0, 0]],
        "eve": {"pos": [4, 4], "status": "DORMANT"},
        "obstacles": [],
        "clues": [
            {"pos": [0, 2], "type": "decoy", "spoof_pos": [4, 0], "noise_sigma": 0.0},
        ],
        "resources": {
            "initial_battery": 10.0,
            "battery_capacity": 30.0,
            "max_steps": 50,
            "scan_budget": 2,
            "recharge_per_action": 15.0,
            "action_costs": {"move": 1.0, "inspect": 2.0, "scan": 4.0, "recharge": 0.0, "terminate": 0.0},
        },
        "random_seed": 3,
    }


def test_recharge_at_dock_restores_battery_up_to_capacity():
    env = Environment(_dock_config())
    env.reset()
    obs, _, _, _ = env.step(Action.RECHARGE)
    assert obs.battery == 25.0 and obs.recharged == 15.0
    obs, _, _, _ = env.step(Action.RECHARGE)
    assert obs.battery == 30.0  # capped at capacity
    assert env.get_summary_info()["recharge_count"] == 2


def test_recharge_away_from_dock_has_no_effect():
    env = Environment(_dock_config())
    env.reset()
    env.step(Action.MOVE_DOWN)
    obs, _, _, _ = env.step(Action.RECHARGE)
    assert obs.recharged == 0.0
    assert obs.battery == 9.0
    assert "no charging dock" in obs.message


def test_decoy_payload_points_to_spoof_not_eve():
    env = Environment(_dock_config())
    env.reset()
    env.step(Action.MOVE_RIGHT)
    env.step(Action.MOVE_RIGHT)
    obs, _, _, _ = env.step(Action.INSPECT)
    payload = obs.clue_payload
    assert payload is not None
    assert "type" not in payload and "spoof_pos" not in payload  # indistinguishable from a genuine beacon
    # Decoy at (0, 2) points to spoof (4, 0): distance sqrt(16 + 4), bearing south-west
    assert abs(payload["estimated_distance"] - (20 ** 0.5)) < 1e-6
    dr, dc = payload["bearing_vector"]
    assert dr > 0 and dc < 0


def test_scan_strength_depends_on_hidden_status():
    from src.signal_model import expected_strength

    readings = {}
    for status in ("ACTIVE", "DORMANT"):
        cfg = _dock_config()
        cfg["eve"]["status"] = status
        cfg["sensors"] = {"strength_noise_sigma": 0.0, "scan_noise_sigma": 0.0}
        env = Environment(cfg)
        env.reset()
        obs, _, _, _ = env.step(Action.SCAN)
        readings[status] = obs.scan_result["signal_strength"]
        assert abs(readings[status] - expected_strength(32 ** 0.5, status)) < 1e-9
    assert readings["ACTIVE"] > readings["DORMANT"]


def test_briefing_contains_no_hidden_state():
    env = Environment(_dock_config())
    briefing = env.get_briefing()
    text = repr(briefing)
    assert "spoof" not in text and "DORMANT" not in text and "decoy" not in text
    assert briefing.charging_stations == ((0, 0),)
    assert briefing.battery_capacity == 30.0


def test_eve_visible_only_inside_sensor_radius():
    env = Environment(_dock_config())
    obs = env.reset()
    assert "EVE" not in obs.local_sensor.values()
    env.agent_pos = (3, 3)  # teleport for the test: EVE at (4, 4) is now adjacent
    obs, _, _, _ = env.step(Action.SCAN)
    assert obs.local_sensor[(4, 4)] == "EVE"


def test_invalid_config_is_rejected():
    cfg = _dock_config()
    cfg["obstacles"] = [[4, 4]]  # EVE inside an obstacle
    with pytest.raises(ValueError):
        Environment(cfg)
