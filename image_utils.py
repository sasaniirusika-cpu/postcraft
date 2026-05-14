from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import requests
import numpy as np
import io
import os

CANVAS_SIZE = 1080

def make_gradient_bg(colors, size=CANVAS_SIZE):
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)
    steps = len(colors)
    seg = size // (steps - 1) if steps > 1 else size
    for i in range(steps - 1):
        c1, c2 = colors[i], colors[i + 1]
        for y in range(seg):
            t = y / seg
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            y0 = i * seg + y
            if y0 < size:
                draw.line([(0, y0), (size, y0)], fill=(r, g, b))
    return img

def add_vignette(img, strength=0.6):
    size = img.size[0]
    vig = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(vig)
    for i in range(size // 2):
        t = i / (size // 2)
        val = int(255 * (1 - t ** 0.5) * strength)
        draw.ellipse([i, i, size - i, size - i], outline=val)
    vig = vig.filter(ImageFilter.GaussianBlur(60))
    dark = Image.new("RGB", (size, size), (0, 0, 0))
    img = img.copy()
    img.paste(dark, mask=vig)
    return img

def add_noise(img, amount=8):
    arr = np.array(img).astype(np.int16)
    noise = np.random.randint(-amount, amount, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)

def load_photo_bg(url, size=CANVAS_SIZE):
    try:
        r = requests.get(url, timeout=8)
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        w, h = img.size
        m = min(w, h)
        left = (w - m) // 2
        top = (h - m) // 2
        img = img.crop((left, top, left + m, top + m))
        img = img.resize((size, size), Image.LANCZOS)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.45)
        return img
    except Exception:
        return make_gradient_bg([(15, 12, 41), (45, 42, 99), (36, 36, 62)])

def get_font(size, bold=False, sinhala=False):
    font_paths = []
    if sinhala:
        font_paths = [
            "/usr/share/fonts/truetype/noto/NotoSansSinhala-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansSinhala-Regular.ttf",
            "/usr/share/fonts/noto/NotoSansSinhala-Bold.ttf",
            "/usr/share/fonts/noto/NotoSansSinhala-Regular.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def draw_rounded_rect(draw, box, radius, fill, outline=None, outline_width=2):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=outline_width)

def build_post(bg_image, institute_name, course_name, tagline, bullets, cta, phone, website, accent, accent2, logo_img=None, add_vignette_=True, add_noise_=True, size=CANVAS_SIZE):
    img = bg_image.copy().convert("RGBA")
    if add_vignette_:
        rgb = img.convert("RGB")
        rgb = add_vignette(rgb, strength=0.65)
        img = rgb.convert("RGBA")
    if add_noise_:
        rgb = img.convert("RGB")
        rgb = add_noise(rgb, 6)
        img = rgb.convert("RGBA")
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, 0, size, 6], fill=(*accent, 255))
    inst_font = get_font(28, bold=True)
    badge_text = f"✦  {institute_name}  ✦" if institute_name else "✦  Your Institute  ✦"
    bbox = draw.textbbox((0,0), badge_text, font=inst_font)
    bw = bbox[2] - bbox[0] + 48
    bx = (size - bw) // 2
    draw_rounded_rect(draw, [bx, 30, bx + bw, 80], 24, fill=(*accent, 35), outline=(*accent, 90), outline_width=1)
    draw.text((bx + 24, 44), badge_text, font=inst_font, fill=(*accent, 230))
    y = 200
    if course_name:
        title_font = get_font(88, bold=True, sinhala=True)
        lines = course_name.split("\n")
        for line in lines:
            bbox = draw.textbbox((0,0), line, font=title_font)
            w = bbox[2] - bbox[0]
            x = (size - w) // 2
            draw.text((x+4, y+5), line, font=title_font, fill=(0,0,0,160))
            draw.text((x, y), line, font=title_font, fill=(255,255,255,255))
            y += 100
    draw.rectangle([(size//2 - 80, y+10), (size//2 + 80, y+14)], fill=(*accent, 255))
    y += 36
    if tagline:
        tag_font = get_font(36, bold=True, sinhala=True)
        bbox = draw.textbbox((0,0), tagline, font=tag_font)
        w = bbox[2] - bbox[0]
        x = (size - w) // 2
        draw.text((x, y), tagline, font=tag_font, fill=(*accent, 230))
        y += 60
    if bullets:
        card_y = y + 10
        card_h = len(bullets) * 56 + 30
        draw_rounded_rect(draw, [60, card_y, size-60, card_y + card_h], 16, fill=(255,255,255,18), outline=(*accent, 55), outline_width=1)
        bul_font = get_font(30, bold=False, sinhala=True)
        for i, b in enumerate(bullets):
            by = card_y + 20 + i * 56
            draw.ellipse([84, by+8, 100, by+24], fill=(*accent, 220))
            draw.text((115, by), b, font=bul_font, fill=(230,230,255,240))
        y = card_y + card_h + 30
    if cta:
        cta_font = get_font(38, bold=True, sinhala=True)
        bbox = draw.textbbox((0,0), cta, font=cta_font)
        cw = bbox[2] - bbox[0] + 72
        cx = (size - cw) // 2
        draw_rounded_rect(draw, [cx, y, cx+cw, y+72], 36, fill=(*accent, 230), outline=(*accent2, 200), outline_width=2)
        draw.text((cx+36, y+16), cta, font=cta_font, fill=(255,255,255,255))
        y += 90
    if phone or website:
        contact_font = get_font(26, bold=False)
        contact = ""
        if phone: contact += f"📞 {phone}"
        if phone and website: contact += "   "
        if website: contact += f"🌐 {website}"
        bbox = draw.textbbox((0,0), contact, font=contact_font)
        w = bbox[2] - bbox[0]
        x = (size - w) // 2
        draw.text((x, y), contact, font=contact_font, fill=(200,200,255,200))
    draw.rectangle([0, size-6, size, size], fill=(*accent2, 200))
    img = Image.alpha_composite(img, overlay)
    if logo_img:
        try:
            logo = logo_img.convert("RGBA")
            lw = 160
            ratio = lw / logo.width
            lh = int(logo.height * ratio)
            logo = logo.resize((lw, lh), Image.LANCZOS)
            img.paste(logo, (size - lw - 40, 20), logo)
        except Exception:
            pass
    return img.convert("RGB")

def sketch_to_post_prompt(sketch_description, institute_name):
    return f"""You are a creative social media post designer for a Sri Lankan educational institute called "{institute_name or 'our institute'}".
The user has drawn a rough sketch that represents: {sketch_description}
Respond in JSON format ONLY:
{{
  "course_name": "Course title in Sinhala (max 3 words)",
  "tagline": "Catchy Sinhala tagline (max 8 words)",
  "bullets": ["Sinhala point 1", "Sinhala point 2", "Sinhala point 3", "Sinhala point 4"],
  "cta": "Sinhala call to action (max 5 words)",
  "caption_fb": "Facebook caption in Sinhala + English (150 words max)",
  "caption_ig": "Instagram caption with emojis + hashtags (100 words max)",
  "hashtags": "#hashtags (15 tags)"
}}"""
