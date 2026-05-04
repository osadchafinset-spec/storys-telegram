import io
import base64
import logging
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

from config import GEMINI_API_KEY

logger = logging.getLogger(**name**)

# =========================================

# НАЛАШТУВАННЯ

# =========================================

CANVAS_W = 1080
CANVAS_H = 1920

STYLES = {
“Мінімалізм”:    “minimalist clean background, white and neutral tones, soft light, lots of negative space”,
“Темний преміум”: “dark premium background, deep blacks and golds, cinematic moody lighting, luxury aesthetic”,
“Яскравий поп”:  “vibrant colorful background, bold saturated colors, energetic, trendy Gen-Z aesthetic”,
“Пастельний”:    “soft pastel background, dreamy light colors, gentle gradients, aesthetic cozy mood”,
“Фото”:          “photorealistic scene, cinematic lighting, professional photography style”,
}

DEFAULT_STYLE = “Мінімалізм”

# =========================================

# GEMINI CLIENT

# =========================================

_client = genai.Client(api_key=GEMINI_API_KEY)

# =========================================

# АНАЛІЗ РЕФЕРЕНСУ (Gemini Vision)

# =========================================

async def analyze_reference(image_bytes: bytes) -> str | None:
try:
image_b64 = base64.b64encode(image_bytes).decode(“utf-8”)
response = _client.models.generate_content(
model=“gemini-2.0-flash-001”,
contents=[{
“parts”: [
{“inline_data”: {“mime_type”: “image/jpeg”, “data”: image_b64}},
{“text”: (
“Analyze this image’s visual style for use as a reference “
“for generating Instagram Story backgrounds. “
“Describe ONLY: color palette, lighting mood, textures, atmosphere, artistic style. “
“Do NOT mention people, faces, or specific objects. “
“Give a concise 2-3 sentence description in English “
“suitable for an image generation prompt.”
)}
]
}],
)
return response.text.strip()
except Exception as e:
logger.error(“Gemini Vision reference analysis error: %s”, e)
return None

# =========================================

# ГЕНЕРАЦІЯ ФОНУ (Gemini 2.0 Flash)

# =========================================

async def generate_background(
scene: str,
style: str = DEFAULT_STYLE,
reference_style_desc: str | None = None,
) -> Image.Image | None:
“””
Генерує фонове зображення через Gemini 2.0 Flash image generation.
Повертає PIL Image або None у разі помилки.
“””
style_desc = reference_style_desc if reference_style_desc else STYLES.get(style, STYLES[DEFAULT_STYLE])

```
prompt = (
    f"Instagram Story background image, vertical 9:16 format. "
    f"Scene: {scene}. "
    f"Style: {style_desc}. "
    f"No text overlay, no UI elements, no watermarks. "
    f"Leave the bottom third of the image clean and uncluttered. "
    f"High quality, professional social media visual."
)

try:
    response = _client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["image", "text"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_bytes = part.inline_data.data
            img = Image.open(io.BytesIO(image_bytes))
            return img.resize((CANVAS_W, CANVAS_H))

    logger.error("Gemini returned no image parts")
    return None

except Exception as e:
    logger.error("Gemini image generation error: %s", e)
    return None
```

# =========================================

# НАКЛАДАННЯ ТЕКСТУ (Pillow)

# =========================================

def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
font_paths = [
“/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf”,
“/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf”,
“/System/Library/Fonts/Helvetica.ttc”,
]
for path in font_paths:
if Path(path).exists():
return ImageFont.truetype(path, size)
return ImageFont.load_default()

def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
words = text.split()
lines, current = [], “”
for word in words:
test = f”{current} {word}”.strip()
bbox = draw.textbbox((0, 0), test, font=font)
if bbox[2] <= max_width:
current = test
else:
if current:
lines.append(current)
current = word
if current:
lines.append(current)
return lines

def overlay_text(
image: Image.Image,
slide_text: str,
has_interactive: bool = False,
) -> Image.Image:
img  = image.copy().convert(“RGBA”)
draw = ImageDraw.Draw(img)

```
padding   = 60
max_width = CANVAS_W - padding * 2
font_size = 72
font      = _get_font(font_size)

text_area_bottom = int(CANVAS_H * 0.62) if has_interactive else int(CANVAS_H * 0.85)

# Темний градієнт для читабельності
overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
ov_draw = ImageDraw.Draw(overlay)
ov_draw.rectangle(
    [(0, text_area_bottom - 300), (CANVAS_W, text_area_bottom + 100)],
    fill=(0, 0, 0, 140),
)
img  = Image.alpha_composite(img, overlay)
draw = ImageDraw.Draw(img)

# Текст
lines        = _wrap_text(slide_text, font, max_width, draw)
line_height  = font_size + 16
total_height = len(lines) * line_height
y            = text_area_bottom - total_height - 40

for line in lines:
    bbox = draw.textbbox((0, 0), line, font=font)
    x    = (CANVAS_W - (bbox[2] - bbox[0])) // 2
    draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 180))
    draw.text((x,     y    ), line, font=font, fill=(255, 255, 255, 255))
    y += line_height

# Зона для інтерактиву
if has_interactive:
    zone_top    = int(CANVAS_H * 0.68)
    zone_bottom = int(CANVAS_H * 0.88)
    zone_left   = int(CANVAS_W * 0.1)
    zone_right  = int(CANVAS_W * 0.9)

    zone_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    zone_draw    = ImageDraw.Draw(zone_overlay)
    zone_draw.rounded_rectangle(
        [(zone_left, zone_top), (zone_right, zone_bottom)],
        radius=30,
        fill=(255, 255, 255, 40),
        outline=(255, 255, 255, 120),
        width=3,
    )
    img  = Image.alpha_composite(img, zone_overlay)
    draw = ImageDraw.Draw(img)

    hint_font = _get_font(36)
    hint_text = "📊 місце для стікера"
    hint_bbox = draw.textbbox((0, 0), hint_text, font=hint_font)
    hint_x    = (CANVAS_W - (hint_bbox[2] - hint_bbox[0])) // 2
    hint_y    = zone_top + (zone_bottom - zone_top) // 2 - 18
    draw.text((hint_x, hint_y), hint_text, font=hint_font, fill=(255, 255, 255, 160))

return img.convert("RGB")
```

# =========================================

# ГОЛОВНА ФУНКЦІЯ

# =========================================

async def build_slide(
slide_text: str,
what_to_show: str,
has_interactive: bool = False,
style: str = DEFAULT_STYLE,
reference_style_desc: str | None = None,
) -> bytes | None:
bg = await generate_background(
scene=what_to_show,
style=style,
reference_style_desc=reference_style_desc,
)

```
if bg is None:
    logger.warning("Using black fallback background for slide")
    bg = Image.new("RGB", (CANVAS_W, CANVAS_H), color=(20, 20, 20))

final = overlay_text(bg, slide_text, has_interactive=has_interactive)

buf = io.BytesIO()
final.save(buf, format="JPEG", quality=92)
return buf.getvalue()
```
