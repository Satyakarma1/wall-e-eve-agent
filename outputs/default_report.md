# WALL-E Mission Report — Default wasteland sweep

Config `default` · agent `walle` · outcome **SUCCESS** after 24 steps

## 1. Verdict
| Item | Inference |
| :--- | :--- |
| Conclusion | `EVE_FOUND` |
| EVE location | (10, 10) — **observed directly at rendezvous** |
| EVE status | DORMANT — **observed directly** (P(ACTIVE) = 0.00, P(DORMANT) = 1.00) |
| Remaining uncertainty | -0.00 bits of entropy over EVE's location |
| Recommended next step | EVE is DORMANT at (10, 10): stay with her, shield her and keep her beacon logged until pickup. Nearest dock is 20 moves away; battery left 72 is enough to escort her back. |

## 2. Evidence found
1. Step 0 — **Initial signal** received at (0, 0): bearing 140°, strength 0.07; 20 min old at mission start (timestamp 2805-07-14T05:40:00Z).
2. Step 1 — **Pulse scan** from (0, 0): range ~14.4 cells, beacon strength 0.048.
3. Step 9 — **Beacon** (4, 1) decoded: EVE ~10.8 cells away at bearing 124° → P(genuine) = 0.99.
4. Step 22 — **EVE sighted** at (10, 10) by the local camera.
5. Step 24 — **Rendezvous** at (10, 10): EVE status observed as DORMANT.

## 3. Resources and performance
- Steps: 24 (path length 22 cells)
- Battery: 28.0 consumed, 72.0 remaining, 0.0 recharged over 0 dock action(s)
- Pulse scans: 1 · beacons inspected: 1 · beacons sighted: 1 of 1
- Coverage: 17.6% of free cells visited, 45.1% of the map sensed

## 4. Strategy changes
- **Step 0** → `PULSE_SCAN`: Belief entropy 6.4 bits: first pulse scan to measure EVE's range and signal strength
- **Step 1** → `HUNT_BELIEF_TARGET`: Belief target (11, 10): P=0.14, 21 moves away
- **Step 6** → `ACQUIRE_CLUE`: Beacon at (4, 1) not yet decoded (2 moves): going to inspect it
- **Step 9** → `HUNT_BELIEF_TARGET`: Belief target (10, 10): P=0.26, 15 moves away
- **Step 22** → `HUNT_BELIEF_TARGET`: Re-plan after EVE sighted at (10, 10)!: EVE sighted at (10, 10): closing in (2 moves)

## 5. Decision trace
Full trace with every observation, decision and outcome: `default_trace.json`.

| Step | Position | Action | Strategy | Battery | Top candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (0, 0) | `SCAN` | `PULSE_SCAN` | 100.0 | (11, 11) P=0.03 | Belief entropy 6.4 bits: first pulse scan to measure EVE's range and signal strength |
| 1 | (0, 0) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 96.0 | (11, 10) P=0.14 | Belief target (11, 10): P=0.14, 21 moves away |
| 2 | (1, 0) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 95.0 | (11, 10) P=0.14 | Belief target (11, 10): P=0.14, 20 moves away |
| 3 | (1, 1) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 94.0 | (11, 10) P=0.14 | Belief target (11, 10): P=0.14, 19 moves away |
| 4 | (2, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 93.0 | (11, 10) P=0.14 | Belief target (11, 10): P=0.14, 18 moves away |
| 5 | (2, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 92.0 | (11, 10) P=0.14 | Belief target (11, 10): P=0.14, 17 moves away |
| 6 | (3, 2) | `MOVE_LEFT` | `ACQUIRE_CLUE` | 91.0 | (11, 10) P=0.14 | Beacon at (4, 1) not yet decoded (2 moves): going to inspect it |
| 7 | (3, 1) | `MOVE_DOWN` | `ACQUIRE_CLUE` | 90.0 | (11, 10) P=0.14 | Beacon at (4, 1) not yet decoded (1 moves): going to inspect it |
| 8 | (4, 1) | `INSPECT` | `ACQUIRE_CLUE` | 89.0 | (11, 10) P=0.14 | Standing on beacon (4, 1): decoding its signal |
| 9 | (4, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 87.0 | (10, 10) P=0.26 | Belief target (10, 10): P=0.26, 15 moves away |
| 10 | (4, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 86.0 | (10, 10) P=0.26 | Belief target (10, 10): P=0.26, 14 moves away |
| 11 | (5, 2) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 85.0 | (10, 10) P=0.26 | Belief target (10, 10): P=0.26, 13 moves away |
| … | | | | | | *8 steps omitted* |
| 20 | (8, 8) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 76.0 | (10, 10) P=0.26 | Belief target (10, 10): P=0.26, 4 moves away |
| 21 | (8, 9) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 75.0 | (10, 10) P=0.27 | Belief target (10, 10): P=0.27, 3 moves away |
| 22 | (9, 9) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 74.0 | (10, 10) P=1.00 | EVE sighted at (10, 10): closing in (2 moves) |
| 23 | (9, 10) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 73.0 | (10, 10) P=1.00 | EVE sighted at (10, 10): closing in (1 moves) |

## 6. After-mission evaluation (ground truth, never visible to the agent)
- True EVE position (10, 10), true status DORMANT
- Localization error of the final estimate: 0.00 cells (expected error under the belief: 0.00)
- Status inference correct: yes · true position inside 90% credible region: yes
