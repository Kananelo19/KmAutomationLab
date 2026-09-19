import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from services.retry import run_with_retry


load_dotenv()


class AIExtractedInvoice(BaseModel):
    vendor: str = Field(
        description=(
            "Company or vendor that issued "
            "the invoice"
        )
    )

    invoice_number: str = Field(
        description=(
            "Invoice or statement identifier"
        )
    )

    amount: float = Field(
        description=(
            "Final amount the customer must pay"
        )
    )

    property: str = Field(
        description=(
            "Property or service location where "
            "the work was performed"
        )
    )

    due_date: str = Field(
        description=(
            "Payment due date in YYYY-MM-DD format"
        )
    )


def extract_invoice_with_ai(
    text: str,
) -> AIExtractedInvoice:

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured"
        )

    client = genai.Client(
        api_key=api_key
    )

    prompt = f"""
Extract invoice information from the document below.

Rules:
- Do not invent information.
- vendor is the business that issued the invoice.
- invoice_number is the invoice or statement identifier.
- amount is the final amount owed, not subtotal or tax.
- property is the service/work location, not the vendor address.
- due_date must be formatted YYYY-MM-DD.

DOCUMENT:

{text}
"""

    def request_ai():
        return client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIExtractedInvoice,
            ),
        )

    response = run_with_retry(
        request_ai,
        max_attempts=3,
        base_delay=1.0,
    )

    return AIExtractedInvoice.model_validate_json(
        response.text
    )