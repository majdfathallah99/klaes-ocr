import io
import re
from fastapi import FastAPI, File, UploadFile
from PIL import Image, ImageOps, ImageFilter
import pytesseract

app = FastAPI()


def preprocess(img: Image.Image) -> Image.Image:
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.resize((img.width * 4, img.height * 4))
    img = img.filter(ImageFilter.SHARPEN)
    return img


def crop_image(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    w, h = img.size

    # العرض: شريط سفلي فقط
    width_crop = img.crop((
        int(w * 0.10),
        int(h * 0.82),
        int(w * 0.78),
        int(h * 0.99),
    ))

    # الارتفاع: شريط أيمن أنحف وأكثر دقة
    height_crop = img.crop((
        int(w * 0.83),
        int(h * 0.05),
        int(w * 0.99),
        int(h * 0.82),
    ))

    buf1 = io.BytesIO()
    preprocess(width_crop).save(buf1, format="PNG")

    buf2 = io.BytesIO()
    preprocess(height_crop).save(buf2, format="PNG")

    return buf1.getvalue(), buf2.getvalue()


def ocr_variants(image: Image.Image):
    variants = [
        image,
        image.rotate(90, expand=True),
        image.rotate(270, expand=True),
        ImageOps.invert(image),
        ImageOps.invert(image.rotate(90, expand=True)),
        ImageOps.invert(image.rotate(270, expand=True)),
    ]

    texts = []
    for variant in variants:
        for psm in (6, 7, 11, 13):
            try:
                txt = pytesseract.image_to_string(
                    variant,
                    config=f"--psm {psm} -c tessedit_char_whitelist=0123456789"
                )
                if txt:
                    texts.append(txt)
            except Exception:
                pass
    return texts


def extract_all_numbers(texts):
    nums = []
    for text in texts:
        found = re.findall(r"\d{3,5}", text or "")
        for raw in found:
            txt = raw.strip()

            if len(txt) == 5 and txt.endswith("0"):
                txt = txt[:-1]

            if len(txt) == 4 and txt.startswith("0"):
                txt = txt[1:]

            if txt.isdigit():
                val = int(txt)
                if 300 <= val <= 5000:
                    nums.append(val)
    return nums


def pick_width(texts):
    nums = extract_all_numbers(texts)
    if not nums:
        return 0.0

    counts = {}
    for n in nums:
        counts[n] = counts.get(n, 0) + 1

    # العرض عادة أصغر من الارتفاع
    best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return float(best)


def pick_height(texts):
    nums = extract_all_numbers(texts)
    if not nums:
        return 0.0

    counts = {}
    for n in nums:
        counts[n] = counts.get(n, 0) + 1

    # الارتفاع عادة أكبر أو أوضح، نأخذ الأكثر تكرارًا ثم الأكبر
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

    w_img_bytes, h_img_bytes = crop_image(content)

    w_img = Image.open(io.BytesIO(w_img_bytes))
    h_img = Image.open(io.BytesIO(h_img_bytes))

    width_texts = ocr_variants(w_img)
    height_texts = ocr_variants(h_img)

    return {
        "width": pick_width(width_texts),
        "height": pick_height(height_texts),
        "width_raw": width_texts,
        "height_raw": height_texts,
    }
