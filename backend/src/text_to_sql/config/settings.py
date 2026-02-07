"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure OpenAI Configuration (for chat/LLM)
    azure_openai_api_key: SecretStr = Field(..., description="Azure OpenAI API key")
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_openai_api_version: str = Field(
        default="2024-02-01", description="Azure OpenAI API version"
    )
    azure_openai_deployment_name: str = Field(
        default="gpt-4", description="Azure OpenAI deployment name for chat"
    )

    # Azure OpenAI Embedding Configuration (MSFT Foundry)
    azure_embedding_api_key: SecretStr = Field(
        ..., description="Azure OpenAI Embedding API subscription key"
    )
    azure_embedding_endpoint: str = Field(
        ..., description="Azure OpenAI Embedding endpoint URL"
    )
    azure_embedding_api_version: str = Field(
        default="2024-12-01-preview", description="Azure OpenAI Embedding API version"
    )
    azure_embedding_deployment_name: str = Field(
        default="text-embedding-ada-002", description="Azure OpenAI embedding deployment name"
    )

    # ChromaDB Configuration
    chromadb_persist_directory: str = Field(
        default="./chroma_data", description="ChromaDB persistence directory"
    )

    # PostgreSQL Configuration
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_database: str = Field(..., description="PostgreSQL database name")
    postgres_user: str = Field(..., description="PostgreSQL username")
    postgres_password: SecretStr = Field(..., description="PostgreSQL password")

    # Session Storage Configuration
    session_storage_type: Literal["memory", "sqlite", "mongodb"] = Field(
        default="mongodb", description="Session storage type"
    )
    session_storage_path: str = Field(
        default="./sessions.db", description="Path for SQLite session storage"
    )

    # MongoDB Configuration
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI",
    )
    mongodb_database: str = Field(
        default="text_to_sql_agent", description="MongoDB database name"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_debug: bool = Field(default=False, description="Enable debug mode")

    # SQL Validation Settings
    sql_max_rows: int = Field(default=1000, description="Maximum rows to return from queries")
    sql_timeout_seconds: int = Field(default=30, description="SQL query timeout in seconds")

    # Pagination Settings
    pagination_default_limit: int = Field(default=100, description="Default pagination limit")

    # CSV Download Settings
    csv_max_rows: int = Field(default=2500, description="Maximum rows for CSV download")

    # System Rules Configuration
    system_rules_path: str | None = Field(
        default=None, description="Path to system rules JSON file (defaults to sample_data/system_rules.json)"
    )

    @property
    def postgres_dsn(self) -> str:
        """Get PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )

    @property
    def postgres_async_dsn(self) -> str:
        """Get PostgreSQL async connection string for asyncpg."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
