from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import pandas as pd
import io
import fitz
import pytesseract
from PIL import Image
import tempfile
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("static/frontend.html", "r", encoding="utf-8") as f:
        return f.read()

def extract_text_from_pdf(file_bytes):
    text = ""
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_with_ocr(file_bytes):
    images = []
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp.close()
        doc = fitz.open(tmp.name)
        for page_num in range(len(doc)):
            pix = doc[page_num].get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        os.remove(tmp.name)

    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    return text

def process_excel(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes))
    return df

def process_csv(file_bytes):
    df = pd.read_csv(io.BytesIO(file_bytes))
    return df

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        filename = file.filename
        file_bytes = await file.read()
        try:
            if filename.endswith(('.xls', '.xlsx')):
                df = process_excel(file_bytes)
                results.append({"filename": filename, "status": "success", "data": df.head(5).to_dict(orient="records")})
            elif filename.endswith('.csv'):
                df = process_csv(file_bytes)
                results.append({"filename": filename, "status": "success", "data": df.head(5).to_dict(orient="records")})
            elif filename.endswith('.pdf'):
                try:
                    text = extract_text_from_pdf(file_bytes)
                    if not text.strip():
                        text = extract_text_with_ocr(file_bytes)
                    results.append({"filename": filename, "status": "success", "data": text[:1000]})
                except Exception as e:
                    results.append({"filename": filename, "status": "error", "error": str(e)})
            else:
                results.append({"filename": filename, "status": "unsupported format"})
        except Exception as e:
            results.append({"filename": filename, "status": "error", "error": str(e)})

    return JSONResponse(content={"results": results})
