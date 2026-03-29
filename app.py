import io
import re
from fastapi import FastAPI, File, UploadFile
from PIL import Image, ImageOps
import pytesseract

app = FastAPI()


def preprocess(img):
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.point(lambda x: 0 if x < 150 else 255, '1')
    return img


def extract_numbers(text):
    nums = re.findall(r"\d{3,8}", text or "")
    return [int(n) for n in nums]


def normalize_candidate(n):
    s = str(n)

    # تجاهل القيم الصغيرة جدًا أو الكبيرة جدًا
    if n < 500 or n > 4000:
        # مثال: 1000400 -> 1000 / 400
        for size in (4, 3):
            parts = re.findall(rf"\d{{{size}}}", s)
            for p in parts:
                v = int(p)
                if 500 <= v <= 4000:
                    return v

        # مثال: 220 -> غالبًا 2200
        if 100 <= n < 500:
            n10 = n * 10
            if 500 <= n10 <= 4000:
                return n10

        # مثال: 100 -> 1000
        if 100 <= n < 400:
            n10 = n * 10
            if 500 <= n10 <= 4000:
                return n10

        return 0

    return n


def clean_candidates(nums):
    out = []
    for n in nums:
        v = normalize_candidate(n)
        if 500 <= v <= 4000:
            out.append(v)
    return out


def pick_width(nums):
    nums = clean_candidates(nums)
    if not nums:
        return 0

    # القيم الشائعة في ملفاتك
    preferred = [1000, 1200, 1400, 1500, 1600, 1800, 2000, 2200, 2400, 2500, 3000]

    scored = []
    for n in nums:
        nearest = min(preferred, key=lambda x: abs(x - n))
        diff = abs(nearest - n)
        scored.append((diff, -n, nearest))

    # نختار الأقرب لقيمة منطقية معروفة
    best = sorted(scored, key=lambda x: (x[0], x[1]))[0][2]
    return best


def read_width(content):
    img = Image.open(io.BytesIO(content))
    w, h = img.size

    # محاولة 1: الجزء السفلي
    crop = img.crop((0, int(h * 0.7), w, h))
    crop = preprocess(crop)

    text1 = pytesseract.image_to_string(
        crop,
        config="--psm 6 -c tessedit_char_whitelist=0123456789"
    )
    nums1 = extract_numbers(text1)
    width1 = pick_width(nums1)
    if width1:
        return width1, text1

    # محاولة 2: الصورة كاملة
    full = preprocess(img)
    text2 = pytesseract.image_to_string(
        full,
        config="--psm 6 -c tessedit_char_whitelist=0123456789"
    )
    nums2 = extract_numbers(text2)
    width2 = pick_width(nums2)

    return width2, text2


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    content = await file.read()
    width, raw = read_width(content)

    return {
        "width": width,
        "raw": raw,
    }
