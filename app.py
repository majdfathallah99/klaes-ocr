import io
import re
from fastapi import FastAPI, File, UploadFile
from PIL import Image, ImageOps
import pytesseract

app = FastAPI()


def preprocess(img: Image.Image) -> Image.Image:
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.resize((img.width * 2, img.height * 2))
    return img


def crop_image(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    w, h = img.size

    width_crop = img.crop((
        int(w * 0.10),
        int(h * 0.82),
        int(w * 0.78),
        int(h * 0.99),
    ))

    height_crop = img.crop((
        int(w * 0.84),
        int(h * 0.08),
        int(w * 0.99),
        int(h * 0.82),
    ))

    buf1 = io.BytesIO()
    preprocess(width_crop).save(buf1, format="PNG")

    buf2 = io.BytesIO()
    preprocess(height_crop).save(buf2, format="PNG")

    return buf1.getvalue(), buf2.getvalue()


def read_width_text(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(
        img,
        config="--psm 7 -c tessedit_char_whitelist=0123456789"
    )


def read_height_text(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).rotate(270, expand=True)
    return pytesseract.image_to_string(
        img,
        config="--psm 7 -c tessedit_char_whitelist=0123456789"
    )


def extract_number(text, prefer_larger=False):
    nums = re.findall(r"\d{3,5}", text or "")
    vals = []

    for raw in nums:
        txt = raw.strip()

        if len(txt) == 5 and txt.endswith("0"):
            txt = txt[:-1]

        if len(txt) == 4 and txt.startswith("0"):
            txt = txt[1:]

        if txt.isdigit():
            val = int(txt)
            if 300 <= val <= 3000:
                vals.append(val)

    if not vals:
        return 0.0

    vals = sorted(set(vals))
    return float(max(vals) if prefer_larger else min(vals))


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    content = await file.read()

    w_img, h_img = crop_image(content)

    w_text = read_width_text(w_img)
    h_text = read_height_text(h_img)

    return {
        "width": extract_number(w_text, prefer_larger=False),
        "height": extract_number(h_text, prefer_larger=True),
        "width_raw": w_text,
        "height_raw": h_text,
    }
