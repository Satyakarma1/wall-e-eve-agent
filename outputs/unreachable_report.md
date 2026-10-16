# WALL-E Mission Report — EVE sealed behind debris

Config `unreachable` · agent `walle` · outcome **TERMINATED_BY_AGENT** after 21 steps

## 1. Verdict
| Item | Inference |
| :--- | :--- |
| Conclusion | `EVE_UNREACHABLE` |
| EVE location | (9, 9) — P = 0.88, P(within 1 cell) = 1.00, 90% credible region = 2 cell(s) |
| EVE status | ACTIVE — confidence 100% (P(ACTIVE) = 1.00, P(DORMANT) = 0.00) |
| Remaining uncertainty | 0.64 bits of entropy over EVE's location |
| Recommended next step | EVE is almost certainly sealed inside debris near (9, 9) (P=0.88). Next: clear the debris at (7, 9) (the thinnest wall between WALL-E's area and the pocket), or send an aerial unit. |

## 2. Evidence found
1. Step 0 — **Initial signal** received at (0, 0): bearing 130°, strength 0.20; 15 min old at mission start (timestamp 2805-07-14T05:45:00Z).
2. Step 1 — **Pulse scan** from (0, 0): range ~13.2 cells, beacon strength 0.192.
3. Step 10 — **Beacon** (4, 4) decoded: EVE ~7.1 cells away at bearing 135° → P(genuine) = 0.99.

## 3. Resources and performance
- Steps: 21 (path length 18 cells)
- Battery: 24.0 consumed, 36.0 remaining, 0.0 recharged over 0 dock action(s)
- Pulse scans: 1 · beacons inspected: 1 · beacons sighted: 1 of 1
- Coverage: 17.9% of free cells visited, 51.0% of the map sensed

## 4. Strategy changes
- **Step 0** → `PULSE_SCAN`: Belief entropy 6.1 bits: first pulse scan to measure EVE's range and signal strength
- **Step 1** → `HUNT_BELIEF_TARGET`: Belief target (9, 9): P=0.71, 18 moves away
- **Step 9** → `ACQUIRE_CLUE`: Standing on beacon (4, 4): decoding its signal
- **Step 10** → `HUNT_BELIEF_TARGET`: Belief target (9, 9): P=0.88, 10 moves away
- **Step 20** → `ABORT_UNREACHABLE`: EVE most likely at (9, 9) (P=0.88) but only 0.0% of the belief lies in cells WALL-E can reach: debris seals her off. Terminating to save resources.

## 5. Decision trace
Full trace with every observation, decision and outcome: `unreachable_trace.json`.

| Step | Position | Action | Strategy | Battery | Top candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (0, 0) | `SCAN` | `PULSE_SCAN` | 60.0 | (9, 9) P=0.04 | Belief entropy 6.1 bits: first pulse scan to measure EVE's range and signal strength |
| 1 | (0, 0) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 56.0 | (9, 9) P=0.71 | Belief target (9, 9): P=0.71, 18 moves away |
| 2 | (0, 1) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 55.0 | (9, 9) P=0.71 | Belief target (9, 9): P=0.71, 17 moves away |
| 3 | (1, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 54.0 | (9, 9) P=0.71 | Belief target (9, 9): P=0.71, 16 moves away |
| 4 | (1, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 53.0 | (9, 9) P=0.71 | Belief target (9, 9): P=0.71, 15 moves away |
| 5 | (2, 2) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 52.0 | (9, 9) P=0.71 | Belief target (9, 9): P=0.71, 14 moves away |
| 6 | (2, 3) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 51.0 | (9, 9) P=0.71 | Belief target (9, 9): P=0.71, 13 moves away |
| 7 | (3, 3) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 50.0 | (9, 9) P=0.71 | Belief target (9, 9): P=0.71, 12 moves away |
| 8 | (3, 4) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 49.0 | (9, 9) P=0.71 | Belief target (9, 9): P=0.71, 11 moves away |
| 9 | (4, 4) | `INSPECT` | `ACQUIRE_CLUE` | 48.0 | (9, 9) P=0.71 | Standing on beacon (4, 4): decoding its signal |
| 10 | (4, 4) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 46.0 | (9, 9) P=0.88 | Belief target (9, 9): P=0.88, 10 moves away |
| 11 | (4, 5) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 45.0 | (9, 9) P=0.88 | Belief target (9, 9): P=0.88, 9 moves away |
| … | | | | | | *5 steps omitted* |
| 17 | (6, 7) | `MOVE_LEFT` | `HUNT_BELIEF_TARGET` | 39.0 | (9, 9) P=0.88 | Belief target (9, 9): P=0.88, 7 moves away |
| 18 | (6, 6) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 38.0 | (9, 9) P=0.88 | Belief target (9, 9): P=0.88, 6 moves away |
| 19 | (7, 6) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 37.0 | (9, 9) P=0.88 | Belief target (9, 9): P=0.88, 5 moves away |
| 20 | (8, 6) | `TERMINATE` | `ABORT_UNREACHABLE` | 36.0 | (9, 9) P=0.88 | EVE most likely at (9, 9) (P=0.88) but only 0.0% of the belief lies in cells WALL-E can reach: debris seals her off. Terminating to save resources. |

## 6. After-mission evaluation (ground truth, never visible to the agent)
- True EVE position (9, 9), true status ACTIVE
- Localization error of the final estimate: 0.00 cells (expected error under the belief: 0.12)
- Status inference correct: yes · true position inside 90% credible region: yes
