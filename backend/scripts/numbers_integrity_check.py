"""Deterministic reconciliation for a 10-case completed batch fixture."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.batch_processor import calculate_metrics


def case(diagnosis: str, action: str, amount: int, outcome: str, allowed: bool) -> SimpleNamespace:
    return SimpleNamespace(diagnosis=diagnosis, recommended_action=action, revenue_at_risk_paise=amount, outcome_status=outcome, recovered_amount_paise=amount if outcome == "success" else 0, execution_status="executed" if allowed else "stopped", policy_allowed=allowed)


cases = [
    case("card_expired", "send_card_update_link", 499_900, "success", True), case("card_expired", "send_downgrade_offer", 499_900, "pending", True),
    case("insufficient_funds", "send_payment_plan", 499_900, "pending", True), case("mandate_rejected", "send_downgrade_offer", 499_900, "pending", True),
    case("card_expired", "send_downgrade_offer", 499_900, "pending", False), case("insufficient_funds", "retry", 200_000, "success", True),
    case("authentication_failed", "send_card_update_link", 300_000, "failed", True), case("mandate_rejected", "stop", 400_000, "pending", False),
    case("insufficient_funds", "send_payment_plan", 250_000, "pending", True), case("card_expired", "send_card_update_link", 600_000, "success", True),
]
batch = SimpleNamespace(); calculate_metrics(batch, cases)
actions = batch.actions_executed; outcomes = batch.successful_recoveries + batch.failed_recoveries + batch.pending_recoveries
diagnosis_recovered = sum(item["recovered_paise"] for item in batch.metrics_by_diagnosis.values())
action_success = sum(item["success"] for item in batch.metrics_by_action.values())
rate = batch.total_revenue_recovered_paise / batch.revenue_at_risk_paise
checks = {
    "cases_analyzed": batch.cases_analyzed == len(cases), "risk_sum": batch.revenue_at_risk_paise == sum(item.revenue_at_risk_paise for item in cases),
    "action_or_stopped": actions + batch.stopped_by_policy == len(cases), "outcome_partition": outcomes == actions,
    "recovered_sum": batch.total_revenue_recovered_paise == sum(item.recovered_amount_paise for item in cases if item.outcome_status == "success"),
    "recovery_rate": rate == batch.total_revenue_recovered_paise / batch.revenue_at_risk_paise, "diagnosis_recovered": diagnosis_recovered == batch.total_revenue_recovered_paise,
    "action_success": action_success == batch.successful_recoveries,
}
print(f"cases={batch.cases_analyzed} risk={batch.revenue_at_risk_paise} executed={actions} stopped={batch.stopped_by_policy} success={batch.successful_recoveries} failed={batch.failed_recoveries} pending={batch.pending_recoveries} recovered={batch.total_revenue_recovered_paise} rate={rate:.6f}")
for name, value in checks.items(): print(f"{'PASS' if value else 'FAIL'} {name}")
if not all(checks.values()): raise SystemExit(1)
