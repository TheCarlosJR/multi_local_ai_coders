"""
Continue.dev Server Configuration

Configuration file for the production-ready Continue.dev server.
Can be loaded from environment variables or config file.
"""

import os
from typing import Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Server configuration."""
    
    # Server settings
    host: str = os.getenv("CONTINUE_HOST", "127.0.0.1")
    port: int = int(os.getenv("CONTINUE_PORT", "8000"))
    reload: bool = os.getenv("CONTINUE_RELOAD", "false").lower() == "true"
    
    # Security
    secret_key: str = os.getenv(
        "CONTINUE_SECRET_KEY",
        "change-me-in-production-use-strong-secret"
    )
    enable_auth: bool = os.getenv("CONTINUE_AUTH", "true").lower() == "true"
    api_keys: list = None  # Can be loaded from file
    
    # Features
    enable_redis: bool = os.getenv("CONTINUE_REDIS", "false").lower() == "true"
    redis_host: str = os.getenv("CONTINUE_REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("CONTINUE_REDIS_PORT", "6379"))
    
    # Rate limiting
    rate_limit_requests: int = int(os.getenv("CONTINUE_RATE_LIMIT", "100"))
    rate_limit_window: int = int(os.getenv("CONTINUE_RATE_WINDOW", "3600"))
    
    # Observability
    enable_tracing: bool = os.getenv("CONTINUE_TRACING", "false").lower() == "true"
    jaeger_host: str = os.getenv("CONTINUE_JAEGER_HOST", "localhost")
    jaeger_port: int = int(os.getenv("CONTINUE_JAEGER_PORT", "6831"))
    
    # CORS
    cors_origins: list = None
    
    # Logging
    log_level: str = os.getenv("CONTINUE_LOG_LEVEL", "INFO")
    log_dir: Path = Path(os.getenv("CONTINUE_LOG_DIR", "logs"))
    
    def __post_init__(self):
        """Post-init processing."""
        
        # Parse CORS origins from env
        if self.cors_origins is None:
            cors_str = os.getenv("CONTINUE_CORS_ORIGINS", "*")
            self.cors_origins = [s.strip() for s in cors_str.split(",")]
        
        # Load API keys from file if specified
        api_keys_file = os.getenv("CONTINUE_API_KEYS_FILE")
        if api_keys_file and Path(api_keys_file).exists():
            with open(api_keys_file) as f:
                self.api_keys = [line.strip() for line in f if line.strip()]
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment."""
        return cls()
    
    @classmethod
    def from_file(cls, config_file: Path) -> "ServerConfig":
        """Load configuration from JSON file."""
        
        import json
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file) as f:
            data = json.load(f)
        
        return cls(**data)


# ============================================================
# EXAMPLE CONFIGURATIONS
# ============================================================

# Development configuration
CONFIG_DEV = ServerConfig(
    host="127.0.0.1",
    port=8000,
    reload=True,
    enable_auth=False,  # No auth in dev
    log_level="DEBUG",
)

# Production configuration
CONFIG_PROD = ServerConfig(
    host="0.0.0.0",
    port=8000,
    reload=False,
    enable_auth=True,
    enable_redis=True,
    enable_tracing=True,
    log_level="WARNING",
)

# Get active config from environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if ENVIRONMENT == "production":
    ACTIVE_CONFIG = CONFIG_PROD
else:
    ACTIVE_CONFIG = CONFIG_DEV
