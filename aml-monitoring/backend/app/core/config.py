"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://aml:amlsecret@localhost:5432/amldb"

    # App
    secret_key: str = "changeme-in-production"
    debug: bool = False
    seed: int = 42

    # Artifacts
    artifacts_dir: str = "/app/artifacts"

    # ML — demo uses 60 epochs for reliable convergence on imbalanced data
    gnn_hidden_channels: int = 64
    gnn_num_layers: int = 2
    gnn_epochs_demo: int = 60
    gnn_epochs_full: int = 120
    gnn_lr: float = 0.01


@lru_cache
def get_settings() -> Settings:
    return Settings()
