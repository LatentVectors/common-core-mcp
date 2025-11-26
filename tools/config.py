"""Centralized configuration for the tools module."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ToolsSettings(BaseSettings):
    """Configuration settings for the tools module."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    csp_api_key: str = ""
    csp_base_url: str = "https://api.commonstandardsproject.com/api/v1"
    max_requests_per_minute: int = 60

    # Path Configuration
    # These are computed properties based on project root
    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent

    @property
    def raw_data_dir(self) -> Path:
        """Get the raw data directory."""
        return self.project_root / "data" / "raw"

    @property
    def standard_sets_dir(self) -> Path:
        """Get the standard sets directory."""
        return self.raw_data_dir / "standardSets"

    @property
    def processed_data_dir(self) -> Path:
        """Get the processed data directory."""
        return self.project_root / "data" / "processed"

    # Logging Configuration
    log_file: str = "data/cli.log"
    log_rotation: str = "10 MB"
    log_retention: str = "7 days"

    # Pinecone Configuration
    pinecone_api_key: str = ""
    pinecone_index_name: str = "common-core-standards"
    pinecone_namespace: str = "standards"


_settings: ToolsSettings | None = None


def get_settings() -> ToolsSettings:
    """Get the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = ToolsSettings()
    return _settings
