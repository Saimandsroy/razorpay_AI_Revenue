from fastapi import FastAPI
from pydantic import BaseModel

from app.config import get_settings
from app.razorpay_client import create_client

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    environment: str
    razorpay_test_client_configured: bool


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    # Client construction validates our local SDK wiring without making an external call.
    client = create_client(settings)
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        razorpay_test_client_configured=client is not None,
    )
