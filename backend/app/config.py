from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _BACKEND_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 元数据 SQLite（会话 / 消息）
    metadata_db_path: Path = _DATA_DIR / "metadata.db"
    # 分析业务 SQLite（NL2SQL 只读）
    analytics_db_path: Path = _DATA_DIR / "analytics.db"

    dashscope_api_key: str | None = None
    openai_api_key: str | None = None
    dashscope_compat_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen3-max"

    jwt_secret: str = "change-me-in-production-use-long-random"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # 演示：任意账号密码均可登录（与 Phase1 一致）；False 时用 login_username/login_password
    auth_demo_mode: bool = True
    login_username: str = "demo"
    login_password: str = "demo123"

    nl2sql_top_k: int = 10
    nl2sql_max_rows: int = 500
    sql_statement_timeout_sec: float = 30.0

    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174,http://127.0.0.1:5175,http://localhost:5175"

    @property
    def metadata_db_url(self) -> str:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.metadata_db_path.as_posix()}"

    @property
    def analytics_db_url(self) -> str:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.analytics_db_path.as_posix()}"

    def llm_api_key(self) -> str:
        return self.dashscope_api_key or self.openai_api_key or ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
