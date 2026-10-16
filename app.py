"""Streamlit dashboard: run a mission and watch it as an animated, step-synchronized replay.

Run:  .\\.venv\\Scripts\\python.exe -m streamlit run app.py
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.agent import STRATEGY_DESCRIPTIONS
from src.frames import STRATEGY_LABELS
from src.metrics import AGENTS, run_full_evaluation_suite
from src.mission_generator import generate_mission
from src.replay_player import render_replay_html
from src.report import recommend_next_step, render_report_markdown
from src.simulation import run_mission, save_trace_json
from src.visualization import create_animated_mission_gif, plot_static_mission_summary

st.set_page_config(page_title="WALL-E & EVE's Signal", page_icon=":material/smart_toy:", layout="wide")

PRESETS = {
    "Default sweep (beacon + scans)": "default",
    "Spoofed beacon (decoy)": "decoy",
    "Low battery: recharge sorties": "recharge",
    "EVE sealed behind debris": "unreachable",
    "Noisy sensors": "noisy",
    "Hard maze, stale coordinates": "hard",
}
VIEWS = ["Animated replay", "Mission report", "Decision trace", "Static summary", "Benchmark"]


def load_config(source: str, preset: str, seed: int, size: int, noisy: bool, decoys: int) -> dict:
    if source == "Preset":
        return json.loads(Path(f"config/{PRESETS[preset]}.json").read_text(encoding="utf-8"))
    return generate_mission(seed, size=(size, size), n_decoys=decoys, noisy=noisy)


@st.cache_data(max_entries=32, show_spinner="Simulating mission…")
def simulate(source: str, preset: str, seed: int, size: int, noisy: bool, decoys: int, agent: str):
    config = load_config(source, preset, seed, size, noisy, decoys)
    result = run_mission(config, agent_type=agent)
    return result, render_replay_html(result), render_report_markdown(result), json.dumps(config, indent=2)


@st.cache_data(max_entries=16, show_spinner="Rendering summary figure…")
def summary_png(*key) -> bytes:
    result = simulate(*key)[0]
    with tempfile.TemporaryDirectory() as tmp:
        return plot_static_mission_summary(result, Path(tmp) / "summary.png").read_bytes()


@st.cache_data(max_entries=8, show_spinner="Rendering GIF (one frame per step)…")
def mission_gif(*key) -> bytes:
    result = simulate(*key)[0]
    with tempfile.TemporaryDirectory() as tmp:
        return create_animated_mission_gif(result, Path(tmp) / "mission.gif", duration_per_frame_ms=220).read_bytes()


@st.cache_data(max_entries=2, show_spinner="Running benchmark missions…")
def benchmark(n_missions: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        summary = run_full_evaluation_suite(tmp, n_missions=n_missions)
        summary["png"] = (Path(tmp) / "benchmark_generalization.png").read_bytes()
    return summary


def trace_bytes(result) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        return save_trace_json(result, Path(tmp) / "trace.json").read_bytes()


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Mission")
    source = st.segmented_control("Mission source", ["Preset", "Random"], default="Preset", required=True)
    preset, seed, size, noisy, decoys = list(PRESETS)[0], 0, 12, False, 0
    if source == "Preset":
        preset = st.selectbox("Sample mission", list(PRESETS))
    else:
        seed = int(st.number_input("Seed", min_value=0, max_value=99_999, value=7, step=1))
        size = st.slider("Grid size", 10, 18, 14)
        noisy = st.toggle("Noisy sensors")
        decoys = st.slider("Decoy beacons", 0, 2, 1)
    agent = st.selectbox("Agent", list(AGENTS), format_func=AGENTS.get)
    st.caption("Changing any setting re-runs the mission; results are cached.")
    with st.expander("What the strategies mean"):
        for strategy, text in STRATEGY_DESCRIPTIONS.items():
            st.markdown(f"**{STRATEGY_LABELS[strategy.value]}**: {text}")

key = (source, preset, seed, size, noisy, decoys, agent)
result, replay_html, report_md, config_json = simulate(*key)
inf = result.inference

# ------------------------------------------------------------------ header + KPIs
st.title("WALL-E & EVE's Signal")
st.caption(f"{result.mission_name} · {result.ground_truth['grid_size'][0]}×{result.ground_truth['grid_size'][1]} grid · "
           f"agent: {AGENTS[agent]}")

kpis = st.columns(6)
kpis[0].metric("Outcome", result.status.replace("_", " ").title())
kpis[1].metric("Steps", result.total_steps)
kpis[2].metric("Battery left", f"{result.battery_remaining:.0f} / {result.briefing['battery_capacity']:.0f}")
kpis[3].metric("Recharges", result.recharge_count)
kpis[4].metric("Beacons decoded", f"{result.clues_inspected} / {result.total_clues}")
kpis[5].metric("EVE status", f"{inf['status_estimate'].title()} ({inf['status_confidence']:.0%})")

alert = st.success if result.success else st.warning
alert(recommend_next_step(result), title=f"{inf['conclusion'].replace('_', ' ').title()} at {tuple(inf['map_estimate'])}",
      icon=":material/flag:")

view = st.segmented_control("View", VIEWS, default=VIEWS[0], required=True, label_visibility="collapsed")

if view == "Animated replay":
    st.iframe(replay_html, height=1090, alt="Animated mission replay with map, belief heatmap and decision panel")
    cols = st.columns(3)
    cols[0].download_button("Download replay (HTML)", replay_html, f"{result.config_name}_replay.html", "text/html",
                            icon=":material/download:", width="stretch")
    cols[1].download_button("Download full trace (JSON)", trace_bytes(result), f"{result.config_name}_trace.json",
                            "application/json", icon=":material/data_object:", width="stretch")
    if cols[2].button("Render animated GIF", icon=":material/movie:", width="stretch"):
        gif = mission_gif(*key)
        st.image(gif, alt="Animated GIF of the mission, one frame per step")
        st.download_button("Download GIF", gif, f"{result.config_name}_animation.gif", "image/gif", icon=":material/download:")

elif view == "Mission report":
    st.markdown(report_md)
    st.download_button("Download report (Markdown)", report_md, f"{result.config_name}_report.md", "text/markdown",
                       icon=":material/download:")

elif view == "Decision trace":
    rows = [{
        "step": s["step"],
        "position": str(tuple(s["agent_pos"])),
        "action": s["action"],
        "strategy": STRATEGY_LABELS[s["strategy"]],
        "battery": s["battery"],
        "best guess": f"{tuple(s['top_candidate'])} P={s['top_candidate_prob']:.2f}",
        "entropy (bits)": s["belief_entropy"],
        "P(dormant)": s["status_belief"].get("DORMANT", 0.0),
        "reason": s["reason"],
        "observed": "; ".join(s["events"]),
    } for s in result.action_trace]
    df = pd.DataFrame(rows)
    used = [STRATEGY_LABELS[s] for s in dict.fromkeys(x["strategy"] for x in result.action_trace)]
    chosen = st.pills("Filter strategies", used, selection_mode="multi", default=used)
    st.dataframe(
        df[df["strategy"].isin(chosen or used)],
        hide_index=True,
        column_config={
            "battery": st.column_config.ProgressColumn("battery", min_value=0,
                                                       max_value=float(result.briefing["battery_capacity"]), format="%.0f"),
            "P(dormant)": st.column_config.NumberColumn(format="%.2f"),
            "reason": st.column_config.TextColumn(width="large"),
            "observed": st.column_config.TextColumn(width="large"),
        },
        alt="Step-by-step decision trace",
    )
    st.caption("Every row is one decision: what WALL-E observed, believed, chose and why. "
               "The JSON download on the replay view also holds the raw observations and outcomes.")

elif view == "Static summary":
    st.image(summary_png(*key), alt="Mission summary: map, battery, entropy and status/beacon reliability")

else:
    st.markdown("Every agent runs the **same seeded random missions** under four sensing conditions. "
                "Bars show means; error bars are 95% intervals (Wilson for success rates).")
    saved = Path("outputs/benchmark_summary.json")
    n = st.slider("Missions per condition", 10, 100, 60, step=10)
    if st.button("Run benchmark", icon=":material/science:"):
        summary = benchmark(n)
        st.image(summary["png"], alt="Benchmark bar charts")
        agg = summary["aggregate"]
    elif saved.exists() and Path("outputs/benchmark_generalization.png").exists():
        summary = json.loads(saved.read_text(encoding="utf-8"))
        st.image("outputs/benchmark_generalization.png", alt="Benchmark bar charts")
        agg = summary["aggregate"]
        st.caption(f"Showing saved results ({summary['missions_per_condition']} missions per condition).")
    else:
        agg = None
        st.info("No saved benchmark yet. Click **Run benchmark** or run `python main.py --benchmark`.")
    if agg:
        st.dataframe(pd.DataFrame([{
            "condition": c, "agent": a["label"], "success %": round(100 * a["success_rate"], 1),
            "95% CI": f"{100 * a['success_ci95'][0]:.0f}–{100 * a['success_ci95'][1]:.0f}%",
            "mean steps": a["mean_steps"], "battery used": a["mean_battery_used"],
            "status inferred before contact %": round(100 * a["status_inference_accuracy"], 1),
            "decoys flagged": f"{a['decoys_flagged']}/{a['decoys_inspected']}" if a["decoys_inspected"] else "–",
        } for c, by_agent in agg.items() for a in by_agent.values()]), hide_index=True, alt="Benchmark summary table")

with st.expander("Mission config (JSON)"):
    st.code(config_json, language="json")
