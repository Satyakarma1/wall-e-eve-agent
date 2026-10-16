# WALL-E Mission Report — Low battery: sorties from the dock

Config `recharge` · agent `walle` · outcome **SUCCESS** after 87 steps

## 1. Verdict
| Item | Inference |
| :--- | :--- |
| Conclusion | `EVE_FOUND` |
| EVE location | (12, 11) — **observed directly at rendezvous** |
| EVE status | DORMANT — **observed directly** (P(ACTIVE) = 0.00, P(DORMANT) = 1.00) |
| Remaining uncertainty | -0.00 bits of entropy over EVE's location |
| Recommended next step | EVE is DORMANT at (12, 11): stay with her, shield her and keep her beacon logged until pickup. Nearest dock is 16 moves away; battery left 24 is enough to escort her back. |

## 2. Evidence found
1. Step 0 — **Initial signal** received at (7, 0): strength 0.12; 120 min old at mission start (timestamp 2805-07-14T04:00:00Z).
2. Step 1 — **Pulse scan** from (7, 0): range ~11.3 cells, beacon strength 0.062.
3. Step 85 — **EVE sighted** at (12, 11) by the local camera.
4. Step 87 — **Rendezvous** at (12, 11): EVE status observed as DORMANT.

## 3. Resources and performance
- Steps: 87 (path length 82 cells)
- Battery: 86.0 consumed, 24.0 remaining, 70.0 recharged over 4 dock action(s)
- Pulse scans: 1 · beacons inspected: 0 · beacons sighted: 0 of 0
- Coverage: 32.2% of free cells visited, 62.8% of the map sensed

## 4. Strategy changes
- **Step 0** → `PULSE_SCAN`: Belief entropy 7.4 bits: first pulse scan to measure EVE's range and signal strength
- **Step 1** → `HUNT_BELIEF_TARGET`: Belief target (7, 12): P=0.03, 12 moves away
- **Step 17** → `RETURN_TO_CHARGE`: Turning back to dock (7, 0) (14 moves): battery 20 < 21 needed to reach (11, 11) (3) and return to a dock (15) with reserve
- **Step 33** → `HUNT_BELIEF_TARGET`: Belief target (2, 11): P=0.05, 16 moves away
- **Step 52** → `RETURN_TO_CHARGE`: Turning back to dock (7, 0) (17 moves): battery 21 < 26 needed to reach (10, 12) (8) and return to a dock (15) with reserve
- **Step 71** → `HUNT_BELIEF_TARGET`: Belief target (12, 11): P=0.09, 16 moves away
- **Step 85** → `HUNT_BELIEF_TARGET`: Re-plan after EVE sighted at (12, 11)!: EVE sighted at (12, 11): closing in (2 moves)

## 5. Decision trace
Full trace with every observation, decision and outcome: `recharge_trace.json`.

| Step | Position | Action | Strategy | Battery | Top candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (7, 0) | `SCAN` | `PULSE_SCAN` | 40.0 | (0, 13) P=0.01 | Belief entropy 7.4 bits: first pulse scan to measure EVE's range and signal strength |
| 1 | (7, 0) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 36.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 12 moves away |
| 2 | (7, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 35.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 11 moves away |
| 3 | (7, 2) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 34.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 10 moves away |
| 4 | (7, 3) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 33.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 9 moves away |
| 5 | (7, 4) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 32.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 8 moves away |
| 6 | (7, 5) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 31.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 7 moves away |
| 7 | (7, 6) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 30.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 6 moves away |
| 8 | (7, 7) | `MOVE_UP` | `HUNT_BELIEF_TARGET` | 29.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 9 moves away |
| 9 | (6, 7) | `MOVE_UP` | `HUNT_BELIEF_TARGET` | 28.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 8 moves away |
| 10 | (5, 7) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 27.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 7 moves away |
| 11 | (5, 8) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 26.0 | (7, 12) P=0.03 | Belief target (7, 12): P=0.03, 6 moves away |
| … | | | | | | *71 steps omitted* |
| 83 | (10, 9) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 28.0 | (12, 11) P=0.09 | Belief target (12, 11): P=0.09, 4 moves away |
| 84 | (10, 10) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 27.0 | (12, 11) P=0.11 | Belief target (12, 11): P=0.11, 3 moves away |
| 85 | (11, 10) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 26.0 | (12, 11) P=1.00 | EVE sighted at (12, 11): closing in (2 moves) |
| 86 | (11, 11) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 25.0 | (12, 11) P=1.00 | EVE sighted at (12, 11): closing in (1 moves) |

## 6. After-mission evaluation (ground truth, never visible to the agent)
- True EVE position (12, 11), true status DORMANT
- Localization error of the final estimate: 0.00 cells (expected error under the belief: 0.00)
- Status inference correct: yes · true position inside 90% credible region: yes
