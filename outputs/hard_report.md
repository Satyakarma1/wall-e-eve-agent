# WALL-E Mission Report — Hard maze with stale coordinates

Config `hard` · agent `walle` · outcome **SUCCESS** after 33 steps

## 1. Verdict
| Item | Inference |
| :--- | :--- |
| Conclusion | `EVE_FOUND` |
| EVE location | (15, 15) — **observed directly at rendezvous** |
| EVE status | ACTIVE — **observed directly** (P(ACTIVE) = 1.00, P(DORMANT) = 0.00) |
| Remaining uncertainty | -0.00 bits of entropy over EVE's location |
| Recommended next step | EVE is ACTIVE at (15, 15): hand over the plant and escort her to the dock. Nearest dock is 14 moves away; battery left 50 is enough to escort her back. |

## 2. Evidence found
1. Step 0 — **Initial signal** received at (0, 0): approx. coordinates (12, 12), strength 0.06; 90 min old at mission start (timestamp 2805-07-14T04:30:00Z).
2. Step 1 — **Pulse scan** from (0, 0): range ~20.4 cells, beacon strength 0.030.
3. Step 7 — **Pulse scan** from (3, 2): range ~18.3 cells, beacon strength 0.124.
4. Step 29 — **Beacon** (12, 14) decoded: EVE ~3.2 cells away at bearing 162° → P(genuine) = 1.00.
5. Step 31 — **EVE sighted** at (15, 15) by the local camera.
6. Step 33 — **Rendezvous** at (15, 15): EVE status observed as ACTIVE.

## 3. Resources and performance
- Steps: 33 (path length 30 cells)
- Battery: 40.0 consumed, 50.0 remaining, 0.0 recharged over 0 dock action(s)
- Pulse scans: 2 · beacons inspected: 1 · beacons sighted: 1 of 3
- Coverage: 13.5% of free cells visited, 33.6% of the map sensed

## 4. Strategy changes
- **Step 0** → `PULSE_SCAN`: Belief entropy 7.4 bits: first pulse scan to measure EVE's range and signal strength
- **Step 1** → `HUNT_BELIEF_TARGET`: Belief target (14, 15): P=0.12, 29 moves away
- **Step 6** → `PULSE_SCAN`: Belief entropy 3.8 bits: scanning from a new vantage point 3 cells from the last scan to triangulate
- **Step 7** → `HUNT_BELIEF_TARGET`: Belief target (15, 15): P=0.47, 25 moves away
- **Step 27** → `ACQUIRE_CLUE`: Beacon at (12, 14) not yet decoded (1 moves): going to inspect it
- **Step 29** → `HUNT_BELIEF_TARGET`: Belief target (15, 15): P=0.87, 4 moves away
- **Step 31** → `HUNT_BELIEF_TARGET`: Re-plan after EVE sighted at (15, 15)!: EVE sighted at (15, 15): closing in (2 moves)

## 5. Decision trace
Full trace with every observation, decision and outcome: `hard_trace.json`.

| Step | Position | Action | Strategy | Battery | Top candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (0, 0) | `SCAN` | `PULSE_SCAN` | 90.0 | (13, 13) P=0.01 | Belief entropy 7.4 bits: first pulse scan to measure EVE's range and signal strength |
| 1 | (0, 0) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 86.0 | (14, 15) P=0.12 | Belief target (14, 15): P=0.12, 29 moves away |
| 2 | (0, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 85.0 | (14, 15) P=0.12 | Belief target (14, 15): P=0.12, 28 moves away |
| 3 | (0, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 84.0 | (14, 15) P=0.12 | Belief target (14, 15): P=0.12, 27 moves away |
| 4 | (1, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 83.0 | (14, 15) P=0.12 | Belief target (14, 15): P=0.12, 26 moves away |
| 5 | (2, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 82.0 | (14, 15) P=0.12 | Belief target (14, 15): P=0.12, 25 moves away |
| 6 | (3, 2) | `SCAN` | `PULSE_SCAN` | 81.0 | (14, 15) P=0.12 | Belief entropy 3.8 bits: scanning from a new vantage point 3 cells from the last scan to triangulate |
| 7 | (3, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 77.0 | (15, 15) P=0.47 | Belief target (15, 15): P=0.47, 25 moves away |
| 8 | (4, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 76.0 | (15, 15) P=0.47 | Belief target (15, 15): P=0.47, 24 moves away |
| 9 | (5, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 75.0 | (15, 15) P=0.47 | Belief target (15, 15): P=0.47, 23 moves away |
| 10 | (6, 2) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 74.0 | (15, 15) P=0.47 | Belief target (15, 15): P=0.47, 22 moves away |
| 11 | (6, 3) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 73.0 | (15, 15) P=0.47 | Belief target (15, 15): P=0.47, 21 moves away |
| … | | | | | | *17 steps omitted* |
| 29 | (12, 14) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 54.0 | (15, 15) P=0.87 | Belief target (15, 15): P=0.87, 4 moves away |
| 30 | (13, 14) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 53.0 | (15, 15) P=0.93 | Belief target (15, 15): P=0.93, 3 moves away |
| 31 | (14, 14) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 52.0 | (15, 15) P=1.00 | EVE sighted at (15, 15): closing in (2 moves) |
| 32 | (14, 15) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 51.0 | (15, 15) P=1.00 | EVE sighted at (15, 15): closing in (1 moves) |

## 6. After-mission evaluation (ground truth, never visible to the agent)
- True EVE position (15, 15), true status ACTIVE
- Localization error of the final estimate: 0.00 cells (expected error under the belief: 0.00)
- Status inference correct: yes · true position inside 90% credible region: yes
