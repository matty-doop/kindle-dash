"""Generate the Kindle's offline fallback screens (kindle/dashboard/assets/*.png)."""
from PIL import Image, ImageDraw
from render import W, H, font, icon, BLACK, MID, WHITE

SCREENS = {
    "nowifi": ("No Wi-Fi", ["Can't reach the internet.", "Will keep retrying.",
                            "If it doesn't recover, plug into a",
                            "computer's USB port for a minute."], "cloud"),
    "battery": ("Battery low", ["Plug in the Kindle to keep", "the dashboard running."], None),
    "server": ("Dashboard unavailable", ["The image couldn't be loaded.", "Will keep retrying."], "cloud"),
    "notfound": ("Dashboard not found", ["Check DASH_URL in", "dashboard/config.sh"], None),
    "unauthorized": ("Access denied", ["Check DASH_URL in", "dashboard/config.sh"], None),
}

for name, (title, lines, ic) in SCREENS.items():
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    y = 520
    if name == "battery":
        x0, y0 = W / 2 - 110, 380
        d.rounded_rectangle([x0, y0, x0 + 200, y0 + 100], radius=14, outline=BLACK, width=8)
        d.rectangle([x0 + 200, y0 + 30, x0 + 220, y0 + 70], fill=BLACK)
        d.rectangle([x0 + 18, y0 + 18, x0 + 50, y0 + 82], fill=BLACK)
    elif ic:
        icon(d, ic, W / 2, 420, 110)
    else:
        y = 460
    d.text((W / 2, y), title, font=font("Bold", 64), fill=BLACK, anchor="ma")
    y += 110
    for line in lines:
        d.text((W / 2, y), line, font=font("Medium", 38), fill=MID, anchor="ma")
        y += 56
    img.save(f"kindle/dashboard/assets/err-{name}.png", optimize=True)
    print("wrote", name)
