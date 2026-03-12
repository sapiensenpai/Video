"""
ai_visual_engine.py

AI-powered visual generation using Replicate APIs.

Flow per scene:
  1. Generate a cinematic start-frame image (FLUX dev, optionally seeded from
     the previous scene's last frame for seamless visual continuity).
  2. Feed the start-frame into an image-to-video model (minimax/video-01)
     to produce a realistic motion clip.
  3. Extract the last frame of that clip → becomes the next scene's seed image.

This creates a "flowing" video where each scene visually evolves from the one
before it — similar to Runway, Kling, or Google VideoFX story-mode generation.

Usage:
  python main.py --ai-video
  (requires REPLICATE_API_TOKEN environment variable)
"""

import os
import io
import subprocess
import urllib.request
from pathlib import Path

from utils.config import (
    REPLICATE_API_TOKEN,
    TEMP_DIR,
    TEMP_FRAMES_DIR,
    TEMP_CLIPS_DIR,
)

# ---------------------------------------------------------------------------
# Cinematic style suffix appended to every generated image prompt
# ---------------------------------------------------------------------------
_STYLE = (
    "9:16 vertical video frame, ultra-cinematic, professional app advertisement, "
    "dark moody purple and deep blue atmosphere, volumetric studio lighting, "
    "soft bokeh depth of field, premium medical wellness brand, "
    "photorealistic, 8K, sharp focus"
)

# ---------------------------------------------------------------------------
# Per-scene visual prompt overrides
# ---------------------------------------------------------------------------
_SCENE_PROMPTS: dict[str, str] = {
    "HOOK": (
        "extreme close-up of anxious person's face bathed in cold smartphone glow, "
        "dark bedroom, Google search results reflected in glasses, worried expression, "
        "deep purple shadows, cinematic noir lighting"
    ),
    "THE_PROBLEM": (
        "person scrolling frantically through chaotic medical websites on phone, "
        "overlapping American and British flags symbolising wrong country info, "
        "frustrated expression, cluttered information overload, dark moody tones"
    ),
    "INTRODUCE_SOLUTION": (
        "elegant smartphone floating in space showing clean purple health app logo, "
        "soft white and lavender light rays emanating from screen, "
        "pristine white background with purple gradient, premium product photography"
    ),
    "FEATURE_SEARCH": (
        "sleek smartphone showing a beautifully designed medication search list UI, "
        "floating above deep purple gradient, soft lens flare, "
        "clean minimal interface visible, professional tech photography"
    ),
    "FEATURE_AI_CHAT": (
        "close-up of phone screen showing an AI chat conversation about medication, "
        "warm ambient purple glow on person's face, focused calm expression, "
        "futuristic but approachable, soft bokeh background"
    ),
    "FEATURE_INTERACTIONS": (
        "two prescription medication bottles with a glowing warning symbol between them, "
        "phone screen showing interaction checker result, dramatic purple side lighting, "
        "clinical yet cinematic, dark background"
    ),
    "FEATURE_REMINDERS": (
        "phone showing colorful medication reminder calendar propped on bedside table, "
        "morning golden hour light mixing with purple tones, "
        "pill organiser in soft focus behind phone, warm and reassuring"
    ),
    "FEATURE_NHS": (
        "NHS prescription paper held up to phone camera with blue scan beam, "
        "NHS branding merging with purple app identity, clean clinical environment, "
        "high-tech barcode scanning visual effect"
    ),
    "TRUST_PRIVACY": (
        "abstract glowing digital privacy shield with padlock, "
        "flowing data particles in purple and white, "
        "GDPR text subtly embedded in background, secure encrypted aesthetic"
    ),
    "CTA_CLOSE": (
        "three iPhones arranged in a perfect arc showing beautiful purple health app UI, "
        "App Store badge floating above, deep purple to black radial gradient background, "
        "premium Apple-style product photography, hero shot"
    ),
}


def _ensure_replicate():
    """Import replicate and set API token, raising if unavailable."""
    try:
        import replicate as _replicate
    except ImportError:
        raise RuntimeError(
            "The 'replicate' package is not installed.\n"
            "Run:  pip install replicate"
        )
    if not REPLICATE_API_TOKEN:
        raise RuntimeError(
            "REPLICATE_API_TOKEN is not set.\n"
            "Export it before running:  export REPLICATE_API_TOKEN=r8_your_key"
        )
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
    return _replicate


def _download(url: str, dest: Path) -> Path:
    """Download a URL to dest, handling both plain strings and FileOutput objects."""
    url_str = url if isinstance(url, str) else str(url)
    # FileOutput objects from newer replicate SDK may support .url attribute
    if hasattr(url, "url"):
        url_str = str(url.url)
    urllib.request.urlretrieve(url_str, str(dest))
    return dest


def _build_prompt(scene: dict) -> str:
    scene_name = scene["scene_name"]
    visual = _SCENE_PROMPTS.get(scene_name, "professional medical app advertisement on smartphone")
    return f"{visual}, {_STYLE}"


# ---------------------------------------------------------------------------
# Stage 1 — Generate start-frame image via FLUX dev
# ---------------------------------------------------------------------------

def _generate_start_frame(
    replicate,
    prompt: str,
    scene_num: int,
    last_frame_path: Path | None,
) -> Path:
    """
    Generate a cinematic start-frame image.

    If last_frame_path is provided, FLUX dev treats it as an image-to-image
    reference (prompt_strength=0.65), ensuring visual style continuity from
    the previous scene.
    """
    out_path = TEMP_FRAMES_DIR / f"ai_start_{scene_num:02d}.png"

    if last_frame_path and last_frame_path.exists():
        with open(str(last_frame_path), "rb") as f:
            output = replicate.run(
                "black-forest-labs/flux-dev",
                input={
                    "prompt": prompt,
                    "image": f,
                    "prompt_strength": 0.65,  # 0 = clone image, 1 = ignore image
                    "num_inference_steps": 28,
                    "aspect_ratio": "9:16",
                    "output_format": "png",
                },
            )
    else:
        output = replicate.run(
            "black-forest-labs/flux-dev",
            input={
                "prompt": prompt,
                "num_inference_steps": 28,
                "aspect_ratio": "9:16",
                "output_format": "png",
            },
        )

    # output is a list; first item is a URL string or FileOutput
    result = output[0] if isinstance(output, list) else output
    _download(result, out_path)
    return out_path


# ---------------------------------------------------------------------------
# Stage 2 — Generate video clip from start-frame via minimax/video-01
# ---------------------------------------------------------------------------

def _generate_video_clip(
    replicate,
    start_frame_path: Path,
    prompt: str,
    duration: float,
    scene_num: int,
) -> Path:
    """
    Generate a video clip from a start-frame image using minimax/video-01.
    minimax generates ~6 second clips; we trim or loop to match scene duration.
    """
    raw_path = TEMP_CLIPS_DIR / f"scene_{scene_num:02d}_raw.mp4"
    out_path = TEMP_CLIPS_DIR / f"scene_{scene_num:02d}.mp4"

    with open(str(start_frame_path), "rb") as f:
        output = replicate.run(
            "minimax/video-01",
            input={
                "prompt": prompt,
                "first_frame_image": f,
            },
        )

    # minimax returns a single URL/FileOutput
    url = output if isinstance(output, str) else output
    _download(url, raw_path)

    # Trim or loop to match the required scene duration
    _fit_to_duration(raw_path, out_path, duration)
    return out_path


def _fit_to_duration(src: Path, dst: Path, target: float):
    """Trim or loop src clip to exactly target seconds, writing to dst."""
    # Get actual clip duration
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(src),
        ],
        capture_output=True, text=True,
    )
    try:
        actual = float(result.stdout.strip())
    except ValueError:
        actual = target  # assume it's fine if we can't measure

    if actual >= target:
        # Just trim
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), "-t", str(target), "-c", "copy", str(dst)],
            capture_output=True,
        )
    else:
        # Loop then trim
        loops = int(target / actual) + 2
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-stream_loop", str(loops),
                "-i", str(src),
                "-t", str(target),
                "-c", "copy",
                str(dst),
            ],
            capture_output=True,
        )
    # Ensure dst exists (fallback: just copy src as-is)
    if not dst.exists():
        import shutil
        shutil.copy(str(src), str(dst))


# ---------------------------------------------------------------------------
# Stage 3 — Extract last frame for next-scene continuity
# ---------------------------------------------------------------------------

def _extract_last_frame(clip_path: Path, scene_num: int) -> Path | None:
    """Extract the very last frame of a video clip as a PNG."""
    out_path = TEMP_FRAMES_DIR / f"last_frame_{scene_num:02d}.png"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-sseof", "-0.5",          # seek to 0.5s before end
            "-i", str(clip_path),
            "-vframes", "1",
            "-q:v", "2",
            str(out_path),
        ],
        capture_output=True,
    )
    return out_path if out_path.exists() else None


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def generate_ai_video_scenes(script: dict, preview: bool = False) -> dict:
    """
    Generate AI visuals for every scene in the script.

    Each scene goes through three stages:
      1. FLUX dev generates a cinematic start-frame (seeded from previous last-frame
         for visual continuity — this is the "flow" between scenes).
      2. minimax/video-01 animates that start-frame into a ~6s video clip.
      3. The clip's last frame is extracted to seed the next scene.

    Falls back to screenshot/Ken Burns rendering if any stage fails for a scene.

    Updates each scene dict with:
      - "frame_path"  → path to the AI-generated start frame PNG
      - "clip_path"   → path to the generated MP4 clip
    """
    replicate = _ensure_replicate()

    scenes = script["scenes"]
    total = len(scenes)
    last_frame_path: Path | None = None

    for i, scene in enumerate(scenes, 1):
        scene_num = scene["scene_number"]
        duration = scene.get("actual_duration_seconds", scene["duration_seconds"])
        prompt = _build_prompt(scene)

        print(f"    scene {i}/{total} ({scene['scene_name']}):")
        try:
            # --- Stage 1: start frame --------------------------------------
            seed_desc = "seeded from prev last-frame" if last_frame_path else "fresh generation"
            print(f"      [1/3] Generating start frame ({seed_desc})...", end=" ", flush=True)
            start_frame = _generate_start_frame(replicate, prompt, scene_num, last_frame_path)
            scene["frame_path"] = str(start_frame)
            print("done")

            # --- Stage 2: video clip ---------------------------------------
            print(f"      [2/3] Animating clip ({duration:.1f}s target)...", end=" ", flush=True)
            clip_path = _generate_video_clip(replicate, start_frame, prompt, duration, scene_num)
            scene["clip_path"] = str(clip_path)
            print("done")

            # --- Stage 3: extract last frame for continuity ---------------
            print(f"      [3/3] Extracting last frame...", end=" ", flush=True)
            last_frame_path = _extract_last_frame(clip_path, scene_num)
            print("done" if last_frame_path else "skipped (could not extract)")

        except Exception as exc:
            print(f"\n      ⚠ AI generation failed: {exc}")
            print(f"        Falling back to screenshot + Ken Burns for this scene...")
            # Graceful fallback: standard pipeline for this scene
            from pipeline.image_processor import process_scene_image
            from pipeline.motion_engine import apply_motion_to_scene
            frame_path = process_scene_image(scene, preview=preview)
            scene["frame_path"] = frame_path
            clip_path = apply_motion_to_scene(scene, preview=preview)
            scene["clip_path"] = clip_path
            last_frame_path = None  # break the continuity chain at failure points

    return script
