import io
import re
from fastapi import FastAPI, File, UploadFile, HTTPException
from PIL import Image
import pytesseract

app = FastAPI()

# عدّل هذا فقط إذا كان مسار التثبيت مختلفًا عندك
pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"


def crop_image(img_bytes: bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    w, h = img.size

    width_crop = img.crop((
        int(w * 0.05),
        int(h * 0.80),
        int(w * 0.78),
        int(h * 0.99),
    ))

    height_crop = img.crop((
        int(w * 0.78),
        int(h * 0.05),
        int(w * 0.99),
        int(h * 0.82),
    ))

    return width_crop, height_crop


def read_text(image, rotate=False):
    if rotate:
        image = image.rotate(270, expand=True)

    text = pytesseract.image_to_string(
        image,
        config="--psm 7 -c tessedit_char_whitelist=0123456789"
    )
    return text or ""


def extract_number(text):
    nums = re.findall(r"\d{3,5}", text or "")
    valid = []

    for raw in nums:
        txt = raw.strip()

        if len(txt) == 5 and txt.endswith("0"):
            txt = txt[:-1]

        if len(txt) == 4 and txt.startswith("0"):
            txt = txt[1:]

        if txt.isdigit():
            value = int(txt)
            if 300 <= value <= 5000:
                valid.append(value)

    if not valid:
        return 0.0

    counts = {}
    for value in valid:
        counts[value] = counts.get(value, 0) + 1

    best = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))[0][0]
    return float(best)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        w_img, h_img = crop_image(content)

        w_text = read_text(w_img, rotate=False)
        h_text = read_text(h_img, rotate=True)

        return {
            "filename": file.filename,
            "width": extract_number(w_text),
            "height": extract_number(h_text),
            "width_raw": w_text,
            "height_raw": h_text,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))