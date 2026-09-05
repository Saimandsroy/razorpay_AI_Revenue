import asyncio
import uuid

from app.models import AuditEvent, RecoveryCase
from app.services import demo_batch, processor


class FakeDb:
    def __init__(self) -> None:
        self.items: list[object] = []

    def scalar(self, _: object) -> None:
        return None

    def scalars(self, _: object) -> list:
        return []

    def add(self, item: object) -> None:
        if isinstance(item, RecoveryCase) and item.recovered_amount_paise is None:
            item.recovered_amount_paise = 0
        self.items.append(item)

    def flush(self) -> None:
        for item in self.items:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()

    def commit(self) -> None:
        self.flush()

    def refresh(self, _: object) -> None:
        pass

    def get(self, model: type, identifier: object) -> object | None:
        return next((item for item in self.items if isinstance(item, model) and getattr(item, "id", None) == identifier), None)


def test_demo_batch_uses_production_pipeline_and_persists_audits(monkeypatch) -> None:
    async def unavailable(*_: object) -> None:
        return None

    monkeypatch.setattr(processor, "get_gemini_recommendation", unavailable)
    monkeypatch.setattr(processor, "get_gemini_failure_reason", lambda: "Gemini not configured")
    db = FakeDb()
    batch = asyncio.run(demo_batch.process_demo_batch(db))
    cases = [item for item in db.items if isinstance(item, RecoveryCase)]
    events = [item for item in db.items if isinstance(item, AuditEvent)]

    assert batch.name.startswith("demo-")
    assert batch.cases_analyzed == 5
    assert {case.outcome_status for case in cases} == {"success", "failed", "pending"}
    assert batch.successful_recoveries == 1
    assert batch.failed_recoveries == 1
    assert batch.pending_recoveries == 1
    assert len(events) >= 5 * 10
    assert all(any(event.event_type == "GEMINI_REASONING_RECEIVED" and event.case_id == case.id for event in events) for case in cases)
