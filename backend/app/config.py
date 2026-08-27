from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Razorpay AI Revenue Recovery API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://recovery:recovery@localhost:5432/recovery"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def razorpay_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
