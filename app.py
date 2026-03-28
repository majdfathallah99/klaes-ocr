import io
import re
from fastapi import FastAPI, File, UploadFile
from PIL import Image
import pytesseract

app = FastAPI()


def crop_image(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    w, h = img.size

    # قص الجزء السفلي (عرض)
    width_crop = img.crop((0, int(h * 0.7), int(w * 0.8), h))

    # قص الجزء الأيمن (ارتفاع)
    height_crop = img.crop((int(w * 0.7), 0, w, int(h * 0.8)))

    buf1 = io.BytesIO()
    width_crop.save(buf1, format="PNG")

    buf2 = io.BytesIO()
    height_crop.save(buf2, format="PNG")

    return buf1.getvalue(), buf2.getvalue()


def read_text(image_bytes, rotate=False):
    img = Image.open(io.BytesIO(image_bytes))

    # 🔥 حل مشكلة النص العمودي (height)
    if rotate:
        img = img.rotate(90, expand=True)

    return pytesseract.image_to_string(
        img,
        config="--psm 6 -c tessedit_char_whitelist=0123456789"
    )


def extract_number(text):
    nums = re.findall(r"\d+", text)

    candidates = []
    for n in nums:
        val = int(n)
        if 300 <= val <= 5000:
            candidates.append(val)

    if candidates:
        return float(max(candidates))

    return 0.0


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

    # width عادي
    w_text = read_text(w_img)

    # height مع تدوير 🔥
    h_text = read_text(h_img, rotate=True)

    return {
        "width": extract_number(w_text),
        "height": extract_number(h_text),
        "width_raw": w_text,
        "height_raw": h_text,
    }
