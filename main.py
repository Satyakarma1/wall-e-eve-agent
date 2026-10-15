"""Main entry point for WALL-E & EVE's Signal Autonomous AI Agent."""

import argparse
import sys
from pathlib import Path

from src.simulation import run_mission, save_mission_report
from src.visualization import plot_static_mission_summary, create_animated_mission_gif
from src.metrics import run_full_evaluation_suite


def main() -> int:
    parser = argparse.ArgumentParser(
        description="WALL-E & EVE's Signal: Autonomous AI Exploration Agent"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.json",
        help="Path to JSON configuration file (default: config/default.json)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed override"
    )
    parser.add_argument(
        "--gif",
        action="store_true",
        default=True,
        help="Generate animated mission GIF (enabled by default)"
    )
    parser.add_argument(
        "--no-gif",
        dest="gif",
        action="store_false",
        help="Disable animated GIF generation to speed up execution"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Execute statistical multi-seed benchmark evaluation suite"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Directory to save generated visual and textual artifacts"
    )

    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.benchmark:
        print("=" * 60)
        print("RUNNING STATISTICAL BENCHMARK & EVALUATION SUITE")
        print("=" * 60)
        report = run_full_evaluation_suite(
            default_cfg="config/default.json",
            noisy_cfg="config/noisy.json",
            output_dir=str(out_dir)
        )
        walle_agg = report["walle_default"]["aggregate"]
        base_agg = report["baseline_default"]["aggregate"]
        noisy_agg = report["walle_noisy"]["aggregate"]

        print(f"\n[RESULTS] WALL-E Agent (Clean):")
        print(f"  Success Rate: {walle_agg['success_rate_pct']}%")
        print(f"  Mean Steps:   {walle_agg['mean_steps']} +/- {walle_agg['std_steps']}")
        print(f"  Battery Used: {walle_agg['mean_battery_used']} +/- {walle_agg['std_battery_used']}")

        print(f"\n[RESULTS] Baseline Agent (Frontier):")
        print(f"  Success Rate: {base_agg['success_rate_pct']}%")
        print(f"  Mean Steps:   {base_agg['mean_steps']} +/- {base_agg['std_steps']}")
        print(f"  Battery Used: {base_agg['mean_battery_used']} +/- {base_agg['std_battery_used']}")

        print(f"\n[RESULTS] WALL-E Agent (Noisy Sensors):")
        print(f"  Success Rate: {noisy_agg['success_rate_pct']}%")
        print(f"  Mean Steps:   {noisy_agg['mean_steps']} +/- {noisy_agg['std_steps']}")
        print(f"  Pred Error:   {noisy_agg['mean_prediction_error']} +/- {noisy_agg['std_prediction_error']}")

        print(f"\nPlots & Summary saved to: {out_dir.resolve()}")
        return 0

    print("=" * 60)
    print(f"STARTING WALL-E EXPLORATION MISSION: {args.config}")
    print("=" * 60)

    result = run_mission(args.config, random_seed=args.seed)

    print(f"\nMission Outcome:     [{result.status}]")
    print(f"Success:             {result.success}")
    print(f"Steps Taken:         {result.total_steps}")
    print(f"Path Length:         {result.path_length} cells")
    print(f"Battery Consumed:    {result.battery_used:.1f} units")
    print(f"Battery Remaining:   {result.battery_remaining:.1f} units")
    print(f"Exploration Coverage:{result.exploration_coverage_pct:.1f}%")
    print(f"Clues Discovered:    {result.clues_discovered} / {result.total_clues}")

    if result.strategy_transitions:
        print("\nStrategy Evolution:")
        for step, strat, reason in result.strategy_transitions:
            print(f"  [Step {step:02d}] {strat:<20} -> {reason}")

    # Generate static visualization
    summary_img = out_dir / f"{result.config_name}_summary.png"
    plot_static_mission_summary(result, summary_img)
    print(f"\nSaved mission summary plot: {summary_img}")

    # Save markdown mission report
    report_file = out_dir / f"{result.config_name}_report.md"
    save_mission_report(result, report_file)
    print(f"Saved mission report:       {report_file}")

    # Generate animated GIF if requested
    if args.gif:
        gif_file = out_dir / f"{result.config_name}_animation.gif"
        print(f"Generating animated replay: {gif_file} (please wait)...")
        create_animated_mission_gif(result, gif_file, duration_per_frame_ms=200)
        print(f"Saved animated GIF:         {gif_file}")

    print("\nMission execution complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
