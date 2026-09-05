import asyncio
import traceback

from app.config import get_settings
from app.db import SessionLocal
from app.razorpay_client import create_client
from app.models import RecoveryBatch, RecoveryCase
from app.services.processor import process_payment
from app.services.outcome_tracker import track_outcome


async def main():
    client = create_client(get_settings())
    db = SessionLocal()

    try:
        batch = RecoveryBatch(
            name="debug-batch",
            status="processing"
        )

        db.add(batch)
        db.commit()
        db.refresh(batch)

        payments = client.payment.all({"count": 20}).get("items", [])

        eligible = [
            p for p in payments
            if p.get("status") == "failed"
            and int(p.get("amount", 0)) > 10_000
        ]

        print("ELIGIBLE PAYMENTS:", len(eligible))

        for payment in eligible:
            payment_id = payment["id"]

            print("\n" + "=" * 60)
            print("PROCESSING:", payment_id)

            try:
                response = await process_payment(
                    db,
                    client,
                    payment_id,
                    batch
                )

                print("PROCESS SUCCESS:", response.case_id)

                case = db.get(
                    RecoveryCase,
                    response.case_id
                )

                if case:
                    try:
                        await track_outcome(
                            db,
                            client,
                            case,
                            timeout_seconds=0
                        )
                        print("OUTCOME TRACKING: SUCCESS")

                    except Exception as e:
                        print("OUTCOME TRACKING FAILED")
                        print("TYPE:", type(e).__name__)
                        print("ERROR:", e)
                        traceback.print_exc()

            except Exception as e:
                print("PROCESSING FAILED")
                print("TYPE:", type(e).__name__)
                print("ERROR:", e)
                traceback.print_exc()

    finally:
        db.close()


asyncio.run(main())
