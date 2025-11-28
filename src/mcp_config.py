"""MCP server configuration module."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class McpSettings(BaseSettings):
    """Configuration settings for the MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Pinecone Configuration
    pinecone_api_key: str = ""
    pinecone_index_name: str = "common-core-standards"
    pinecone_namespace: str = "standards"


_settings: McpSettings | None = None


def get_mcp_settings() -> McpSettings:
    """Get the singleton MCP settings instance."""
    global _settings
    if _settings is None:
        _settings = McpSettings()
    return _settings

