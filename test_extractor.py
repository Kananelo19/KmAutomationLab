import pymupdf

from services.invoice_extractor import extract_invoice_data


document = pymupdf.open("test_documents/invoice_vendor3.pdf")

text = ""

for page in document:
    text += page.get_text()

document.close()


result = extract_invoice_data(text)

print(result)