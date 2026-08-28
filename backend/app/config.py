from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Razorpay AI Revenue Recovery API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://recovery:recovery@localhost:5433/recovery"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    anthropic_api_key: str | None = None
    claude_model: str | None = None
    allowed_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @model_validator(mode="after")
    def require_test_mode_razorpay_key(self) -> "Settings":
        if self.razorpay_key_id and not self.razorpay_key_id.startswith("rzp_test_"):
            raise ValueError("Only Razorpay test-mode credentials are permitted.")
        return self

    @property
    def razorpay_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
