import pymupdf

from services.ai_invoice_extractor import extract_invoice_with_ai


document = pymupdf.open(
    "test_documents/invoice_vendor3.pdf"
)

text = ""

for page in document:
    text += page.get_text()

document.close()


result = extract_invoice_with_ai(text)

print(result.model_dump())