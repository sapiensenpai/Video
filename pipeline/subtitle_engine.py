"""
subtitle_engine.py
Generates an ASS subtitle file for styled lower-third captions.
"""

from pathlib import Path
from utils.config import TEMP_DIR, OUTPUT_WIDTH, OUTPUT_HEIGHT

# TikTok-style: large white bold text, thick black outline, centre-screen
# Alignment 5 = middle-centre; BorderStyle 1 = outline+shadow; Outline 5px
ASS_HEADER = """\
[Script Info]
Title: MyMeds UK Ad
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,76,&H00FFFFFF,&H000000FF,&H00000000,&HB4000000,-1,0,0,0,100,100,1,0,1,5,0,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _seconds_to_ass(t: float) -> str:
    """Convert float seconds to ASS timestamp h:mm:ss.cc"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int((t - int(t)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _chunk_text(text: str, words_per_chunk: int = 3) -> list[str]:
    """Split narration into short, punchy caption chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), words_per_chunk):
        chunks.append(" ".join(words[i:i + words_per_chunk]))
    return chunks


def generate_subtitles(script: dict, preview: bool = False) -> str:
    """
    Generate an ASS subtitle file covering all scenes.
    Returns the path to the saved .ass file.
    """
    out_path = TEMP_DIR / "subtitles.ass"

    play_w = OUTPUT_WIDTH if not preview else OUTPUT_WIDTH // 2
    play_h = OUTPUT_HEIGHT if not preview else OUTPUT_HEIGHT // 2

    header = ASS_HEADER.format(play_res_x=play_w, play_res_y=play_h)
    lines = [header]

    current_time = 0.0

    for scene in script["scenes"]:
        duration = scene.get("actual_duration_seconds", scene["duration_seconds"])
        narration = scene["narration"]

        chunks = _chunk_text(narration, words_per_chunk=3)
        if not chunks:
            current_time += duration
            continue

        chunk_dur = duration / len(chunks)

        for chunk in chunks:
            start = current_time
            end = current_time + chunk_dur
            safe_chunk = chunk.replace("{", "\\{").replace("}", "\\}")
            line = (
                f"Dialogue: 0,{_seconds_to_ass(start)},{_seconds_to_ass(end)},"
                f"Default,,0,0,0,,{safe_chunk}"
            )
            lines.append(line)
            current_time += chunk_dur

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)
