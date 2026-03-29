import io
import re
from fastapi import FastAPI, File, UploadFile
from PIL import Image, ImageOps
import pytesseract

app = FastAPI()


# -------------------------
# preprocessing
# -------------------------
def preprocess(img):
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.point(lambda x: 0 if x < 150 else 255, '1')
    return img


# -------------------------
# extract numbers
# -------------------------
def extract_numbers(text):
    nums = re.findall(r"\d{3,5}", text)
    return [int(n) for n in nums]


# -------------------------
# choose width smartly
# -------------------------
def pick_width(nums):
    if not nums:
        return 0
    # غالبًا width بين 800 و 3000
    candidates = [n for n in nums if 500 < n < 4000]
    return max(candidates) if candidates else max(nums)


# -------------------------
# OCR logic
# -------------------------
def read_width(content):
    img = Image.open(io.BytesIO(content))

    # محاولة 1: crop الجزء السفلي
    w, h = img.size
    crop = img.crop((0, int(h * 0.7), w, h))

    crop = preprocess(crop)

    text1 = pytesseract.image_to_string(
        crop,
        config="--psm 6 -c tessedit_char_whitelist=0123456789"
    )

    nums1 = extract_numbers(text1)
    width1 = pick_width(nums1)

    # إذا نجح نرجعه
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


# -------------------------
# API
# -------------------------
@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    content = await file.read()

    width, raw = read_width(content)

    return {
        "width": width,
        "raw": raw,
    }
