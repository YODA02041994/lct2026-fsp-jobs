"""Настройки сервиса. Всё берётся из переменных окружения (или файла .env); без ключей работает демонстрационный режим."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FSP_", env_file=".env", extra="ignore")

    app_name: str = "Карьера ФСП"
    database_url: str = "sqlite:///./data/fsp.db"
    secret_key: str = "dev-secret-change-me"          # в проде задаётся обязательно
    access_token_hours: int = 12
    root_path: str = ""                               # "/fsp" на стенде
    public_url: str = "http://localhost:8000"         # для ссылок в письмах
    frontend_dir: str = "../frontend"

    # почта: если SMTP не задан — демонстрационный режим, ссылка подтверждения показывается на экране
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.org"

    # внешняя модель (OpenAI-совместимая точка); пусто — работаем правилами
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # тест
    test_block_size: int = 5
    test_blocks: int = 2
    test_item_seconds: int = 90
    grade_change_cooldown_days: int = 90

    # ФСП ID (OIDC). Пусто — встроенный издатель-заглушка
    fsp_oidc_issuer: str = ""
    fsp_oidc_client_id: str = ""
    fsp_oidc_client_secret: str = ""

    demo_mode: bool = True

    @property
    def email_demo(self) -> bool:
        return not self.smtp_host


@lru_cache
def get_settings() -> Settings:
    return Settings()
