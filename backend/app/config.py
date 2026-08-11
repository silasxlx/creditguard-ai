from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.example"),
        env_prefix="CREDIT_REVIEW_",
        extra="ignore",
    )

    environment: str = "local"
    business_db: str = "data/business.db"
    checkpoint_db: str = "data/checkpoints.db"
    storage_root: str = "data/storage"
    allow_memory_checkpoint: bool = False
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    mineru_base_url: str | None = None
    mineru_api_key: str | None = None
    policy_root: str = "config/policies/synthetic-v1"
    rule_pack_path: str = "config/rules/rule-pack-v1.yaml"
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_api_key: str | None = None
    use_remote_models: bool = False

    @property
    def business_db_path(self) -> Path:
        return Path(self.business_db)

    @property
    def checkpoint_db_path(self) -> Path:
        return Path(self.checkpoint_db)

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_root)

    def ensure_runtime_dirs(self) -> None:
        self.business_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
