"""Streamlit interactive dashboard for WALL-E & EVE autonomous exploration agent."""

import sys
from pathlib import Path

try:
    import streamlit as st
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap, Normalize

    from src.simulation import run_mission
    from src.visualization import plot_static_mission_summary
    from src.metrics import run_full_evaluation_suite
except ImportError as e:
    print(f"[NOTE] Streamlit dashboard dependencies not fully installed: {e}")
    print("To launch the interactive dashboard, run:")
    print("    pip install streamlit")
    print("    streamlit run app.py")
    sys.exit(0)


def render_step_map(result, t: int):
    """Render the grid map and belief distribution at a specific time step t."""
    gt = result.ground_truth
    rows, cols = gt["grid_size"]
    obstacles = {tuple(o) for o in gt["obstacles"]}
    eve_pos = tuple(gt["eve_pos"])
    start_pos = tuple(gt["start_pos"])
    path = result.path_taken
    trace = result.action_trace
    belief_hist = result.belief_history

    current_pos = path[min(t, len(path) - 1)]
    visited_so_far = set(path[:t + 1])

    fig, (ax_grid, ax_heat) = plt.subplots(1, 2, figsize=(12, 6))

    # Grid background
    bg = np.zeros((rows, cols), dtype=float)
    for r in range(rows):
        for c in range(cols):
            if (r, c) in obstacles:
                bg[r, c] = 1.0
            elif (r, c) in visited_so_far:
                bg[r, c] = 0.5
            else:
                bg[r, c] = 0.0

    cmap = ListedColormap(["#F8FAFC", "#CBD5E1", "#334155"])
    ax_grid.imshow(bg, cmap=cmap, norm=Normalize(0.0, 1.0), origin="upper")
    ax_grid.set_xticks(range(cols))
    ax_grid.set_yticks(range(rows))
    ax_grid.grid(color="#94A3B8", linestyle=":", linewidth=0.8, alpha=0.5)

    if t > 0:
        hist_r = [p[0] for p in path[:t + 1]]
        hist_c = [p[1] for p in path[:t + 1]]
        ax_grid.plot(hist_c, hist_r, color="#2563EB", linestyle="--", linewidth=2.0)

    # Start and clue markers
    ax_grid.scatter(start_pos[1], start_pos[0], color="#16A34A", s=180, marker="o", label="Start")
    for c_str in gt["clues"].keys():
        c_tuple = tuple(map(int, c_str.strip("()").split(",")))
        is_disc = c_tuple in visited_so_far
        ax_grid.scatter(
            c_tuple[1], c_tuple[0],
            color="#EA580C" if is_disc else "#94A3B8",
            s=200, marker="*",
            label="Clue (Found)" if is_disc else "Clue (Unvisited)"
        )

    # WALL-E current marker
    ax_grid.scatter(current_pos[1], current_pos[0], color="#F59E0B", s=220, marker="s", edgecolors="black", label="WALL-E")

    # Reveal EVE on final frame or if found
    if t >= len(path) - 1 or current_pos == eve_pos:
        ax_grid.scatter(eve_pos[1], eve_pos[0], color="#DC2626", s=220, marker="X", edgecolors="black", label="EVE Target")

    ax_grid.set_title(f"World Map at Step {t}", fontsize=12, weight="bold")
    ax_grid.legend(loc="upper left", bbox_to_anchor=(0.0, -0.08), ncol=3, fontsize=8)

    # Belief Heatmap
    belief_grid = belief_hist[min(t, len(belief_hist) - 1)]
    im = ax_heat.imshow(belief_grid, cmap="inferno", origin="upper")
    ax_heat.set_title("Bayesian Belief Distribution P(EVE = (r, c))", fontsize=12, weight="bold")
    ax_heat.set_xticks(range(cols))
    ax_heat.set_yticks(range(rows))
    plt.colorbar(im, ax=ax_heat, fraction=0.046, pad=0.04)

    st.pyplot(fig)
    plt.close(fig)


def main():
    st.set_page_config(page_title="WALL-E & EVE's Signal", page_icon="🤖", layout="wide")
    st.title("🤖 WALL-E & EVE's Signal: Autonomous AI Agent")
    st.markdown(
        "Interactive dashboard for autonomous grid exploration, Bayesian clue decoding, "
        "and explainable AI decision-making."
    )

    st.sidebar.header("Mission Settings")
    cfg_options = {
        "Default Scenario (12x12)": "config/default.json",
        "Hard Maze Scenario (16x16)": "config/hard.json",
        "Unreachable Target (10x10)": "config/unreachable.json",
        "Noisy Sensor Scenario (12x12)": "config/noisy.json"
    }
    selected_name = st.sidebar.selectbox("Choose Configuration", list(cfg_options.keys()))
    cfg_file = cfg_options[selected_name]

    seed_val = st.sidebar.number_input("Random Seed", min_value=0, max_value=9999, value=42)

    if "result" not in st.session_state or st.sidebar.button("Run Simulation"):
        with st.spinner("Simulating autonomous mission..."):
            st.session_state["result"] = run_mission(cfg_file, random_seed=seed_val)

    result = st.session_state["result"]

    # Top KPI metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    status_label = "✅ SUCCESS" if result.success else f"❌ {result.status}"
    col1.metric("Mission Status", status_label)
    col2.metric("Total Steps", result.total_steps)
    col3.metric("Path Length", f"{result.path_length} cells")
    col4.metric("Battery Remaining", f"{result.battery_remaining:.1f} / 100")
    col5.metric("Coverage", f"{result.exploration_coverage_pct:.1f}%")

    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["🎮 Step-by-Step Replay", "📊 Mission Summary", "📜 Decision Trace"])

    with tab1:
        st.subheader("Interactive Step-by-Step Mission Replay")
        step_idx = st.slider("Select Simulation Step", 0, len(result.path_taken) - 1, len(result.path_taken) - 1)
        render_step_map(result, step_idx)

        # Show decision info for the selected step
        if step_idx < len(result.action_trace):
            entry = result.action_trace[step_idx]
            st.info(
                f"**Step {entry['step']}** | Action: `{entry['action']}` | Strategy: `{entry['strategy']}` | "
                f"Battery: {entry['battery']:.1f} | Top Candidate: {entry['top_candidate']} (P={entry['top_candidate_prob']:.3f})\n\n"
                f"**Decision Reason**: {entry['reason']}"
            )

    with tab2:
        st.subheader("Resource & Uncertainty Analytics")
        summary_path = Path("outputs") / f"{result.config_name}_summary.png"
        if not summary_path.exists():
            plot_static_mission_summary(result, summary_path)
        st.image(str(summary_path), caption="Mission Performance & Trajectory Analytics", use_container_width=True)

    with tab3:
        st.subheader("Full Explainable Action Trace")
        st.dataframe(result.action_trace)


if __name__ == "__main__":
    main()
