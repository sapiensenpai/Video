#!/usr/bin/env python3
"""
main.py — MyMeds UK AI Video Ad Generator
Run with: python main.py [--preview] [--no-music] [--no-subs]
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
# Ensure project root is on the path when running from any working directory   #
# --------------------------------------------------------------------------- #
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import ensure_dirs, ELEVENLABS_API_KEY, TEMP_DIR
from pipeline.script_generator import get_script
from pipeline.voice_generator import generate_all_voices
from pipeline.image_processor import process_all_images
from pipeline.motion_engine import apply_motion_to_all
from pipeline.subtitle_engine import generate_subtitles
from pipeline.music_mixer import prepare_music
from pipeline.video_assembler import assemble_video


def _check_ffmpeg():
    if not shutil.which("ffmpeg"):
        print(
            "\n[ERROR] ffmpeg is not installed or not on PATH.\n"
            "Install it with:\n"
            "  Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  Mac:           brew install ffmpeg\n"
        )
        sys.exit(1)


def _cleanup_temp():
    try:
        shutil.rmtree(str(TEMP_DIR))
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Generate the MyMeds UK promotional video ad."
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Generate a low-resolution preview (540x960) for faster testing.",
    )
    parser.add_argument(
        "--no-music",
        action="store_true",
        help="Skip background music.",
    )
    parser.add_argument(
        "--no-subs",
        action="store_true",
        help="Skip subtitle generation.",
    )
    args = parser.parse_args()

    preview = args.preview
    no_music = args.no_music
    no_subs = args.no_subs

    if preview:
        print("\n** PREVIEW MODE — generating 540x960 low-res version **\n")

    start_time = time.time()

    # --- Pre-flight checks ---
    _check_ffmpeg()

    # --- Create directories ---
    ensure_dirs()
    # Ensure temp subdirs exist after potential cleanup
    (TEMP_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (TEMP_DIR / "frames").mkdir(parents=True, exist_ok=True)
    (TEMP_DIR / "clips").mkdir(parents=True, exist_ok=True)
    (TEMP_DIR / "music").mkdir(parents=True, exist_ok=True)

    try:
        # ------------------------------------------------------------------- #
        # Step 1 — Load script                                                 #
        # ------------------------------------------------------------------- #
        print("[1/7] Loading script...", end=" ", flush=True)
        script = get_script()
        scenes = script["scenes"]
        total_target = script["total_target_duration"]
        print(f"✓ ({len(scenes)} scenes, ~{total_target}s target)")

        # ------------------------------------------------------------------- #
        # Step 2 — Generate voiceover                                          #
        # ------------------------------------------------------------------- #
        print(f"[2/7] Generating voiceover via ElevenLabs...")
        if not ELEVENLABS_API_KEY:
            print(
                "\n[ERROR] ELEVENLABS_API_KEY is not set.\n"
                "Set it before running:\n"
                "  export ELEVENLABS_API_KEY=sk_your_key_here\n"
            )
            sys.exit(1)
        script = generate_all_voices(script, preview=preview)
        total_actual = sum(s.get("actual_duration_seconds", s["duration_seconds"]) for s in scenes)
        print(f"  ✓ Voiceover complete. Total audio duration: {total_actual:.1f}s")

        # ------------------------------------------------------------------- #
        # Step 3 — Process screenshots                                         #
        # ------------------------------------------------------------------- #
        print("[3/7] Processing screenshots...")
        script = process_all_images(script, preview=preview)
        print("  ✓ All frames processed.")

        # ------------------------------------------------------------------- #
        # Step 4 — Apply Ken Burns motion                                      #
        # ------------------------------------------------------------------- #
        print("[4/7] Applying Ken Burns motion effects...")
        script = apply_motion_to_all(script, preview=preview)
        print("  ✓ Motion effects applied.")

        # ------------------------------------------------------------------- #
        # Step 5 — Generate subtitles                                          #
        # ------------------------------------------------------------------- #
        if not no_subs:
            print("[5/7] Generating subtitles...", end=" ", flush=True)
            subs_path = generate_subtitles(script, preview=preview)
            print(f"✓ ({subs_path})")
        else:
            print("[5/7] Subtitles skipped (--no-subs).")

        # ------------------------------------------------------------------- #
        # Step 6 — Prepare background music                                    #
        # ------------------------------------------------------------------- #
        print("[6/7] Preparing background music...")
        music_path = prepare_music(total_actual, no_music=no_music)
        if music_path:
            print(f"  ✓ Music ready: {music_path}")
        else:
            print("  ✓ No music (skipped).")

        # ------------------------------------------------------------------- #
        # Step 7 — Assemble final video                                        #
        # ------------------------------------------------------------------- #
        print("[7/7] Assembling final video...")
        output_path = assemble_video(
            script,
            music_path=music_path,
            no_subs=no_subs,
            preview=preview,
        )

        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"  VIDEO COMPLETE!")
        print(f"  Output: {output_path}")
        print(f"  Duration: ~{total_actual:.0f}s")
        print(f"  Elapsed: {elapsed:.0f}s")
        print(f"{'='*60}\n")

    finally:
        _cleanup_temp()


if __name__ == "__main__":
    main()
