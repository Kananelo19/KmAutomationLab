from pydantic import ValidationError

from schemas import ExtractedInvoice


APPROVAL_THRESHOLD = 5000.00


def process_extracted_invoice(
    extraction_result: dict,
) -> dict:

    try:
        invoice = ExtractedInvoice.model_validate(
            extraction_result["data"]
        )

    except ValidationError as error:
        return {
            "success": False,
            "status": "human_review",
            "reason": (
                "Extracted invoice failed validation"
            ),
            "validation_errors": error.errors(),
        }

    if invoice.amount > APPROVAL_THRESHOLD:
        status = "manager_review"

        reason = (
            f"Invoice exceeds "
            f"${APPROVAL_THRESHOLD:,.2f} "
            "automatic processing threshold"
        )

    else:
        status = "approved_for_processing"

        reason = (
            "Invoice passed automatic "
            "processing rules"
        )

    return {
        "success": True,
        "status": status,
        "reason": reason,
        "extraction_method":
            extraction_result["extraction_method"],
        "invoice": invoice.model_dump(
            mode="json"
        ),
    }