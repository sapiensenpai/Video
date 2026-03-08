"""
video_assembler.py
Assembles scene clips, narration audio, optional music, and subtitles into
the final output video using FFmpeg and pydub.
"""

import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from utils.audio_compat import AudioSegment

from utils.config import (
    TEMP_DIR, OUTPUT_DIR,
    MUSIC_VOLUME_DB,
)


def _concat_video_clips(scenes: list[dict]) -> Path:
    """Concatenate silent scene clips into one video file."""
    concat_file = TEMP_DIR / "concat.txt"
    lines = []
    for scene in scenes:
        clip = scene.get("clip_path", "")
        if clip and Path(clip).exists():
            lines.append(f"file '{clip}'")

    concat_file.write_text("\n".join(lines))

    out = TEMP_DIR / "video_no_audio.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(out),
    ]
    _run(cmd, "concat video clips")
    return out


def _concat_narration(scenes: list[dict]) -> Path:
    """Join all scene audio files into a single narration track."""
    combined = AudioSegment.empty()
    for scene in scenes:
        audio_path = scene.get("audio_path", "")
        if audio_path and Path(audio_path).exists():
            try:
                combined += AudioSegment.from_mp3(audio_path)
            except Exception as exc:
                print(f"    Warning: could not read audio for scene {scene['scene_number']}: {exc}")
                dur = scene.get("actual_duration_seconds", scene["duration_seconds"])
                combined += AudioSegment.silent(duration=int(dur * 1000))
        else:
            dur = scene.get("actual_duration_seconds", scene["duration_seconds"])
            combined += AudioSegment.silent(duration=int(dur * 1000))

    out = TEMP_DIR / "narration_full.mp3"
    combined.export(str(out), format="mp3")
    return out


def _mix_audio(narration_path: Path, music_path: str | None) -> Path:
    """Overlay background music under narration. Returns path to mixed audio."""
    narration = AudioSegment.from_mp3(str(narration_path))
    out = TEMP_DIR / "audio_mixed.mp3"

    if music_path and Path(music_path).exists():
        music = AudioSegment.from_mp3(music_path)
        music = music + MUSIC_VOLUME_DB
        # Pad or trim music to match narration length
        if len(music) < len(narration):
            loops = (len(narration) // len(music)) + 1
            music = music * loops
        music = music[:len(narration)]
        mixed = narration.overlay(music)
        mixed.export(str(out), format="mp3")
    else:
        narration.export(str(out), format="mp3")

    return out


def _run(cmd: list[str], step: str):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n  FFmpeg error during '{step}':")
        print("  CMD:", " ".join(cmd))
        print("  STDERR:", result.stderr[-2000:])
        raise RuntimeError(f"FFmpeg failed: {step}")


def assemble_video(
    script: dict,
    music_path: str | None,
    no_subs: bool = False,
    preview: bool = False,
) -> str:
    """
    Full assembly pipeline:
    1. Concatenate scene clips
    2. Build narration audio
    3. Mix with music
    4. Burn subtitles + combine with audio
    5. Save to output/

    Returns path to the final video.
    """
    scenes = script["scenes"]
    title = script.get("title", "MyMeds_UK_Ad")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_preview" if preview else ""
    final_path = OUTPUT_DIR / f"{title}{suffix}_{timestamp}.mp4"

    print("    Concatenating video clips...", end=" ", flush=True)
    video_no_audio = _concat_video_clips(scenes)
    print("done")

    print("    Building narration audio...", end=" ", flush=True)
    narration_full = _concat_narration(scenes)
    print("done")

    print("    Mixing audio...", end=" ", flush=True)
    audio_mixed = _mix_audio(narration_full, music_path)
    print("done")

    print("    Encoding final video...", end=" ", flush=True)
    subs_file = TEMP_DIR / "subtitles.ass"

    if not no_subs and subs_file.exists():
        # Escape path for FFmpeg filter (handle colons on Windows paths)
        subs_str = str(subs_file).replace("\\", "/").replace(":", "\\:")
        vf = f"ass={subs_str}"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_no_audio),
            "-i", str(audio_mixed),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "medium" if not preview else "ultrafast",
            "-crf", "18" if not preview else "28",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(final_path),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_no_audio),
            "-i", str(audio_mixed),
            "-c:v", "libx264",
            "-preset", "medium" if not preview else "ultrafast",
            "-crf", "18" if not preview else "28",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(final_path),
        ]

    _run(cmd, "final encode")
    print("done")

    return str(final_path)
