# WALL-E Mission Report — UNREACHABLE
**Outcome**: `FAILURE_BATTERY` [FAILED]

## Quantitative Performance Metrics
- **Mission Succeeded**: No
- **Total Steps**: 56
- **Path Length Travelled**: 54 cells
- **Battery Consumed**: 60.0 units
- **Battery Remaining**: 0.0 units
- **Pulse Scans Executed**: 1
- **Cells Visited**: 55
- **Exploration Coverage**: 57.89%
- **Clues Discovered**: 1 / 1

## Key Strategy Changes
- **Step 0** -> `PULSE_SCAN`: Entropy high; firing deep radar scan pulse
- **Step 1** -> `HUNT_BELIEF_TARGET`: Belief indicates EVE candidate at (9, 9) (P=0.317)
- **Step 31** -> `ACQUIRE_CLUE`: Navigating to clue at (4, 4)
- **Step 34** -> `HUNT_BELIEF_TARGET`: Belief indicates EVE candidate at (9, 0) (P=0.930)
- **Step 47** -> `EXPLORE_FOR_CLUES`: Exploring toward frontier (7, 1)

## Action Trace (First 15 Steps)
| Step | Position | Action | Strategy | Battery | Top Belief Candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (0, 0) | `SCAN` | `PULSE_SCAN` | 60.0 | (9, 9) P=0.01 | Emitting omnidirectional pulse scan to resolve candidate ambiguity |
| 1 | (0, 0) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 56.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 2 | (0, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 55.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 3 | (0, 2) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 54.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 4 | (0, 3) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 53.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 5 | (0, 4) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 52.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 6 | (0, 5) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 51.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 7 | (0, 6) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 50.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 8 | (0, 7) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 49.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 9 | (0, 8) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 48.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 10 | (0, 9) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 47.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 11 | (1, 9) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 46.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 12 | (2, 9) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 45.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 13 | (3, 9) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 44.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
| 14 | (4, 9) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 43.0 | (9, 9) P=0.317 | Advancing toward top candidate (9, 9) via A* |
*(... and 41 more recorded steps)*