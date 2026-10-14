"""Deterministic 16:9 pale-blue/white illustrations. No text or market direction."""
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter

WIDTH, HEIGHT = 1600, 900
TOPICS = ("macro", "banking", "energy", "technology", "bvb", "commodities", "global")
KEYWORDS = {
    "energy": ("石油", "原油", "布伦特", "天然气", "能源", "WTI", "oil", "gas", "petrom", "romgaz"),
    "technology": ("半导体", "芯片", "人工智能", "科技", "AI", "semiconductor", "nvidia"),
    "banking": ("银行", "财报", "bank", "BRD", "TLV", "transilvania"),
    "commodities": ("黄金", "白银", "铜价", "金价", "gold", "silver", "copper"),
    "bvb": ("罗马尼亚", "布加勒斯特", "BVB", "BET指数", "romanian", "bucharest"),
    "macro": ("通胀", "利率", "央行", "CPI", "PCE", "美联储", "ECB", "美元", "汇率", "inflation", "rate"),
}

def select_topic(facts):
    text = " ".join(facts).lower()
    hits = []
    for topic, words in KEYWORDS.items():
        if any(w.lower() in text for w in words):
            hits.append(topic)
    # Mixed or unknown narratives use a neutral world motif, not an invented chart.
    return hits[0] if len(hits) == 1 else "global"

def render_background(topic):
    if topic not in TOPICS:
        raise ValueError("unsupported image topic")
    im = Image.new("RGB", (WIDTH, HEIGHT))
    px = im.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            blend = min(1, 0.30 * x / WIDTH + 0.62 * y / HEIGHT)
            px[x, y] = (
                int(253 - 27 * blend),
                int(254 - 14 * blend),
                int(255 - 5 * blend),
            )
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, "RGBA")
    gd.ellipse((880, -300, 1880, 700), fill=(130, 198, 240, 85))
    gd.ellipse((-500, 320, 480, 1350), fill=(194, 229, 252, 85))
    im = Image.alpha_composite(im.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(95)))

    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")
    ink = (58, 136, 193, 110)
    soft = (74, 161, 219, 50)
    shade = (100, 178, 223, 23)
    # Wide empty area left keeps this a background, not a factual infographic.
    d.ellipse((850, 120, 1530, 790), outline=soft, width=5)
    d.ellipse((930, 200, 1450, 720), outline=soft, width=3)
    d.arc((790, 50, 1640, 850), 30, 215, fill=ink, width=3)
    if topic in ("global", "macro"):
        d.ellipse((1000, 210, 1410, 620), outline=ink, width=9)
        for offset in (-95, 95):
            d.arc((1090 + offset, 210, 1320 - offset, 620), 70, 290, fill=ink, width=5)
        d.line([(1010, 415), (1400, 415)], fill=ink, width=6)
        d.arc((1000, 315, 1410, 510), 0, 180, fill=ink, width=4)
    elif topic in ("banking", "bvb"):
        d.polygon([(980, 360), (1210, 225), (1435, 360)], fill=shade)
        d.line([(980, 360), (1210, 225), (1435, 360)], fill=ink, width=13, joint="curve")
        d.line([(990, 385), (1430, 385)], fill=ink, width=11)
        for x in (1030, 1140, 1250, 1360):
            d.rounded_rectangle((x, 405, x + 46, 630), radius=8, outline=ink, width=8)
        for y in (655, 682):
            d.line([(975, y), (1450, y)], fill=ink, width=9)
    elif topic == "energy":
        for x in (1010, 1140, 1270):
            d.rounded_rectangle((x, 400, x + 108, 645), radius=20, fill=shade, outline=ink, width=7)
            d.arc((x, 385, x + 108, 420), 185, 355, fill=ink, width=5)
        d.line([(1020, 585), (1405, 585)], fill=ink, width=7)
        d.line([(1050, 400), (1100, 325), (1260, 325), (1335, 400)], fill=ink, width=7)
        d.line([(1210, 325), (1210, 250)], fill=ink, width=8)
    elif topic == "technology":
        d.rounded_rectangle((1075, 300, 1375, 600), radius=45, fill=shade, outline=ink, width=12)
        d.rounded_rectangle((1140, 365, 1310, 535), radius=30, outline=ink, width=7)
        for v in range(4):
            p = 1120 + 72 * v
            d.line([(p, 300), (p, 245)], fill=ink, width=8)
            d.line([(p, 600), (p, 655)], fill=ink, width=8)
            d.line([(1075, 345 + 70 * v), (1020, 345 + 70 * v)], fill=ink, width=8)
            d.line([(1375, 345 + 70 * v), (1430, 345 + 70 * v)], fill=ink, width=8)
    elif topic == "commodities":
        d.polygon([(1030, 405), (1100, 305), (1320, 305), (1400, 405), (1220, 650)],
                  fill=shade)
        d.line([(1030, 405), (1100, 305), (1320, 305), (1400, 405),
                (1220, 650), (1030, 405)], fill=ink, width=10, joint="curve")
        d.line([(1030, 405), (1400, 405)], fill=ink, width=8)
        d.line([(1100, 305), (1220, 650), (1320, 305)], fill=ink, width=5)
    d.ellipse((1450, 140, 1472, 162), fill=(84, 166, 215, 70))
    d.ellipse((895, 715, 920, 740), fill=(84, 166, 215, 55))
    im = Image.alpha_composite(im, overlay.filter(ImageFilter.GaussianBlur(.4))).convert("RGB")
    buf = BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
