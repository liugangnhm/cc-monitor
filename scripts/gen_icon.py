"""Generate cc-monitor app icon."""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = xy
    r = radius

    # Four corners
    draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill, outline=outline, width=width)
    draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill, outline=outline, width=width)
    draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill, outline=outline, width=width)
    draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill, outline=outline, width=width)

    # Rectangles
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill, outline=outline, width=0)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill, outline=outline, width=0)

    if outline:
        # Redraw edges for clean outline
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)


def create_icon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size // 16
    corner_r = size // 5

    # ── Background: gradient-ish purple rounded square ──
    # Main bg
    draw_rounded_rect(
        draw,
        [margin, margin, size - margin, size - margin],
        corner_r,
        fill=(99, 102, 241, 255),  # #6366f1
    )
    # Lighter overlay on top half for subtle gradient feel
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    draw_rounded_rect(
        ov_draw,
        [margin, margin, size - margin, size // 2],
        corner_r,
        fill=(255, 255, 255, 30),
    )
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # ── Monitor screen ──
    cx, cy = size // 2, size // 2 - size // 12
    sw = size * 3 // 5   # screen width
    sh = size * 2 // 5   # screen height
    sr = size // 16      # screen corner radius

    # Screen outer (white border)
    sx0 = cx - sw // 2 - 3
    sy0 = cy - sh // 2 - 3
    sx1 = cx + sw // 2 + 3
    sy1 = cy + sh // 2 + 3
    draw_rounded_rect(draw, [sx0, sy0, sx1, sy1], sr + 2,
                      fill=(255, 255, 255, 255))

    # Screen inner (dark background)
    draw_rounded_rect(draw,
                      [cx - sw // 2, cy - sh // 2, cx + sw // 2, cy + sh // 2],
                      sr,
                      fill=(30, 27, 75, 255))  # #1e1b4b dark indigo

    # ── Status dots inside screen ──
    dot_r = max(size // 28, 3)
    dot_y = cy - sh // 6
    colors = [
        (34, 197, 94, 255),    # green - completed
        (245, 158, 11, 255),   # amber - in progress
        (203, 213, 225, 255),  # gray - pending
    ]
    total_dots_w = len(colors) * dot_r * 2 + (len(colors) - 1) * dot_r * 2
    start_x = cx - total_dots_w // 2 + dot_r

    for i, color in enumerate(colors):
        dx = start_x + i * dot_r * 4
        draw.ellipse(
            [dx - dot_r, dot_y - dot_r, dx + dot_r, dot_y + dot_r],
            fill=color,
        )

    # ── Small horizontal lines under dots (task rows) ──
    line_w = sw * 3 // 8
    line_h = max(size // 50, 2)
    line_start_x = cx - line_w // 2

    for i, color in enumerate(colors):
        ly = dot_y + dot_r * 2 + i * (line_h + max(size // 40, 4)) + line_h
        alpha = 180 if i < 2 else 100
        draw.rounded_rectangle(
            [line_start_x, ly, line_start_x + line_w * (3 - i) // 3, ly + line_h],
            radius=line_h // 2,
            fill=(*color[:3], alpha),
        )

    # ── Monitor stand ──
    stand_w = size // 8
    stand_h = size // 14
    stand_top = cy + sh // 2 + size // 20

    # Stand neck
    draw.rounded_rectangle(
        [cx - size // 40, cy + sh // 2, cx + size // 40, stand_top],
        radius=2,
        fill=(255, 255, 255, 230),
    )

    # Stand base
    draw.rounded_rectangle(
        [cx - stand_w // 2, stand_top, cx + stand_w // 2, stand_top + stand_h],
        radius=stand_h // 2,
        fill=(255, 255, 255, 230),
    )

    return img


def main():
    output_dir = Path(__file__).resolve().parent.parent / "assets"
    output_dir.mkdir(exist_ok=True)

    # Generate base 256x256
    icon_256 = create_icon(256)
    icon_256.save(output_dir / "icon.png", "PNG")
    print(f"Saved icon.png ({icon_256.size})")

    # Generate .ico with multiple sizes
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = []
    for s in sizes:
        resized = icon_256.resize((s, s), Image.LANCZOS)
        icons.append(resized)

    ico_path = output_dir / "cc-monitor.ico"
    icons[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:],
    )
    print(f"Saved cc-monitor.ico with sizes: {sizes}")

    # Also save a preview
    preview = icon_256.resize((64, 64), Image.LANCZOS)
    preview.save(output_dir / "icon_preview.png", "PNG")
    print("Done!")


if __name__ == "__main__":
    main()
