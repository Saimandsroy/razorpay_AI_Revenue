import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RecoveryBatch, RecoveryCase
from app.services.outcome_tracker import track_outcome
from app.services.processor import process_payment

logger = logging.getLogger("batch_processor")


def calculate_metrics(batch: RecoveryBatch, cases: list[RecoveryCase]) -> None:
    by_diagnosis: dict[str, dict[str, int | float]] = defaultdict(lambda: {"attempts": 0, "success": 0, "recovered_paise": 0})
    by_action: dict[str, dict[str, int | float]] = defaultdict(lambda: {"attempts": 0, "success": 0})
    for case in cases:
        diagnosis, action = by_diagnosis[case.diagnosis], by_action[case.recommended_action or "stop"]
        diagnosis["attempts"] += 1; action["attempts"] += 1
        if case.outcome_status == "success":
            diagnosis["success"] += 1; diagnosis["recovered_paise"] += case.recovered_amount_paise; action["success"] += 1
    for group in (by_diagnosis, by_action):
        for value in group.values(): value["rate"] = round(value["success"] / value["attempts"], 3) if value["attempts"] else 0
    batch.cases_analyzed = len(cases)
    batch.revenue_at_risk_paise = sum(case.revenue_at_risk_paise for case in cases)
    batch.actions_executed = sum(case.execution_status in {"executed", "scheduled", "proposed"} for case in cases)
    batch.stopped_by_policy = sum(not bool(case.policy_allowed) for case in cases)
    batch.successful_recoveries = sum(case.outcome_status == "success" for case in cases)
    batch.failed_recoveries = sum(case.outcome_status == "failed" for case in cases)
    batch.pending_recoveries = sum(case.outcome_status == "pending" and case.execution_status in {"executed", "scheduled", "proposed"} for case in cases)
    batch.total_revenue_recovered_paise = sum(case.recovered_amount_paise for case in cases)
    batch.metrics_by_diagnosis, batch.metrics_by_action = dict(by_diagnosis), dict(by_action)


async def process_batch(db: Session, client: Any, batch: RecoveryBatch, batch_size: int = 50) -> None:
    batch.status = "processing"
    db.commit()

    payments = client.payment.all({"count": batch_size}).get("items", [])

    payments_scanned = len(payments)
    eligible_count = 0
    already_processed_count = 0
    skipped_count = 0
    processing_error_count = 0

    for payment in payments:
        payment_id = payment.get("id", "unknown")

        # --- Filter: only process eligible failed payments above minimum amount ---
        if payment.get("status") != "failed" or int(payment.get("amount", 0)) <= 10_000:
            skipped_count += 1
            logger.debug(
                "Skipped payment %s: status=%s amount=%s",
                payment_id, payment.get("status"), payment.get("amount"),
            )
            continue

        eligible_count += 1

        try:
            response, was_duplicate = await process_payment(db, client, payment_id, batch)

            if was_duplicate:
                # Idempotent: this payment was already in the DB — count it but
                # do NOT create a second RecoveryCase.
                already_processed_count += 1
                logger.info("Payment %s already processed — skipping.", payment_id)
                continue

            case = db.get(RecoveryCase, response.case_id)
            if case:
                await track_outcome(db, client, case, timeout_seconds=0)

        except HTTPException as exc:
            # HTTP exceptions from Razorpay fetch (e.g. 422 non-failed payment) are
            # expected in some scenarios — log and continue.
            processing_error_count += 1
            logger.warning(
                "Payment %s rejected by pipeline (HTTP %s): %s",
                payment_id, exc.status_code, exc.detail,
            )

        except Exception:
            # Truly unexpected errors — log full traceback so they are visible,
            # then continue so the batch does not abort entirely.
            processing_error_count += 1
            logger.exception("Unexpected error processing payment %s", payment_id)

    cases = list(db.scalars(select(RecoveryCase).where(RecoveryCase.batch_id == batch.id)))
    calculate_metrics(batch, cases)
    batch.status = "complete"

    # Store processing statistics in the batch metrics for dashboard visibility.
    batch.metrics_by_diagnosis = {
        **batch.metrics_by_diagnosis,
        "_batch_stats": {
            "payments_scanned": payments_scanned,
            "eligible": eligible_count,
            "already_processed": already_processed_count,
            "skipped_ineligible": skipped_count,
            "processing_errors": processing_error_count,
            "new_cases_created": len(cases),
        },
    }

    db.commit()
    logger.info(
        "Batch %s complete: scanned=%s eligible=%s new=%s duplicates=%s skipped=%s errors=%s",
        batch.id, payments_scanned, eligible_count, len(cases),
        already_processed_count, skipped_count, processing_error_count,
    )
