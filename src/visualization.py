"""Static mission summary (PNG) and step-synchronized animated replay (GIF) with Matplotlib + Pillow."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for headless/reproducible rendering
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, Patch
from PIL import Image

from src.frames import STRATEGY_COLORS_LIGHT, STRATEGY_LABELS, STRATEGY_ORDER, mission_frames
from src.simulation import SimulationResult

Coord = Tuple[int, int]

# Reference palette roles (light mode)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8984"
FOG = "#cfcdc6"
FREE = "#f0efec"
VISITED = "#e3e0d6"
OBSTACLE = "#3d3b38"
CRITICAL = "#d03b3b"
GOOD = "#0ca30c"
BELIEF_CMAP = LinearSegmentedColormap.from_list(
    "belief_blue", ["#f7f9fc", "#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)

plt.rcParams.update({
    "font.size": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK_2,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
})


def _cell_grid(rows: int, cols: int, revealed: Dict[Coord, str], visited: set,
               all_obstacles: Optional[set] = None) -> np.ndarray:
    """0 fog, 1 free, 2 visited, 3 sensed obstacle, 4 obstacle never sensed (evaluation view only)."""
    grid = np.zeros((rows, cols))
    for (r, c), kind in revealed.items():
        grid[r, c] = 3 if kind == "OBSTACLE" else (2 if (r, c) in visited else 1)
    for r, c in all_obstacles or ():
        if (r, c) not in revealed:
            grid[r, c] = 4
    return grid


_CELL_CMAP = ListedColormap([FOG, FREE, VISITED, OBSTACLE, "#a8a59d"])


def _setup_map_axis(ax, rows: int, cols: int) -> None:
    ax.set_xlim(-0.5, cols - 0.5)
    ax.set_ylim(rows - 0.5, -0.5)
    ax.set_xticks(range(cols))
    ax.set_yticks(range(rows))
    ax.set_xticks(np.arange(-0.5, cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, rows, 1), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=1.2)
    ax.tick_params(which="both", length=0, labelsize=7)
    ax.set_aspect("equal")


def _draw_segments(ax, segments: List[Tuple[Coord, Coord, str]], alpha: float = 1.0) -> None:
    if not segments:
        return
    lines = [[(a[1], a[0]), (b[1], b[0])] for a, b, _ in segments]
    colors = [STRATEGY_COLORS_LIGHT.get(s, INK_2) for _, _, s in segments]
    ax.add_collection(LineCollection(lines, colors=colors, linewidths=3.0, capstyle="round", alpha=alpha, zorder=4))


def _strategy_legend_handles(strategies: List[str]) -> List[Line2D]:
    used = [s for s in STRATEGY_ORDER if s in strategies]
    return [Line2D([0], [0], color=STRATEGY_COLORS_LIGHT[s], lw=3, label=STRATEGY_LABELS[s]) for s in used]


def _draw_static_markers(ax, gt: Dict[str, Any]) -> None:
    for d in gt["charging_stations"]:
        ax.scatter(d[1], d[0], marker="P", s=170, color=GOOD, edgecolors=SURFACE, linewidths=1.5, zorder=6)
    sr, sc = gt["start_pos"]
    ax.scatter(sc, sr, marker="o", s=150, facecolors="none", edgecolors=INK, linewidths=1.8, zorder=6)


def _draw_beacons(ax, sighted: List[Coord], inspected: List[Coord], flagged: List[Coord]) -> None:
    for pos in sighted:
        if pos in flagged:
            ax.scatter(pos[1], pos[0], marker="*", s=260, color=MUTED, edgecolors=SURFACE, zorder=7)
            ax.scatter(pos[1], pos[0], marker="x", s=150, color=CRITICAL, linewidths=2.5, zorder=8)
        elif pos in inspected:
            ax.scatter(pos[1], pos[0], marker="*", s=260, color=INK, edgecolors=SURFACE, zorder=7)
        else:
            ax.scatter(pos[1], pos[0], marker="*", s=260, facecolors=SURFACE, edgecolors=INK, linewidths=1.3, zorder=7)


def _draw_walle(ax, pos: Coord, strategy: Optional[str]) -> None:
    ax.scatter(pos[1], pos[0], marker="s", s=230, color=INK, edgecolors=SURFACE, linewidths=1.5, zorder=10)
    ax.scatter(pos[1], pos[0], marker="s", s=60, color=STRATEGY_COLORS_LIGHT.get(strategy or "", "#eda100"), zorder=11)


def _draw_eve(ax, pos: Coord, label: Optional[str] = None) -> None:
    ax.scatter(pos[1], pos[0], marker="o", s=230, color="white", edgecolors="#0d366b", linewidths=2.2, zorder=9)
    ax.scatter(pos[1], pos[0], marker="o", s=40, color="#3987e5", zorder=9)
    if label:
        ax.annotate(label, (pos[1], pos[0]), xytext=(6, -12), textcoords="offset points",
                    fontsize=7, color=INK, zorder=12,
                    bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec=MUTED, lw=0.6))


MARKER_LEGEND = [
    Line2D([0], [0], marker="s", color=INK, markerfacecolor=INK, markersize=8, lw=0, label="WALL-E"),
    Line2D([0], [0], marker="o", color="#0d366b", markerfacecolor="white", markersize=8, lw=0, label="EVE"),
    Line2D([0], [0], marker="P", color=GOOD, markersize=9, lw=0, label="Charging dock"),
    Line2D([0], [0], marker="*", color=INK, markersize=11, lw=0, label="Beacon (decoded)"),
    Line2D([0], [0], marker="x", color=CRITICAL, markersize=8, lw=0, markeredgewidth=2, label="Beacon rejected as spoofed"),
    Patch(facecolor=FOG, edgecolor=MUTED, label="Never sensed (fog)"),
]


# =============================================================================
# Static summary
# =============================================================================
def plot_static_mission_summary(
    result: SimulationResult,
    output_path: Union[str, Path] = "outputs/mission_summary.png",
) -> Path:
    """
    After-mission summary: map with strategy-colored path and correctly placed strategy changes,
    plus battery, belief entropy and status/beacon-reliability curves.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    gt = result.ground_truth
    rows, cols = gt["grid_size"]
    frames = mission_frames(result)
    final = frames[-1]
    trace = result.action_trace

    fig = plt.figure(figsize=(17, 12.5))
    gs = fig.add_gridspec(4, 2, width_ratios=[1.3, 1.0], height_ratios=[1, 1, 1, 1.05], hspace=0.5, wspace=0.12)
    ax_map = fig.add_subplot(gs[:, 0])
    ax_batt = fig.add_subplot(gs[0, 1])
    ax_ent = fig.add_subplot(gs[1, 1])
    ax_prob = fig.add_subplot(gs[2, 1])
    ax_list = fig.add_subplot(gs[3, 1])

    # ---------------- map (evaluation view) ----------------
    all_obstacles = {tuple(o) for o in gt["obstacles"]}
    grid = _cell_grid(rows, cols, final["revealed"], set(result.path_taken), all_obstacles)
    ax_map.imshow(grid, cmap=_CELL_CMAP, vmin=-0.5, vmax=4.5, origin="upper")
    _setup_map_axis(ax_map, rows, cols)

    for scan in final["scans"]:
        ax_map.add_patch(Circle((scan["pos"][1], scan["pos"][0]), scan["distance"], fill=False,
                                ls=(0, (3, 3)), lw=0.9, ec=STRATEGY_COLORS_LIGHT["PULSE_SCAN"], alpha=0.55, zorder=3))
        ax_map.scatter(scan["pos"][1], scan["pos"][0], marker="o", s=60, facecolors="none",
                       edgecolors=STRATEGY_COLORS_LIGHT["PULSE_SCAN"], linewidths=2, zorder=8)
    _draw_segments(ax_map, final["segments"])
    _draw_static_markers(ax_map, gt)
    _draw_beacons(ax_map, final["clues_sighted"], final["clues_inspected"], final["flagged_decoys"])

    sighted = set(final["clues_sighted"])
    for clue in gt["clues"]:
        pos = tuple(clue["pos"])
        if pos not in sighted:
            ax_map.scatter(pos[1], pos[0], marker="*", s=200, facecolors="none", edgecolors=MUTED,
                           linewidths=1.2, ls="--", zorder=6)
            kind = "decoy" if clue["type"] == "decoy" else "beacon"
            ax_map.annotate(f"{kind} never found", (pos[1], pos[0]), xytext=(5, 5), textcoords="offset points",
                            fontsize=6.5, color=MUTED)

    eve = tuple(gt["eve_pos"])
    _draw_eve(ax_map, eve, "EVE (true position)" if not result.success else None)
    if not result.success:
        est = tuple(result.inference["map_estimate"])
        ax_map.scatter(est[1], est[0], marker="+", s=420, color="#0d366b", linewidths=2.2, zorder=12)
        ax_map.annotate(f"inferred P={result.inference['map_probability']:.2f}", (est[1], est[0]),
                        xytext=(-60, 12), textcoords="offset points", fontsize=7, color="#0d366b")
    _draw_walle(ax_map, tuple(result.path_taken[-1]), final["strategy"])

    # Strategy changes: numbered badges at the cell WALL-E actually occupied at that step
    stacked: Dict[Coord, int] = {}
    for i, (step, strat, reason) in enumerate(result.strategy_transitions):
        pos = tuple(trace[step]["agent_pos"]) if step < len(trace) else tuple(result.path_taken[-1])
        k = stacked.get(pos, 0)
        stacked[pos] = k + 1
        x, y = pos[1] - 0.3 + 0.3 * (k % 3), pos[0] - 0.3 - 0.3 * (k // 3)
        ax_map.scatter(x, y, marker="o", s=190, color=STRATEGY_COLORS_LIGHT.get(strat, INK_2),
                       edgecolors=SURFACE, linewidths=1.2, zorder=13)
        ax_map.text(x, y, str(i + 1), ha="center", va="center", fontsize=7, color="white", weight="bold", zorder=14)

    ax_list.axis("off")
    ax_list.set_title("Strategy changes (numbers match the map badges)", fontsize=10, loc="left")
    transitions = result.strategy_transitions
    shown = transitions if len(transitions) <= 11 else transitions[:10]
    for i, (step, strat, reason) in enumerate(shown):
        y = 1.0 - i * 0.092
        ax_list.scatter(0.012, y, marker="o", s=150, color=STRATEGY_COLORS_LIGHT.get(strat, INK_2),
                        transform=ax_list.transAxes, clip_on=False)
        ax_list.text(0.012, y, str(i + 1), transform=ax_list.transAxes, ha="center", va="center",
                     fontsize=6.5, color="white", weight="bold")
        text = f"Step {step} · {STRATEGY_LABELS.get(strat, strat)}: {reason}"
        ax_list.text(0.035, y, textwrap.shorten(text, 112, placeholder="…"), transform=ax_list.transAxes,
                     fontsize=7.5, color=INK, va="center")
    if len(transitions) > len(shown):
        ax_list.text(0.035, 1.0 - len(shown) * 0.092, f"… {len(transitions) - len(shown)} more in the report",
                     transform=ax_list.transAxes, fontsize=7.5, color=MUTED, va="center")

    used = sorted({s for _, _, s in final["segments"]} | {s for _, s, _ in result.strategy_transitions})
    ax_map.legend(handles=_strategy_legend_handles(used) + MARKER_LEGEND, loc="upper center",
                  bbox_to_anchor=(0.5, -0.04), ncol=4, fontsize=8, frameon=False)
    ax_map.set_title(f"Mission map — after-mission evaluation view (true EVE and unfound beacons shown)",
                     fontsize=11, loc="left")

    # ---------------- battery ----------------
    steps = [0] + [s["step"] + 1 for s in trace]
    battery = [result.briefing.get("initial_battery", trace[0]["battery"] if trace else 0)] + [s["outcome"]["battery"] for s in trace]
    ax_batt.plot(steps, battery, color=INK, lw=2)
    cap = result.briefing.get("battery_capacity")
    if cap:
        ax_batt.axhline(cap, color=MUTED, lw=1, ls=(0, (4, 3)))
        ax_batt.annotate("capacity", (steps[-1], cap), xytext=(-4, 3), textcoords="offset points",
                         ha="right", fontsize=7, color=MUTED)
    for s in trace:
        if s["action"] == "RECHARGE" and s["outcome"]["recharged"] > 0:
            ax_batt.scatter(s["step"] + 1, s["outcome"]["battery"], marker="P", s=70, color=GOOD, zorder=5)
    for step, strat, _ in result.strategy_transitions:
        if strat == "RETURN_TO_CHARGE":
            ax_batt.axvline(step, color=STRATEGY_COLORS_LIGHT[strat], lw=1.2, ls=(0, (2, 2)))
            ax_batt.annotate("turn back", (step, cap or max(battery)),
                             xytext=(3, -12), textcoords="offset points", fontsize=7, color=INK_2)
    ax_batt.set_title("Battery (dock recharges marked +)", fontsize=10, loc="left")
    ax_batt.set_xlabel("Step")
    ax_batt.set_ylim(0, (cap or max(battery)) * 1.08)
    ax_batt.grid(True, color="#e6e4dd", lw=0.6)

    # ---------------- entropy ----------------
    ent_steps = [s["step"] for s in trace] + [steps[-1]]
    ent = [s["belief_entropy"] for s in trace] + [result.inference["entropy_bits"]]
    ax_ent.plot(ent_steps, ent, color="#2a78d6", lw=2)
    for s in trace:
        if s["action"] in ("SCAN", "INSPECT"):
            nxt = s["step"] + 1
            y = ent[min(nxt, len(ent) - 1)]
            marker = "D" if s["action"] == "SCAN" else "*"
            ax_ent.scatter(nxt, y, marker=marker, s=60 if marker == "D" else 110, color=INK, zorder=5)
    for step, _, reason in result.strategy_transitions:
        if "rejected as spoofed" in reason:
            ax_ent.axvline(step, color=CRITICAL, lw=1.2, ls=(0, (2, 2)))
            ax_ent.annotate("decoy rejected", (step, max(ent)), xytext=(3, -10), textcoords="offset points",
                            fontsize=7, color=CRITICAL)
    ax_ent.set_title("Belief uncertainty: entropy in bits (◆ scan, ★ beacon decoded)", fontsize=10, loc="left")
    ax_ent.set_xlabel("Step")
    ax_ent.set_ylim(bottom=0)
    ax_ent.grid(True, color="#e6e4dd", lw=0.6)

    # ---------------- status and beacon reliability (one probability axis) ----------------
    p_steps = [s["step"] for s in trace]
    p_dormant = [s["status_belief"].get("DORMANT", 0.0) for s in trace]
    ax_prob.plot(p_steps, p_dormant, color=INK, lw=2, label="P(EVE is dormant)")
    beacon_keys = sorted({k for s in trace for k in s["clue_reliability"]})
    dashes = [(0, (5, 2)), (0, (1, 1.5)), (0, (8, 2, 2, 2))]
    for i, key in enumerate(beacon_keys):
        xs = [s["step"] for s in trace if key in s["clue_reliability"]]
        ys = [s["clue_reliability"][key] for s in trace if key in s["clue_reliability"]]
        ax_prob.plot(xs, ys, color=MUTED, lw=1.8, ls=dashes[i % len(dashes)], label=f"P(beacon ({key}) is genuine)")
    ax_prob.set_ylim(-0.03, 1.03)
    ax_prob.legend(loc="center right", fontsize=7.5, frameon=False)
    ax_prob.set_title("Inferred EVE status and beacon reliability", fontsize=10, loc="left")
    ax_prob.set_xlabel("Step")
    ax_prob.grid(True, color="#e6e4dd", lw=0.6)

    inf = result.inference
    verdict = (f"{result.status} · {result.total_steps} steps · battery left {result.battery_remaining:.0f} · "
               f"conclusion {inf['conclusion']} at {tuple(inf['map_estimate'])} · status {inf['status_estimate']} "
               f"({inf['status_confidence']:.0%})")
    fig.suptitle(f"WALL-E & EVE — {result.mission_name or result.config_name}", fontsize=15, weight="bold",
                 x=0.06, ha="left", y=0.985, color=INK)
    fig.text(0.06, 0.945, verdict, fontsize=10, color=GOOD if result.success else CRITICAL, ha="left")

    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return out


# =============================================================================
# Animated GIF
# =============================================================================
def _render_frame(frame: Dict[str, Any], result: SimulationResult, total: int, final_view: bool) -> Image.Image:
    gt = result.ground_truth
    rows, cols = gt["grid_size"]
    fig = plt.figure(figsize=(12.8, 6.6), dpi=80)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.82], left=0.04, right=0.97, top=0.80, bottom=0.12, wspace=0.12)
    ax_map, ax_bel = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])

    grid = _cell_grid(rows, cols, frame["revealed"], set(frame["path"]))
    ax_map.imshow(grid, cmap=_CELL_CMAP, vmin=-0.5, vmax=4.5, origin="upper")
    _setup_map_axis(ax_map, rows, cols)
    _draw_segments(ax_map, frame["segments"])
    _draw_static_markers(ax_map, gt)
    _draw_beacons(ax_map, frame["clues_sighted"], frame["clues_inspected"], frame["flagged_decoys"])

    color = STRATEGY_COLORS_LIGHT.get(frame["strategy"] or "", INK_2)
    if frame["plan"] and len(frame["plan"]) > 1 and not frame["is_final"]:
        plan = [p for p in frame["plan"] if p != frame["pos"]]
        if plan:
            xs = [frame["pos"][1]] + [p[1] for p in plan]
            ys = [frame["pos"][0]] + [p[0] for p in plan]
            ax_map.plot(xs, ys, color=color, lw=1.4, ls=(0, (2, 2)), alpha=0.85, zorder=5)
            ax_map.scatter(plan[-1][1], plan[-1][0], marker="o", s=90, facecolors="none", edgecolors=color, lw=1.6, zorder=5)

    if frame["action"] == "SCAN" and frame["scans"]:
        scan = frame["scans"][-1]
        ax_map.add_patch(Circle((scan["pos"][1], scan["pos"][0]), scan["distance"], fill=False, lw=1.6,
                                ls=(0, (4, 3)), ec=STRATEGY_COLORS_LIGHT["PULSE_SCAN"], zorder=6))
    if frame["action"] == "INSPECT" and frame["decoded"]:
        dec = frame["decoded"][-1]
        (r, c), (dr, dc), d = dec["pos"], dec["vector"], dec["distance"]
        ax_map.add_patch(FancyArrowPatch((c, r), (c + dc * d, r + dr * d), arrowstyle="-|>", mutation_scale=14,
                                         color=STRATEGY_COLORS_LIGHT["ACQUIRE_CLUE"], lw=2, zorder=8))

    if frame["eve_visible"] is not None:
        _draw_eve(ax_map, frame["eve_visible"])
    elif final_view:
        _draw_eve(ax_map, tuple(gt["eve_pos"]), "EVE true position (revealed after mission)")
    _draw_walle(ax_map, frame["pos"], frame["strategy"])

    belief = frame["belief"]
    if belief is not None:
        ax_bel.imshow(belief, cmap=BELIEF_CMAP, vmin=0, vmax=max(float(belief.max()), 1e-9), origin="upper")
        top = frame["top_candidate"]
        ax_bel.scatter(top[1], top[0], marker="+", s=200, color=CRITICAL, linewidths=2)
        _setup_map_axis(ax_bel, rows, cols)
        ax_bel.grid(which="minor", color="white", linewidth=0.6)
        status = frame["status_belief"]
        ax_bel.set_title(
            f"WALL-E's belief over EVE's location · entropy {frame['entropy']:.1f} bits\n"
            f"best guess {tuple(top)} P={frame['top_probability']:.2f} · "
            f"P(active)={status.get('ACTIVE', 0):.2f}  P(dormant)={status.get('DORMANT', 0):.2f}",
            fontsize=9, loc="left",
        )

    step_label = "Start" if frame["step"] is None else f"Step {frame['step']} of {total}"
    strategy = STRATEGY_LABELS.get(frame["strategy"] or "", "Briefing")
    cap = result.briefing.get("battery_capacity", 0)
    fig.text(0.04, 0.955, f"{step_label} · {frame['action']} · {strategy}", fontsize=13, weight="bold", color=INK)
    fig.text(0.04, 0.915, f"Battery {frame['battery']:.0f}/{cap:.0f} · scans left {frame['scan_budget']}",
             fontsize=10, color=INK_2)
    reason = "  ".join(textwrap.wrap(frame["reason"], 150)[:2])
    fig.text(0.04, 0.865, reason, fontsize=9, color=color if frame["strategy"] else INK_2)
    events = "  ·  ".join(frame["events"])[:170]
    if events:
        fig.text(0.04, 0.83, events, fontsize=8.5, color=INK, style="italic")
    if final_view:
        banner = f"Mission end: {result.status} — {result.inference['conclusion']}"
        fig.text(0.97, 0.955, banner, fontsize=12, weight="bold", ha="right",
                 color=GOOD if result.success else CRITICAL)

    handles = _strategy_legend_handles([s for _, _, s in frame["segments"]] + [frame["strategy"] or ""])
    ax_map.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=4, fontsize=7.5, frameon=False)

    fig.canvas.draw()
    image = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert("RGB")
    plt.close(fig)
    return image


def create_animated_mission_gif(
    result: SimulationResult,
    output_path: Union[str, Path] = "outputs/mission_animation.gif",
    duration_per_frame_ms: int = 250,
    hold_final_ms: int = 2500,
) -> Path:
    """One GIF frame per mission step (scans and inspections included), all panels in sync."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    frames = mission_frames(result)
    total = result.total_steps
    images = [_render_frame(f, result, total, final_view=(i == len(frames) - 1)) for i, f in enumerate(frames)]
    durations = [duration_per_frame_ms] * (len(images) - 1) + [hold_final_ms]
    images[0].save(out, save_all=True, append_images=images[1:], duration=durations, loop=0, optimize=True)
    return out
