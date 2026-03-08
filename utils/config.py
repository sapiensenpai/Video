import os
from pathlib import Path

# --- Project Paths ---
BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets"
SCREENSHOTS_DIR = ASSETS_DIR / "screenshots"
LOGO_DIR = ASSETS_DIR / "logo"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
TEMP_AUDIO_DIR = TEMP_DIR / "audio"
TEMP_FRAMES_DIR = TEMP_DIR / "frames"
TEMP_CLIPS_DIR = TEMP_DIR / "clips"

# --- API Keys ---
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")

# --- Brand Colours ---
BRAND_PURPLE = "#7B2FBE"
LIGHT_PURPLE = "#D8B4FE"
GRADIENT_DARK_START = "#1a0a2e"
GRADIENT_DARK_END = "#4a1a6b"
ACCENT_PINK = "#E879F9"
WHITE = "#FFFFFF"
DARK_TEXT = "#1A1A1A"

# --- Video Settings ---
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
FRAME_RATE = 30
FRAME_PADDING = 1200   # slightly larger than output for Ken Burns room
FRAME_PADDING_H = 2134

# --- Audio Settings ---
AUDIO_SILENCE_PADDING_MS = 300   # 0.3s silence after each clip
MUSIC_VOLUME_DB = -20

def ensure_dirs():
    """Create all required directories if they don't exist."""
    for d in [
        SCREENSHOTS_DIR, LOGO_DIR, FONTS_DIR, OUTPUT_DIR,
        TEMP_AUDIO_DIR, TEMP_FRAMES_DIR, TEMP_CLIPS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)
