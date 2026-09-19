import re
from datetime import datetime


def extract_invoice_data(text: str) -> dict:
    invoice_number_match = re.search(
        r"(?:Invoice Number|Invoice #):\s*(.+)",
        text,
        re.IGNORECASE
    )

    due_date_match = re.search(
        r"(?:Due Date|Payment Due):\s*(.+)",
        text,
        re.IGNORECASE
    )

    property_match = re.search(
        r"(?:Property|Service Location):\s*(.+)",
        text,
        re.IGNORECASE
    )

    amount_match = re.search(
        r"(?:Total Due|Balance Due):\s*\$?([\d,]+\.\d{2})",
        text,
        re.IGNORECASE
    )

    # For our controlled invoices,
    # the vendor is the first non-empty line.
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    vendor = lines[0] if lines else None

    if not all([
        vendor,
        invoice_number_match,
        due_date_match,
        property_match,
        amount_match
    ]):
        return {
            "success": False,
            "error": "Required invoice fields could not be extracted"
        }

    amount = float(
        amount_match.group(1).replace(",", "")
    )

    raw_due_date = due_date_match.group(1).strip()

    due_date = datetime.strptime(
        raw_due_date,
        "%B %d, %Y"
    ).date().isoformat()

    return {
        "success": True,
        "data": {
            "vendor": vendor,
            "invoice_number": invoice_number_match.group(1).strip(),
            "amount": amount,
            "property": property_match.group(1).strip(),
            "due_date": due_date
        }
    }