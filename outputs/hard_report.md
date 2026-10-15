# WALL-E Mission Report — HARD
**Outcome**: `SUCCESS` [SUCCESS]

## Quantitative Performance Metrics
- **Mission Succeeded**: Yes
- **Total Steps**: 34
- **Path Length Travelled**: 30 cells
- **Battery Consumed**: 44.0 units
- **Battery Remaining**: 46.0 units
- **Pulse Scans Executed**: 3
- **Cells Visited**: 31
- **Exploration Coverage**: 13.54%
- **Clues Discovered**: 1 / 3

## Key Strategy Changes
- **Step 0** -> `PULSE_SCAN`: Entropy high; firing deep radar scan pulse
- **Step 3** -> `HUNT_BELIEF_TARGET`: Belief indicates EVE candidate at (15, 14) (P=0.228)
- **Step 28** -> `ACQUIRE_CLUE`: Navigating to clue at (12, 14)
- **Step 30** -> `HUNT_BELIEF_TARGET`: Belief indicates EVE candidate at (15, 14) (P=0.479)

## Action Trace (First 15 Steps)
| Step | Position | Action | Strategy | Battery | Top Belief Candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (0, 0) | `SCAN` | `PULSE_SCAN` | 90.0 | (15, 15) P=0.004 | Emitting omnidirectional pulse scan to resolve candidate ambiguity |
| 1 | (0, 0) | `SCAN` | `PULSE_SCAN` | 86.0 | (15, 14) P=0.123 | Emitting omnidirectional pulse scan to resolve candidate ambiguity |
| 2 | (0, 0) | `SCAN` | `PULSE_SCAN` | 82.0 | (14, 14) P=0.124 | Emitting omnidirectional pulse scan to resolve candidate ambiguity |
| 3 | (0, 0) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 78.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 4 | (0, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 77.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 5 | (0, 2) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 76.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 6 | (0, 3) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 75.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 7 | (0, 4) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 74.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 8 | (0, 5) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 73.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 9 | (0, 6) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 72.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 10 | (0, 7) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 71.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 11 | (0, 8) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 70.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 12 | (0, 9) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 69.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 13 | (0, 10) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 68.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
| 14 | (0, 11) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 67.0 | (15, 14) P=0.228 | Advancing toward top candidate (15, 14) via A* |
*(... and 19 more recorded steps)*