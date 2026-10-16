# Technical Specification: WALL-E & EVE's Signal Autonomous AI Agent

## 1. Project Overview & Role
- **Project Name**: WALL-E & EVE's Signal — Autonomous AI Agent
- **Target Platform**: Windows 11 / Python 3.11 / VS Code / PowerShell
- **Purpose**: Autonomous exploration agent inspired by WALL-E searching for EVE across a contaminated wasteland grid.
- **Core Design Philosophy**: Complete separation of hidden environment state from the agent's observation space. Transparent, explainable decision-making (Observe-Decide-Act loop), Bayesian belief modeling over location and operational status, A* pathfinding, solar dock recharging, spoofed beacon filtering, and rigorous automated testing (52/52 passing).

---

## 2. System Architecture & Components

```
+-----------------------------------------------------------------------+
|                             Simulation Runner                         |
|                             (src/simulation.py)                       |
+-----------------------------------+-----------------------------------+
                                    |
          +-------------------------+-------------------------+
          |                                                   |
          v                                                   v
+-----------------------+                           +-------------------+
|      Environment      |                           |       Agent       |
|  (src/environment.py) |                           |  (src/agent.py)   |
|                       |                           |                   |
| - Hidden Ground Truth |     Observation Dict      | - Internal Map    |
|   (EVE pos & status)  |-------------------------->| - A* Pathfinding  |
| - Boundary & Obstacles|                           | - Joint Belief    |
| - Solar Charging Docks|<--------------------------| - Decision Policy |
| - Resource Depletion  |        Action Request     | - Strategy Trace  |
| - Decoy Spoofed Clues |   (MOVE, SCAN, RECHARGE)  | - Energy Safety   |
+-----------------------+                           +-------------------+
          |                                                   |
          +-------------------------+-------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                       Outputs & Visualization                         |
|                (src/visualization.py, src/replay_player.py)           |
|                (src/metrics.py, src/report.py)                        |
|                                                                       |
| - Static Path & Strategy Map (.png)                                   |
| - Animated Mission GIF (.gif) & Interactive HTML Player (.html)       |
| - Multi-seed Generalization Benchmark (4 conditions x 3 agents)       |
| - Structured Markdown Mission Reports (.md) & Trace JSON (.json)      |
| - Streamlit Interactive Dashboard (app.py)                            |
+-----------------------------------------------------------------------+
```

---

## 3. Environment & Rules Specification

### 3.1 Grid World Model
- **Grid Coordinates**: Discrete 2D grid $(r, c)$ where $r \in [0, H-1]$ (row, vertical, 0 at top) and $c \in [0, W-1]$ (column, horizontal, 0 at left).
- **Cell Types**:
  - `0`: Free / Traversable terrain
  - `1`: Impassable Obstacle / Debris pile
- **Special Entities**:
  - `Start`: Initial WALL-E coordinate $(r_0, c_0)$.
  - `Docks`: Solar charging docks where `RECHARGE` restores battery.
  - `Clues`: Directive signal beacons (genuine or spoofed decoys).
  - `EVE`: True hidden target coordinate $(r^*, c^*)$ and operational state (`ACTIVE` / `DORMANT`).

### 3.2 Information Boundary (Hidden vs Observable)
- **Hidden State** (Environment only):
  - True coordinate and status of EVE (`_eve_pos`, `_eve_status`).
  - Global unobserved obstacles (revealed only as WALL-E explores or scans).
  - Raw clue payload and spoof targets (revealed only upon inspection).
- **Observable State** (Agent receives):
  - Agent current coordinate $(r, c)$.
  - Local visibility (cardinal/diagonal neighboring cells within radius $R_{local} = 1$, Chebyshev $\le 1$).
  - Remaining battery / energy and step counter.
  - Charging docks list and remaining scan budget.
  - Clue detection event (if at or adjacent to a clue).
  - Inspection payload (only returned when executing `INSPECT` at a clue cell).

### 3.3 Action Space & Costs
| Action | Description | Battery Cost | Condition / Effect |
| :--- | :--- | :---: | :--- |
| `MOVE_UP` | Move to $(r-1, c)$ | 1.0 unit | Blocked if boundary or obstacle; consumes cost regardless |
| `MOVE_DOWN` | Move to $(r+1, c)$ | 1.0 unit | Blocked if boundary or obstacle; consumes cost regardless |
| `MOVE_LEFT` | Move to $(r, c-1)$ | 1.0 unit | Blocked if boundary or obstacle; consumes cost regardless |
| `MOVE_RIGHT` | Move to $(r, c+1)$ | 1.0 unit | Blocked if boundary or obstacle; consumes cost regardless |
| `INSPECT` | Inspect clue at current cell | 2.0 units | Decodes directional vector and distance estimate |
| `SCAN` | Omnidirectional radar pulse | 4.0 units | Measures radial distance and signal amplitude (must be $\ge 3$ cells from prior scan) |
| `RECHARGE` | Solar dock recharge | 0.0 units | Restores $+25.0$ battery up to capacity when on a dock; no-op elsewhere |
| `TERMINATE` | Agent halts mission | 0.0 units | Aborts when reachable belief mass $< 5\%$ (`EVE_UNREACHABLE`) |

### 3.4 Terminal Conditions
1. **SUCCESS**: WALL-E reaches EVE's true coordinate $(r^*, c^*)$.
2. **FAILURE_BATTERY**: Battery drops to $\le 0$ before reaching EVE.
3. **FAILURE_TIMEOUT**: Step count exceeds `max_steps`.
4. **TERMINATED_BY_AGENT**: Agent detects target is blocked/unreachable (`EVE_UNREACHABLE`).

---

## 4. Agent Internal Design & Algorithms

### 4.1 Belief State Representation (`src/belief.py`)
- Represents a 2D joint posterior grid in log space:
  $$B(r, c, s) = P(\text{EVE} = (r, c), \text{Status} = s)$$
  for $s \in \{\text{ACTIVE}, \text{DORMANT}\}$.
- **Prior**: Initial signal reading with age-dependent bearing spread.
- **Camera Pruning**: Visited free cells without EVE receive $B(r, c, \cdot) \leftarrow 0$.
- **Decoy-Robust Reliability Mixture**:
  $$L_{\text{beacon}}(r, c) = 0.8 \cdot L_{\text{genuine}}(r, c) + 0.2 \cdot U$$
  Beacons with $P(\text{genuine}) < 0.20$ are rejected as decoys.
- **Signal Amplitude**: Distinguishes `ACTIVE` from `DORMANT` status via radar pulse amplitude ($1.0$ vs $0.5$).
- **Entropy Tracking**: Shannon Entropy $H(B) = -\sum_{r,c,s} B(r, c, s) \log_2(B(r, c, s) + \epsilon)$.

### 4.2 Pathfinding (`src/pathfinding.py`)
- Classical $A^*$ search with Manhattan heuristic, breaking ties towards straight lines.
- Dynamic obstacle map updated upon local sensing.
- Reachability analysis via BFS to identify connected traversable components.

### 4.3 Hierarchical Strategy Engine (`src/agent.py`)
Priority tiers:
1. `RECHARGE_AT_DOCK`: At dock with battery $< \text{capacity}$.
2. `TURN_BACK_FOR_ENERGY`: Battery $< \text{trip\_to\_dock} + \text{reserve}$.
3. `ACQUIRE_CLUE`: Navigate to discovered uninspected beacon.
4. `TRIANGULATE_SCAN`: Radar pulse from new vantage point ($\ge 3$ cells apart).
5. `HUNT_BELIEF_TARGET`: Navigate to top candidate $\arg\max B(r, c)$.
6. `EXPLORE_FOR_CLUES`: Frontier-based exploration.
7. `ABORT_UNREACHABLE`: Abort if reachable candidate mass $< 0.05$.

---

## 5. Visualizations & Evaluation Metrics

### 5.1 Visual Artifacts
1. **Interactive Canvas Replay (`outputs/*_replay.html`)**: Standalone HTML5 canvas player with scrubber, timeline, ripples, and decision explanation pane.
2. **Animated Mission Replay (`outputs/*_animation.gif`)**: Frame-by-frame GIF (1 frame per step; no visual leaks).
3. **Static Mission Summary (`outputs/*_summary.png`)**: 4-panel figure with trajectory, battery curve, entropy decay, and status inference.
4. **Generalization Benchmark (`outputs/benchmark_generalization.png`)**: 4-condition comparative analysis.

---

## 6. Acceptance Criteria Verification
- [x] Python 3.11 compatible, verified on Windows PowerShell.
- [x] Clear separation of hidden ground truth from agent observation (`MissionBriefing`).
- [x] Configurable via JSON (`config/default.json`, `config/decoy.json`, `config/recharge.json`, etc.).
- [x] $A^*$ pathfinding with obstacle avoidance and straight-line tie-breaking.
- [x] Joint Bayesian belief updating over location AND status with entropy tracking.
- [x] Decoy/spoofed signal rejection via exact posterior calculation.
- [x] Energy management with solar dock recharging and turn-back policy.
- [x] Full action trace JSON and Markdown mission reports.
- [x] Interactive HTML canvas replay player, animated GIFs, and static PNG summaries.
- [x] 60-mission generalization benchmark suite across 4 conditions and 3 agents.
- [x] 52 of 52 automated tests passing (`pytest`).
- [x] Interactive Streamlit dashboard (`app.py`).
