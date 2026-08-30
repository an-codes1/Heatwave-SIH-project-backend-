from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bhubaneswar Heat Health Early Warning API"
    debug: bool = True

    database_url: str

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    notification_dry_run: bool = True

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_sms_from: str | None = None
    twilio_whatsapp_from: str | None = None
    alert_recipient_phone: str | None = None

    admin_api_key: str | None = None

    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: float = 30.0
    db_pool_recycle: int = 1800

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]
        return value


settings = Settings()