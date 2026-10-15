# WALL-E Mission Report — DEFAULT
**Outcome**: `SUCCESS` [SUCCESS]

## Quantitative Performance Metrics
- **Mission Succeeded**: Yes
- **Total Steps**: 27
- **Path Length Travelled**: 22 cells
- **Battery Consumed**: 40.0 units
- **Battery Remaining**: 60.0 units
- **Pulse Scans Executed**: 4
- **Cells Visited**: 23
- **Exploration Coverage**: 17.56%
- **Clues Discovered**: 1 / 1

## Key Strategy Changes
- **Step 0** -> `PULSE_SCAN`: Entropy high; firing deep radar scan pulse
- **Step 4** -> `HUNT_BELIEF_TARGET`: Belief indicates EVE candidate at (11, 9) (P=0.185)
- **Step 19** -> `ACQUIRE_CLUE`: Navigating to clue at (6, 8)
- **Step 21** -> `HUNT_BELIEF_TARGET`: Belief indicates EVE candidate at (10, 10) (P=0.366)

## Action Trace (First 15 Steps)
| Step | Position | Action | Strategy | Battery | Top Belief Candidate | Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | (0, 0) | `SCAN` | `PULSE_SCAN` | 100.0 | (11, 11) P=0.007 | Emitting omnidirectional pulse scan to resolve candidate ambiguity |
| 1 | (0, 0) | `SCAN` | `PULSE_SCAN` | 96.0 | (11, 9) P=0.095 | Emitting omnidirectional pulse scan to resolve candidate ambiguity |
| 2 | (0, 0) | `SCAN` | `PULSE_SCAN` | 92.0 | (11, 8) P=0.096 | Emitting omnidirectional pulse scan to resolve candidate ambiguity |
| 3 | (0, 0) | `SCAN` | `PULSE_SCAN` | 88.0 | (10, 10) P=0.148 | Emitting omnidirectional pulse scan to resolve candidate ambiguity |
| 4 | (0, 0) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 84.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 5 | (0, 1) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 83.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 6 | (0, 2) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 82.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 7 | (0, 3) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 81.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 8 | (0, 4) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 80.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 9 | (0, 5) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 79.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 10 | (0, 6) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 78.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 11 | (0, 7) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 77.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 12 | (0, 8) | `MOVE_RIGHT` | `HUNT_BELIEF_TARGET` | 76.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 13 | (0, 9) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 75.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
| 14 | (1, 9) | `MOVE_DOWN` | `HUNT_BELIEF_TARGET` | 74.0 | (11, 9) P=0.185 | Advancing toward top candidate (11, 9) via A* |
*(... and 12 more recorded steps)*