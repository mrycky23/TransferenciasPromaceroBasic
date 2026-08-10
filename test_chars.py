import pdfplumber

with pdfplumber.open('RPTFACTURASRECAUDACION08082026.PDF') as pdf:
    page = pdf.pages[0]
    chars = page.chars
    print(f"Number of characters on page 1: {len(chars)}")
    if len(chars) > 0:
        print("First 10 characters:")
        for c in chars[:10]:
            print(f"'{c['text']}' at ({c['x0']}, {c['top']})")
