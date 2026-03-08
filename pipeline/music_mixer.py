"""
music_mixer.py
Downloads royalty-free background music (Pixabay) or generates silent placeholder.
Trims/loops to total video duration and reduces volume to -20 dB.
"""

import os
import requests
from pathlib import Path
from utils.audio_compat import AudioSegment

from utils.config import TEMP_DIR, PIXABAY_API_KEY, MUSIC_VOLUME_DB

MUSIC_PATH = TEMP_DIR / "music" / "background.mp3"


def _ensure_music_dir():
    MUSIC_PATH.parent.mkdir(parents=True, exist_ok=True)


def _generate_silence(duration_ms: int) -> AudioSegment:
    return AudioSegment.silent(duration=duration_ms)


def _try_pixabay(duration_ms: int) -> bool:
    """Attempt to fetch a track from Pixabay. Returns True on success."""
    if not PIXABAY_API_KEY:
        return False
    try:
        resp = requests.get(
            "https://pixabay.com/api/music/",
            params={
                "key": PIXABAY_API_KEY,
                "mood": "calm",
                "genre": "ambient",
                "per_page": 3,
            },
            timeout=15,
        )
        if not resp.ok:
            return False
        hits = resp.json().get("hits", [])
        if not hits:
            return False
        audio_url = hits[0].get("audio")
        if not audio_url:
            return False
        audio_resp = requests.get(audio_url, timeout=60)
        if not audio_resp.ok:
            return False
        raw_path = MUSIC_PATH.with_suffix(".raw.mp3")
        raw_path.write_bytes(audio_resp.content)
        track = AudioSegment.from_mp3(str(raw_path))
        # Loop until long enough
        while len(track) < duration_ms + 5000:
            track = track + track
        track = track[:duration_ms + 3000].fade_out(3000)
        track = track + AudioSegment.silent(duration=max(0, duration_ms - len(track)))
        track = track[:duration_ms]
        track = track + MUSIC_VOLUME_DB  # reduce volume
        track.export(str(MUSIC_PATH), format="mp3")
        raw_path.unlink(missing_ok=True)
        return True
    except Exception as exc:
        print(f"    Pixabay music fetch failed: {exc}")
        return False


def prepare_music(total_duration_seconds: float, no_music: bool = False) -> str | None:
    """
    Prepare background music track.
    Returns path to the prepared file, or None if music is disabled/unavailable.
    """
    if no_music:
        return None

    _ensure_music_dir()
    duration_ms = int(total_duration_seconds * 1000) + 3000  # a little extra

    if PIXABAY_API_KEY:
        print("    Trying Pixabay for background music...", end=" ", flush=True)
        if _try_pixabay(duration_ms):
            print("downloaded.")
            return str(MUSIC_PATH)
        print("failed — using silence placeholder.")

    # Fall back to silence
    silence = _generate_silence(duration_ms)
    silence.export(str(MUSIC_PATH), format="mp3")
    print("    No PIXABAY_API_KEY set — using silent background track.")
    return str(MUSIC_PATH)
