from datetime import date

from pydantic import BaseModel, Field


class ExtractedInvoice(BaseModel):
    vendor: str = Field(
        min_length=2,
        max_length=100,
    )

    invoice_number: str = Field(
        min_length=1,
        max_length=50,
    )

    amount: float = Field(
        gt=0,
    )

    property: str = Field(
        min_length=3,
        max_length=200,
    )

    due_date: date