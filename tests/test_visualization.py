"""Test suite for static and animated visualizations."""

from pathlib import Path
from src.simulation import run_mission
from src.visualization import plot_static_mission_summary, create_animated_mission_gif


def test_visualizations_generate_valid_files(tmp_path):
    config_path = Path("config/default.json")
    result = run_mission(config_path, random_seed=42)

    # Test static summary plot
    summary_png = tmp_path / "test_summary.png"
    out_png = plot_static_mission_summary(result, summary_png)
    assert out_png.exists()
    assert out_png.stat().st_size > 1000  # Non-empty image

    # Test animated GIF
    animation_gif = tmp_path / "test_animation.gif"
    out_gif = create_animated_mission_gif(result, animation_gif, duration_per_frame_ms=100)
    assert out_gif.exists()
    assert out_gif.stat().st_size > 5000  # Non-empty GIF
