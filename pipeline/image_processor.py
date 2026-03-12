"""
image_processor.py
Resizes/crops screenshots to video-frame size and applies text overlays using Pillow.
Output frames are slightly larger than 1080x1920 to give Ken Burns room to pan/zoom.

For app-screenshot scenes, composites the screenshot into a realistic phone mockup
over a blurred, brand-tinted version of the same screenshot.
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


# --- Phone mockup composite -------------------------------------------------

def _phone_mockup_frame(raw: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Compose a professional phone-mockup frame:
      - Full-bleed blurred + brand-tinted background from the screenshot
      - Realistic phone body (dark bezel, rounded corners) centred on canvas
      - App screenshot fitted into the phone screen
      - Subtle gloss highlight and drop shadow for depth
    """
    # 1. Blurred background ------------------------------------------------
    bg = _cover_crop(raw.copy(), target_w, target_h).convert("RGBA")
    bg_blur = bg.filter(ImageFilter.GaussianBlur(radius=40))
    # Dark + brand-purple tint overlay
    tint = Image.new("RGBA", bg.size, (*_hex_to_rgb("#1a0a2e"), 170))
    bg_blur.alpha_composite(tint)
    canvas = bg_blur

    # 2. Phone geometry ----------------------------------------------------
    phone_h = int(target_h * 0.72)
    phone_w = int(phone_h / 2.17)          # iPhone 14 Pro aspect ≈ 1:2.17
    phone_x = (target_w - phone_w) // 2
    phone_y = int(target_h * 0.11)

    corner_r     = int(phone_w * 0.095)    # outer corner radius
    bezel_side   = int(phone_w * 0.032)
    bezel_top    = int(phone_h * 0.055)
    bezel_bot    = int(phone_h * 0.038)

    screen_x = phone_x + bezel_side
    screen_y = phone_y + bezel_top
    screen_w = phone_w - bezel_side * 2
    screen_h = phone_h - bezel_top - bezel_bot
    screen_cr = max(2, corner_r - bezel_side)

    # 3. Drop shadow -------------------------------------------------------
    shadow = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle(
        [phone_x + 18, phone_y + 28, phone_x + phone_w + 18, phone_y + phone_h + 28],
        radius=corner_r, fill=(0, 0, 0, 140),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=22))
    canvas.alpha_composite(shadow)

    # 4. Phone body --------------------------------------------------------
    body = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(body)
    # Outer frame — very dark charcoal with slight purple tint
    bdraw.rounded_rectangle(
        [phone_x, phone_y, phone_x + phone_w, phone_y + phone_h],
        radius=corner_r, fill=(22, 18, 30, 255),
    )
    # Inner bezel rim (slightly lighter) — gives a metallic edge feel
    rim_inset = max(2, bezel_side // 3)
    bdraw.rounded_rectangle(
        [phone_x + rim_inset, phone_y + rim_inset,
         phone_x + phone_w - rim_inset, phone_y + phone_h - rim_inset],
        radius=max(2, corner_r - rim_inset), fill=(38, 32, 50, 255),
    )
    canvas.alpha_composite(body)

    # 5. Screenshot inside phone screen ------------------------------------
    screen_img = _cover_crop(raw.copy(), screen_w, screen_h).convert("RGBA")

    # Rounded mask matching screen corners
    screen_mask = Image.new("L", (screen_w, screen_h), 0)
    ImageDraw.Draw(screen_mask).rounded_rectangle(
        [0, 0, screen_w - 1, screen_h - 1], radius=screen_cr, fill=255,
    )
    canvas.paste(screen_img, (screen_x, screen_y), mask=screen_mask)

    # 6. Dynamic island / notch -------------------------------------------
    notch_w = int(screen_w * 0.28)
    notch_h = int(screen_h * 0.025)
    notch_h = max(notch_h, 18)
    notch_x = screen_x + (screen_w - notch_w) // 2
    notch_y = screen_y + int(screen_h * 0.008)

    notch_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    ImageDraw.Draw(notch_layer).rounded_rectangle(
        [notch_x, notch_y, notch_x + notch_w, notch_y + notch_h],
        radius=notch_h // 2, fill=(15, 12, 20, 250),
    )
    canvas.alpha_composite(notch_layer)

    # 7. Gloss highlight (top third of phone, subtle white sheen) ----------
    gloss = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).rounded_rectangle(
        [phone_x + 2, phone_y + 2,
         phone_x + phone_w - 2, phone_y + int(phone_h * 0.28)],
        radius=corner_r, fill=(255, 255, 255, 16),
    )
    canvas.alpha_composite(gloss)

    # 8. Subtle brand-purple glow behind phone bottom ----------------------
    glow = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_cx = target_w // 2
    glow_cy = phone_y + phone_h + int(phone_h * 0.05)
    glow_rx, glow_ry = int(phone_w * 0.7), int(phone_h * 0.08)
    glow_draw.ellipse(
        [glow_cx - glow_rx, glow_cy - glow_ry,
         glow_cx + glow_rx, glow_cy + glow_ry],
        fill=(*_hex_to_rgb(BRAND_PURPLE), 80),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=35))
    canvas.alpha_composite(glow)

    return canvas.convert("RGB")


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

    style_map = {
        "bold_white_on_dark":   {"text": (255, 255, 255), "outline": (0, 0, 0),     "shadow": True},
        "bold_white_outline":   {"text": (255, 255, 255), "outline": (0, 0, 0),     "shadow": False},
        "brand_purple":         {"text": _hex_to_rgb(BRAND_PURPLE), "outline": None, "shadow": False},
        "brand_purple_bold":    {"text": _hex_to_rgb(BRAND_PURPLE), "outline": None, "shadow": False},
    }
    cfg = style_map.get(style, style_map["bold_white_outline"])

    def text_size(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    w1, h1 = text_size(line1, font1) if line1 else (0, 0)
    w2, h2 = text_size(line2, font2) if line2 else (0, 0)
    gap = 16
    block_h = h1 + (gap + h2 if line2 else 0)

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

    if style in ("bold_white_outline", "bold_white_on_dark"):
        pad = 20
        max_w = max(w1, w2) + pad * 2
        draw.rectangle(
            [(width // 2 - max_w // 2, y_start - pad),
             (width // 2 + max_w // 2, y_start + block_h + pad)],
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
    color = cfg["text"]

    if line1:
        draw_text_line(line1, font1, y_start, color, outline, cfg["shadow"])
    if line2:
        draw_text_line(line2, font2, y_start + h1 + gap, color, outline, cfg["shadow"])

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
        if background == "light_gradient_purple":
            img = _light_gradient(target_w, target_h)
        else:
            img = _dark_gradient(target_w, target_h)
    else:
        src_path = SCREENSHOTS_DIR / screenshot
        if src_path.exists():
            raw = Image.open(str(src_path)).convert("RGB")
            if background == "light_gradient_purple":
                # Logo scene: light gradient + centred logo
                base = _light_gradient(target_w, target_h)
                logo_w = int(target_w * 0.6)
                scale = logo_w / raw.width
                logo_h = int(raw.height * scale)
                raw_resized = raw.resize((logo_w, logo_h), Image.LANCZOS)
                paste_x = (target_w - logo_w) // 2
                paste_y = int(target_h * 0.2)
                base.paste(raw_resized, (paste_x, paste_y))
                img = base
            else:
                # App screenshot: phone mockup composite
                img = _phone_mockup_frame(raw, target_w, target_h)
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
