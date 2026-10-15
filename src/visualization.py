"""High-resolution static and animated visualizations using Matplotlib and Pillow."""

from __future__ import annotations
import math
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, Union
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless/reproducible rendering
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, Normalize
import matplotlib.patches as patches
import numpy as np
from PIL import Image

from src.simulation import SimulationResult
from src.environment import Coord


def plot_static_mission_summary(
    result: SimulationResult,
    output_path: Union[str, Path] = "outputs/mission_summary.png"
) -> Path:
    """
    Generate a 4-panel comprehensive mission summary figure:
    1. Grid World Map with Trajectory, Obstacles, Clues, and Strategy Callouts.
    2. Battery Consumption Curve over Steps.
    3. Belief Entropy Reduction Curve over Steps.
    4. Final Posterior Belief Heatmap.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    gt = result.ground_truth
    rows, cols = gt["grid_size"]
    obstacles = {tuple(o) for o in gt["obstacles"]}
    eve_pos = tuple(gt["eve_pos"])
    start_pos = tuple(gt["start_pos"])

    fig = plt.figure(figsize=(16, 12), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.3, 1.0], height_ratios=[1.0, 1.0])

    ax_map = fig.add_subplot(gs[:, 0])
    ax_batt = fig.add_subplot(gs[0, 1])
    ax_entropy = fig.add_subplot(gs[1, 1])

    # -------------------------------------------------------------
    # 1. Main Map Visualization
    # -------------------------------------------------------------
    # Grid background matrix: 0: unvisited free, 1: obstacle, 2: visited free
    bg = np.zeros((rows, cols), dtype=float)
    visited_set = set(result.path_taken)
    for r in range(rows):
        for c in range(cols):
            if (r, c) in obstacles:
                bg[r, c] = 1.0  # Obstacle
            elif (r, c) in visited_set:
                bg[r, c] = 0.5  # Visited free cell
            else:
                bg[r, c] = 0.0  # Unvisited free cell

    custom_cmap = ListedColormap(["#F8FAFC", "#CBD5E1", "#334155"])
    norm = Normalize(vmin=0.0, vmax=1.0)
    ax_map.imshow(bg, cmap=custom_cmap, norm=norm, origin="upper")

    # Grid lines
    ax_map.set_xticks(np.arange(-0.5, cols, 1), minor=True)
    ax_map.set_yticks(np.arange(-0.5, rows, 1), minor=True)
    ax_map.grid(which="minor", color="#94A3B8", linestyle="-", linewidth=0.8, alpha=0.5)
    ax_map.tick_params(which="minor", size=0)

    # Major ticks
    ax_map.set_xticks(range(cols))
    ax_map.set_yticks(range(rows))
    ax_map.set_xlim(-0.5, cols - 0.5)
    ax_map.set_ylim(rows - 0.5, -0.5)

    # Plot travelled path
    path = result.path_taken
    if len(path) > 1:
        path_r = [p[0] for p in path]
        path_c = [p[1] for p in path]
        ax_map.plot(
            path_c, path_r,
            color="#2563EB", linestyle="--", linewidth=2.5, alpha=0.8,
            label="Travelled Path", zorder=3
        )
        # Directional arrows along the path
        for i in range(len(path) - 1):
            r1, c1 = path[i]
            r2, c2 = path[i + 1]
            if r1 != r2 or c1 != c2:
                ax_map.annotate(
                    "",
                    xy=(c2, r2),
                    xytext=(c1, r1),
                    arrowprops=dict(
                        arrowstyle="-|>",
                        color="#1D4ED8",
                        lw=1.5,
                        mutation_scale=12,
                        shrinkA=8,
                        shrinkB=8,
                    ),
                    zorder=4
                )

    # Plot Start, Clues, and EVE
    ax_map.scatter(
        start_pos[1], start_pos[0],
        color="#16A34A", s=280, marker="o", edgecolors="black", linewidth=2,
        label=f"WALL-E Start ({start_pos[0]}, {start_pos[1]})", zorder=6
    )

    # Discovered / Visited clues
    clue_dict = gt["clues"]
    for c_str in clue_dict.keys():
        # parse key like "(6, 8)"
        c_tuple = tuple(map(int, c_str.strip("()").split(",")))
        is_disc = c_tuple in visited_set
        ax_map.scatter(
            c_tuple[1], c_tuple[0],
            color="#EA580C" if is_disc else "#CA8A04",
            s=260, marker="*", edgecolors="black", linewidth=1.5,
            label=f"Clue Beacon {'(Inspected)' if is_disc else '(Unvisited)'}",
            zorder=6
        )

    # EVE Position
    ax_map.scatter(
        eve_pos[1], eve_pos[0],
        color="#DC2626", s=280, marker="X", edgecolors="black", linewidth=2,
        label=f"EVE Target ({eve_pos[0]}, {eve_pos[1]})", zorder=6
    )

    # Strategy change annotations on the map
    # Annotate up to 4 key transitions to keep the map readable
    transition_count = 0
    for step_num, strat, reason in result.strategy_transitions:
        if transition_count >= 5:
            break
        # Find position at this step
        if step_num < len(path):
            pr, pc = path[step_num]
            ax_map.annotate(
                f"S{step_num}: {strat}",
                xy=(pc, pr),
                xytext=(pc + 0.35, pr - 0.4),
                bbox=dict(boxstyle="round,pad=0.2", fc="#FEF3C7", ec="#D97706", lw=1.2, alpha=0.9),
                fontsize=8,
                weight="bold",
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.2", color="#D97706"),
                zorder=7
            )
            transition_count += 1

    outcome_color = "#15803D" if result.success else "#B91C1C"
    ax_map.set_title(
        f"Mission Map: [{result.status}] — Steps: {result.total_steps} | Coverage: {result.exploration_coverage_pct}%",
        fontsize=13, weight="bold", color=outcome_color
    )
    ax_map.set_xlabel("Grid Column", fontsize=11)
    ax_map.set_ylabel("Grid Row", fontsize=11)
    ax_map.legend(loc="upper left", bbox_to_anchor=(0.0, -0.08), ncol=2, fontsize=9)

    # -------------------------------------------------------------
    # 2. Battery Consumption Curve
    # -------------------------------------------------------------
    steps = [e["step"] for e in result.action_trace]
    batteries = [e["battery"] for e in result.action_trace]
    ax_batt.plot(steps, batteries, color="#D97706", linewidth=2.5, label="Battery Remaining")
    ax_batt.fill_between(steps, batteries, 0, color="#FEF3C7", alpha=0.4)
    ax_batt.set_title("Resource Depletion: Battery vs Step", fontsize=12, weight="bold")
    ax_batt.set_xlabel("Simulation Step", fontsize=10)
    ax_batt.set_ylabel("Battery Level", fontsize=10)
    ax_batt.grid(True, linestyle=":", alpha=0.6)
    ax_batt.set_ylim(0, max(batteries, default=100) * 1.05)
    ax_batt.legend(loc="upper right", fontsize=9)

    # -------------------------------------------------------------
    # 3. Belief Entropy Reduction Curve
    # -------------------------------------------------------------
    entropies = [e["belief_entropy"] for e in result.action_trace]
    ax_entropy.plot(steps, entropies, color="#7C3AED", linewidth=2.5, label="Shannon Entropy H(B)")
    ax_entropy.fill_between(steps, entropies, 0, color="#EDE9FE", alpha=0.4)

    # Mark clue inspections or scans on entropy curve
    for e in result.action_trace:
        if e["action"] == "INSPECT":
            ax_entropy.scatter(
                e["step"], e["belief_entropy"],
                color="#EA580C", s=80, marker="*", zorder=5, label="Clue Inspected"
            )
        elif e["action"] == "SCAN":
            ax_entropy.scatter(
                e["step"], e["belief_entropy"],
                color="#2563EB", s=60, marker="D", zorder=5, label="Radar Scan"
            )

    ax_entropy.set_title("Belief Uncertainty: Shannon Entropy vs Step", fontsize=12, weight="bold")
    ax_entropy.set_xlabel("Simulation Step", fontsize=10)
    ax_entropy.set_ylabel("Entropy (bits)", fontsize=10)
    ax_entropy.grid(True, linestyle=":", alpha=0.6)

    # Deduplicate legend items
    handles, labels = ax_entropy.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax_entropy.legend(by_label.values(), by_label.keys(), loc="upper right", fontsize=9)

    fig.suptitle(
        f"WALL-E & EVE Autonomous Mission Summary — {result.config_name.upper()}\n"
        f"Result: {result.status} | Steps: {result.total_steps} | Battery Remaining: {result.battery_remaining}",
        fontsize=15, weight="bold", y=1.02
    )

    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def create_animated_mission_gif(
    result: SimulationResult,
    output_path: Union[str, Path] = "outputs/mission_animation.gif",
    duration_per_frame_ms: int = 250
) -> Path:
    """
    Generate an animated GIF showing the mission execution frame-by-frame:
    - Left Panel: Dynamic agent movement, explored path, obstacle map.
    - Right Panel: Dynamic Bayesian belief heatmap shifting as evidence is gathered.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    gt = result.ground_truth
    rows, cols = gt["grid_size"]
    obstacles = {tuple(o) for o in gt["obstacles"]}
    eve_pos = tuple(gt["eve_pos"])
    start_pos = tuple(gt["start_pos"])
    path = result.path_taken
    trace = result.action_trace
    belief_hist = result.belief_history

    frames: List[Image.Image] = []

    # Frame generation loop
    total_frames = len(path)
    for t in range(total_frames):
        current_pos = path[t]
        visited_so_far = set(path[:t + 1])

        fig, (ax_grid, ax_heat) = plt.subplots(1, 2, figsize=(14, 7), constrained_layout=True)

        # ---------------- Grid Map ----------------
        bg = np.zeros((rows, cols), dtype=float)
        for r in range(rows):
            for c in range(cols):
                if (r, c) in obstacles:
                    bg[r, c] = 1.0  # Obstacle
                elif (r, c) in visited_so_far:
                    bg[r, c] = 0.5  # Visited
                else:
                    bg[r, c] = 0.0  # Unexplored

        custom_cmap = ListedColormap(["#F8FAFC", "#E2E8F0", "#334155"])
        ax_grid.imshow(bg, cmap=custom_cmap, norm=Normalize(0.0, 1.0), origin="upper")

        ax_grid.set_xticks(range(cols))
        ax_grid.set_yticks(range(rows))
        ax_grid.set_xlim(-0.5, cols - 0.5)
        ax_grid.set_ylim(rows - 0.5, -0.5)
        ax_grid.grid(color="#94A3B8", linestyle=":", linewidth=0.8, alpha=0.5)

        # Draw travelled path up to step t
        if t > 0:
            hist_r = [p[0] for p in path[:t + 1]]
            hist_c = [p[1] for p in path[:t + 1]]
            ax_grid.plot(hist_c, hist_r, color="#3B82F6", linestyle="--", linewidth=2.0, alpha=0.8)

        # Start position
        ax_grid.scatter(start_pos[1], start_pos[0], color="#16A34A", s=200, marker="o", edgecolors="black", label="Start")

        # Clues
        for c_str in gt["clues"].keys():
            c_tuple = tuple(map(int, c_str.strip("()").split(",")))
            is_found = c_tuple in visited_so_far
            ax_grid.scatter(
                c_tuple[1], c_tuple[0],
                color="#EA580C" if is_found else "#CBD5E1",
                s=220, marker="*", edgecolors="black",
                label="Clue (Found)" if is_found else "Clue (Hidden)"
            )

        # WALL-E current position
        ax_grid.scatter(
            current_pos[1], current_pos[0],
            color="#F59E0B", s=320, marker="s", edgecolors="black", linewidth=2,
            label="WALL-E (Current)", zorder=10
        )

        # Show EVE only if reached or mission finished
        if t == total_frames - 1 or current_pos == eve_pos:
            ax_grid.scatter(
                eve_pos[1], eve_pos[0],
                color="#DC2626", s=280, marker="X", edgecolors="black", linewidth=2,
                label="EVE (Target)", zorder=9
            )

        # Step trace metadata
        step_rec = trace[min(t, len(trace) - 1)] if trace else {}
        action_name = step_rec.get("action", "START")
        strategy_name = step_rec.get("strategy", "EXPLORATION")
        battery_now = step_rec.get("battery", 100.0)

        ax_grid.set_title(
            f"Step {t}/{total_frames - 1} | Action: {action_name}\n"
            f"Strategy: {strategy_name} | Battery: {battery_now:.1f}",
            fontsize=11, weight="bold"
        )
        ax_grid.legend(loc="upper left", bbox_to_anchor=(0.0, -0.05), ncol=3, fontsize=8)

        # ---------------- Bayesian Belief Heatmap ----------------
        belief_grid = belief_hist[min(t, len(belief_hist) - 1)]
        im_heat = ax_heat.imshow(belief_grid, cmap="inferno", origin="upper")
        ax_heat.set_title(
            f"Bayesian Belief Distribution P(EVE = (r, c))\n"
            f"Max Prob: {np.max(belief_grid):.3f} | Top Cand: {divmod(int(np.argmax(belief_grid)), cols)}",
            fontsize=11, weight="bold"
        )
        ax_heat.set_xticks(range(cols))
        ax_heat.set_yticks(range(rows))
        ax_heat.set_xlim(-0.5, cols - 0.5)
        ax_heat.set_ylim(rows - 0.5, -0.5)
        plt.colorbar(im_heat, ax=ax_heat, fraction=0.046, pad=0.04)

        # Render figure to canvas and convert to PIL Image
        fig.canvas.draw()
        rgba_arr = np.asarray(fig.canvas.buffer_rgba())
        frame_img = Image.fromarray(rgba_arr, mode="RGBA").convert("RGB")
        frames.append(frame_img)
        plt.close(fig)

    # Save animated GIF via Pillow
    if frames:
        frames[0].save(
            out,
            save_all=True,
            append_images=frames[1:],
            duration=duration_per_frame_ms,
            loop=0
        )

    return out
