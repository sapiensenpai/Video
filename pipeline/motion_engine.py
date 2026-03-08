"""
motion_engine.py
Applies Ken Burns pan/zoom effects to static frames using FFmpeg's zoompan filter.
Outputs per-scene video clips (no audio).
"""

import subprocess
import shutil
from pathlib import Path

from utils.config import (
    OUTPUT_WIDTH, OUTPUT_HEIGHT,
    FRAME_RATE, TEMP_CLIPS_DIR,
)

# Output dimensions string
OUT_SIZE = f"{OUTPUT_WIDTH}x{OUTPUT_HEIGHT}"


def _build_zoompan_filter(motion: str, total_frames: int, preview: bool) -> str:
    """Return the FFmpeg zoompan filter string for the given motion type."""
    tf = total_frames
    w, h = OUTPUT_WIDTH, OUTPUT_HEIGHT
    if preview:
        w //= 2
        h //= 2

    filters = {
        "slow_zoom_in": (
            f"zoompan=z='min(zoom+0.001,1.12)':d={tf}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}"
        ),
        "slow_zoom_out": (
            f"zoompan=z='if(eq(on,1),1.12,max(zoom-0.001,1.0))':d={tf}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}"
        ),
        "pan_up_slow": (
            f"zoompan=z='1.08':d={tf}"
            f":x='iw/2-(iw/zoom/2)':y='max(ih/2-(ih/zoom/2) - (on*0.8), 0)':s={w}x{h}"
        ),
        "pan_down_slow": (
            f"zoompan=z='1.08':d={tf}"
            f":x='iw/2-(iw/zoom/2)':y='min(on*0.8, ih-ih/zoom)':s={w}x{h}"
        ),
        "gentle_pulse_zoom": (
            f"zoompan=z='1.0+0.04*sin(on/({tf}/3.14159))':d={tf}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}"
        ),
    }
    return filters.get(motion, filters["slow_zoom_in"])


def apply_motion_to_scene(scene: dict, preview: bool = False) -> str:
    """
    Apply Ken Burns motion to a scene's frame and produce a silent video clip.
    Returns the path to the output clip.
    """
    nn = scene["scene_number"]
    frame_path = scene["frame_path"]
    duration = scene.get("actual_duration_seconds", scene["duration_seconds"])
    motion = scene.get("motion", "slow_zoom_in")
    out_path = TEMP_CLIPS_DIR / f"scene_{nn:02d}.mp4"

    fps = FRAME_RATE
    total_frames = max(1, int(duration * fps))

    zoompan = _build_zoompan_filter(motion, total_frames, preview)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_path,
        "-vf", zoompan,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast" if not preview else "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        str(out_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n  FFmpeg error for scene {nn}:")
        print("  CMD:", " ".join(cmd))
        print("  STDERR:", result.stderr[-1000:])
        raise RuntimeError(f"FFmpeg failed for scene {nn}")

    return str(out_path)


def apply_motion_to_all(script: dict, preview: bool = False) -> dict:
    """Apply Ken Burns to all scenes. Updates each scene with 'clip_path'."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg not found. Install it with: apt install ffmpeg  (or brew install ffmpeg)"
        )

    scenes = script["scenes"]
    total = len(scenes)
    for i, scene in enumerate(scenes, 1):
        print(f"    scene {i}/{total} ({scene['scene_name']})...", end=" ", flush=True)
        path = apply_motion_to_scene(scene, preview=preview)
        scene["clip_path"] = path
        print("done")
    return script
