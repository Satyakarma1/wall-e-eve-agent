# Technical Specification: WALL-E & EVE's Signal Autonomous AI Agent

## 1. Project Overview & Role
- **Project Name**: WALL-E & EVE's Signal — Autonomous AI Agent
- **Target Platform**: Windows 11 / Python 3.11 / VS Code / PowerShell
- **Purpose**: Autonomous exploration agent inspired by WALL-E searching for EVE across a contaminated wasteland grid.
- **Core Design Philosophy**: Complete separation of hidden environment state from the agent's observation space. Transparent, explainable decision-making (Observe-Decide-Act loop), Bayesian belief modeling, A* pathfinding, and rigorous automated testing.

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
|   (EVE position, etc) |-------------------------->| - A* Pathfinding  |
| - Boundary & Obstacles|                           | - Belief State    |
| - Resource Depletion  |<--------------------------| - Decision Policy |
| - Collision Checks    |        Action Request     | - Strategy Trace  |
+-----------------------+                           +-------------------+
          |                                                   |
          +-------------------------+-------------------------+
                                    |
                                    v
+-----------------------------------+-----------------------------------+
|                       Outputs & Visualization                         |
|                       (src/visualization.py)                          |
|                       (src/metrics.py)                                |
|                                                                       |
| - Static Path & Strategy Map (.png)                                   |
| - Animated Mission GIF (.gif)                                         |
| - Multi-seed Benchmark Metrics & Plots                                |
| - Optional Streamlit Dashboard (app.py)                               |
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
  - `Clues`: Set of Directive signal beacons $\{k_i: (r_i, c_i)\}$.
  - `EVE`: True hidden target coordinate $(r^*, c^*)$.

### 3.2 Information Boundary (Hidden vs Observable)
- **Hidden State** (Environment only):
  - True coordinate of EVE.
  - Global unobserved obstacles (revealed only as WALL-E explores or scans).
  - Raw clue payload (revealed only upon inspection).
- **Observable State** (Agent receives):
  - Agent current coordinate $(r, c)$.
  - Local visibility (cardinal/diagonal neighboring cells within radius $R_{local} = 1$).
  - Remaining battery / energy.
  - Remaining scan budget.
  - Mission step counter.
  - Clue detection event (if at or adjacent to a clue).
  - Inspection payload (only returned when executing `INSPECT` at a clue cell).

### 3.3 Action Space & Costs
| Action | Description | Battery Cost | Condition / Effect |
| :--- | :--- | :--- | :--- |
| `MOVE_UP` | Move to $(r-1, c)$ | 1.0 unit | Blocked if boundary or obstacle; consumes cost regardless |
| `MOVE_DOWN` | Move to $(r+1, c)$ | 1.0 unit | Blocked if boundary or obstacle; consumes cost regardless |
| `MOVE_LEFT` | Move to $(r, c-1)$ | 1.0 unit | Blocked if boundary or obstacle; consumes cost regardless |
| `MOVE_RIGHT` | Move to $(r, c+1)$ | 1.0 unit | Blocked if boundary or obstacle; consumes cost regardless |
| `INSPECT` | Inspect clue at current cell | 2.0 units | Decodes directional vector and distance estimate to EVE |
| `SCAN` | Deep radar/radio pulse | 4.0 units | Measures omnidirectional signal distance with sensor noise $\sigma_{scan}$ |
| `TERMINATE` | Agent halts mission | 0.0 units | Declares target unreachable or mission complete |

### 3.4 Terminal Conditions
1. **SUCCESS**: WALL-E reaches EVE's true coordinate $(r^*, c^*)$.
2. **FAILURE_BATTERY**: Battery drops to $\le 0$ before reaching EVE.
3. **FAILURE_TIMEOUT**: Step count exceeds `max_steps`.
4. **FAILURE_UNREACHABLE**: Agent mathematically proves all candidate target cells in its belief distribution are unreachable due to obstacle enclosures.

---

## 4. Agent Internal Design & Algorithms

### 4.1 Belief State Representation (`src/belief.py`)
- Represents a 2D probability grid $B(r, c) = P(\text{EVE} = (r, c))$.
- **Prior**: Uniform over all non-obstacle cells:
  $$B_0(r, c) = \frac{1}{|\text{Free Cells}|}$$
- **Zero Evidence**: Whenever a cell $(r, c)$ is visited and EVE is not present, $B(r, c) \leftarrow 0$.
- **Clue Observation Likelihood**:
  - Clue provides estimated distance $\hat{d}$ and direction $\vec{u}$.
  - Likelihood model:
    $$L(r, c \mid \hat{d}, \sigma) = \frac{1}{\sqrt{2\pi\sigma^2}} \exp\left(-\frac{(\| (r, c) - (r_{clue}, c_{clue}) \| - \hat{d})^2}{2\sigma^2}\right)$$
  - Directional weighting: $\max(0, \cos(\theta_{(r,c)} - \theta_{clue}))$.
- **Bayes Update**:
  $$B_{t+1}(r, c) = \frac{B_t(r, c) \cdot L(r, c)}{\sum_{u, v} B_t(u, v) \cdot L(u, v)}$$
- **Uncertainty Metric**: Shannon Entropy $H(B) = -\sum_{r,c} B(r, c) \log_2(B(r, c) + \epsilon)$.

### 4.2 Pathfinding (`src/pathfinding.py`)
- Classical $A^*$ algorithm using Manhattan distance heuristic:
  $$h(n) = |r_n - r_{goal}| + |c_n - c_{goal}|$$
- Dynamically checks known obstacles.
- If path cannot be found (goal is partitioned by obstacles), returns `None`, allowing agent to detect unreachable candidates.

### 4.3 Hierarchical Strategy Engine (`src/agent.py`)
- Explainable Finite State Machine:
  1. `EXPLORE_FOR_CLUES`: Moves along unvisited frontiers towards promising signal areas.
  2. `ACQUIRE_CLUE`: Navigates directly via $A^*$ to discovered clue, executes `INSPECT`.
  3. `HUNT_BELIEF_TARGET`: Selects highest-probability candidate $\arg\max_{(r, c)} B(r, c)$, plans $A^*$ route.
  4. `PULSE_SCAN`: When trapped in multimodal belief or high entropy, triggers deep `SCAN`.
  5. `ABORT_UNREACHABLE`: Triggered when battery budget is insufficient or all candidate cells are blocked.

### 4.4 Action Trace Log
Every step produces an explainable trace entry:
```json
{
  "step": 12,
  "position": [4, 7],
  "action": "MOVE_RIGHT",
  "reason": "Following A* waypoint to inspect discovered clue at (4, 8)",
  "strategy": "ACQUIRE_CLUE",
  "battery": 82.0,
  "top_candidate": [10, 10],
  "top_candidate_prob": 0.421,
  "belief_entropy": 2.14
}
```

---

## 5. Visualizations & Evaluation Metrics

### 5.1 Visual Artifacts
1. **Static Mission Summary (`outputs/mission_summary.png`)**:
   - High-contrast grid map with obstacles, starting marker, travelled trajectory with directional breadcrumbs, discovered clues, and EVE's location.
   - Dual inset subplots: Battery consumption vs step, Belief entropy vs step.
2. **Animated Mission Replay (`outputs/mission_animation.gif`)**:
   - Frame-by-frame visualization showing WALL-E moving, fog of war clearing, clue inspection, belief heatmap shifting, and final rendezvous.

### 5.2 Quantitative Metrics
- **Mission Success Rate (%)**: Successful missions / Total missions.
- **Path Length & Steps Taken**: Total distance travelled.
- **Exploration Coverage (%)**: Visited free cells / Total reachable free cells.
- **Energy Efficiency**: Energy remaining upon completion.
- **Scan Usage**: Count of deep radar scans.
- **Prediction Accuracy**: Distance between top candidate $\arg\max B(r,c)$ and ground truth EVE $(r^*, c^*)$ over time.

---

## 6. Acceptance Criteria
- [x] Python 3.11 compatible, runnable on Windows PowerShell.
- [x] Clear separation of hidden ground truth from agent observation.
- [x] Configurable via JSON (`config/default.json`, `config/hard.json`, `config/unreachable.json`, etc.).
- [x] $A^*$ pathfinding with obstacle avoidance.
- [x] Bayesian belief updating and entropy tracking.
- [x] Full action trace with explainable reasons.
- [x] Matplotlib static summary plot and animated GIF export.
- [x] Multi-seed statistical benchmark runner with baseline comparison.
- [x] Automated test suite passing with high coverage (`pytest`).
- [x] Optional Streamlit interactive dashboard (`app.py`).
