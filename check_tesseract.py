import shutil

tesseract_path = shutil.which("tesseract")
print(f"Tesseract found at: {tesseract_path}")

import os
common_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Usuario\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
]

for p in common_paths:
    if os.path.exists(p):
        print(f"Tesseract found in common path: {p}")
