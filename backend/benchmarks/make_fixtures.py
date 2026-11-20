"""Generate benchmark fixtures with known ground truth.

IMPORTANT: handwriting fixtures are *font-rendered* (Ink Free / Segoe Script) with
jitter. They are a smoke test for the handwriting path, NOT a substitute for real
human handwriting. Real handwriting should be added to fixtures/ with a .txt
ground-truth file of the same name; the benchmark runner picks it up automatically.
"""
import random, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = Path(__file__).parent / "fixtures"
OUT.mkdir(exist_ok=True)
F = Path("C:/Windows/Fonts")
random.seed(7)

def font(name, size, idx=0):
    return ImageFont.truetype(str(F / name), size, index=idx)

def render(lines, fnt, size=(1100, None), bg=(250, 249, 245), fg=(25, 25, 30), pad=60, lh=1.5, rtl=False, jitter=0):
    h = int(pad * 2 + len(lines) * fnt.size * lh)
    im = Image.new("RGB", (size[0], size[1] or h), bg)
    d = ImageDraw.Draw(im)
    y = pad
    for ln in lines:
        dy = random.randint(-jitter, jitter) if jitter else 0
        if rtl:
            w = d.textlength(ln, font=fnt)
            d.text((size[0] - pad - w, y + dy), ln, font=fnt, fill=fg)
        else:
            d.text((pad + (random.randint(0, jitter) if jitter else 0), y + dy), ln, font=fnt, fill=fg)
        y += int(fnt.size * lh)
    return im

def save(name, im, truth):
    im.save(OUT / f"{name}.png")
    (OUT / f"{name}.txt").write_text("\n".join(truth) if isinstance(truth, list) else truth, encoding="utf-8")

EN = ["The quick brown fox jumps over the lazy dog.",
      "Invoice 20418 was issued on 14 March 2024 for 1,250.75 dollars.",
      "Please send the signed contract to the office before Friday."]

# 1 clean printed
save("en_clean", render(EN, font("times.ttf", 38)), EN)
# 2 low resolution
im = render(EN, font("arial.ttf", 38)); w, h = im.size
save("en_lowres", im.resize((int(w * .4), int(h * .4)), Image.BILINEAR), EN)
# 3 rotated
im = render(EN, font("georgia.ttf", 38), size=(1350, None), bg=(255, 255, 255)).rotate(8, expand=True, fillcolor=(255, 255, 255), resample=Image.BICUBIC)
save("en_rotated", im, EN)
# 4 blurry
save("en_blurry", render(EN, font("arial.ttf", 40)).filter(ImageFilter.GaussianBlur(2.2)), EN)
# 5 perspective photo with background + shadow
base = np.array(render(EN, font("times.ttf", 40), size=(1100, 420)))
H, W = base.shape[:2]
bgc = np.full((H + 300, W + 300, 3), (70, 90, 110), np.uint8)
src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
dst = np.float32([[170, 110], [W + 60, 150], [W + 110, H + 170], [130, H + 140]])
M = cv2.getPerspectiveTransform(src, dst)
warp = cv2.warpPerspective(base, M, (W + 300, H + 300), borderValue=(0, 0, 0))
mask = cv2.warpPerspective(np.full((H, W), 255, np.uint8), M, (W + 300, H + 300))
photo = np.where(mask[..., None] > 0, warp, bgc)
grad = np.linspace(1.0, 0.62, W + 300)[None, :, None]
photo = np.clip(photo * grad, 0, 255).astype(np.uint8)
save("en_perspective_photo", Image.fromarray(photo), EN)
# 6/7 handwriting-style (SYNTHETIC)
HW = ["Dear Sam, thanks for the notes from Tuesday.", "Meet me at 4:30 near the old library.", "Bring the red folder and two pens."]
save("hw_inkfree_synthetic", render(HW, font("Inkfree.ttf", 44), bg=(246, 244, 236), fg=(30, 40, 110), lh=1.6, jitter=6), HW)
save("hw_cursive_synthetic", render(HW, font("segoesc.ttf", 40), bg=(246, 244, 236), fg=(30, 40, 110), lh=1.7, jitter=4), HW)
# 8 Latin-script languages
DE = ["Die Straße ist heute wegen Bauarbeiten gesperrt.", "Müller & Söhne öffnen um 9 Uhr."]
FR = ["Le café de l'été est très agréable à Genève.", "Où êtes-vous allés hier soir ?"]
ES = ["El niño comió piñas en la montaña.", "¿Dónde está la biblioteca más cercana?"]
for n, t in (("de", DE), ("fr", FR), ("es", ES)):
    save(f"{n}_clean", render(t, font("times.ttf", 40), size=(1100, None)), t)
# 9 CJK / Korean / Russian
ZH = ["今天的天气非常好。", "我们明天去北京参加会议。"]
save("zh_clean", render(ZH, font("msyh.ttc", 40)), ZH)
KO = ["오늘은 날씨가 아주 좋습니다.", "내일 서울에서 회의가 있습니다."]
save("ko_clean", render(KO, font("malgun.ttf", 40)), KO)
JA = ["今日はとても良い天気です。", "明日は東京で会議があります。"]
save("ja_clean", render(JA, font("YuGothM.ttc", 40)), JA)
RU = ["Москва является столицей России.", "Завтра будет солнечный день."]
save("ru_clean", render(RU, font("times.ttf", 40)), RU)
# 10 Arabic (RTL) with explicit shaping so rendering is correct without raqm
import arabic_reshaper
from bidi.algorithm import get_display
AR = ["القاهرة هي عاصمة مصر", "الطقس جميل اليوم"]
shaped = [get_display(arabic_reshaper.reshape(t)) for t in AR]
save("ar_clean", render(shaped, font("segoeui.ttf", 42), rtl=True), AR)
# 11 table with ruled grid
rows = [["Item", "Qty", "Price"], ["Pencil", "12", "3.40"], ["Notebook", "5", "12.00"], ["Eraser", "8", "1.60"]]
im = Image.new("RGB", (900, 420), (255, 255, 255)); d = ImageDraw.Draw(im); f = font("arial.ttf", 34)
cw, rh, x0, y0 = [380, 200, 220], 80, 40, 40
for r, row in enumerate(rows):
    x = x0
    for c, cell in enumerate(row):
        d.rectangle([x, y0 + r * rh, x + cw[c], y0 + (r + 1) * rh], outline=(0, 0, 0), width=3)
        d.text((x + 18, y0 + r * rh + 20), cell, font=f, fill=(0, 0, 0)); x += cw[c]
save("table_grid", im, "\n".join(" ".join(r) for r in rows))
# 12 math (plain-text ground truth; LaTeX needs a VLM)
MA = ["x² + y² = z²", "E = mc²", "H₂O and CO₂ are common"]
save("math_unicode", render(MA, font("cambria.ttc", 46)), MA)
# 13 scanned-like PDF (images only, 2 pages) + text-layer PDF
import pymupdf
pages = [render(EN, font("times.ttf", 36), bg=(255, 255, 255)), render(DE, font("times.ttf", 36), bg=(255, 255, 255))]
doc = pymupdf.open()
for p in pages:
    page = doc.new_page(width=595, height=842)
    tmp = OUT / "_p.png"; p.save(tmp)
    page.insert_image(pymupdf.Rect(30, 30, 565, 30 + 535 * p.height / p.width), filename=str(tmp))
    tmp.unlink()
doc.save(OUT / "pdf_scanned_2p.pdf")
(OUT / "pdf_scanned_2p.txt").write_text("\n".join(EN) + "\n\n" + "\n".join(DE), encoding="utf-8")
print("fixtures:", len(list(OUT.glob('*.*'))))
