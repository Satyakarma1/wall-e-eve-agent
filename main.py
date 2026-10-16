"""Command-line entry point for WALL-E & EVE's Signal.

Examples (Windows PowerShell, from the project folder):
    .\\.venv\\Scripts\\python.exe main.py                               # default mission + all outputs
    .\\.venv\\Scripts\\python.exe main.py --config config/decoy.json    # another sample mission
    .\\.venv\\Scripts\\python.exe main.py --ascii                       # animate the mission in the terminal
    .\\.venv\\Scripts\\python.exe main.py --random 7 --decoys 1         # seeded random mission
    .\\.venv\\Scripts\\python.exe main.py --benchmark                   # generalization benchmark
    .\\.venv\\Scripts\\python.exe main.py --all                         # regenerate outputs for every sample config
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Union

from src.ascii_view import final_ascii_summary, play_ascii
from src.metrics import CONDITIONS, run_full_evaluation_suite
from src.mission_generator import generate_mission
from src.replay_player import save_replay_html
from src.simulation import AGENT_TYPES, SimulationResult, run_mission, save_mission_report, save_trace_json
from src.visualization import create_animated_mission_gif, plot_static_mission_summary

SAMPLE_CONFIGS = ["default", "decoy", "recharge", "unreachable", "noisy", "hard"]


def run_and_save(config: Union[str, Path, Dict[str, Any]], args: argparse.Namespace, out_dir: Path) -> SimulationResult:
    """Run one mission, print a summary and write every output artifact."""
    result = run_mission(config, random_seed=args.seed, agent_type=args.agent)
    inf = result.inference
    name = result.config_name if args.agent == "walle" else f"{result.config_name}_{args.agent}"

    print("=" * 72)
    print(f"MISSION: {result.mission_name}  [{result.config_name}, agent={args.agent}]")
    print("=" * 72)
    print(f"Outcome:             {result.status}")
    print(f"Steps / path length: {result.total_steps} / {result.path_length} cells")
    print(f"Battery:             {result.battery_used:.1f} used, {result.battery_remaining:.1f} left, "
          f"{result.energy_recharged:.1f} recharged ({result.recharge_count} dock actions)")
    print(f"Scans / beacons:     {result.scan_count} scans, {result.clues_inspected} decoded, "
          f"{result.clues_discovered}/{result.total_clues} sighted")
    print(f"Conclusion:          {inf['conclusion']} at {tuple(inf['map_estimate'])} (P={inf['map_probability']:.2f})")
    print(f"EVE status:          {inf['status_estimate']} (confidence {inf['status_confidence']:.0%})")
    if inf["flagged_decoys"]:
        print(f"Spoofed beacons:     {', '.join(str(tuple(d)) for d in inf['flagged_decoys'])}")
    print("\nStrategy changes:")
    for step, strat, reason in result.strategy_transitions:
        print(f"  [step {step:3d}] {strat:<20} {reason}")

    outputs = [
        plot_static_mission_summary(result, out_dir / f"{name}_summary.png"),
        save_mission_report(result, out_dir / f"{name}_report.md"),
        save_trace_json(result, out_dir / f"{name}_trace.json"),
        save_replay_html(result, out_dir / f"{name}_replay.html"),
    ]
    ascii_path = out_dir / f"{name}_ascii.txt"
    ascii_path.write_text(final_ascii_summary(result), encoding="utf-8")
    outputs.append(ascii_path)
    if args.gif:
        outputs.append(create_animated_mission_gif(result, out_dir / f"{name}_animation.gif", duration_per_frame_ms=220))
    print("\nSaved:")
    for p in outputs:
        print(f"  {p}")
    if args.ascii:
        play_ascii(result, delay=args.ascii_delay)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="WALL-E & EVE's Signal: autonomous search agent")
    parser.add_argument("--config", default="config/default.json", help="Mission config JSON (default: config/default.json)")
    parser.add_argument("--seed", type=int, default=None, help="Override the config's random seed (sensor noise)")
    parser.add_argument("--agent", choices=AGENT_TYPES, default="walle", help="walle (default), naive or baseline")
    parser.add_argument("--random", type=int, metavar="SEED", help="Run a generated random mission instead of --config")
    parser.add_argument("--size", type=int, default=None, help="Grid size for --random (square)")
    parser.add_argument("--noisy", action="store_true", help="Noisy sensors for --random")
    parser.add_argument("--decoys", type=int, default=0, help="Number of decoy beacons for --random")
    parser.add_argument("--no-gif", dest="gif", action="store_false", help="Skip the animated GIF (faster)")
    parser.add_argument("--ascii", action="store_true", help="Animate the mission in the terminal")
    parser.add_argument("--ascii-delay", type=float, default=0.15, help="Seconds per ASCII frame")
    parser.add_argument("--all", action="store_true", help="Regenerate outputs for every sample config")
    parser.add_argument("--benchmark", action="store_true", help="Run the generalization benchmark")
    parser.add_argument("--missions", type=int, default=60, help="Random missions per benchmark condition")
    parser.add_argument("--output-dir", default="outputs", help="Where to write outputs")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.benchmark:
        print(f"Running generalization benchmark: {len(CONDITIONS)} conditions x {args.missions} missions x 3 agents ...")
        summary = run_full_evaluation_suite(out_dir, n_missions=args.missions)
        for condition, by_agent in summary["aggregate"].items():
            print(f"\n[{condition}]")
            for agent, a in by_agent.items():
                lo, hi = a["success_ci95"]
                detect = (f", decoys flagged {a['decoys_flagged']}/{a['decoys_inspected']} inspected"
                          if a["decoys_inspected"] else "")
                print(f"  {a['label']:<38} success {100 * a['success_rate']:5.1f}% (95% CI {100 * lo:.0f}-{100 * hi:.0f}%)"
                      f" | steps {a['mean_steps']:6.1f} +/- {a['steps_ci95']:.1f} | battery {a['mean_battery_used']:6.1f}"
                      f" | status inferred before contact {100 * a['status_inference_accuracy']:.0f}%{detect}")
        print(f"\nSaved: {out_dir / 'benchmark_generalization.png'}, benchmark_summary.json, benchmark_trials.csv")
        return 0

    if args.all:
        for name in SAMPLE_CONFIGS:
            run_and_save(Path("config") / f"{name}.json", args, out_dir)
            print()
        return 0

    if args.random is not None:
        size = (args.size, args.size) if args.size else None
        config = generate_mission(args.random, size=size, n_decoys=args.decoys, noisy=args.noisy)
        run_and_save(config, args, out_dir)
        return 0

    run_and_save(args.config, args, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
