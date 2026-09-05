import logging

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_db
from app.models import AuditEvent, RecoveryAction, RecoveryBatch, RecoveryCase
from app.razorpay_client import create_client
from app.schemas import (
    ActionEventRequest,
    AuditTrailItem,
    BatchStartResponse,
    BatchSummary,
    CaseListItem,
    CaseListItemV2,
    CustomerJourneyResponse,
    FailedPaymentSummary,
    IntelligenceSnapshot,
    ProcessPaymentRequest,
    ProcessPaymentResponse,
    RecoveryActionListItem,
    RecoveryActionResponse,
    RecoveryActionsStatsResponse,
    TimelineEvent,
)
from app.services.action_events import DuplicateEventError, InvalidEventError, process_action_event
from app.services.batch_processor import process_batch
from app.services.demo_batch import clear_demo_batches, process_demo_batch
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
    from fastapi.responses import JSONResponse as _JSONResponse
    client = create_client(settings)
    if client is None:
        raise HTTPException(503, "Razorpay test-mode credentials are not configured.")
    response, was_duplicate = await process_payment(db, client, payload.payment_id)
    if was_duplicate:
        # Return same schema with a header signalling idempotent replay — no 409.
        return JSONResponse(
            status_code=200,
            content=response.model_dump(mode="json"),
            headers={"X-Idempotent-Replay": "true"},
        )
    return response


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


@app.get("/api/v1/batch/live", response_model=BatchStartResponse, tags=["batch"])
async def get_or_create_live_batch(db: Session = Depends(get_db)) -> BatchStartResponse:
    batch = db.scalar(select(RecoveryBatch).where(RecoveryBatch.name == "live-session").order_by(RecoveryBatch.created_at.desc()))
    if not batch or batch.status != "processing":
        batch = RecoveryBatch(name="live-session", status="processing")
        db.add(batch)
        db.commit()
        db.refresh(batch)
    return BatchStartResponse(batch_id=batch.id, status=batch.status, created_at=batch.created_at.isoformat() if batch.created_at else None, cases_count=0)


@app.post("/api/v1/demo/batch", response_model=BatchStartResponse, tags=["demo"])
async def start_demo_batch(db: Session = Depends(get_db)) -> BatchStartResponse:
    """Development-only fixtures; no Razorpay SDK/API calls are made here."""
    if settings.environment.lower() == "production":
        raise HTTPException(404, "Demo fixtures are disabled in production.")
    batch = await process_demo_batch(db)
    return BatchStartResponse(batch_id=batch.id, status=batch.status, created_at=batch.created_at.isoformat() if batch.created_at else None, cases_count=batch.cases_analyzed)


@app.post("/api/v1/demo/recovery-batch", response_model=BatchStartResponse, tags=["demo"])
def create_simulator_batch_endpoint(db: Session = Depends(get_db)) -> BatchStartResponse:
    if settings.environment.lower() == "production":
        raise HTTPException(404, "Demo fixtures are disabled in production.")
    from app.services.simulator import create_simulator_batch
    batch = create_simulator_batch(db)
    return BatchStartResponse(batch_id=batch.id, status=batch.status, created_at=batch.created_at.isoformat() if batch.created_at else None, cases_count=0)


@app.post("/api/v1/demo/batch/{batch_id}/advance", tags=["demo"])
async def advance_simulator_batch_endpoint(batch_id: str, db: Session = Depends(get_db)):
    if settings.environment.lower() == "production":
        raise HTTPException(404, "Demo fixtures are disabled in production.")
    from app.services.simulator import advance_simulator_batch
    try:
        return await advance_simulator_batch(db, batch_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/v1/demo/batch/{batch_id}/simulate-responses", tags=["demo"])
def simulate_responses_endpoint(batch_id: str, db: Session = Depends(get_db)):
    if settings.environment.lower() == "production":
        raise HTTPException(404, "Demo fixtures are disabled in production.")
    from app.services.simulator import simulate_customer_responses
    try:
        return simulate_customer_responses(db, batch_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/v1/demo/batch/{batch_id}/simulate-recoveries", tags=["demo"])
def simulate_recoveries_endpoint(batch_id: str, db: Session = Depends(get_db)):
    if settings.environment.lower() == "production":
        raise HTTPException(404, "Demo fixtures are disabled in production.")
    from app.services.simulator import simulate_recoveries
    try:
        return simulate_recoveries(db, batch_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

@app.delete("/api/v1/demo/batches", tags=["demo"])
def clear_demo_data(db: Session = Depends(get_db)) -> dict[str, int]:
    if settings.environment.lower() == "production":
        raise HTTPException(404, "Demo fixtures are disabled in production.")
    return {"deleted_batches": clear_demo_batches(db)}


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


@app.get("/api/v1/audit", tags=["system"])
def global_audit_feed(limit: int = 100, event_type: str | None = None, db: Session = Depends(get_db)):
    """Global audit event stream — most recent events across all cases."""
    if not 1 <= limit <= 500:
        raise HTTPException(422, "limit must be between 1 and 500")
    query = select(AuditEvent, RecoveryCase).join(RecoveryCase, AuditEvent.case_id == RecoveryCase.id).order_by(AuditEvent.created_at.desc()).limit(limit)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    rows = list(db.execute(query))
    return [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "case_id": str(event.case_id),
            "payment_id": case.razorpay_payment_id,
            "customer": case.customer_name or case.customer_id,
            "timestamp": event.created_at.isoformat() if event.created_at else None,
            "data": event.metadata_,
        }
        for event, case in rows
    ]


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


# ── Recovery Actions API ──────────────────────────────────────────────


def _action_to_response(action: RecoveryAction) -> RecoveryActionResponse:
    return RecoveryActionResponse(
        id=action.id, case_id=action.case_id, action_type=action.action_type,
        channel=action.channel, status=action.status, recipient=action.recipient,
        provider=action.provider, provider_reference=action.provider_reference,
        action_url=action.action_url, amount_paise=action.amount_paise,
        sent_at=action.sent_at.isoformat() if action.sent_at else None,
        clicked_at=action.clicked_at.isoformat() if action.clicked_at else None,
        responded_at=action.responded_at.isoformat() if action.responded_at else None,
        completed_at=action.completed_at.isoformat() if action.completed_at else None,
        revenue_recovered_paise=action.revenue_recovered_paise,
        failure_reason=action.failure_reason,
        created_at=action.created_at.isoformat() if action.created_at else None,
    )


@app.get("/api/v1/cases/{case_id}/journey", response_model=CustomerJourneyResponse, tags=["cases"])
def case_journey(case_id: str, db: Session = Depends(get_db)) -> CustomerJourneyResponse:
    """Full customer recovery journey: case details, actions, timeline, and revenue."""
    case = db.get(RecoveryCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    # Fetch actions
    actions = list(db.scalars(
        select(RecoveryAction).where(RecoveryAction.case_id == case_id).order_by(RecoveryAction.created_at)
    ))

    # Build timeline from audit events
    audit_events = list(db.scalars(
        select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.created_at)
    ))
    timeline = [
        TimelineEvent(
            event_type=event.event_type,
            timestamp=event.created_at.isoformat() if event.created_at else None,
            message=event.message,
        )
        for event in audit_events
    ]

    # Revenue summary
    total_recovered = sum(a.revenue_recovered_paise for a in actions)

    return CustomerJourneyResponse(
        case={
            "id": str(case.id),
            "payment_id": case.razorpay_payment_id,
            "customer_name": case.customer_name,
            "customer_email": None,  # extracted from payment if available
            "customer_id": case.customer_id,
            "amount_paise": case.amount_paise,
            "diagnosis": case.diagnosis,
            "recovery_score": float(case.recovery_score) if case.recovery_score is not None else None,
            "recommended_action": case.recommended_action,
            "policy_allowed": case.policy_allowed,
            "policy_reason": case.policy_reason,
            "status": case.status,
            "outcome_status": case.outcome_status,
            "execution_status": case.execution_status,
        },
        actions=[_action_to_response(a) for a in actions],
        timeline=timeline,
        revenue={
            "at_risk_paise": case.revenue_at_risk_paise,
            "recovered_paise": total_recovered,
        },
    )


@app.get("/api/v1/recovery-actions", response_model=list[RecoveryActionListItem], tags=["recovery-actions"])
def list_recovery_actions(
    batch_id: str | None = None,
    case_id: str | None = None,
    action_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[RecoveryActionListItem]:
    """List recovery actions with optional filtering."""
    query = select(RecoveryAction, RecoveryCase).join(RecoveryCase, RecoveryAction.case_id == RecoveryCase.id)
    if batch_id:
        query = query.where(RecoveryCase.batch_id == batch_id)
    if case_id:
        query = query.where(RecoveryAction.case_id == case_id)
    if action_type:
        query = query.where(RecoveryAction.action_type == action_type)
    if status:
        query = query.where(RecoveryAction.status == status)
    query = query.order_by(RecoveryAction.created_at.desc()).limit(min(limit, 200))

    results = db.execute(query).all()
    return [
        RecoveryActionListItem(
            id=action.id, case_id=action.case_id,
            customer=case.customer_name or case.customer_id,
            amount_paise=case.amount_paise,
            action_type=action.action_type, channel=action.channel,
            status=action.status, recipient=action.recipient,
            sent_at=action.sent_at.isoformat() if action.sent_at else None,
            revenue_recovered_paise=action.revenue_recovered_paise,
        )
        for action, case in results
    ]


@app.get("/api/v1/recovery-actions/stats", response_model=RecoveryActionsStatsResponse, tags=["recovery-actions"])
def recovery_actions_stats(batch_id: str | None = None, db: Session = Depends(get_db)) -> RecoveryActionsStatsResponse:
    """Aggregated recovery action statistics for dashboard cards."""
    query = select(RecoveryAction)
    if batch_id:
        query = query.join(RecoveryCase, RecoveryAction.case_id == RecoveryCase.id).where(RecoveryCase.batch_id == batch_id)
    actions = list(db.scalars(query))

    total_sent = sum(1 for a in actions if a.status not in ("cancelled",))
    successful = sum(1 for a in actions if a.status == "completed")
    pending = sum(1 for a in actions if a.status in ("pending", "sent", "delivered", "clicked", "accepted", "payment_pending"))
    failed = sum(1 for a in actions if a.status == "failed")
    revenue_recovered = sum(a.revenue_recovered_paise for a in actions)
    revenue_at_risk = sum(a.amount_paise for a in actions)

    # Recovered by action type
    by_action: dict[str, dict] = {}
    for a in actions:
        if a.action_type not in by_action:
            by_action[a.action_type] = {"sent": 0, "successful": 0, "revenue_recovered_paise": 0}
        by_action[a.action_type]["sent"] += 1
        if a.status == "completed":
            by_action[a.action_type]["successful"] += 1
        by_action[a.action_type]["revenue_recovered_paise"] += a.revenue_recovered_paise

    return RecoveryActionsStatsResponse(
        total_sent=total_sent, successful=successful, pending=pending,
        failed=failed, revenue_recovered_paise=revenue_recovered,
        revenue_at_risk_paise=revenue_at_risk, by_action=by_action,
    )


@app.post("/api/v1/recovery-actions/{action_id}/events", tags=["recovery-actions"])
def post_action_event(
    action_id: str,
    payload: ActionEventRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Record a customer interaction event against a recovery action."""
    action = db.get(RecoveryAction, action_id)
    if not action:
        raise HTTPException(404, "Recovery action not found")
    try:
        updated = process_action_event(db, action, payload.event_type, payload.metadata)
        return {
            "action_id": str(updated.id),
            "status": updated.status,
            "event_type": payload.event_type,
            "message": "Event processed successfully",
        }
    except InvalidEventError as e:
        raise HTTPException(422, str(e))
    except DuplicateEventError as e:
        raise HTTPException(409, str(e))


@app.get("/api/v1/batch/{batch_id}/cases/v2", response_model=list[CaseListItemV2], tags=["batch"])
def batch_cases_v2(batch_id: str, status: str | None = None, sort: str = "amount_desc", db: Session = Depends(get_db)) -> list[CaseListItemV2]:
    """Enhanced case list with recovery score, execution status, and outcome status."""
    query = select(RecoveryCase).where(RecoveryCase.batch_id == batch_id)
    if status:
        query = query.where(RecoveryCase.status == status)
    query = query.order_by(RecoveryCase.amount_paise.desc() if sort == "amount_desc" else RecoveryCase.created_at.desc())
    return [
        CaseListItemV2(
            case_id=item.id,
            customer=item.customer_name or item.customer_id,
            amount_paise=item.amount_paise,
            diagnosis=item.diagnosis,
            recovery_score=float(item.recovery_score) if item.recovery_score is not None else None,
            action=item.recommended_action,
            execution_status=item.execution_status,
            status=item.status,
            outcome_status=item.outcome_status,
            recovered_amount_paise=item.recovered_amount_paise,
        )
        for item in db.scalars(query)
    ]
