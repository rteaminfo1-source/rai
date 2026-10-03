# Генерирует иконку приложения (красная «R» RTeam на тёмном фоне) в PNG.
from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Скруглённый тёмный квадрат-подложка
pad = 10
radius = 52
d.rounded_rectangle([pad, pad, SIZE - pad, SIZE - pad], radius=radius, fill=(14, 14, 20, 255))
# Тонкая рамка
d.rounded_rectangle([pad, pad, SIZE - pad, SIZE - pad], radius=radius, outline=(255, 42, 42, 90), width=3)

# Буква R по центру
def find_font(sz):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

font = find_font(170)
text = "R"
bbox = d.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
x = (SIZE - tw) / 2 - bbox[0]
y = (SIZE - th) / 2 - bbox[1] - 6
# лёгкое свечение
for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
    d.text((x+dx, y+dy), text, font=font, fill=(255, 42, 42, 60))
d.text((x, y), text, font=font, fill=(255, 60, 60, 255))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "winres", "icon.png")
img.save(out)
print("saved", out, img.size)
