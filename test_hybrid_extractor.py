import pymupdf

from services.hybrid_invoice_extractor import extract_invoice


def read_pdf(path: str) -> str:
    document = pymupdf.open(path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


print("\n--- VENDOR 1 ---")
text = read_pdf("test_documents/invoice.pdf")
print(extract_invoice(text))


print("\n--- VENDOR 2 ---")
text = read_pdf("test_documents/invoice_vendor2.pdf")
print(extract_invoice(text))


print("\n--- VENDOR 3 ---")
text = read_pdf("test_documents/invoice_vendor3.pdf")
print(extract_invoice(text))