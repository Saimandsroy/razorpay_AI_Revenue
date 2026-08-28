import logging

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_db
from app.models import AuditEvent, RecoveryBatch, RecoveryCase
from app.razorpay_client import create_client
from app.schemas import AuditTrailItem, BatchStartResponse, BatchSummary, CaseListItem, FailedPaymentSummary, IntelligenceSnapshot, ProcessPaymentRequest, ProcessPaymentResponse
from app.services.batch_processor import process_batch
from app.services.intelligence import build_intelligence_snapshot
from app.services.processor import list_failed_payments, process_payment

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
logger = logging.getLogger("recovery_api")
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(Exception)
async def unhandled_error(_: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=error)
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error. Check API logs."})


class HealthResponse(BaseModel):
    status: str
    environment: str
    razorpay_test_client_configured: bool


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    # Client construction validates our local SDK wiring without making an external call.
    client = create_client(settings)
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        razorpay_test_client_configured=client is not None,
    )


@app.post("/api/v1/cases/process", response_model=ProcessPaymentResponse, tags=["recovery"])
async def process_single_failed_payment(payload: ProcessPaymentRequest, db: Session = Depends(get_db)) -> ProcessPaymentResponse:
    client = create_client(settings)
    if client is None:
        raise HTTPException(503, "Razorpay test-mode credentials are not configured.")
    return await process_payment(db, client, payload.payment_id)


async def _run_batch(batch_id: object) -> None:
    db = SessionLocal()
    try:
        batch, client = db.get(RecoveryBatch, batch_id), create_client(settings)
        if batch and client:
            await process_batch(db, client, batch)
    finally:
        db.close()


@app.post("/api/v1/batch/process", response_model=BatchStartResponse, tags=["batch"])
async def start_batch(background_tasks: BackgroundTasks, batch_size: int = 50, db: Session = Depends(get_db)) -> BatchStartResponse:
    if not 1 <= batch_size <= 50: raise HTTPException(422, "batch_size must be between 1 and 50")
    if create_client(settings) is None: raise HTTPException(503, "Razorpay test-mode credentials are not configured.")
    batch = RecoveryBatch(name=f"recovery-{batch_size}", status="processing")
    db.add(batch); db.commit(); db.refresh(batch)
    background_tasks.add_task(_run_batch, batch.id)
    return BatchStartResponse(batch_id=batch.id, status=batch.status, created_at=batch.created_at.isoformat() if batch.created_at else None, cases_count=0)


@app.get("/api/v1/batch/{batch_id}/summary", response_model=BatchSummary, tags=["batch"])
def batch_summary(batch_id: str, db: Session = Depends(get_db)) -> BatchSummary:
    batch = db.get(RecoveryBatch, batch_id)
    if not batch: raise HTTPException(404, "Batch not found")
    rate = batch.total_revenue_recovered_paise / batch.revenue_at_risk_paise if batch.revenue_at_risk_paise else 0
    return BatchSummary(batch_id=batch.id, status=batch.status, cases_analyzed=batch.cases_analyzed, revenue_at_risk_paise=batch.revenue_at_risk_paise, revenue_recovered_paise=batch.total_revenue_recovered_paise, recovery_rate=round(rate, 3), by_diagnosis=batch.metrics_by_diagnosis, by_action=batch.metrics_by_action)


@app.get("/api/v1/batch/{batch_id}/cases", response_model=list[CaseListItem], tags=["batch"])
def batch_cases(batch_id: str, status: str | None = None, sort: str = "amount_desc", db: Session = Depends(get_db)) -> list[CaseListItem]:
    query = select(RecoveryCase).where(RecoveryCase.batch_id == batch_id)
    if status: query = query.where(RecoveryCase.status == status)
    query = query.order_by(RecoveryCase.amount_paise.desc() if sort == "amount_desc" else RecoveryCase.created_at.desc())
    return [CaseListItem(case_id=item.id, customer=item.customer_name or item.customer_id, amount_paise=item.amount_paise, diagnosis=item.diagnosis, action=item.recommended_action, status=item.status, recovered_amount_paise=item.recovered_amount_paise) for item in db.scalars(query)]


@app.get("/api/v1/cases/{case_id}/full", tags=["cases"])
def case_full(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(RecoveryCase, case_id)
    if not case: raise HTTPException(404, "Case not found")
    return {"case_id": str(case.id), "customer": case.customer_name or case.customer_id, "amount_paise": case.amount_paise, "diagnosis": case.diagnosis, "action": case.recommended_action, "status": case.status, "recovered_amount_paise": case.recovered_amount_paise, "policy_allowed": case.policy_allowed, "policy_reason": case.policy_reason, "execution": case.execution_result, "outcome_status": case.outcome_status}


@app.get("/api/v1/cases/{case_id}/audit", response_model=list[AuditTrailItem], tags=["cases"])
def case_audit(case_id: str, db: Session = Depends(get_db)) -> list[AuditTrailItem]:
    return [AuditTrailItem(event_type=item.event_type, timestamp=item.created_at.isoformat() if item.created_at else None, data=item.metadata_) for item in db.scalars(select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at))]


@app.get("/api/v1/payments/failed", response_model=list[FailedPaymentSummary], tags=["recovery"])
def detect_failed_payments(limit: int = 100) -> list[FailedPaymentSummary]:
    if not 1 <= limit <= 100:
        raise HTTPException(422, "limit must be between 1 and 100")
    client = create_client(settings)
    if client is None:
        raise HTTPException(503, "Razorpay test-mode credentials are not configured.")
    return list_failed_payments(client, limit)


@app.get("/api/v1/intelligence/scan", response_model=IntelligenceSnapshot, tags=["recovery"])
def scan_recovery_intelligence(limit: int = 100) -> IntelligenceSnapshot:
    if not 1 <= limit <= 100:
        raise HTTPException(422, "limit must be between 1 and 100")
    client = create_client(settings)
    if client is None:
        raise HTTPException(503, "Razorpay test-mode credentials are not configured.")
    payments = client.payment.all({"count": limit}).get("items", [])
    return build_intelligence_snapshot(payments)
