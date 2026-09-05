import uuid
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.orm import Session

from app.models import RecoveryBatch, RecoveryCase, RecoveryAction
from app.services.demo_batch import _fixture_client
from app.services.processor import process_payment, _audit
from app.services.action_events import process_action_event
from app.services.batch_processor import calculate_metrics

def create_simulator_batch(db: Session) -> RecoveryBatch:
    """Create an explicit simulator batch."""
    batch = RecoveryBatch(name=f"simulator-{uuid.uuid4().hex[:12]}", status="processing")
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


async def advance_simulator_batch(db: Session, batch_id: str) -> dict[str, Any]:
    """Runs the detection->action process for 5 deterministic demo cases into the batch."""
    batch = db.get(RecoveryBatch, batch_id)
    if not batch:
        raise ValueError("Batch not found")

    client = _fixture_client()
    cases = []

    # We use notes.demo_scenario=true to pass policy guardrails safely
    for payment_id in client.demo_payment_ids:
        class SimulatorClientWrapper:
            def __init__(self, c):
                self.c = c
                self.payment = self.PaymentWrapper(c.payment)
                self.payment_link = c.payment_link

            class PaymentWrapper:
                def __init__(self, p):
                    self.p = p
                def fetch(self, pid):
                    data = self.p.fetch(pid)
                    data.setdefault("notes", {})["demo_scenario"] = data.get("error_code", "true")
                    return data
                def all(self, query):
                    return self.p.all(query)

        wrapped_client = SimulatorClientWrapper(client)

        response, was_duplicate = await process_payment(db, wrapped_client, payment_id, batch)
        if not was_duplicate:
            case = db.get(RecoveryCase, response.case_id)
            if case:
                cases.append(case)

    # Update batch-level aggregates now that all cases are committed.
    # Keep status="processing" — the simulator has further stages (simulate-responses,
    # simulate-recoveries) that must still be able to advance this batch.
    calculate_metrics(batch, cases)
    db.commit()

    return {"status": "advanced", "cases_processed": len(cases)}


def simulate_customer_responses(db: Session, batch_id: str) -> dict[str, Any]:
    """Simulates customer clicks/responses on the recovery actions."""
    batch = db.get(RecoveryBatch, batch_id)
    if not batch:
        raise ValueError("Batch not found")

    cases = db.query(RecoveryCase).filter(RecoveryCase.batch_id == batch_id).all()
    actions_updated = 0

    for case in cases:
        actions = db.query(RecoveryAction).filter(RecoveryAction.case_id == case.id).all()
        for action in actions:
            if action.status == "sent":
                # We simulate clicks for the success and pending cases
                if case.diagnosis == "card_expired" and case.amount_paise > 400000:
                    process_action_event(db, action, "LINK_CLICKED", {"environment": "test", "source": "simulation"})
                elif case.diagnosis == "insufficient_funds":
                    process_action_event(db, action, "PLAN_VIEWED", {"environment": "test", "source": "simulation"})
                    process_action_event(db, action, "PLAN_ACCEPTED", {"environment": "test", "source": "simulation"})

                actions_updated += 1

    return {"status": "responses_simulated", "actions_updated": actions_updated}


def simulate_recoveries(db: Session, batch_id: str) -> dict[str, Any]:
    """Simulates final revenue captures for the eligible actions."""
    batch = db.get(RecoveryBatch, batch_id)
    if not batch:
        raise ValueError("Batch not found")

    cases = db.query(RecoveryCase).filter(RecoveryCase.batch_id == batch_id).all()
    recoveries = 0

    for case in cases:
        actions = db.query(RecoveryAction).filter(RecoveryAction.case_id == case.id).all()
        for action in actions:
            if action.status in ["clicked", "accepted"]:
                # Mark explicitly as simulated capture
                simulated_ref = f"demo_capture_{uuid.uuid4().hex[:8]}"

                # We do this directly to avoid calling Razorpay SDK
                action.status = "completed"
                action.completed_at = datetime.now(UTC)
                action.revenue_recovered_paise = action.amount_paise

                case.status = "success"
                case.outcome_status = "success"
                case.recovered_amount_paise = action.amount_paise

                db.add(action)
                db.add(case)

                _audit(db, case.id, "PAYMENT_CAPTURED", "Simulated payment capture successful.", {
                    "environment": "test",
                    "source": "simulation",
                    "simulated_reference": simulated_ref,
                    "amount_paise": action.amount_paise
                })

                _audit(db, case.id, "REVENUE_RECOVERED", f"Simulated recovery complete for {action.amount_paise} paise.", {
                    "environment": "test",
                    "source": "simulation",
                    "revenue_recovered_paise": action.amount_paise
                })

                recoveries += 1

    # Refresh cases from DB so calculate_metrics sees the updated outcome_status values
    # that were just written above before the flush.
    db.flush()
    fresh_cases = db.query(RecoveryCase).filter(RecoveryCase.batch_id == batch_id).all()
    calculate_metrics(batch, fresh_cases)
    batch.status = "complete"
    db.commit()

    return {"status": "recoveries_simulated", "recoveries": recoveries}
