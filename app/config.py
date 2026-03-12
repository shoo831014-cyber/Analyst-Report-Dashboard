from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Analyst Report Dashboard", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    database_url: str = Field(default="sqlite:///./data/app.db", alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_playwright_fallback: bool = Field(default=True, alias="ENABLE_PLAYWRIGHT_FALLBACK")
    snapshot_dir: str = Field(default="./data/snapshots", alias="SNAPSHOT_DIR")
    log_dir: str = Field(default="./data/logs", alias="LOG_DIR")
    sector_mapping_xlsx: str = Field(
        default="d:/backup01/Desktop/종목 구분_대분류10.xlsx",
        alias="SECTOR_MAPPING_XLSX",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )

    @property
    def snapshot_path(self) -> Path:
        return Path(self.snapshot_dir)

    @property
    def log_path(self) -> Path:
        return Path(self.log_dir)

    @property
    def sector_mapping_xlsx_path(self) -> Path:
        return Path(self.sector_mapping_xlsx)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
