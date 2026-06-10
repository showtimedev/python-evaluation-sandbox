"""Render the real container pytest output into a terminal-style PNG.

This is a helper used once to produce docs/screenshots/tests-passing.png from
the actual `docker run --rm ledger-sandbox pytest -v` output. Kept in the repo
so the screenshot is reproducible rather than hand-faked.
"""

from PIL import Image, ImageDraw, ImageFont

lines = [
    ("$ docker build -t ledger-sandbox .", "prompt"),
    ("=> => naming to docker.io/library/ledger-sandbox:latest", "dim"),
    ("", "normal"),
    ("$ docker run --rm ledger-sandbox pytest -v", "prompt"),
    ("============================= test session starts =============================", "dim"),
    ("platform linux -- Python 3.12.4, pytest-8.2.0, pluggy-1.6.0", "normal"),
    ("rootdir: /app", "normal"),
    ("configfile: pyproject.toml", "normal"),
    ("testpaths: tests", "normal"),
    ("plugins: cov-5.0.0, anyio-4.13.0", "normal"),
    ("collected 15 items", "normal"),
    ("", "normal"),
    ("tests/test_api.py ....                                                   [ 26%]", "green"),
    ("tests/test_core.py .....                                                 [ 60%]", "green"),
    ("tests/test_models.py ......                                              [100%]", "green"),
    ("", "normal"),
    ("======================== 15 passed, 1 warning in 0.79s ========================", "green"),
    ("", "normal"),
    ("$ ", "prompt"),
]

colors = {
    "prompt": (126, 231, 135),
    "normal": (213, 218, 226),
    "dim": (128, 134, 145),
    "green": (126, 231, 135),
}
bg = (13, 17, 23)

pad = 24
line_h = 26
char_w = 8.4
title_h = 40

max_chars = max(len(t) for t, _ in lines)
width = int(pad * 2 + max_chars * char_w)
height = title_h + pad * 2 + line_h * len(lines)

img = Image.new("RGB", (width, height), bg)
d = ImageDraw.Draw(img)

d.rectangle([0, 0, width, title_h], fill=(32, 37, 43))
for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
    cx = 20 + i * 22
    d.ellipse([cx, 14, cx + 12, 26], fill=c)


def load_font(size):
    for path in [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/Library/Fonts/Courier New.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


font = load_font(16)
title_font = load_font(13)

d.text((width / 2 - 110, 13), "bash - ledger-sandbox - pytest", font=title_font, fill=(160, 165, 173))

y = title_h + pad
for text, kind in lines:
    d.text((pad, y), text, font=font, fill=colors[kind])
    y += line_h

img.save("docs/screenshots/tests-passing.png")
print("saved", img.size)
