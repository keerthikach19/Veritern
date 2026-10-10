from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid", env_file_encoding="utf-8")
    app_env: Literal["local", "protected"] = "local"
    app_mode: Literal["live", "demo"] = "live"
    groq_api_key: SecretStr = SecretStr("")
    groq_model: Literal["openai/gpt-oss-20b"] = "openai/gpt-oss-20b"
    groq_timeout_seconds: float = Field(35, gt=0, le=60)
    groq_max_attempts: int = Field(3, ge=1, le=3)
    groq_max_calls_per_case: int = Field(3, ge=1, le=12)
    groq_max_completion_tokens: int = Field(3000, ge=128, le=8000)
    case_input_token_budget: int = Field(36000, ge=1000)
    case_output_token_budget: int = Field(12000, ge=128)
    search_backend: Literal["serper", "brave", "searxng", "manual"] = "serper"
    serper_api_key: SecretStr = SecretStr("")
    brave_api_key: SecretStr = SecretStr("")
    searxng_base_url: str = "http://127.0.0.1:8080"
    searxng_auth_token: SecretStr = SecretStr("")
    search_query_limit: int = Field(6, ge=1, le=8)
    search_results_per_query: int = Field(4, ge=1, le=10)
    fetch_page_limit: int = Field(10, ge=1, le=16)
    fetch_max_per_domain: int = Field(4, ge=1, le=8)
    fetch_max_concurrent: int = Field(3, ge=1, le=5)
    fetch_timeout_seconds: float = Field(12, gt=0, le=30)
    fetch_max_bytes: int = Field(2000000, ge=10000, le=5000000)
    max_redirects: int = Field(3, ge=0, le=5)
    case_deadline_seconds: float = Field(120, ge=10, le=300)
    upload_max_files: int = Field(5, ge=1, le=5)
    upload_max_bytes: int = Field(10000000, ge=1000, le=10000000)
    pdf_max_pages: int = Field(15, ge=1, le=30)
    ocr_max_pages_per_case: int = Field(6, ge=1, le=10)
    image_max_pixels: int = Field(20000000, ge=1000, le=20000000)
    storage_dir: Path = Path("private_data")
    raw_upload_retention_hours: int = Field(24, ge=1, le=168)
    public_cache_ttl_hours: int = Field(24, ge=1, le=168)
    save_case_history: bool = False
    enable_private_uploads: bool = True
    ephemeral_storage: bool = False
    display_timezone: str = "Asia/Kolkata"

    @model_validator(mode="after")
    def validate_storage(self):
        path = self.storage_dir.resolve()
        if path == Path(path.anchor) or path == Path.home() or path == Path.cwd():
            raise ValueError("STORAGE_DIR must be a dedicated private subdirectory")
        if self.app_env == "protected" and self.enable_private_uploads:
            raise ValueError("Protected demo requires ENABLE_PRIVATE_UPLOADS=false")
        return self

    @property
    def search_ready(self) -> bool:
        return {
            "serper": bool(self.serper_api_key.get_secret_value()),
            "brave": bool(self.brave_api_key.get_secret_value()),
            "searxng": bool(self.searxng_base_url),
            "manual": False,
        }[self.search_backend]
