import pymupdf

from services.hybrid_invoice_extractor import extract_invoice
from services.invoice_processor import process_extracted_invoice


def read_pdf(path: str) -> str:
    document = pymupdf.open(path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


invoice_files = [
    "test_documents/invoice.pdf",
    "test_documents/invoice_vendor2.pdf",
    "test_documents/invoice_vendor3.pdf"
]


for invoice_file in invoice_files:
    print(f"\n--- {invoice_file} ---")

    text = read_pdf(invoice_file)

    extraction = extract_invoice(text)

    result = process_extracted_invoice(extraction)

    print(result)