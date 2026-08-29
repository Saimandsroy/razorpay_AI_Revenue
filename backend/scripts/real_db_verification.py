"""Verify that the production recovery pipeline persists to the Compose PostgreSQL database.

This script uses a Razorpay-shaped in-memory client.  It never contacts Razorpay
or creates a real payment link.  It removes only the batch, case, and audit
events created for this verification before exiting.
"""
import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal
from app.models import AuditEvent, RecoveryBatch, RecoveryCase
from app.services.processor import process_payment


class FakePaymentApi:
    def __init__(self, payment: dict, history: list[dict]) -> None:
        self.payment = payment
        self.history = history

    def fetch(self, payment_id: str) -> dict:
        if payment_id != self.payment["id"]:
            raise KeyError(f"Unknown synthetic payment: {payment_id}")
        return dict(self.payment)

    def all(self, query: dict) -> dict:
        if query.get("customer_id") != self.payment["customer_id"]:
            return {"items": []}
        return {"items": list(self.history)}


class FakePaymentLinkApi:
    def create(self, payload: dict) -> dict:
        return {
            "id": "plink_real_db_verification",
            "short_url": "https://example.invalid/real-db-verification",
            "reference_id": payload.get("reference_id"),
        }


def _client(payment: dict, history: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(
        payment=FakePaymentApi(payment, history),
        payment_link=FakePaymentLinkApi(),
    )


def _cleanup(payment_id: str) -> None:
    """Remove exactly the case graph identified by this run's unique payment ID."""
    with SessionLocal() as db:
        cases = list(db.scalars(select(RecoveryCase).where(RecoveryCase.razorpay_payment_id == payment_id)))
        case_ids = [case.id for case in cases]
        batch_ids = list({case.batch_id for case in cases})
        if case_ids:
            db.execute(delete(AuditEvent).where(AuditEvent.case_id.in_(case_ids)))
            db.execute(delete(RecoveryCase).where(RecoveryCase.id.in_(case_ids)))
        if batch_ids:
            db.execute(delete(RecoveryBatch).where(RecoveryBatch.id.in_(batch_ids)))
        db.commit()


def _final_counts() -> tuple[int, int, int]:
    with SessionLocal() as db:
        return (
            len(list(db.scalars(select(RecoveryBatch.id)))),
            len(list(db.scalars(select(RecoveryCase.id)))),
            len(list(db.scalars(select(AuditEvent.id)))),
        )


def _report_check(label: str, passed: bool) -> bool:
    print(f"{'PASS' if passed else 'FAIL'} {label}")
    return passed


async def main() -> int:
    token = uuid.uuid4().hex
    payment_id = f"pay_real_db_verify_{token}"
    customer_id = f"cust_real_db_verify_{token}"
    now = int(datetime.now(UTC).timestamp())
    payment = {
        "id": payment_id,
        "status": "failed",
        "amount": 499_900,
        "currency": "INR",
        "customer_id": customer_id,
        "error_code": "BAD_REQUEST_CARD_EXPIRED",
        "notes": {"customer_name": "Real DB Verification Customer"},
        "bank": "VERIFY_BANK",
        "created_at": now,
    }
    history = [
        payment,
        {
            "id": f"pay_history_{token}",
            "status": "captured",
            "amount": 1_800_000,
            "currency": "INR",
            "customer_id": customer_id,
            "created_at": now,
        },
    ]
    client = _client(payment, history)
    created_case_id = None
    failed = False

    print("REAL_DB_VERIFICATION")
    print("Database: PostgreSQL")
    try:
        process_db = SessionLocal()
        try:
            result = await process_payment(process_db, client, payment_id)
            created_case_id = result.case_id
        except Exception:
            process_db.rollback()
            raise
        finally:
            process_db.close()

        # A new SessionLocal proves that committed data, rather than in-session
        # state, is being verified.
        with SessionLocal() as db:
            matching_cases = list(db.scalars(select(RecoveryCase).where(RecoveryCase.id == created_case_id)))
            case = matching_cases[0] if len(matching_cases) == 1 else None
            audit_events = list(
                db.scalars(
                    select(AuditEvent)
                    .where(AuditEvent.case_id == created_case_id)
                    .order_by(AuditEvent.created_at, AuditEvent.id)
                )
            )

        print("Persistence:", "PASS" if case is not None else "FAIL")
        print("Case:")
        checks = [
            ("exactly one recovery_cases row created", len(matching_cases) == 1),
            ("payment_id", case is not None and case.razorpay_payment_id == payment_id),
            ("amount", case is not None and case.amount_paise == payment["amount"]),
            ("diagnosis", case is not None and bool(case.diagnosis)),
            ("recovery_score", case is not None and case.recovery_score is not None),
            ("recommended_action", case is not None and bool(case.recommended_action)),
            ("policy_allowed", case is not None and case.policy_allowed is not None),
            ("execution_status", case is not None and bool(case.execution_status)),
            ("execution_result", case is not None and case.execution_result is not None),
            ("outcome_status", case is not None and bool(case.outcome_status)),
        ]
        passed = all(_report_check(label, condition) for label, condition in checks)

        event_types = [event.event_type for event in audit_events]
        print("Audit event types:", ", ".join(event_types) or "(none)")
        print("Audit:")
        audit_checks = [
            ("DETECTED", "DETECTED" in event_types),
            ("DIAGNOSED", "DIAGNOSED" in event_types),
            ("SCORED", "SCORED" in event_types),
            ("CLAUDE_REASONING_RECEIVED", "CLAUDE_REASONING_RECEIVED" in event_types),
            ("POLICY_GATE", "POLICY_GATE" in event_types),
            ("ACTION_EXECUTED/ACTION_STOPPED", bool({"ACTION_EXECUTED", "ACTION_STOPPED"} & set(event_types))),
        ]
        passed = all(_report_check(label, condition) for label, condition in audit_checks) and passed
        print("FINAL:", "PASS" if passed else "FAIL")
        failed = not passed
    except Exception as error:
        failed = True
        print(f"EXCEPTION: {type(error).__name__}: {error}")
    finally:
        try:
            _cleanup(payment_id)
        except Exception as cleanup_error:
            failed = True
            print(f"CLEANUP_EXCEPTION: {type(cleanup_error).__name__}: {cleanup_error}")
        batches, cases, audit_events = _final_counts()
        print("FINAL DATABASE COUNTS")
        print(f"batches={batches}")
        print(f"cases={cases}")
        print(f"audit_events={audit_events}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
