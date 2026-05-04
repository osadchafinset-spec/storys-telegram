import io
import base64
import logging
import random
from pathlib import Path

from google import genai
from PIL import Image, ImageDraw, ImageFont

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

CANVAS_W = 1080
CANVAS_H = 1920

STYLES = {
    "Мінімалізм": "minimalist clean background, white tones, soft light",
    "Темний преміум": "dark premium, black and gold, cinematic lighting",
    "Яскравий поп": "bright vibrant colors, trendy social media aesthetic",
    "Пастельний": "soft pastel colors, gentle gradients",
    "Фото": "photorealistic, cinematic lighting",
}

DEFAULT_STYLE = "Мінімалізм"

_client = genai.Client(api_key=GEMINI_API_KEY)

# =========================================
# ANALYZE REFERENCE
# =========================================

async def analyze_reference(image_bytes: bytes) -> str | None:
    try:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = _client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {
                    "parts": [
                        {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                        {"text": "Describe visual style for Instagram Story background. Colors, light, mood."},
                    ]
                }
            ],
        )

        if response and response.text:
            return response.text.strip()

        return None

    except Exception as e:
        logger.error("Reference analysis error: %s", e)
        return None


# =========================================
# GENERATE BACKGROUND
# =========================================

async def generate_background(scene, style, reference_style_desc):

    style_desc = reference_style_desc if reference_style_desc else STYLES.get(style, STYLES[DEFAULT_STYLE])

   prompt = (
    f"Instagram Story image, vertical 9:16.\n"

    f"REALISTIC SCENE:\n{scene}\n\n"

    "IMPORTANT:\n"
    "- This is NOT abstract background\n"
    "- Show real objects, real situation\n"
    "- No gradients, no empty backgrounds\n"
    "- No minimalism\n\n"

    "COMPOSITION:\n"
    "- Clear subject in frame\n"
    "- Instagram style content\n"
    "- Looks like real photo or video frame\n\n"

    f"STYLE: {style_desc}\n"
    "High detail, professional, realistic"
)

    try:
        response = _client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=prompt,
        )

        if not response or not response.candidates:
            return None

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                img = Image.open(io.BytesIO(part.inline_data.data))
                return img.resize((CANVAS_W, CANVAS_H))

        return None

    except Exception as e:
        logger.error("Image generation error: %s", e)
        return None


# =========================================
# FALLBACK
# =========================================

def generate_gradient():
    img = Image.new("RGB", (CANVAS_W, CANVAS_H))
    draw = ImageDraw.Draw(img)

    c1 = tuple(random.randint(40, 120) for _ in range(3))
    c2 = tuple(random.randint(150, 255) for _ in range(3))

    for y in range(CANVAS_H):
        ratio = y / CANVAS_H
        color = tuple(int(c1[i] * (1 - ratio) + c2[i] * ratio) for i in range(3))
        draw.line([(0, y), (CANVAS_W, y)], fill=color)

    return img


# =========================================
# TEXT
# =========================================

def _get_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def overlay_text(img, text):
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)

    font = _get_font(72)
    max_w = CANVAS_W - 120

    text = text[:180]  # захист

    lines = wrap(text, font, max_w, draw)

    y = int(CANVAS_H * 0.6)

    for line in lines:
        w = draw.textlength(line, font=font)
        x = (CANVAS_W - w) // 2

        draw.text((x+3, y+3), line, font=font, fill=(0,0,0,150))
        draw.text((x, y), line, font=font, fill=(255,255,255,255))

        y += 80

    return img.convert("RGB")


# =========================================
# MAIN
# =========================================

async def build_slide(
    slide_text,
    what_to_show,
    has_interactive=False,
    style=DEFAULT_STYLE,
    reference_style_desc=None,
):
    bg = None

    # 🔥 RETRY
    for _ in range(3):
        bg = await generate_background(
            scene=what_to_show,
            style=style,
            reference_style_desc=reference_style_desc,
        )
        if bg:
            break

    if bg is None:
        logger.warning("Fallback used")
        bg = generate_gradient()

    final = overlay_text(bg, slide_text)

    buf = io.BytesIO()
    final.save(buf, format="JPEG", quality=90)

    return buf.getvalue()
