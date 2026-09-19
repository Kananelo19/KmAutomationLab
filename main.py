from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pymupdf
import shutil

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request

from database import get_db
from models import (
    AuditEvent,
    InvoiceRecord,
    Job,
)
from services.hybrid_invoice_extractor import (
    extract_invoice,
)
from services.invoice_processor import (
    process_extracted_invoice,
)


INVOICE_STORAGE = Path(
    "storage/invoices"
)

INVOICE_STORAGE.mkdir(
    parents=True,
    exist_ok=True,
)


app = FastAPI(
    title="KM Automation",
    version="1.0.0",
)


app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


templates = Jinja2Templates(
    directory="templates"
)


def now():
    return datetime.now(
        timezone.utc
    )


def add_audit_event(
    db: Session,
    job_id: str,
    event_type: str,
    actor: str,
    message: str,
    invoice_id: int | None = None,
):
    db.add(
        AuditEvent(
            job_id=job_id,
            invoice_id=invoice_id,
            event_type=event_type,
            actor=actor,
            message=message,
            created_at=now(),
        )
    )


@app.get("/")
def home():
    return RedirectResponse(
        url="/dashboard",
        status_code=303,
    )


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "KM Automation",
    }


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

@app.get(
    "/dashboard",
    response_class=HTMLResponse,
)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    invoices = (
        db.query(InvoiceRecord)
        .order_by(
            InvoiceRecord.created_at.desc()
        )
        .all()
    )

    review_invoices = [
        invoice
        for invoice in invoices
        if invoice.workflow_status
        == "manager_review"
    ]

    automatic_count = sum(
        1
        for invoice in invoices
        if invoice.workflow_status
        == "approved_for_processing"
    )

    approved_count = sum(
        1
        for invoice in invoices
        if invoice.workflow_status
        == "approved"
    )
    
    result = request.query_params.get("result")

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "invoices": invoices,
            "review_invoices":
                review_invoices,
            "total_invoices":
                len(invoices),
            "review_count":
                len(review_invoices),
            "automatic_count":
                automatic_count,
            "approved_count":
                approved_count,
            "result": result,
        },
    )


# ---------------------------------------------------------
# INVOICE HISTORY
# ---------------------------------------------------------

@app.get(
    "/dashboard/invoices/{invoice_id}/history",
    response_class=HTMLResponse,
)
def dashboard_history(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
):

    invoice = (
        db.query(InvoiceRecord)
        .filter(
            InvoiceRecord.id
            == invoice_id
        )
        .first()
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.job_id
            == invoice.job_id
        )
        .order_by(
            AuditEvent.created_at.asc(),
            AuditEvent.id.asc(),
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "invoice": invoice,
            "events": events,
            "Result": result,
        },
    )


@app.get(
    "/invoices/{invoice_id}/history"
)
def invoice_history(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    invoice = (
        db.query(InvoiceRecord)
        .filter(
            InvoiceRecord.id
            == invoice_id
        )
        .first()
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.job_id
            == invoice.job_id
        )
        .order_by(
            AuditEvent.created_at.asc(),
            AuditEvent.id.asc(),
        )
        .all()
    )

    return {
        "invoice_id": invoice.id,
        "vendor": invoice.vendor,
        "invoice_number":
            invoice.invoice_number,
        "current_status":
            invoice.workflow_status,
        "history": [
            {
                "event_type":
                    event.event_type,
                "actor":
                    event.actor,
                "message":
                    event.message,
                "created_at":
                    event.created_at,
            }
            for event in events
        ],
    }


# ---------------------------------------------------------
# REVIEW QUEUE
# ---------------------------------------------------------

@app.get("/invoices/review")
def review_queue(
    db: Session = Depends(get_db),
):

    invoices = (
        db.query(InvoiceRecord)
        .filter(
            InvoiceRecord.workflow_status
            == "manager_review"
        )
        .order_by(
            InvoiceRecord.created_at.asc()
        )
        .all()
    )

    return {
        "count": len(invoices),
        "invoices": [
            {
                "id": invoice.id,
                "vendor": invoice.vendor,
                "invoice_number":
                    invoice.invoice_number,
                "amount": invoice.amount,
                "property":
                    invoice.property,
                "due_date":
                    invoice.due_date,
                "workflow_status":
                    invoice.workflow_status,
                "review_reason":
                    invoice.review_reason,
            }
            for invoice in invoices
        ],
    }


# ---------------------------------------------------------
# APPROVAL / REJECTION
# ---------------------------------------------------------

def change_invoice_status(
    invoice_id: int,
    new_status: str,
    db: Session,
):

    invoice = (
        db.query(InvoiceRecord)
        .filter(
            InvoiceRecord.id
            == invoice_id
        )
        .first()
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    if (
        invoice.workflow_status
        != "manager_review"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Only invoices awaiting "
                "manager review can be changed"
            ),
        )

    if new_status == "approved":
        message = (
            "Invoice approved by manager"
        )
        event_type = "invoice_approved"

    else:
        message = (
            "Invoice rejected by manager"
        )
        event_type = "invoice_rejected"

    invoice.workflow_status = (
        new_status
    )

    invoice.review_reason = message

    job = (
        db.query(Job)
        .filter(
            Job.job_id
            == invoice.job_id
        )
        .first()
    )

    if job:
        job.status = new_status
        job.current_step = new_status
        job.completed_at = now()

    add_audit_event(
        db=db,
        job_id=invoice.job_id,
        invoice_id=invoice.id,
        event_type=event_type,
        actor="manager",
        message=message,
    )

    db.commit()
    db.refresh(invoice)

    return invoice


@app.post(
    "/invoices/{invoice_id}/approve"
)
def approve_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    invoice = change_invoice_status(
        invoice_id,
        "approved",
        db,
    )

    return {
        "message":
            "Invoice approved",
        "invoice_id":
            invoice.id,
        "status":
            invoice.workflow_status,
    }


@app.post(
    "/invoices/{invoice_id}/reject"
)
def reject_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    invoice = change_invoice_status(
        invoice_id,
        "rejected",
        db,
    )

    return {
        "message":
            "Invoice rejected",
        "invoice_id":
            invoice.id,
        "status":
            invoice.workflow_status,
    }


@app.post(
    "/dashboard/invoices/{invoice_id}/approve"
)
def dashboard_approve(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    change_invoice_status(
        invoice_id,
        "approved",
        db,
    )

    return RedirectResponse(
        url="/dashboard",
        status_code=303,
    )


@app.post(
    "/dashboard/invoices/{invoice_id}/reject"
)
def dashboard_reject(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    change_invoice_status(
        invoice_id,
        "rejected",
        db,
    )

    return RedirectResponse(
        url="/dashboard",
        status_code=303,
    )


# ---------------------------------------------------------
# GET INVOICE / JOB
# ---------------------------------------------------------

@app.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):

    invoice = (
        db.query(InvoiceRecord)
        .filter(
            InvoiceRecord.id
            == invoice_id
        )
        .first()
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    return invoice


@app.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
):

    job = (
        db.query(Job)
        .filter(
            Job.job_id == job_id
        )
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return job


# ---------------------------------------------------------
# CORE PROCESSOR
# ---------------------------------------------------------

def process_uploaded_invoice(
    file: UploadFile,
    db: Session,
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail=(
                "File must have a filename"
            ),
        )

    if (
        file.content_type
        != "application/pdf"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF invoices are allowed"
            ),
        )

    job_id = str(uuid4())

    file_path = (
        INVOICE_STORAGE
        / f"{job_id}.pdf"
    )

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer,
        )

    job = Job(
        job_id=job_id,
        status="processing",
        current_step="received",
        attempts=1,
        event_type="invoice.uploaded",
        sender="manual_upload",
        filename=file.filename,
        created_at=now(),
    )

    db.add(job)

    add_audit_event(
        db,
        job_id,
        "invoice_received",
        "system",
        f"Invoice received: {file.filename}",
    )

    db.commit()
    db.refresh(job)

    try:

        job.current_step = (
            "extracting_text"
        )

        document = pymupdf.open(
            file_path
        )

        extracted_text = "".join(
            page.get_text()
            for page in document
        )

        document.close()

        if not extracted_text.strip():
            raise ValueError(
                "PDF contains no "
                "extractable text"
            )

        add_audit_event(
            db,
            job_id,
            "text_extracted",
            "system",
            (
                "Text successfully "
                "extracted from PDF"
            ),
        )

        job.current_step = (
            "extracting_fields"
        )

        extraction_result = (
            extract_invoice(
                extracted_text
            )
        )

        method = extraction_result[
            "extraction_method"
        ]

        add_audit_event(
            db,
            job_id,
            f"{method}_extraction_used",
            "system",
            (
                f"{method.title()} "
                "extraction completed"
            ),
        )

        job.current_step = "validating"

        processing_result = (
            process_extracted_invoice(
                extraction_result
            )
        )

        if not processing_result[
            "success"
        ]:

            job.status = "human_review"
            job.current_step = (
                "human_review"
            )

            job.error = (
                processing_result["reason"]
            )

            add_audit_event(
                db,
                job_id,
                "validation_failed",
                "system",
                processing_result[
                    "reason"
                ],
            )

            db.commit()

            return {
                "job_id": job_id,
                "status":
                    "human_review",
                "reason":
                    processing_result[
                        "reason"
                    ],
            }

        add_audit_event(
            db,
            job_id,
            "validation_passed",
            "system",
            (
                "Invoice passed "
                "validation"
            ),
        )

        invoice_data = (
            processing_result["invoice"]
        )

        existing = (
            db.query(InvoiceRecord)
            .filter(
                InvoiceRecord.vendor
                == invoice_data["vendor"],
                InvoiceRecord.invoice_number
                == invoice_data[
                    "invoice_number"
                ],
            )
            .first()
        )

        if existing:

            job.status = "duplicate"
            job.current_step = (
                "duplicate"
            )

            job.completed_at = now()

            add_audit_event(
                db,
                job_id,
                "duplicate_detected",
                "system",
                (
                    "Duplicate invoice "
                    f"matches invoice "
                    f"#{existing.id}"
                ),
                existing.id,
            )

            db.commit()

            return {
                "job_id": job_id,
                "status": "duplicate",
                "existing_invoice_id":
                    existing.id,
            }

        invoice = InvoiceRecord(
            job_id=job_id,
            vendor=invoice_data[
                "vendor"
            ],
            invoice_number=invoice_data[
                "invoice_number"
            ],
            amount=invoice_data[
                "amount"
            ],
            property=invoice_data[
                "property"
            ],
            due_date=invoice_data[
                "due_date"
            ],
            extraction_method=method,
            workflow_status=
                processing_result[
                    "status"
                ],
            review_reason=
                processing_result[
                    "reason"
                ],
            created_at=now(),
        )

        db.add(invoice)

        # Get invoice.id without
        # committing yet.
        db.flush()

        add_audit_event(
            db,
            job_id,
            "invoice_saved",
            "system",
            (
                "Invoice saved "
                "to PostgreSQL"
            ),
            invoice.id,
        )

        if (
            processing_result["status"]
            == "manager_review"
        ):

            event_type = (
                "manager_review_required"
            )

        else:

            event_type = (
                "automatic_processing_approved"
            )

        add_audit_event(
            db,
            job_id,
            event_type,
            "system",
            processing_result[
                "reason"
            ],
            invoice.id,
        )

        job.status = (
            processing_result["status"]
        )

        job.current_step = (
            processing_result["status"]
        )

        job.completed_at = now()

        try:
            db.commit()

        except IntegrityError:

            db.rollback()

            existing = (
                db.query(InvoiceRecord)
                .filter(
                    InvoiceRecord.vendor
                    == invoice_data[
                        "vendor"
                    ],
                    InvoiceRecord.invoice_number
                    == invoice_data[
                        "invoice_number"
                    ],
                )
                .first()
            )

            job = (
                db.query(Job)
                .filter(
                    Job.job_id == job_id
                )
                .first()
            )

            if job:
                job.status = "duplicate"
                job.current_step = (
                    "duplicate"
                )
                job.completed_at = now()

                add_audit_event(
                    db,
                    job_id,
                    "duplicate_detected",
                    "system",
                    (
                        "Database constraint "
                        "prevented duplicate"
                    ),
                    (
                        existing.id
                        if existing
                        else None
                    ),
                )

                db.commit()

            return {
                "job_id": job_id,
                "status": "duplicate",
                "existing_invoice_id": (
                    existing.id
                    if existing
                    else None
                ),
            }

        db.refresh(invoice)

        return {
            "job_id": job_id,
            "invoice_id": invoice.id,
            "status":
                invoice.workflow_status,
            "extraction_method":
                invoice.extraction_method,
            "invoice":
                invoice_data,
        }

    except Exception as error:

        db.rollback()

        job = (
            db.query(Job)
            .filter(
                Job.job_id == job_id
            )
            .first()
        )

        if job:

            job.status = "failed"
            job.current_step = "failed"
            job.error = str(error)

            add_audit_event(
                db,
                job_id,
                "processing_failed",
                "system",
                str(error),
            )

            db.commit()

        raise HTTPException(
            status_code=422,
            detail=(
                "Invoice processing "
                f"failed: {error}"
            ),
        )


# ---------------------------------------------------------
# API UPLOAD
# ---------------------------------------------------------

@app.post("/invoices/upload")
def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    return process_uploaded_invoice(
        file,
        db,
    )


# ---------------------------------------------------------
# DASHBOARD UPLOAD
# ---------------------------------------------------------

@app.post("/dashboard/upload")
def dashboard_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    result = process_uploaded_invoice(
        file,
        db,
    )

    status = result.get(
        "status",
        "processed",
    )

    return RedirectResponse(
        url=(
            "/dashboard"
            f"?result={status}"
        ),
        status_code=303,
    )