# Original prototype preserved for reference
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

GRID_SIZE = 12

world = np.zeros((GRID_SIZE, GRID_SIZE), dtype=int)

obstacles = [
    (1, 3), (2, 3), (3, 3), (4, 3),
    (5, 6), (6, 6), (7, 6),
    (8, 2), (8, 3), (8, 4),
    (3, 9), (4, 9), (5, 9),
]

for row, col in obstacles:
    world[row, col] = 1

start = (0, 0)
clue = (6, 8)
eve = (10, 10)

fig, ax = plt.subplots(figsize=(8, 8))

cmap = ListedColormap(["#F2F4F7", "#475569"])
ax.imshow(world, cmap=cmap, vmin=0, vmax=1)

ax.scatter(start[1], start[0], color="green", s=180,
           marker="o", label="WALL-E: Start")

ax.scatter(clue[1], clue[0], color="orange", s=180,
           marker="*", label="Signal clue")

ax.scatter(eve[1], eve[0], color="red", s=180,
           marker="X", label="EVE: Hidden target")

ax.set_xticks(np.arange(-0.5, GRID_SIZE, 1))
ax.set_yticks(np.arange(-0.5, GRID_SIZE, 1))
ax.grid(color="white", linewidth=1.5)

ax.set_xlim(-0.5, GRID_SIZE - 0.5)
ax.set_ylim(GRID_SIZE - 0.5, -0.5)
ax.set_xticks(range(GRID_SIZE))
ax.set_yticks(range(GRID_SIZE))

ax.set_title("WALL-E & EVE: World Map (Debug View)")
ax.set_xlabel("Column")
ax.set_ylabel("Row")
ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1))

plt.tight_layout()
if __name__ == "__main__":
    plt.show()
