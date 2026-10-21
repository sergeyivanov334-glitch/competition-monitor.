"""Настройки приложения."""

import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT = project_root()
load_dotenv(ROOT / ".env")


class Settings(BaseSettings):
    llm_provider: str = "openai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"

    proxy_api: str = ""
    proxy_base_url: str = "https://api.proxyapi.ru/openai/v1"
    proxy_model: str = "gpt-4o-mini"
    proxy_vision_model: str = "gpt-4o-mini"

    api_host: str = "127.0.0.1"
    api_port: int = 8090

    history_file: str = "history.json"
    max_history_items: int = 10

    niche: str = "Моушн-дизайн и интерфейсная анимация для SaaS"
    competitor_urls: str = (
        "https://rive.app,"
        "https://lottiefiles.com,"
        "https://jitter.video,"
        "https://www.schoolofmotion.com"
    )
    monitor_file: str = "monitor_state.json"
    monitor_interval_hours: int = 24

    parser_timeout: int = 45
    parser_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    max_image_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        extra="ignore",
    )

    @property
    def history_path(self) -> Path:
        path = Path(self.history_file)
        if not path.is_absolute():
            path = ROOT / path
        return path

    @property
    def frontend_dir(self) -> Path:
        return ROOT / "frontend"

    @property
    def data_dir(self) -> Path:
        return ROOT / "data"

    @property
    def monitor_path(self) -> Path:
        path = Path(self.monitor_file)
        if not path.is_absolute():
            path = ROOT / path
        return path

    @property
    def competitor_url_list(self) -> list[str]:
        return [item.strip() for item in self.competitor_urls.split(",") if item.strip()]


settings = Settings()
