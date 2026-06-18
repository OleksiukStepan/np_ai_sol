from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    concurrency: int = 5

    input_path: str = "samples/input_requests.csv"
    output_dir: str = "output"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    google_sheet_id: str = ""
    google_service_account_json: str = "keys/service_account.json"

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def sheets_enabled(self) -> bool:
        return bool(self.google_sheet_id)


def load_settings() -> Settings:
    return Settings()
