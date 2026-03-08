"""
image_processor.py
Resizes/crops screenshots to video-frame size and applies text overlays using Pillow.
Output frames are slightly larger than 1080x1920 to give Ken Burns room to pan/zoom.
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from utils.config import (
    SCREENSHOTS_DIR,
    FONTS_DIR,
    TEMP_FRAMES_DIR,
    FRAME_PADDING,
    FRAME_PADDING_H,
    OUTPUT_WIDTH,
    OUTPUT_HEIGHT,
    BRAND_PURPLE,
    LIGHT_PURPLE,
    GRADIENT_DARK_START,
    GRADIENT_DARK_END,
    WHITE,
)

# --- Colour helpers ---------------------------------------------------------

def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# --- Font loading -----------------------------------------------------------

def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates = [
            str(FONTS_DIR / "Inter-Bold.ttf"),
            str(FONTS_DIR / "Poppins-Bold.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "arialbd.ttf",
            "Arial Bold.ttf",
        ]
    else:
        candidates = [
            str(FONTS_DIR / "Inter-Regular.ttf"),
            str(FONTS_DIR / "Poppins-Regular.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "arial.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    # Last resort: default bitmap font (no size control)
    return ImageFont.load_default()


# --- Background generators --------------------------------------------------

def _dark_gradient(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    top = _hex_to_rgb(GRADIENT_DARK_START)
    bot = _hex_to_rgb(GRADIENT_DARK_END)
    for y in range(height):
        t = y / height
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def _light_gradient(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    top = _hex_to_rgb("#f3e8ff")
    bot = _hex_to_rgb("#ddd6fe")
    for y in range(height):
        t = y / height
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def _placeholder(width: int, height: int, scene_name: str) -> Image.Image:
    img = _dark_gradient(width, height)
    draw = ImageDraw.Draw(img)
    font = _load_font(60)
    draw.text((width // 2, height // 2), scene_name, font=font, fill=(200, 200, 200),
              anchor="mm")
    return img


# --- Cover-crop helper ------------------------------------------------------

def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize to fill target dimensions then centre-crop."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = math.ceil(src_w * scale)
    new_h = math.ceil(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


# --- Text overlay -----------------------------------------------------------

def _draw_text_overlay(
    img: Image.Image,
    line1: str,
    line2: str,
    position: str,
    style: str,
    width: int,
    height: int,
) -> Image.Image:
    if not line1 and not line2:
        return img

    draw = ImageDraw.Draw(img, "RGBA")

    font1 = _load_font(60, bold=True)
    font2 = _load_font(44, bold=True)

    # Colour config per style
    style_map = {
        "bold_white_on_dark":   {"text": (255, 255, 255), "outline": (0, 0, 0),     "shadow": True},
        "bold_white_outline":   {"text": (255, 255, 255), "outline": (0, 0, 0),     "shadow": False},
        "brand_purple":         {"text": _hex_to_rgb(BRAND_PURPLE), "outline": None, "shadow": False},
        "brand_purple_bold":    {"text": _hex_to_rgb(BRAND_PURPLE), "outline": None, "shadow": False},
    }
    cfg = style_map.get(style, style_map["bold_white_outline"])

    # Measure text bounding boxes
    def text_size(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    w1, h1 = text_size(line1, font1) if line1 else (0, 0)
    w2, h2 = text_size(line2, font2) if line2 else (0, 0)
    gap = 16
    block_h = h1 + (gap + h2 if line2 else 0)

    # Vertical position
    if position == "center":
        y_start = (height - block_h) // 2
    elif position == "top":
        y_start = int(height * 0.08)
    elif position == "bottom":
        y_start = int(height * 0.82)
    elif position == "below_center":
        y_start = int(height * 0.58)
    else:
        y_start = int(height * 0.82)

    # Semi-transparent background rectangle for readability (on screenshot scenes)
    if style in ("bold_white_outline", "bold_white_on_dark"):
        pad = 20
        max_w = max(w1, w2) + pad * 2
        rect_top = y_start - pad
        rect_bot = y_start + block_h + pad
        draw.rectangle(
            [(width // 2 - max_w // 2, rect_top), (width // 2 + max_w // 2, rect_bot)],
            fill=(0, 0, 0, 140),
        )

    def draw_text_line(text, font, y, color, outline_color, shadow):
        x = width // 2
        if shadow:
            for dx, dy in [(2, 2), (-2, 2), (2, -2), (-2, -2)]:
                draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 200), anchor="mt")
        if outline_color:
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font,
                                  fill=outline_color + (255,) if len(outline_color) == 3 else outline_color,
                                  anchor="mt")
        draw.text((x, y), text, font=font, fill=color, anchor="mt")

    outline = cfg["outline"]
    outline_rgba = outline if outline else None
    color = cfg["text"]

    if line1:
        draw_text_line(line1, font1, y_start, color, outline_rgba, cfg["shadow"])
    if line2:
        draw_text_line(line2, font2, y_start + h1 + gap, color, outline_rgba, cfg["shadow"])

    return img


# --- Main public function ----------------------------------------------------

def process_scene_image(scene: dict, preview: bool = False) -> str:
    """
    Process a scene's screenshot (or generate a background) and save as a PNG frame.
    Returns the path to the saved frame.
    """
    nn = scene["scene_number"]
    out_path = TEMP_FRAMES_DIR / f"scene_{nn:02d}.png"

    target_w = FRAME_PADDING
    target_h = FRAME_PADDING_H
    if preview:
        target_w = target_w // 2
        target_h = target_h // 2

    screenshot = scene.get("screenshot")
    background = scene.get("background")

    # --- Build base image ---
    if screenshot is None:
        # Generated background
        if background == "light_gradient_purple":
            img = _light_gradient(target_w, target_h)
        else:
            img = _dark_gradient(target_w, target_h)
    else:
        src_path = SCREENSHOTS_DIR / screenshot
        if src_path.exists():
            raw = Image.open(str(src_path)).convert("RGB")
            # For logo scene use light gradient base + centred logo
            if background == "light_gradient_purple":
                base = _light_gradient(target_w, target_h)
                # Scale logo to fit 60% of width
                logo_w = int(target_w * 0.6)
                scale = logo_w / raw.width
                logo_h = int(raw.height * scale)
                raw_resized = raw.resize((logo_w, logo_h), Image.LANCZOS)
                paste_x = (target_w - logo_w) // 2
                paste_y = int(target_h * 0.2)
                base.paste(raw_resized, (paste_x, paste_y))
                img = base
            else:
                img = _cover_crop(raw, target_w, target_h)
        else:
            print(f"    WARNING: screenshot {screenshot!r} not found — using placeholder.")
            img = _placeholder(target_w, target_h, scene["scene_name"])

    # --- Apply text overlay ---
    overlay = scene.get("text_overlay", {})
    if overlay:
        img = _draw_text_overlay(
            img,
            overlay.get("line1", ""),
            overlay.get("line2", ""),
            overlay.get("position", "bottom"),
            overlay.get("style", "bold_white_outline"),
            target_w,
            target_h,
        )

    img.save(str(out_path), "PNG")
    return str(out_path)


def process_all_images(script: dict, preview: bool = False) -> dict:
    """Process images for all scenes. Updates each scene with 'frame_path'."""
    scenes = script["scenes"]
    total = len(scenes)
    for i, scene in enumerate(scenes, 1):
        print(f"    scene {i}/{total} ({scene['scene_name']})...", end=" ", flush=True)
        path = process_scene_image(scene, preview=preview)
        scene["frame_path"] = path
        print("done")
    return script
