from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = ""
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "qwen2.5:3b-instruct"
    embedding_model: str = "bge-m3"
    chroma_path: str = "data/chroma"
    jwt_secret: str = "dev-only-change-this-jwt-secret-key"
    jwt_expires_minutes: int = 720
    app_timezone: str = "Asia/Shanghai"
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "糖安食助"
    report_send_hour: int = 20
    report_send_minute: int = 0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
