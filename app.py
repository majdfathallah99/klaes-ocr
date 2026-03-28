import io
import re
from fastapi import FastAPI, File, UploadFile
from PIL import Image, ImageOps
import pytesseract

app = FastAPI()


def crop_image(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    w, h = img.size

    # قص العرض من أسفل الصورة
    width_crop = img.crop((
        int(w * 0.05),
        int(h * 0.78),
        int(w * 0.80),
        int(h * 1.00),
    ))

    # قص الارتفاع من يمين الصورة
    height_crop = img.crop((
        int(w * 0.72),
        int(h * 0.02),
        int(w * 1.00),
        int(h * 0.88),
    ))

    buf1 = io.BytesIO()
    width_crop.save(buf1, format="PNG")

    buf2 = io.BytesIO()
    height_crop.save(buf2, format="PNG")

    return buf1.getvalue(), buf2.getvalue()


def _ocr_candidates(img: Image.Image):
    variants = []

    # الصورة الأصلية
    variants.append(img)

    # تدوير 90
    variants.append(img.rotate(90, expand=True))

    # تدوير 270
    variants.append(img.rotate(270, expand=True))

    texts = []
    for variant in variants:
        v = ImageOps.autocontrast(variant.convert("L"))
        v = v.resize((v.width * 3, v.height * 3))

        try:
            txt = pytesseract.image_to_string(
                v,
                config="--psm 6 -c tessedit_char_whitelist=0123456789"
            )
            texts.append(txt or "")
        except Exception:
            texts.append("")

    return texts


def read_text(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    texts = _ocr_candidates(img)

    # اختر النص الذي يحتوي أكبر عدد من الأرقام
    def score(t):
        return len(re.findall(r"\d", t or ""))

    return max(texts, key=score)


def extract_number(text):
    nums = re.findall(r"\d+", text or "")
    candidates = []

    for n in nums:
        val = int(n)

        # نطاق منطقي لمقاسات Klaes
        if 300 <= val <= 5000:
            candidates.append(val)

    if not candidates:
        return 0.0

    # نأخذ الأكثر تكرارًا، ثم الأكبر
    counts = {}
    for val in candidates:
        counts[val] = counts.get(val, 0) + 1

    best = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))[0][0]
    return float(best)


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

    w_text = read_text(w_img)
    h_text = read_text(h_img)

    return {
        "width": extract_number(w_text),
        "height": extract_number(h_text),
        "width_raw": w_text,
        "height_raw": h_text,
    }
