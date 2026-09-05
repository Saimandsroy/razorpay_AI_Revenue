import asyncio
import traceback

from app.razorpay_client import create_client
from app.config import get_settings
from app.db import SessionLocal
from app.services.processor import process_payment


PAYMENT_ID = "pay_TXGCYDgk7IVaZ6"



async def main():
    client = create_client(get_settings())
    db = SessionLocal()

    try:
        print("Testing:", PAYMENT_ID)

        result = await process_payment(
            db,
            client,
            PAYMENT_ID,
        )

        print("\nSUCCESS")
        print(result)

    except Exception as e:
        print("\nFAILED")
        print("ERROR TYPE:", type(e).__name__)
        print("ERROR:", e)
        traceback.print_exc()

    finally:
        db.close()


asyncio.run(main())
