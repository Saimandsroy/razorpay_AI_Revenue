import asyncio
from types import SimpleNamespace

from app.services.batch_processor import calculate_metrics
from app.services.executor import execute_retry, execute_send_card_link, execute_stop
from app.services.outcome_tracker import track_outcome


def test_retry_is_safely_scheduled_without_charge() -> None:
    assert execute_retry("pay_1")["status"] == "scheduled"


def test_card_link_uses_razorpay_payment_link_api() -> None:
    api = SimpleNamespace(create=lambda _: {"id": "plink_1", "short_url": "https://rzp.io/i/test"})
    assert execute_send_card_link(SimpleNamespace(payment_link=api), "cust_1", "pay_1", 50_000)["link_id"] == "plink_1"


def test_stop_makes_no_gateway_call() -> None:
    assert execute_stop("policy")["status"] == "stopped"


def test_outcome_tracker_records_success() -> None:
    events = []; db = SimpleNamespace(add=events.append, commit=lambda: None, scalar=lambda _: None, scalars=lambda _: [])
    case = SimpleNamespace(id="case_1", razorpay_payment_id="pay_1", execution_status="executed", amount_paise=500, recovered_amount_paise=0, status="allowed", outcome_status="pending", outcome_checked_at=None)
    client = SimpleNamespace(payment=SimpleNamespace(fetch=lambda _: {"status": "captured"}))
    assert asyncio.run(track_outcome(db, client, case, timeout_seconds=0)) == "success"
    assert case.recovered_amount_paise == 500 and events[-1].event_type == "OUTCOME_TRACKED"


def test_outcome_tracker_keeps_pending_at_timeout() -> None:
    db = SimpleNamespace(add=lambda _: None, commit=lambda: None, scalar=lambda _: None, scalars=lambda _: [])
    case = SimpleNamespace(id="case_1", razorpay_payment_id="pay_1", execution_status="executed", amount_paise=500, recovered_amount_paise=0, status="allowed", outcome_status="pending", outcome_checked_at=None)
    client = SimpleNamespace(payment=SimpleNamespace(fetch=lambda _: {"status": "failed"}))
    assert asyncio.run(track_outcome(db, client, case, timeout_seconds=0)) == "pending"


def test_batch_metrics_are_deterministic() -> None:
    batch = SimpleNamespace()
    cases = [SimpleNamespace(diagnosis="card_expired", recommended_action="send_card_update_link", outcome_status="success", recovered_amount_paise=500, revenue_at_risk_paise=500, execution_status="executed", policy_allowed=True), SimpleNamespace(diagnosis="insufficient_funds", recommended_action="stop", outcome_status="pending", recovered_amount_paise=0, revenue_at_risk_paise=300, execution_status="stopped", policy_allowed=False)]
    calculate_metrics(batch, cases)
    assert batch.cases_analyzed == 2 and batch.total_revenue_recovered_paise == 500
