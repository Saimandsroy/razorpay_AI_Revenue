"""Regression tests for the simulator batch metric consistency bug.

Bug: advance_simulator_batch() created 5 RecoveryCase rows but never called
calculate_metrics(), leaving batch.cases_analyzed=0 and all revenue totals at 0.
The /summary endpoint reads from the batch row directly, so it always returned zeros.

These tests prove that after POST /demo/batch/{id}/advance the batch summary is
immediately consistent with its cases, and that the full simulate-responses +
simulate-recoveries lifecycle also produces consistent final metrics.
"""
import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import RecoveryBatch, RecoveryCase
from app.services.simulator import (
    advance_simulator_batch,
    create_simulator_batch,
    simulate_customer_responses,
    simulate_recoveries,
)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Core regression: advance must produce consistent batch summary immediately
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_advance_populates_batch_summary(db):
    """After advance, cases_analyzed and revenue_at_risk must match the 5 cases.

    REGRESSION: This previously returned cases_analyzed=0, revenue_at_risk_paise=0
    because calculate_metrics() was never called inside advance_simulator_batch().
    """
    batch = create_simulator_batch(db)
    await advance_simulator_batch(db, str(batch.id))

    db.refresh(batch)

    assert batch.cases_analyzed == 5, (
        f"Expected 5 cases_analyzed after advance, got {batch.cases_analyzed}. "
        "REGRESSION: calculate_metrics was not called after cases were committed."
    )
    assert batch.revenue_at_risk_paise == 1_999_500, (
        f"Expected revenue_at_risk_paise=1_999_500, got {batch.revenue_at_risk_paise}"
    )
    assert batch.total_revenue_recovered_paise == 0  # nothing recovered yet
    assert batch.status == "processing"  # still in-flight — more stages follow


@pytest.mark.anyio
async def test_advance_diagnosis_breakdown(db):
    """by_diagnosis must accurately reflect the 5 fixture scenarios."""
    batch = create_simulator_batch(db)
    await advance_simulator_batch(db, str(batch.id))
    db.refresh(batch)

    by_diag = batch.metrics_by_diagnosis
    # 3 card_expired: Demo Link_Failure (599900), Demo High_Value (499900), Demo Churn_Risk (199900)
    assert by_diag["card_expired"]["attempts"] == 3, f"card_expired attempts wrong: {by_diag}"
    # 1 insufficient_funds: Demo Cash_Flow (299900)
    assert by_diag["insufficient_funds"]["attempts"] == 1, f"insufficient_funds wrong: {by_diag}"
    # 1 mandate_rejected: Demo Mandate_Churn (399900)
    assert by_diag["mandate_rejected"]["attempts"] == 1, f"mandate_rejected wrong: {by_diag}"


@pytest.mark.anyio
async def test_advance_action_breakdown(db):
    """by_action must accurately reflect the recommended actions for the 5 cases."""
    batch = create_simulator_batch(db)
    await advance_simulator_batch(db, str(batch.id))
    db.refresh(batch)

    by_action = batch.metrics_by_action
    assert by_action["send_card_update_link"]["attempts"] == 3, f"send_card_update_link: {by_action}"
    assert by_action["send_payment_plan"]["attempts"] == 1, f"send_payment_plan: {by_action}"
    assert by_action["send_downgrade_offer"]["attempts"] == 1, f"send_downgrade_offer: {by_action}"


@pytest.mark.anyio
async def test_summary_row_matches_case_totals(db):
    """batch.revenue_at_risk_paise must equal the sum of each case's revenue_at_risk_paise."""
    batch = create_simulator_batch(db)
    await advance_simulator_batch(db, str(batch.id))
    db.refresh(batch)

    cases = list(db.scalars(select(RecoveryCase).where(RecoveryCase.batch_id == batch.id)))
    case_revenue_total = sum(c.revenue_at_risk_paise for c in cases)

    assert batch.cases_analyzed == len(cases)
    assert batch.revenue_at_risk_paise == case_revenue_total


# ---------------------------------------------------------------------------
# Full lifecycle: advance → responses → recoveries
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_full_simulator_lifecycle_metrics(db):
    """The batch reaches a consistent complete state after the full lifecycle."""
    batch = create_simulator_batch(db)
    batch_id = str(batch.id)

    await advance_simulator_batch(db, batch_id)
    simulate_customer_responses(db, batch_id)
    result = simulate_recoveries(db, batch_id)

    db.refresh(batch)

    assert batch.status == "complete"
    assert batch.cases_analyzed == 5
    assert batch.revenue_at_risk_paise == 1_999_500
    assert batch.total_revenue_recovered_paise > 0, (
        "Expected at least one simulated recovery; total_revenue_recovered_paise is 0"
    )
    assert result["recoveries"] >= 1


@pytest.mark.anyio
async def test_simulate_recoveries_commit_order(db):
    """Verify the secondary bug is fixed: calculate_metrics commits its results.

    Old bug: db.commit() was called BEFORE calculate_metrics(), so the metric
    fields (cases_analyzed, revenue_at_risk_paise, etc.) were never persisted.
    """
    batch = create_simulator_batch(db)
    batch_id = str(batch.id)

    await advance_simulator_batch(db, batch_id)
    simulate_customer_responses(db, batch_id)
    simulate_recoveries(db, batch_id)

    # Force the session to re-read from the DB to catch commit order issues.
    db.expire(batch)
    db.refresh(batch)

    assert batch.total_revenue_recovered_paise > 0, (
        "total_revenue_recovered_paise should be > 0 after simulate-recoveries — "
        "commit order bug would cause this to remain 0."
    )
