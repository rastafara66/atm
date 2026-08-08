# -*- coding: utf-8 -*-
"""Draw the module icon and the store banner.

Everything is rendered at 4x and downscaled, which is what gives the edges
their smoothness -- Pillow has no antialiased drawing of its own.

    python tools/make_icons.py

Writes atm/static/description/icon.png, banner.png and favicon.ico.
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'atm', 'static', 'description')

SS = 4  # supersampling factor

# Odoo's own palette, so the icon does not look foreign next to the stock apps.
PLUM_TOP = (135, 90, 123)      # #875A7B
PLUM_BOTTOM = (91, 58, 83)     # #5B3A53
TEAL = (0, 160, 157)           # #00A09D
TEAL_LIGHT = (94, 205, 202)
PAPER = (255, 255, 255)
PAPER_SHADE = (222, 230, 238)
INK = (150, 163, 178)


def vertical_gradient(size, top, bottom):
    """A one-pixel-wide gradient stretched to size -- cheaper than per-pixel."""
    width, height = size
    strip = Image.new('RGB', (1, height))
    for y in range(height):
        t = y / max(height - 1, 1)
        strip.putpixel((0, y), tuple(
            int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return strip.resize(size, Image.BICUBIC)


def rounded_mask(size, radius):
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (size[0] - 1, size[1] - 1)], radius=radius, fill=255)
    return mask


def draw_sheet(draw, box, tilt=0, shade=False):
    """A sheet of paper with a folded corner and a few lines of text."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    fold = int(w * 0.30)

    body = [
        (x0, y0 + tilt), (x1 - fold, y0), (x1, y0 + fold),
        (x1, y1 - tilt), (x0, y1),
    ]
    draw.polygon(body, fill=PAPER_SHADE if shade else PAPER)
    # The folded corner: only a little darker than the sheet, or it reads as a
    # separate object rather than as paper.
    draw.polygon([(x1 - fold, y0), (x1, y0 + fold), (x1 - fold, y0 + fold)],
                 fill=(206, 216, 228) if not shade else (188, 200, 214))

    line_x0 = x0 + int(w * 0.16)
    line_x1 = x1 - int(w * 0.16)
    for i in range(3):
        ly = y0 + int(h * (0.45 + i * 0.16))
        end = line_x1 if i < 2 else line_x0 + int((line_x1 - line_x0) * 0.55)
        draw.rounded_rectangle([(line_x0, ly), (end, ly + int(h * 0.055))],
                               radius=int(h * 0.03), fill=INK)


def draw_arrow(draw, y, x0, x1, thickness, head, color, pointing_right=True):
    """A straight shaft with a triangular head."""
    if pointing_right:
        shaft = [(x0, y - thickness // 2), (x1 - head, y + thickness // 2)]
        tip = [(x1 - head, y - head), (x1, y), (x1 - head, y + head)]
    else:
        shaft = [(x0 + head, y - thickness // 2), (x1, y + thickness // 2)]
        tip = [(x0 + head, y - head), (x0, y), (x0 + head, y + head)]
    draw.rectangle(shaft, fill=color)
    draw.polygon(tip, fill=color)


def build_icon(size=256):
    """Two documents with exchange arrows between them."""
    s = size * SS
    canvas = Image.new('RGBA', (s, s), (0, 0, 0, 0))

    background = vertical_gradient((s, s), PLUM_TOP, PLUM_BOTTOM).convert('RGBA')
    background.putalpha(rounded_mask((s, s), radius=int(s * 0.22)))
    canvas = Image.alpha_composite(canvas, background)

    draw = ImageDraw.Draw(canvas)

    # Two sheets and the arrows between them, centred and large: at 24 px in a
    # menu only the silhouette survives, so it has to carry the meaning.
    sheet_w, sheet_h = int(s * 0.275), int(s * 0.45)
    top = int(s * 0.275)
    draw_sheet(draw, (int(s * 0.07), top,
                      int(s * 0.07) + sheet_w, top + sheet_h))
    draw_sheet(draw, (s - int(s * 0.07) - sheet_w, top,
                      s - int(s * 0.07), top + sheet_h))

    gap_x0, gap_x1 = int(s * 0.385), int(s * 0.615)
    thickness, head = int(s * 0.062), int(s * 0.072)
    draw_arrow(draw, int(s * 0.425), gap_x0, gap_x1, thickness, head,
               TEAL_LIGHT, pointing_right=True)
    draw_arrow(draw, int(s * 0.575), gap_x0, gap_x1, thickness, head,
               TEAL, pointing_right=False)

    return canvas.resize((size, size), Image.LANCZOS)


def load_font(px, bold=False):
    for name in (('arialbd.ttf', 'calibrib.ttf') if bold
                 else ('arial.ttf', 'calibri.ttf')):
        path = os.path.join(r'C:\Windows\Fonts', name)
        if os.path.exists(path):
            return ImageFont.truetype(path, px)
    return ImageFont.load_default()


def fit_font(draw, text, max_width, start_px, bold=False):
    """Largest font size at which the text still fits the column."""
    px = start_px
    while px > 8:
        font = load_font(px, bold=bold)
        if draw.textlength(text, font=font) <= max_width:
            return font
        px = int(px * 0.94)
    return load_font(px, bold=bold)


def build_banner(width=560, height=315):
    """The card image shown in the App Store listing."""
    w, h = width * SS, height * SS
    canvas = vertical_gradient((w, h), PLUM_TOP, PLUM_BOTTOM).convert('RGBA')

    margin = int(w * 0.07)
    icon_px = int(h * 0.40)
    icon_y = (h - icon_px) // 2
    icon = build_icon(96).resize((icon_px, icon_px), Image.LANCZOS)

    # A soft drop shadow so the tile lifts off the background.
    shadow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    shadow.paste(Image.new('RGBA', (icon_px, icon_px), (0, 0, 0, 100)),
                 (margin, icon_y + int(h * 0.022)), icon.split()[3])
    canvas = Image.alpha_composite(
        canvas, shadow.filter(ImageFilter.GaussianBlur(int(h * 0.022))))
    canvas.paste(icon, (margin, icon_y), icon)

    draw = ImageDraw.Draw(canvas)
    text_x = margin + icon_px + int(w * 0.05)
    column = w - text_x - margin

    title = 'Data Exchange'
    subtitle = 'JSON sync with your accounting system'
    entities = 'contacts · products · orders · invoices · payments'

    title_font = fit_font(draw, title, column, int(h * 0.135), bold=True)
    sub_font = fit_font(draw, subtitle, column, int(h * 0.060))
    ent_font = fit_font(draw, entities, column, int(h * 0.050))

    # Stack the three lines as one block and centre that block vertically.
    gap_a, gap_b = int(h * 0.055), int(h * 0.048)
    ascent = title_font.size + gap_a + sub_font.size + gap_b + ent_font.size
    y = (h - ascent) // 2

    draw.text((text_x, y), title, font=title_font, fill=PAPER, anchor='la')
    y += title_font.size + gap_a
    draw.text((text_x, y), subtitle, font=sub_font, fill=TEAL_LIGHT, anchor='la')
    y += sub_font.size + gap_b
    draw.text((text_x, y), entities, font=ent_font, fill=(216, 206, 216),
              anchor='la')

    return canvas.resize((width, height), Image.LANCZOS).convert('RGB')


def main():
    icon = build_icon(256)
    icon.save(os.path.join(OUT, 'icon.png'))
    print('icon.png      256x256')

    banner = build_banner()
    banner.save(os.path.join(OUT, 'banner.png'))
    print('banner.png    560x315')

    icon.save(os.path.join(OUT, 'favicon.ico'),
              sizes=[(16, 16), (32, 32), (48, 48)])
    print('favicon.ico   16/32/48')


if __name__ == '__main__':
    main()
