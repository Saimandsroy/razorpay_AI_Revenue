from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.razorpay_client import create_client
from app.schemas import FailedPaymentSummary, IntelligenceSnapshot, ProcessPaymentRequest, ProcessPaymentResponse
from app.services.intelligence import build_intelligence_snapshot
from app.services.processor import list_failed_payments, process_payment

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


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


@app.post("/api/v1/batch/process", response_model=ProcessPaymentResponse, tags=["recovery"])
def process_single_failed_payment(payload: ProcessPaymentRequest, db: Session = Depends(get_db)) -> ProcessPaymentResponse:
    client = create_client(settings)
    if client is None:
        raise HTTPException(503, "Razorpay test-mode credentials are not configured.")
    return process_payment(db, client, payload.payment_id)


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
