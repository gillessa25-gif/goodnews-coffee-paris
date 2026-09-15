"""Build the brand assets: paper and grain textures, app icon, OG card."""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, "assets")
DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
HELVETICA = "/System/Library/Fonts/Helvetica.ttc"

INK = (22, 41, 58)
PAPER = (251, 246, 236)
CREMA = (192, 122, 46)


def serif(size, index=1):
    try:
        return ImageFont.truetype(DIDOT, size, index=index)
    except OSError:
        return ImageFont.truetype(GEORGIA, size)


def sans(size, index=0):
    try:
        return ImageFont.truetype(HELVETICA, size, index=index)
    except OSError:
        return ImageFont.load_default()


def make_grain(path, size=128):
    rng = np.random.default_rng(7)
    noise = rng.normal(0.5, 0.11, (size, size)).clip(0, 1)
    fine = np.asarray(
        Image.fromarray((noise * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.4))
    ).astype(np.float32) / 255.0
    out = (fine * 255).astype(np.uint8)
    Image.fromarray(out, mode="L").save(path, optimize=True)


def draw_seal(canvas, cx, cy, r, ink=INK, crema=CREMA, cream=PAPER):
    """House mark: a cup seen from above, its crema lit from the upper left."""
    d = ImageDraw.Draw(canvas)

    def disc(x, y, radius, fill):
        d.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fill)

    disc(cx, cy, r, ink)
    d.ellipse([cx - r * 0.86, cy - r * 0.86, cx + r * 0.86, cy + r * 0.86],
              outline=cream, width=max(2, int(r * 0.055)))
    disc(cx, cy, r * 0.62, crema)
    disc(cx - r * 0.09, cy - r * 0.05, r * 0.45, cream)      # milk
    disc(cx - r * 0.26, cy - r * 0.22, r * 0.43, crema)      # carve the crescent


def make_icon(path, size=180, pad=0.10):
    canvas = Image.new("RGB", (size * 4, size * 4), PAPER)
    r = size * 4 * (0.5 - pad) * 0.96
    draw_seal(canvas, size * 2, size * 2, r)
    canvas.resize((size, size), Image.LANCZOS).save(path, optimize=True)


def make_og(path, frame_path, width=1200, height=630):
    shot = Image.open(frame_path).convert("RGB")
    ratio = max(width / shot.width, height / shot.height)
    shot = shot.resize((int(shot.width * ratio), int(shot.height * ratio)), Image.LANCZOS)
    left = (shot.width - width) // 2
    top = (shot.height - height) // 2
    card = shot.crop((left, top, left + width, top + height))

    scrim = Image.new("RGB", (width, height), (12, 24, 36))
    card = Image.blend(card, scrim, 0.46)

    d = ImageDraw.Draw(card)
    d.rectangle([0, 0, width, height], outline=(236, 226, 208), width=3)

    title = serif(150)
    sub = sans(30, index=0)
    kicker = sans(26, index=0)

    d.line([120, 214, width - 120, 214], fill=(240, 232, 216), width=4)
    d.text((120, 150), "PARIS XVe · CAFÉ DE SPÉCIALITÉ", font=kicker, fill=(226, 196, 150))
    d.text((116, 246), "Good News", font=title, fill=(250, 245, 234))
    d.line([120, 436, width - 120, 436], fill=(240, 232, 216), width=1)
    d.text((120, 462), "COFFEE SHOP", font=sub, fill=(250, 245, 234))
    d.text((120, 512), "27 bis rue Mademoiselle, 75015 · Ouvert 7 j/7 jusqu'à 17 h",
           font=sub, fill=(214, 200, 178))
    card.save(path, quality=88, optimize=True, progressive=True)


def main():
    make_grain(os.path.join(ASSETS, "grain.png"))
    make_icon(os.path.join(ASSETS, "icon-180.png"), 180)
    make_icon(os.path.join(ASSETS, "icon-512.png"), 512)
    make_og(os.path.join(ASSETS, "og.jpg"), os.environ.get("OG_SOURCE", os.path.join(ASSETS, "hero-poster.jpg")))
    print("assets written")


if __name__ == "__main__":
    main()
