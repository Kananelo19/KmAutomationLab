from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    job_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    current_step: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    sender: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class InvoiceRecord(Base):
    __tablename__ = "invoices"

    __table_args__ = (
        UniqueConstraint(
            "vendor",
            "invoice_number",
            name="uq_invoice_vendor_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    job_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
    )

    vendor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    invoice_number: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        nullable=False,
    )

    property: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    due_date: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    extraction_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    workflow_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    review_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    job_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )

    invoice_id: Mapped[int | None] = mapped_column(
        Integer,
        index=True,
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )