from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    mock_blockchain: bool = True
    node1_url: str = "http://localhost:8545"
    node2_url: str = "http://localhost:8546"
    node3_url: str = "http://localhost:8547"
    database_url: str = "sqlite:///./netshield.db"
    secret_key: str = "netshield-dev-secret-key-change-in-production"
    log_level: str = "INFO"
    rate_limit_per_minute: int = 100
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    captive_admin_password: str = "060618Xx"
    captive_admin_username: str = "waybi"
    debug: bool = True
    ledger_file: str = "./ledger_data.json"
    data_dir: str = "./data_records"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
