"""Generalization benchmark: many seeded random missions x sensing conditions x agents.

Every agent faces exactly the same missions (same seeds); conditions only change evidence quality
(noise) or add a spoofed beacon. Success rates carry 95% Wilson intervals; means carry 95% CIs.
These are simulated missions, so the numbers describe this simulator, not real robots.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.mission_generator import generate_mission
from src.simulation import run_mission

CONDITIONS: Dict[str, Dict[str, Any]] = {
    "clean": {},
    "noisy": {"noisy": True},
    "decoy": {"n_decoys": 1},
    "noisy+decoy": {"noisy": True, "n_decoys": 1},
}
AGENTS: Dict[str, str] = {
    "walle": "WALL-E (robust Bayesian)",
    "naive": "WALL-E naive (trusts every beacon)",
    "baseline": "Frontier sweep (ignores signals)",
}
# Reference categorical palette, slots 1-3 (validated all-pairs for up to three series)
AGENT_COLORS = {"walle": "#2a78d6", "naive": "#eb6834", "baseline": "#1baf7a"}
SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e4dd"


def wilson_interval(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """95% Wilson score interval for a proportion (well-behaved at 0% and 100%)."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _mean_ci(values: List[float]) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    arr = np.asarray(values, dtype=float)
    half = 1.96 * arr.std(ddof=1) / math.sqrt(len(arr)) if len(arr) > 1 else 0.0
    return (float(arr.mean()), float(half))


def run_trial(config: Dict[str, Any], agent: str, condition: str) -> Dict[str, Any]:
    """Run one mission and keep the metrics needed for the benchmark."""
    r = run_mission(config, agent_type=agent, record_belief_history=False)
    ev = r.evaluation
    return {
        "condition": condition,
        "agent": agent,
        "seed": config["random_seed"],
        "grid": "x".join(str(v) for v in config["grid_size"]),
        "status": r.status,
        "success": r.success,
        "steps": r.total_steps,
        "battery_used": r.battery_used,
        "recharges": r.recharge_count,
        "scans": r.scan_count,
        "inspects": r.inspect_count,
        "conclusion": r.inference["conclusion"],
        "localization_error": ev["localization_error"],
        "status_correct": ev["status_correct"],
        "status_inference_correct": ev["status_inference_correct"],
        "decoys": len(ev["decoys"]),
        "decoys_inspected": len(ev["decoys_inspected"]),
        "decoys_flagged": len(ev["decoys_flagged"]),
        "genuine_flagged": len(ev["genuine_flagged"]),
    }


def run_benchmark(
    n_missions: int = 60,
    seed_offset: int = 1000,
    conditions: Optional[Dict[str, Dict[str, Any]]] = None,
    agents: Optional[List[str]] = None,
    progress: Optional[Callable[[int, int], None]] = None,
) -> List[Dict[str, Any]]:
    """Every agent x condition on the same seeded random missions."""
    conditions = conditions or CONDITIONS
    agents = agents or list(AGENTS)
    total = len(conditions) * n_missions * len(agents)
    records: List[Dict[str, Any]] = []
    for condition, params in conditions.items():
        for i in range(n_missions):
            config = generate_mission(seed_offset + i, **params)
            for agent in agents:
                records.append(run_trial(config, agent, condition))
                if progress:
                    progress(len(records), total)
    return records


def aggregate(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Summary statistics per condition and agent."""
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for rec in records:
        out.setdefault(rec["condition"], {}).setdefault(rec["agent"], {"_rows": []})["_rows"].append(rec)
    for condition, by_agent in out.items():
        for agent, cell in by_agent.items():
            rows = cell.pop("_rows")
            n = len(rows)
            k = sum(r["success"] for r in rows)
            lo, hi = wilson_interval(k, n)
            steps, steps_ci = _mean_ci([r["steps"] for r in rows])
            battery, battery_ci = _mean_ci([r["battery_used"] for r in rows])
            err, err_ci = _mean_ci([r["localization_error"] for r in rows])
            inspected = sum(r["decoys_inspected"] for r in rows)
            cell.update({
                "label": AGENTS.get(agent, agent),
                "missions": n,
                "successes": k,
                "success_rate": round(k / n, 4) if n else 0.0,
                "success_ci95": [round(lo, 4), round(hi, 4)],
                "mean_steps": round(steps, 2),
                "steps_ci95": round(steps_ci, 2),
                "median_steps_success": float(np.median([r["steps"] for r in rows if r["success"]])) if k else None,
                "mean_battery_used": round(battery, 2),
                "battery_ci95": round(battery_ci, 2),
                "mean_recharges": round(float(np.mean([r["recharges"] for r in rows])), 2),
                "mean_localization_error": round(err, 3),
                "localization_error_ci95": round(err_ci, 3),
                "status_accuracy": round(float(np.mean([r["status_correct"] for r in rows])), 4),
                "status_inference_accuracy": round(float(np.mean([r["status_inference_correct"] for r in rows])), 4),
                "decoys_inspected": inspected,
                "decoys_flagged": sum(r["decoys_flagged"] for r in rows),
                "decoy_detection_rate": round(sum(r["decoys_flagged"] for r in rows) / inspected, 4) if inspected else None,
                "genuine_beacons_wrongly_flagged": sum(r["genuine_flagged"] for r in rows),
                "failures": {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows}) if s != "SUCCESS"},
            })
    return out


def plot_benchmark(agg: Dict[str, Dict[str, Dict[str, Any]]], output_path: Union[str, Path], n_missions: int) -> Path:
    """Grouped bars (conditions x agents): success rate, steps and battery, each with 95% intervals."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    conditions = list(agg)
    agents = [a for a in AGENTS if all(a in agg[c] for c in conditions)]
    x = np.arange(len(conditions))
    width = 0.8 / len(agents)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), facecolor=SURFACE)
    panels = [
        ("Missions succeeded (%)", lambda c: 100 * c["success_rate"],
         lambda c: (100 * (c["success_rate"] - c["success_ci95"][0]), 100 * (c["success_ci95"][1] - c["success_rate"]))),
        ("Steps used per mission (lower is better)", lambda c: c["mean_steps"], lambda c: (c["steps_ci95"], c["steps_ci95"])),
        ("Battery consumed per mission", lambda c: c["mean_battery_used"], lambda c: (c["battery_ci95"], c["battery_ci95"])),
    ]
    for ax, (title, value, err) in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        for j, agent in enumerate(agents):
            cells = [agg[c][agent] for c in conditions]
            vals = [value(c) for c in cells]
            errs = np.array([err(c) for c in cells]).T
            pos = x - 0.4 + width * (j + 0.5)
            ax.bar(pos, vals, width - 0.03, color=AGENT_COLORS[agent], label=AGENTS[agent], zorder=3)
            ax.errorbar(pos, vals, yerr=errs, fmt="none", ecolor=INK_2, elinewidth=1.2, capsize=3, zorder=4)
            if ax is axes[0]:
                for p, v in zip(pos, vals):
                    ax.text(p, 3, f"{v:.0f}", ha="center", va="bottom", fontsize=8, color="white", weight="bold", zorder=5)
        ax.set_xticks(x, conditions)
        ax.set_title(title, loc="left", fontsize=11, weight="bold", color=INK)
        ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(MUTED)
        ax.spines["bottom"].set_color(MUTED)
        ax.tick_params(colors=INK_2)
    axes[0].set_ylim(0, 105)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.94), fontsize=10)
    fig.suptitle(f"Generalization benchmark — {n_missions} random missions per condition, same seeds for every agent "
                 f"(error bars: 95% intervals)", fontsize=13, weight="bold", color=INK, y=1.0)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return out


def run_full_evaluation_suite(
    output_dir: Union[str, Path] = "outputs",
    n_missions: int = 60,
    seed_offset: int = 1000,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """Run the benchmark and save benchmark_summary.json, benchmark_trials.csv and benchmark_generalization.png."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records = run_benchmark(n_missions=n_missions, seed_offset=seed_offset, progress=progress)
    agg = aggregate(records)
    plot_benchmark(agg, out_dir / "benchmark_generalization.png", n_missions)

    summary = {
        "description": "Same seeded random missions for every agent; conditions vary evidence quality or add a decoy.",
        "missions_per_condition": n_missions,
        "seeds": [seed_offset, seed_offset + n_missions - 1],
        "conditions": {c: CONDITIONS[c] for c in agg},
        "agents": AGENTS,
        "aggregate": agg,
    }
    with open(out_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(out_dir / "benchmark_trials.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return summary
