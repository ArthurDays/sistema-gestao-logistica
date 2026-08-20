from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema de Logística API"
    database_url: str = "postgresql+psycopg://logistica:logistica@postgres:5432/logistica"
    cors_origins: str = "http://localhost:3000"
    base_fuel_price_per_liter: Decimal = Decimal("6.00")
    vehicle_catalog_csv_url: str = (
        "https://docs.google.com/spreadsheets/d/"
        "1J8YAtNSqD0se5pJVzgBDnggN7lKF37HPnQlbqL9vSOw/"
        "gviz/tq?tqx=out:csv&gid=521676479"
    )
    catalog_sync_interval_seconds: int = 3600
    jwt_secret_key: str
    access_token_expire_minutes: int = 60
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    n8n_webhook_url: str | None = None
    n8n_webhook_secret: str | None = None
    outbox_max_attempts: int = 5
    outbox_poll_interval_seconds: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
