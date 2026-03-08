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

# Cinematic colour grade applied to every clip: slight contrast/saturation boost + vignette
_GRADE = "eq=contrast=1.12:brightness=0.02:saturation=1.30,vignette=angle=PI/4"


def _build_zoompan_filter(motion: str, total_frames: int, preview: bool) -> str:
    """Return the FFmpeg filter string for the given motion type."""
    tf = total_frames
    w, h = OUTPUT_WIDTH, OUTPUT_HEIGHT
    if preview:
        w //= 2
        h //= 2

    zoom_center_x = "iw/2-(iw/zoom/2)"
    zoom_center_y = "ih/2-(ih/zoom/2)"

    filters = {
        # --- original ---
        "slow_zoom_in": (
            f"zoompan=z='min(zoom+0.001,1.12)':d={tf}"
            f":x='{zoom_center_x}':y='{zoom_center_y}':s={w}x{h}"
        ),
        "slow_zoom_out": (
            f"zoompan=z='if(eq(on,1),1.12,max(zoom-0.001,1.0))':d={tf}"
            f":x='{zoom_center_x}':y='{zoom_center_y}':s={w}x{h}"
        ),
        "pan_up_slow": (
            f"zoompan=z='1.08':d={tf}"
            f":x='{zoom_center_x}':y='max(ih/2-(ih/zoom/2) - (on*0.8), 0)':s={w}x{h}"
        ),
        "pan_down_slow": (
            f"zoompan=z='1.08':d={tf}"
            f":x='{zoom_center_x}':y='min(on*0.8, ih-ih/zoom)':s={w}x{h}"
        ),
        "gentle_pulse_zoom": (
            f"zoompan=z='1.04+0.04*sin(on/({tf}/3.14159))':d={tf}"
            f":x='{zoom_center_x}':y='{zoom_center_y}':s={w}x{h}"
        ),

        # --- new cinematic moves ---
        "dramatic_zoom_in": (
            f"zoompan=z='min(zoom+0.0035,1.30)':d={tf}"
            f":x='{zoom_center_x}':y='{zoom_center_y}':s={w}x{h}"
        ),
        "dramatic_zoom_out": (
            f"zoompan=z='if(eq(on,1),1.30,max(zoom-0.0035,1.0))':d={tf}"
            f":x='{zoom_center_x}':y='{zoom_center_y}':s={w}x{h}"
        ),
        "cinematic_pan_left": (
            f"zoompan=z='1.15':d={tf}"
            f":x='max({zoom_center_x} - on*0.5, 0)'"
            f":y='{zoom_center_y}':s={w}x{h}"
        ),
        "cinematic_pan_right": (
            f"zoompan=z='1.15':d={tf}"
            f":x='min({zoom_center_x} + on*0.5, iw-iw/zoom)'"
            f":y='{zoom_center_y}':s={w}x{h}"
        ),
        "zoom_in_pan_up": (
            f"zoompan=z='min(zoom+0.002,1.20)':d={tf}"
            f":x='{zoom_center_x}':y='max({zoom_center_y} - on*0.4, 0)':s={w}x{h}"
        ),
    }
    zoompan = filters.get(motion, filters["slow_zoom_in"])
    return f"{zoompan},{_GRADE}"


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

    vf = _build_zoompan_filter(motion, total_frames, preview)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_path,
        "-vf", vf,
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
