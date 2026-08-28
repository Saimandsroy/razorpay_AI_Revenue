from app.services.diagnosis import diagnose
from app.services.policy import choose_deterministic_action, evaluate_policy, recommend_action
from app.services.processor import list_failed_payments
from app.services.intelligence import build_intelligence_snapshot, detect_gateway_anomalies
from app.services.scoring import CustomerContext, recovery_score


def test_card_expired_is_diagnosed_and_never_retried() -> None:
    diagnosis = diagnose("BAD_REQUEST_CARD_EXPIRED")
    context = CustomerContext(8, 2, 1_800_000, 3)

    assert diagnosis.category == "card_expired"
    assert choose_deterministic_action(diagnosis.category, context) == "send_card_update_link"
    assert evaluate_policy("retry", diagnosis.category, context).allowed is False


def test_high_value_card_expiry_has_contextual_reasoning_and_rejections() -> None:
    context = CustomerContext(8, 2, 1_800_000, 3)

    recommendation = recommend_action("card_expired", context)

    assert recommendation.action == "send_card_update_link"
    assert "high lifetime value" in recommendation.reasoning
    assert {item.action for item in recommendation.alternatives_rejected} == {"retry", "send_downgrade_offer"}


def test_weighted_recovery_score_is_bounded() -> None:
    context = CustomerContext(8, 2, 1_800_000, 3)

    assert recovery_score(0.74, context) == 0.843


def test_dispute_always_stops_recovery() -> None:
    context = CustomerContext(10, 0, 2_000_000, 1, disputed=True)

    decision = evaluate_policy("send_payment_plan", "insufficient_funds", context)
    assert decision.allowed is False
    assert "disputed" in decision.reason


def test_detection_keeps_only_eligible_failed_payments() -> None:
    class PaymentClient:
        def all(self, _: dict) -> dict:
            return {"items": [
                {"id": "pay_failed", "status": "failed", "amount": 50_000, "currency": "INR"},
                {"id": "pay_small", "status": "failed", "amount": 10_000, "currency": "INR"},
                {"id": "pay_captured", "status": "captured", "amount": 50_000, "currency": "INR"},
            ]}

    class Client:
        payment = PaymentClient()

    assert [payment.payment_id for payment in list_failed_payments(Client(), 100)] == ["pay_failed"]


def test_intelligence_prioritizes_revenue_and_flags_gateway_anomaly() -> None:
    payments = [
        {"id": f"pay_{index}", "status": "failed", "amount": 1_000_000, "currency": "INR", "gateway": "gateway_a", "error_code": "BAD_REQUEST_INSUFFICIENT_FUNDS", "customer_id": "cust_main"}
        for index in range(3)
    ] + [
        {"id": f"pay_gateway_a_ok_{index}", "status": "captured", "amount": 200_000, "currency": "INR", "gateway": "gateway_a", "customer_id": "cust_main"}
        for index in range(2)
    ] + [
        {"id": f"pay_ok_{index}", "status": "captured", "amount": 200_000, "currency": "INR", "gateway": "gateway_b", "customer_id": "cust_main"}
        for index in range(20)
    ]

    anomalies = detect_gateway_anomalies(payments)
    snapshot = build_intelligence_snapshot(payments)

    assert anomalies[0].anomalous is True
    assert snapshot.total_revenue_at_risk_paise == 3_000_000
    assert snapshot.events[0].priority == "P0"
    assert snapshot.events[0].gateway_anomaly is True
