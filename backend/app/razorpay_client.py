import razorpay

from app.config import Settings


def create_client(settings: Settings) -> razorpay.Client | None:
    """Return a Razorpay test-mode client only when credentials are configured."""
    if not settings.razorpay_configured:
        return None
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
