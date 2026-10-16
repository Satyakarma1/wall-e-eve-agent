# WALL-E Mission Report — Spoofed beacon on the scan ring

Config `decoy` · agent `walle` · outcome **SUCCESS** after 28 steps

## 1. Verdict
| Item | Inference |
| :--- | :--- |
| Conclusion | `EVE_FOUND` |
| EVE location | (4, 14) — **observed directly at rendezvous** |
| EVE status | ACTIVE — **observed directly** (P(ACTIVE) = 1.00, P(DORMANT) = 0.00) |
| Remaining uncertainty | -0.00 bits of entropy over EVE's location |
| Recommended next step | EVE is ACTIVE at (4, 14): hand over the plant and escort her to the dock. Nearest dock is 18 moves away; battery left 92 is enough to escort her back. Ignore beacon(s) (1, 1): judged spoofed. |

## 2. Evidence found
1. Step 0 — **Initial signal** received at (0, 0): strength 0.16; 30 min old at mission start (timestamp 2805-07-14T05:30:00Z).
2. Step 3 — **Beacon** (1, 1) decoded: EVE ~13.3 cells away at bearing 168° → **rejected as spoofed** (P genuine = 0.00).
3. Step 4 — **Pulse scan** from (1, 1): range ~13.1 cells, beacon strength 0.171.
4. Step 8 — **Pulse scan** from (4, 1): range ~12.6 cells, beacon strength 0.177.
5. Step 12 — **Pulse scan** from (4, 4): range ~10.1 cells, beacon strength 0.313.
6. Step 26 — **EVE sighted** at (4, 14) by the local camera.
7. Step 28 — **Rendezvous** at (4, 14): EVE status observed as ACTIVE.

## 3. Resources and performance
- Steps: 28 (path length 24 cells)
- Battery: 38.0 consumed, 92.0 remaining, 0.0 recharged over 0 dock action(s)
- Pulse scans: 3 · beacons inspected: 1 · beacons sighted: 1 of 2
- Coverage: 10.4% of free cells visited, 29.3% of the map sensed

## 4. Strategy changes
- **Step 0** → `ACQUIRE_CLUE`: Beacon at (1, 1) not yet decoded (2 moves): going to inspect it
- **Step 3** → `PULSE_SCAN`: Belief entropy 5.2 bits: first pulse scan to measure EVE's range and signal strength
- **Step 4** → `HUNT_BELIEF_TARGET`: Belief target (14, 4): P=0.17, 16 moves away
- **Step 7** → `PULSE_SCAN`: Belief entropy 4.1 bits: scanning from a new vantage point 3 cells from the last scan to triangulate
- **Step 8** → `HUNT_BELIEF_TARGET`: Beacon (1, 1) rejected as spoofed (P genuine=0.07) -> Belief target (5, 14): P=0.08, 14 moves away
- **Step 11** → `PULSE_SCAN`: Belief entropy 4.9 bits: scanning from a new vantage point 3 cells from the last scan to triangulate
- **Step 12** → `HUNT_BELIEF_TARGET`: Belief target (4, 14): P=0.12, 10 moves away
- **Step 26** → `HUNT_BELIEF_TARGET`: Re-plan after EVE sighted at (4, 14)!: EVE sighted at (4, 14): closing in (2 moves)

## 5. Decision trace
Full trace with every observation, decision and outcome: `decoy_trace.json`.

| Step | Position | Action | Strategy | Battery | Top candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (0, 0) | `MOVE_RIGHT` | `ACQUIRE_CLUE` | 130.0 | (8, 12) P=0.01 | Beacon at (1, 1) not yet decoded (2 moves): going to inspect it |
| 1 | (0, 1) | `MOVE_DOWN` | `ACQUIRE_CLUE` | 129.0 | (8, 12) P=0.01 | Beacon at (1, 1) not yet decoded (1 moves): going to inspect it |
| 2 | (1, 1) | `INSPECT` | `ACQUIRE_CLUE` | 128.0 | (8, 12) P=0.01 | Standing on beacon (1, 1): decoding its signal |
| 3 | (1, 1) | `SCAN` | `PULSE_SCAN` | 126.0 | (14, 4) P=0.12 | Belief entropy 5.2 bits: first pulse scan to measure EVE's range and signal strength |
| 4 | (1, 1) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 122.0 | (14, 4) P=0.17 | Belief target (14, 4): P=0.17, 16 moves away |
| 5 | (2, 1) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 121.0 | (14, 4) P=0.17 | Belief target (14, 4): P=0.17, 15 moves away |
| 6 | (3, 1) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 120.0 | (14, 4) P=0.17 | Belief target (14, 4): P=0.17, 14 moves away |
| 7 | (4, 1) | `SCAN` | `PULSE_SCAN` | 119.0 | (14, 4) P=0.17 | Belief entropy 4.1 bits: scanning from a new vantage point 3 cells from the last scan to triangulate |
| 8 | (4, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 115.0 | (5, 14) P=0.08 | Belief target (5, 14): P=0.08, 14 moves away |
| 9 | (4, 2) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 114.0 | (5, 14) P=0.08 | Belief target (5, 14): P=0.08, 13 moves away |
| 10 | (4, 3) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 113.0 | (5, 14) P=0.08 | Belief target (5, 14): P=0.08, 12 moves away |
| 11 | (4, 4) | `SCAN` | `PULSE_SCAN` | 112.0 | (5, 14) P=0.08 | Belief entropy 4.9 bits: scanning from a new vantage point 3 cells from the last scan to triangulate |
| … | | | | | | *12 steps omitted* |
| 24 | (2, 12) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 96.0 | (5, 14) P=0.13 | Belief target (4, 14): P=0.12, 4 moves away |
| 25 | (2, 13) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 95.0 | (5, 14) P=0.15 | Belief target (4, 14): P=0.15, 3 moves away |
| 26 | (3, 13) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 94.0 | (4, 14) P=1.00 | EVE sighted at (4, 14): closing in (2 moves) |
| 27 | (3, 14) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 93.0 | (4, 14) P=1.00 | EVE sighted at (4, 14): closing in (1 moves) |

## 6. After-mission evaluation (ground truth, never visible to the agent)
- True EVE position (4, 14), true status ACTIVE
- Localization error of the final estimate: 0.00 cells (expected error under the belief: 0.00)
- Status inference correct: yes · true position inside 90% credible region: yes
- Decoy beacons: (1, 1) · inspected: (1, 1) · flagged as spoofed: (1, 1)
