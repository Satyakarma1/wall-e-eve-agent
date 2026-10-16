# WALL-E Mission Report — Noisy sensors (same map as default)

Config `noisy` · agent `walle` · outcome **SUCCESS** after 26 steps

## 1. Verdict
| Item | Inference |
| :--- | :--- |
| Conclusion | `EVE_FOUND` |
| EVE location | (10, 10) — **observed directly at rendezvous** |
| EVE status | ACTIVE — **observed directly** (P(ACTIVE) = 1.00, P(DORMANT) = 0.00) |
| Remaining uncertainty | -0.00 bits of entropy over EVE's location |
| Recommended next step | EVE is ACTIVE at (10, 10): hand over the plant and escort her to the dock. Nearest dock is 20 moves away; battery left 64 is enough to escort her back. |

## 2. Evidence found
1. Step 0 — **Initial signal** received at (0, 0): bearing 120°, strength 0.20; 60 min old at mission start (timestamp 2805-07-14T05:00:00Z).
2. Step 1 — **Pulse scan** from (0, 0): range ~14.6 cells, beacon strength 0.129.
3. Step 9 — **Beacon** (4, 1) decoded: EVE ~11.9 cells away at bearing 142° → P(genuine) = 0.98.
4. Step 10 — **Pulse scan** from (4, 1): range ~7.9 cells, beacon strength 0.207.
5. Step 15 — **Pulse scan** from (5, 4): range ~8.0 cells, beacon strength 0.364.
6. Step 25 — **EVE sighted** at (10, 10) by the local camera.
7. Step 26 — **Rendezvous** at (10, 10): EVE status observed as ACTIVE.

## 3. Resources and performance
- Steps: 26 (path length 22 cells)
- Battery: 36.0 consumed, 64.0 remaining, 0.0 recharged over 0 dock action(s)
- Pulse scans: 3 · beacons inspected: 1 · beacons sighted: 1 of 1
- Coverage: 17.6% of free cells visited, 45.8% of the map sensed

## 4. Strategy changes
- **Step 0** → `PULSE_SCAN`: Belief entropy 7.0 bits: first pulse scan to measure EVE's range and signal strength
- **Step 1** → `HUNT_BELIEF_TARGET`: Belief target (10, 11): P=0.11, 21 moves away
- **Step 6** → `ACQUIRE_CLUE`: Beacon at (4, 1) not yet decoded (2 moves): going to inspect it
- **Step 9** → `PULSE_SCAN`: Belief entropy 3.5 bits: scanning from a new vantage point 4 cells from the last scan to triangulate
- **Step 10** → `HUNT_BELIEF_TARGET`: Belief target (11, 10): P=0.17, 16 moves away
- **Step 14** → `PULSE_SCAN`: Belief entropy 3.6 bits: scanning from a new vantage point 3 cells from the last scan to triangulate
- **Step 15** → `HUNT_BELIEF_TARGET`: Belief target (11, 9): P=0.20, 11 moves away
- **Step 25** → `HUNT_BELIEF_TARGET`: Re-plan after EVE sighted at (10, 10)!: EVE sighted at (10, 10): closing in (1 moves)

## 5. Decision trace
Full trace with every observation, decision and outcome: `noisy_trace.json`.

| Step | Position | Action | Strategy | Battery | Top candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (0, 0) | `SCAN` | `PULSE_SCAN` | 100.0 | (6, 11) P=0.01 | Belief entropy 7.0 bits: first pulse scan to measure EVE's range and signal strength |
| 1 | (0, 0) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 96.0 | (10, 11) P=0.10 | Belief target (10, 11): P=0.11, 21 moves away |
| 2 | (0, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 95.0 | (10, 11) P=0.10 | Belief target (10, 11): P=0.11, 20 moves away |
| 3 | (0, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 94.0 | (10, 11) P=0.10 | Belief target (10, 11): P=0.11, 19 moves away |
| 4 | (1, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 93.0 | (10, 11) P=0.10 | Belief target (10, 11): P=0.11, 18 moves away |
| 5 | (2, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 92.0 | (10, 11) P=0.10 | Belief target (10, 11): P=0.11, 17 moves away |
| 6 | (3, 2) | `MOVE_LEFT` | `ACQUIRE_CLUE` | 91.0 | (10, 11) P=0.10 | Beacon at (4, 1) not yet decoded (2 moves): going to inspect it |
| 7 | (3, 1) | `MOVE_DOWN` | `ACQUIRE_CLUE` | 90.0 | (10, 11) P=0.10 | Beacon at (4, 1) not yet decoded (1 moves): going to inspect it |
| 8 | (4, 1) | `INSPECT` | `ACQUIRE_CLUE` | 89.0 | (10, 11) P=0.10 | Standing on beacon (4, 1): decoding its signal |
| 9 | (4, 1) | `SCAN` | `PULSE_SCAN` | 87.0 | (11, 10) P=0.18 | Belief entropy 3.5 bits: scanning from a new vantage point 4 cells from the last scan to triangulate |
| 10 | (4, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 83.0 | (11, 10) P=0.17 | Belief target (11, 10): P=0.17, 16 moves away |
| 11 | (4, 2) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 82.0 | (11, 10) P=0.17 | Belief target (11, 10): P=0.17, 15 moves away |
| … | | | | | | *10 steps omitted* |
| 22 | (9, 7) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 68.0 | (11, 9) P=0.20 | Belief target (11, 9): P=0.20, 4 moves away |
| 23 | (9, 8) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 67.0 | (11, 9) P=0.21 | Belief target (11, 9): P=0.21, 3 moves away |
| 24 | (10, 8) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 66.0 | (11, 10) P=0.26 | Belief target (11, 10): P=0.26, 3 moves away |
| 25 | (10, 9) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 65.0 | (10, 10) P=1.00 | EVE sighted at (10, 10): closing in (1 moves) |

## 6. After-mission evaluation (ground truth, never visible to the agent)
- True EVE position (10, 10), true status ACTIVE
- Localization error of the final estimate: 0.00 cells (expected error under the belief: 0.00)
- Status inference correct: yes · true position inside 90% credible region: yes
