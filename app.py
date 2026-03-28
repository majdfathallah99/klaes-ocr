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
     nums = re.findall(r"\d{3,5}", text)

       candidates = []
       for n in nums:
          val = int(n)

          # فلترة ذكية
             if 400 <= val <= 3000:   # نطاق منطقي للأبواب والنوافذ
              candidates.append(val)

         if not candidates:
              return 0.0

      # خذ أكبر رقم (غالبًا هو البعد)
       return float(max(candidates))


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
