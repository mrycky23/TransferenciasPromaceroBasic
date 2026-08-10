import pdfplumber

print("Extracting first 2 pages of PDF:")
with pdfplumber.open('RPTFACTURASRECAUDACION08082026.PDF') as pdf:
    for i, page in enumerate(pdf.pages[:2]):
        print(f"--- PAGE {i+1} ---")
        text = page.extract_text()
        print(text[:1000] if text else "NO TEXT FOUND")
