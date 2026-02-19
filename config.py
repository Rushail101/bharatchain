"""
config.py — BharatChain Global Configuration
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "BharatChain"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./bharatchain.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Blockchain
    BLOCKCHAIN_BACKEND: str = "simulation"
    WEB3_PROVIDER_URL: str = "http://127.0.0.1:8545"
    CHAIN_ID: int = 1337
    DEPLOYER_PRIVATE_KEY: str = ""
    FABRIC_NETWORK_PROFILE: str = "network-profile.json"
    FABRIC_CHANNEL: str = "bharatchain-channel"
    FABRIC_CHAINCODE: str = "identity-chaincode"
    FABRIC_ORG: str = "UIDAI"
    FABRIC_USER: str = "Admin"

    # Cryptography
    ENCRYPTION_KEY: str = ""
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 30

    # IPFS
    IPFS_HOST: str = "127.0.0.1"
    IPFS_PORT: int = 5001
    IPFS_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    BIOMETRIC_HASH_ITERATIONS: int = 100_000
    MAX_CONSENT_DURATION_DAYS: int = 365
    RATE_LIMIT_PER_MINUTE: int = 60

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "bharatchain.log"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()