from services.invoice_extractor import extract_invoice_data
from services.ai_invoice_extractor import extract_invoice_with_ai


def extract_invoice(text: str) -> dict:
    deterministic_result = extract_invoice_data(text)

    if deterministic_result["success"]:
        return {
            "success": True,
            "extraction_method": "deterministic",
            "data": deterministic_result["data"]
        }

    ai_result = extract_invoice_with_ai(text)

    return {
        "success": True,
        "extraction_method": "ai",
        "data": ai_result.model_dump()
    }