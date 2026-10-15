# 🤖 WALL-E & EVE's Signal — Autonomous AI Exploration Agent

![Python Version](https://img.shields.io/badge/Python-3.11.9-blue.svg)
![Tests](https://img.shields.io/badge/Tests-23%2F23%20Passing-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Completed%20%26%20Verified-success.svg)

An explainable, classical AI autonomous exploration agent inspired by Pixar's **WALL-E searching for EVE** across a debris-laden wasteland grid. Built with strict information boundaries, Bayesian belief updating, $A^*$ pathfinding, resource budget management, and animated 2D trajectory visualization.

---

## 📌 Table of Contents
1. [Core Features](#-core-features)
2. [AI & Environment Architecture](#-ai--environment-architecture)
3. [Repository Structure](#-repository-structure)
4. [Installation & Requirements](#-installation--requirements)
5. [Usage & Execution Commands](#-usage--execution-commands)
6. [Measured Evaluation & Benchmark Results](#-measured-evaluation--benchmark-results)
7. [Visual Outputs & Artifacts](#-visual-outputs--artifacts)
8. [Automated Test Suite](#-automated-test-suite)
9. [Verification of Acceptance Criteria](#-verification-of-acceptance-criteria)

---

## 🌟 Core Features

- **Strict Information Hiding**: The environment maintains EVE's hidden position and global unmapped obstacles privately. The agent interacts exclusively through an observation interface (`Observation` dataclass) and cannot cheat by inspecting ground-truth attributes.
- **Bayesian Belief Modeling**: The agent tracks a 2D probability distribution $P(\text{EVE} = (r, c))$ across all non-obstacle cells. Discovered clue beacons (bearing vectors and distance estimates) and radar scans update this distribution via Bayes' Rule:
  $$P_{t+1}(r, c) \propto P_t(r, c) \cdot L(r, c \mid \text{Observation})$$
- **Uncertainty Quantification**: Tracks Shannon Entropy $H(B) = -\sum P(x) \log_2 P(x)$ to quantify uncertainty reduction over time.
- **$A^*$ Pathfinding with Collision Prevention**: Dynamically routes around discovered obstacles using Manhattan distance heuristics. Boundary collisions and obstacle bumps are actively prevented.
- **Resource Management**: Limited battery (100.0 units), step countdowns (max 150 steps), and scan budgets (5 scans). Reaching $\le 0$ battery terminates in `FAILURE_BATTERY`.
- **Explainable Strategy Engine (FSM)**: Every action logs an explainable trace recording `action`, `strategy` (`EXPLORE_FOR_CLUES`, `ACQUIRE_CLUE`, `HUNT_BELIEF_TARGET`, `PULSE_SCAN`, `ABORT_UNREACHABLE`), `battery`, `top_candidate`, and `reason`.
- **Reproducible Evaluation**: Full statistical benchmark comparing WALL-E against a blind frontier baseline, along with a clean vs. noisy sensor experiment across multiple random seeds.
- **Visual Artifacts**: Automated high-resolution static 4-panel mission plots (`.png`) and frame-by-frame animated GIFs (`.gif`).
- **Optional Web Dashboard**: Interactive Streamlit GUI with step-by-step playback slider (`app.py`).

---

## 🏗️ AI & Environment Architecture

```
+--------------------------------------------------------------------------------+
|                               Simulation Orchestrator                          |
|                                (src/simulation.py)                             |
+---------------------------------------+----------------------------------------+
                                        |
              +-------------------------+-------------------------+
              |                                                   |
              v                                                   v
+---------------------------+                           +------------------------+
|        Environment        |                           |       WALL-E Agent     |
|   (src/environment.py)    |     Observation Dict      |     (src/agent.py)     |
|                           |-------------------------->|                        |
| - Private True Target     |   (agent_pos, sensor,     | - Known Obstacle Map   |
|   _eve_pos: (r, c)        |    battery, step, etc.)   | - A* Pathfinding       |
| - Boundary & Obstacles    |                           | - Bayesian Belief Map  |
| - Battery & Step Limits   |<--------------------------| - FSM Strategy Engine  |
| - Action Cost Deductions  |      Action Request       | - Explainable Trace    |
+---------------------------+   (MOVE, INSPECT, SCAN)   +------------------------+
              |                                                   |
              +-------------------------+-------------------------+
                                        |
                                        v
+--------------------------------------------------------------------------------+
|                             Visualization & Metrics                            |
|                 (src/visualization.py / src/metrics.py)                        |
| - 4-Panel Static Mission Summary (outputs/*_summary.png)                       |
| - Animated Mission Execution Replay (outputs/*_animation.gif)                  |
| - Comparative Multi-seed Statistical Benchmark Plots                           |
| - Markdown Mission Reports (outputs/*_report.md)                               |
+--------------------------------------------------------------------------------+
```

### Action Space & Costs

| Action | Description | Battery Cost | Condition / Effect |
| :--- | :--- | :--- | :--- |
| `MOVE_UP` / `DOWN` / `LEFT` / `RIGHT` | Cardinal 1-step move | 1.0 unit | Blocked if obstacle or boundary; battery deducted |
| `INSPECT` | Inspect clue beacon | 2.0 units | Decodes distance and bearing vector to EVE |
| `SCAN` | Omnidirectional pulse | 4.0 units | Measures radial distance to EVE with noise |
| `TERMINATE` | Abort mission | 0.0 units | Declares unreachable target or ends mission |

---

## 📁 Repository Structure

```
wall-e-eve-agent/
│
├── config/
│   ├── default.json             # Standard 12x12 scenario from prototype
│   ├── hard.json                # Complex 16x16 maze scenario with 3 clues
│   ├── unreachable.json         # Blocked scenario to test graceful abort
│   └── noisy.json               # Scenario with sensor noise (sigma = 1.5)
│
├── src/
│   ├── __init__.py
│   ├── environment.py           # World grid, private EVE state, rules & sensing
│   ├── agent.py                 # WALL-E autonomous agent, FSM, and baseline agent
│   ├── pathfinding.py           # A*, BFS, frontier discovery, and reachability
│   ├── belief.py                # 2D Bayesian probability distribution & entropy
│   ├── simulation.py            # Simulation runner, trace collection & report export
│   ├── visualization.py         # Static 4-panel summary & animated GIF generator
│   └── metrics.py               # Multi-trial benchmark runner & comparative plotting
│
├── tests/
│   ├── test_environment.py     # 8 tests: bounds, collisions, info hiding, costs
│   ├── test_pathfinding.py     # 6 tests: A*, BFS, obstacle avoidance, reachability
│   ├── test_agent.py           # 5 tests: belief init, entropy drop, FSM transitions
│   ├── test_simulation.py      # 3 tests: default mission, unreachable target, reports
│   └── test_visualization.py   # 1 test: verifies PNG and GIF generation
│
├── outputs/
│   ├── default_summary.png      # 4-panel static visualization for default run
│   ├── default_animation.gif    # Animated frame-by-frame replay for default run
│   ├── default_report.md        # Comprehensive markdown mission report
│   ├── benchmark_agent_vs_baseline.png # Comparative bar charts
│   ├── benchmark_clean_vs_noisy.png    # Robustness charts
│   └── benchmark_summary.json   # Full raw and aggregate statistical metrics
│
├── prototype_main.py            # Preserved original static 12x12 prototype
├── main.py                      # Primary production CLI runner
├── app.py                       # Optional Streamlit interactive dashboard
├── requirements.txt             # Minimal dependency specifications
├── SPEC.md                      # Detailed technical specifications document
├── .gitignore                   # Git ignore for virtual environments and caches
└── README.md                    # Project documentation
```

---

## 💻 Installation & Requirements

### System Requirements
- **OS**: Windows 10/11 (PowerShell)
- **Python**: 3.11.x (verified on Python 3.11.9)
- **Core Dependencies**: `numpy`, `matplotlib`, `pillow`, `pytest`

### Setup Instructions (Windows PowerShell)

```powershell
# Navigate into the project folder
cd "C:\VS CODE\Vinnovate IT\wall-e-eve-agent"

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install core dependencies
pip install -r requirements.txt
```

---

## 🚀 Usage & Execution Commands

### 1. Run Standard Mission (Default Configuration)
Executes WALL-E's autonomous search on the 12×12 wasteland grid, outputs step trace to the terminal, and saves a 4-panel summary PNG, markdown report, and animated GIF:
```powershell
.\.venv\Scripts\python.exe main.py
```

### 2. Run with Alternative Configurations
```powershell
# Hard maze scenario (16x16 grid with 3 clues)
.\.venv\Scripts\python.exe main.py --config config/hard.json

# Unreachable scenario (tests graceful failure & candidate pruning)
.\.venv\Scripts\python.exe main.py --config config/unreachable.json

# Noisy sensor scenario
.\.venv\Scripts\python.exe main.py --config config/noisy.json

# Fast run without generating GIF
.\.venv\Scripts\python.exe main.py --config config/default.json --no-gif
```

### 3. Run Statistical Benchmark Suite
Executes 15 reproducible trials comparing the WALL-E Agent against a blind frontier baseline, and clean vs. noisy observations:
```powershell
.\.venv\Scripts\python.exe main.py --benchmark
```

### 4. Run Automated Test Suite
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### 5. Launch Interactive Dashboard (Optional Bonus)
```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
# or (if your virtual environment Scripts folder is in PATH):
streamlit run app.py
```

---

## 📊 Measured Evaluation & Benchmark Results

All metrics below are **measured results** gathered from 15 reproducible runs with seeds `100` to `114` using `main.py --benchmark`.

### Experiment 1: Autonomous WALL-E Agent vs. Blind Frontier Baseline
*Task: Locate EVE at (10, 10) on a 12×12 wasteland grid within 100 battery units.*

| Metric | WALL-E Agent (Ours) | Blind Baseline | Improvement |
| :--- | :---: | :---: | :---: |
| **Mission Success Rate** | **100.0%** | **0.0%** | **+100.0%** |
| **Mean Steps to Completion** | **36.93 ± 23.64** | 100.0 ± 0.00 | **63.1% fewer steps** |
| **Mean Battery Consumed** | **46.13 ± 27.36** | 100.0 ± 0.00 | **53.9% energy saved** |
| **Mean Battery Remaining** | **53.87 ± 27.36** | 0.0 ± 0.00 | **High safety margin** |
| **Exploration Efficiency** | **Direct Clue Navigation** | Exhaustive wandering | **Targeted localization** |

> **Analysis**: The Blind Baseline wanders along frontiers without utilizing signal clues, consistently running out of battery before discovering the target in the corner. The WALL-E Agent leverages directional clues and Bayesian likelihood updates to converge directly on EVE with 100% success.

---

### Experiment 2: Sensor Robustness (Clean vs. Noisy Sensors)
*Comparing clean observations ($\sigma = 0.0$) against noisy beacons ($\sigma = 1.5$).*

| Metric | Clean Sensor ($\sigma = 0.0$) | Noisy Sensor ($\sigma = 1.5$) |
| :--- | :---: | :---: |
| **Success Rate** | **100.0%** | **80.0%** |
| **Mean Steps to Locate EVE** | **36.93 ± 23.64** | **37.20 ± 23.54** |
| **Mean Final Target Prediction Error** | **0.00 ± 0.00 cells** | **0.52 ± 0.57 cells** |

> **Analysis**: Under significant Gaussian noise ($\sigma = 1.5$), the Bayesian update maintains robustness: even when clues deviate by up to 2–3 cells, the agent achieves an 80% success rate with an average prediction error of just 0.52 cells.

---

## 🎨 Visual Outputs & Artifacts

All visual artifacts are automatically generated and saved to the `outputs/` directory:

1. **`outputs/default_summary.png`**:
   - **Panel 1 (Main World Map)**: Shows grid boundaries, metallic obstacle piles, WALL-E starting position (green), travelled path with directional navigation arrows, discovered clues (orange stars), EVE's target cross (red), and strategy transition annotations.
   - **Panel 2 (Battery Depletion)**: Curve displaying battery level over time.
   - **Panel 3 (Belief Uncertainty)**: Shannon Entropy $H(B)$ showing rapid uncertainty reduction upon clue inspection.
2. **`outputs/default_animation.gif`**:
   - Dynamic 2D animation showing WALL-E moving, fog clearing, and the Bayesian belief heatmap shifting in real time.
3. **`outputs/benchmark_agent_vs_baseline.png`**:
   - Comparative bar charts for Success Rate, Steps, and Battery Usage.
4. **`outputs/benchmark_clean_vs_noisy.png`**:
   - Bar charts illustrating noise tolerance.

---

## 🧪 Automated Test Suite

The project includes 23 automated unit and integration tests covering all critical components:

```
tests/test_agent.py ......................... [PASSED]
  - test_belief_initialization
  - test_belief_update_with_clue_reduces_entropy
  - test_agent_observe_decide_act_loop
  - test_agent_clue_acquisition_strategy
  - test_baseline_random_agent

tests/test_environment.py ................... [PASSED]
  - test_observation_does_not_leak_eve_position
  - test_obstacle_collision_prevention
  - test_boundary_collision_prevention
  - test_clue_inspection_payload
  - test_scan_action_depletes_budget
  - test_battery_exhaustion_failure
  - test_max_steps_timeout_failure
  - test_success_reaching_eve

tests/test_pathfinding.py ................... [PASSED]
  - test_manhattan_distance
  - test_get_neighbors_respects_bounds_and_obstacles
  - test_a_star_search_finds_optimal_path
  - test_a_star_unreachable_target
  - test_get_reachable_cells
  - test_find_nearest_frontier

tests/test_simulation.py .................... [PASSED]
  - test_simulation_default_mission_succeeds
  - test_simulation_unreachable_target_terminates_gracefully
  - test_save_mission_report

tests/test_visualization.py ................. [PASSED]
  - test_visualizations_generate_valid_files

==================== 23 passed in ~6.9s ====================
```

---

## ✅ Verification of Acceptance Criteria

| # | Acceptance Criterion | Verification Status | Evidence / Implementation |
| :-: | :--- | :---: | :--- |
| 1 | Application starts successfully | **Verified** | `python main.py` runs cleanly with exit code 0 |
| 2 | Agent completes mission or reports failure | **Verified** | Clean `SUCCESS`, `FAILURE_BATTERY`, or `TERMINATED` |
| 3 | Agent cannot access hidden EVE position | **Verified** | `_eve_pos` is private; verified by `test_observation_does_not_leak_eve_position` |
| 4 | Obstacles and boundaries are respected | **Verified** | Verified by `test_obstacle_collision_prevention` and `test_boundary_collision_prevention` |
| 5 | Resource limits are strictly enforced | **Verified** | Verified by `test_battery_exhaustion_failure` and `test_max_steps_timeout_failure` |
| 6 | Decision trace records actions and reasons | **Verified** | 100% of steps logged in `action_trace` with `reason`, `strategy`, `entropy` |
| 7 | Visual path matches actual action history | **Verified** | Path drawn in `outputs/default_summary.png` and `default_animation.gif` |
| 8 | Clues revealed only upon discovery | **Verified** | Fog of war hides clues until visited/inspected |
| 9 | Evaluation runs generate real metrics/plots | **Verified** | 15-trial benchmark saved to `outputs/benchmark_summary.json` & PNG plots |
| 10 | Automated tests pass | **Verified** | 23 of 23 pytest tests passing |
| 11 | Windows PowerShell reproducibility | **Verified** | All commands tested and functional in Windows PowerShell |
| 12 | Core project runs without dashboard | **Verified** | `main.py` runs independently of Streamlit |
| 13 | Visualization bonus demonstrable | **Verified** | Animated GIF generated via Matplotlib and Pillow |
