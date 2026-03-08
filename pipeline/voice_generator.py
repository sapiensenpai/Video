"""
voice_generator.py
Generates per-scene voiceover audio using the ElevenLabs REST API.
"""

import time
import requests
from pathlib import Path
from pydub import AudioSegment

from utils.config import ELEVENLABS_API_KEY, TEMP_AUDIO_DIR, AUDIO_SILENCE_PADDING_MS

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"

# Fallback voice IDs in priority order
VOICE_FALLBACKS = [
    "N2lVS1w4EtoT3dr4eOWO",  # Callum — young British male
    "pNInz6obpgDQGcFmaJgB",  # Adam
    "21m00Tcm4TlvDq8ikWAM",  # Rachel
]


def _get_working_voice_id(api_key: str) -> str:
    """Try voice IDs in order; return first that is accessible."""
    headers = {"xi-api-key": api_key}
    try:
        resp = requests.get(f"{ELEVENLABS_BASE}/voices", headers=headers, timeout=10)
        if resp.ok:
            available_ids = {v["voice_id"] for v in resp.json().get("voices", [])}
            for vid in VOICE_FALLBACKS:
                if vid in available_ids:
                    return vid
            # Pick first available voice as last resort
            voices = resp.json().get("voices", [])
            if voices:
                return voices[0]["voice_id"]
    except Exception:
        pass
    return VOICE_FALLBACKS[0]


def generate_scene_audio(scene: dict, voice_id: str, voice_settings: dict) -> float:
    """
    Generate TTS audio for a single scene.

    Saves to temp/audio/scene_{nn:02d}.mp3
    Returns the actual duration in seconds (including silence padding).
    """
    nn = scene["scene_number"]
    text = scene["narration"]
    out_path = TEMP_AUDIO_DIR / f"scene_{nn:02d}.mp3"

    if not ELEVENLABS_API_KEY:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not set. "
            "Export it before running: export ELEVENLABS_API_KEY=your_key"
        )

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": voice_settings,
    }

    last_exc = None
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{ELEVENLABS_BASE}/text-to-speech/{voice_id}",
                headers=headers,
                json=payload,
                timeout=60,
            )
            if resp.status_code == 401:
                raise RuntimeError("ElevenLabs API key is invalid or unauthorised.")
            if resp.status_code == 404:
                raise ValueError(f"Voice ID {voice_id!r} not found.")
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            break
        except (ValueError, RuntimeError):
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"ElevenLabs request failed after retries: {last_exc}")

    # Measure actual duration and add silence padding
    audio = AudioSegment.from_mp3(str(out_path))
    silence = AudioSegment.silent(duration=AUDIO_SILENCE_PADDING_MS)
    padded = audio + silence
    padded.export(str(out_path), format="mp3")

    return len(padded) / 1000.0


def generate_all_voices(script: dict, preview: bool = False) -> dict:
    """
    Generate voiceover for every scene in the script.

    Updates each scene dict with 'actual_duration_seconds' and 'audio_path'.
    Returns the updated script.
    """
    api_key = ELEVENLABS_API_KEY
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable is not set.")

    voice_id = script.get("voice_id", VOICE_FALLBACKS[0])
    voice_settings = script.get("voice_settings", {
        "stability": 0.65,
        "similarity_boost": 0.80,
        "style": 0.25,
    })

    scenes = script["scenes"]
    total = len(scenes)

    # Verify the voice is available; fall back if necessary
    working_id = _get_working_voice_id(api_key)
    if working_id != voice_id:
        print(f"  Note: voice {voice_id!r} not available, using {working_id!r} instead.")
        voice_id = working_id

    for i, scene in enumerate(scenes, 1):
        nn = scene["scene_number"]
        print(f"    scene {i}/{total} (scene {nn}: {scene['scene_name']})...", end=" ", flush=True)
        duration = generate_scene_audio(scene, voice_id, voice_settings)
        scene["actual_duration_seconds"] = duration
        scene["audio_path"] = str(TEMP_AUDIO_DIR / f"scene_{nn:02d}.mp3")
        print(f"{duration:.1f}s")

        if preview and i >= 3:
            # In preview mode just do 3 scenes to save time
            for remaining in scenes[i:]:
                remaining["actual_duration_seconds"] = remaining["duration_seconds"]
                remaining["audio_path"] = scene["audio_path"]  # reuse last clip
            break

    return script
