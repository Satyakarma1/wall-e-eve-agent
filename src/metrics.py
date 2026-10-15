"""Evaluation runner, benchmark experiments, statistical metrics, and comparative plots."""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.environment import Environment, Action
from src.agent import WallEAgent, BaselineRandomAgent
from src.simulation import run_mission, SimulationResult


def run_benchmark_trials(
    config_data_or_path: Union[Dict[str, Any], str, Path],
    num_trials: int = 15,
    agent_type: str = "walle",
    seed_offset: int = 100
) -> List[Dict[str, Any]]:
    """
    Run multiple trials of a given agent across reproducible seeds and collect raw metrics.
    """
    results: List[Dict[str, Any]] = []

    for i in range(num_trials):
        seed = seed_offset + i
        env = Environment(config_data_or_path)
        obs = env.reset(new_seed=seed)

        if agent_type == "walle":
            agent = WallEAgent(bounds=env.bounds)
            done = env.done
            while not done:
                action = agent.step(obs)
                obs, _, done, _ = env.step(action)

            # Target prediction error (distance from belief top candidate to true EVE)
            gt_eve = env._eve_pos
            top_cand = agent.belief.most_likely_position()
            pred_error = math.hypot(top_cand[0] - gt_eve[0], top_cand[1] - gt_eve[1])
            final_entropy = agent.belief.get_entropy()
        elif agent_type == "baseline":
            agent = BaselineRandomAgent(bounds=env.bounds)
            done = env.done
            while not done:
                action = agent.step(obs)
                obs, _, done, _ = env.step(action)
            pred_error = 0.0
            final_entropy = 0.0
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        info = env.get_summary_info()
        trial_record = {
            "trial_id": i + 1,
            "seed": seed,
            "agent_type": agent_type,
            "status": info["status"],
            "success": bool(info["success"]),
            "step_count": int(info["step_count"]),
            "path_length": int(info["path_length"]),
            "battery_used": float(info["battery_used"]),
            "battery_remaining": float(info["battery_remaining"]),
            "scan_count": int(info["scan_count"]),
            "cells_visited": int(info["cells_visited"]),
            "exploration_coverage_pct": float(info["exploration_coverage_pct"]),
            "clues_discovered": int(info["clues_discovered"]),
            "prediction_error": round(float(pred_error), 3),
            "final_entropy": round(float(final_entropy), 3)
        }
        results.append(trial_record)

    return results


def calculate_aggregate_metrics(trial_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate mean, standard deviation, and success rates from trial records."""
    if not trial_records:
        return {}

    n = len(trial_records)
    successes = sum(1 for r in trial_records if r["success"])
    success_rate = (successes / n) * 100.0

    steps = [r["step_count"] for r in trial_records]
    path_lens = [r["path_length"] for r in trial_records]
    batt_used = [r["battery_used"] for r in trial_records]
    coverage = [r["exploration_coverage_pct"] for r in trial_records]
    pred_errors = [r["prediction_error"] for r in trial_records]

    return {
        "trials_count": n,
        "success_rate_pct": round(success_rate, 2),
        "mean_steps": round(float(np.mean(steps)), 2),
        "std_steps": round(float(np.std(steps)), 2),
        "mean_path_length": round(float(np.mean(path_lens)), 2),
        "std_path_length": round(float(np.std(path_lens)), 2),
        "mean_battery_used": round(float(np.mean(batt_used)), 2),
        "std_battery_used": round(float(np.std(batt_used)), 2),
        "mean_coverage_pct": round(float(np.mean(coverage)), 2),
        "std_coverage_pct": round(float(np.std(coverage)), 2),
        "mean_prediction_error": round(float(np.mean(pred_errors)), 2),
        "std_prediction_error": round(float(np.std(pred_errors)), 2)
    }


def plot_agent_vs_baseline(
    walle_metrics: Dict[str, Any],
    baseline_metrics: Dict[str, Any],
    output_path: Union[str, Path] = "outputs/benchmark_agent_vs_baseline.png"
) -> Path:
    """Generate comparative bar charts for WALL-E Agent vs Baseline Agent."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)

    labels = ["WALL-E Agent (Ours)", "Baseline Explorer"]
    colors = ["#2563EB", "#94A3B8"]

    # 1. Success Rate
    ax1 = axes[0]
    success_rates = [walle_metrics["success_rate_pct"], baseline_metrics["success_rate_pct"]]
    bars1 = ax1.bar(labels, success_rates, color=colors, width=0.5, edgecolor="black")
    ax1.set_title("Mission Success Rate (%)", fontsize=12, weight="bold")
    ax1.set_ylabel("Success Rate (%)", fontsize=10)
    ax1.set_ylim(0, 110)
    ax1.grid(axis="y", linestyle=":", alpha=0.6)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, yval + 2, f"{yval:.1f}%", ha="center", va="bottom", weight="bold")

    # 2. Steps Taken
    ax2 = axes[1]
    steps_means = [walle_metrics["mean_steps"], baseline_metrics["mean_steps"]]
    steps_stds = [walle_metrics["std_steps"], baseline_metrics["std_steps"]]
    bars2 = ax2.bar(labels, steps_means, yerr=steps_stds, color=colors, width=0.5, capsize=5, edgecolor="black")
    ax2.set_title("Mean Steps to Complete", fontsize=12, weight="bold")
    ax2.set_ylabel("Steps Count", fontsize=10)
    ax2.grid(axis="y", linestyle=":", alpha=0.6)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2.0, yval + 1, f"{yval:.1f}", ha="center", va="bottom", weight="bold")

    # 3. Battery Used
    ax3 = axes[2]
    batt_means = [walle_metrics["mean_battery_used"], baseline_metrics["mean_battery_used"]]
    batt_stds = [walle_metrics["std_battery_used"], baseline_metrics["std_battery_used"]]
    bars3 = ax3.bar(labels, batt_means, yerr=batt_stds, color=colors, width=0.5, capsize=5, edgecolor="black")
    ax3.set_title("Mean Battery Consumed", fontsize=12, weight="bold")
    ax3.set_ylabel("Battery Units", fontsize=10)
    ax3.grid(axis="y", linestyle=":", alpha=0.6)
    for bar in bars3:
        yval = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2.0, yval + 1, f"{yval:.1f}", ha="center", va="bottom", weight="bold")

    fig.suptitle("Comparative Evaluation: Autonomous WALL-E Agent vs Blind Frontier Baseline", fontsize=14, weight="bold")
    plt.savefig(out, dpi=200)
    plt.close(fig)
    return out


def plot_clean_vs_noisy_experiment(
    clean_metrics: Dict[str, Any],
    noisy_metrics: Dict[str, Any],
    output_path: Union[str, Path] = "outputs/benchmark_clean_vs_noisy.png"
) -> Path:
    """Generate comparative charts for Clean Observations vs Noisy Sensors."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    labels = ["Clean Sensor (σ=0.0)", "Noisy Sensor (σ=1.5)"]
    colors = ["#059669", "#D97706"]

    # 1. Success Rate
    ax1 = axes[0]
    vals1 = [clean_metrics["success_rate_pct"], noisy_metrics["success_rate_pct"]]
    bars1 = ax1.bar(labels, vals1, color=colors, width=0.5, edgecolor="black")
    ax1.set_title("Success Rate Under Noise (%)", fontsize=12, weight="bold")
    ax1.set_ylim(0, 110)
    ax1.grid(axis="y", linestyle=":", alpha=0.6)
    for b in bars1:
        ax1.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 2, f"{b.get_height():.1f}%", ha="center", weight="bold")

    # 2. Steps to Target
    ax2 = axes[1]
    vals2 = [clean_metrics["mean_steps"], noisy_metrics["mean_steps"]]
    errs2 = [clean_metrics["std_steps"], noisy_metrics["std_steps"]]
    bars2 = ax2.bar(labels, vals2, yerr=errs2, color=colors, width=0.5, capsize=5, edgecolor="black")
    ax2.set_title("Steps to Locate EVE", fontsize=12, weight="bold")
    ax2.grid(axis="y", linestyle=":", alpha=0.6)
    for b in bars2:
        ax2.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 1, f"{b.get_height():.1f}", ha="center", weight="bold")

    # 3. Final Prediction Error
    ax3 = axes[2]
    vals3 = [clean_metrics["mean_prediction_error"], noisy_metrics["mean_prediction_error"]]
    errs3 = [clean_metrics["std_prediction_error"], noisy_metrics["std_prediction_error"]]
    bars3 = ax3.bar(labels, vals3, yerr=errs3, color=colors, width=0.5, capsize=5, edgecolor="black")
    ax3.set_title("Target Localization Error (cells)", fontsize=12, weight="bold")
    ax3.grid(axis="y", linestyle=":", alpha=0.6)
    for b in bars3:
        ax3.text(b.get_x() + b.get_width() / 2.0, b.get_height() + 0.1, f"{b.get_height():.2f}", ha="center", weight="bold")

    fig.suptitle("Robustness Experiment: Clean Observations vs Noisy Sensors", fontsize=14, weight="bold")
    plt.savefig(out, dpi=200)
    plt.close(fig)
    return out


def run_full_evaluation_suite(
    default_cfg: str = "config/default.json",
    noisy_cfg: str = "config/noisy.json",
    output_dir: str = "outputs"
) -> Dict[str, Any]:
    """Execute complete benchmark suite and save JSON and PNG outputs."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run WALL-E Agent on Default
    walle_trials = run_benchmark_trials(default_cfg, num_trials=15, agent_type="walle")
    walle_agg = calculate_aggregate_metrics(walle_trials)

    # 2. Run Baseline Agent on Default
    baseline_trials = run_benchmark_trials(default_cfg, num_trials=15, agent_type="baseline")
    baseline_agg = calculate_aggregate_metrics(baseline_trials)

    # 3. Run WALL-E Agent on Noisy Config
    noisy_trials = run_benchmark_trials(noisy_cfg, num_trials=15, agent_type="walle")
    noisy_agg = calculate_aggregate_metrics(noisy_trials)

    # 4. Generate comparison plots
    plot_agent_vs_baseline(walle_agg, baseline_agg, out_dir / "benchmark_agent_vs_baseline.png")
    plot_clean_vs_noisy_experiment(walle_agg, noisy_agg, out_dir / "benchmark_clean_vs_noisy.png")

    full_report = {
        "walle_default": {
            "aggregate": walle_agg,
            "raw_trials": walle_trials
        },
        "baseline_default": {
            "aggregate": baseline_agg,
            "raw_trials": baseline_trials
        },
        "walle_noisy": {
            "aggregate": noisy_agg,
            "raw_trials": noisy_trials
        }
    }

    # Save summary JSON
    with open(out_dir / "benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    return full_report
