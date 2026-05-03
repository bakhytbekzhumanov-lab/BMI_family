from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: str = ""
    owner_telegram_id: int
    wife_telegram_id: int

    # Database
    database_url: str
    database_url_sync: str

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Google Calendar
    google_credentials_json: str = "./credentials/google_credentials.json"
    google_token_json: str = "./credentials/google_token.json"
    owner_calendar_id: str = "primary"
    wife_calendar_id: str = ""
    family_calendar_id: str = ""

    # Apple Health
    health_webhook_secret: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    timezone: str = "Asia/Almaty"
    debug: bool = False

    @property
    def family_member_ids(self) -> list[int]:
        return [self.owner_telegram_id, self.wife_telegram_id]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
