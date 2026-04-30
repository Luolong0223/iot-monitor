"""应用配置管理"""
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """全局配置，从环境变量或.env文件加载"""

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "gas_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "change_me_in_production"

    # TDengine
    TDENGINE_HOST: str = "localhost"
    TDENGINE_PORT: int = 6030
    TDENGINE_DB: str = "gas_data"
    TDENGINE_KEEP_DAYS: int = 365

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # JWT
    JWT_SECRET_KEY: str = "change_this_to_a_random_secret_key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""

    # TCP Server
    TCP_HOST: str = "0.0.0.0"
    TCP_PORT: int = 9000

    # 系统
    SYSTEM_NAME: str = "贵阳燃气外围数据采集管理平台"
    LOG_LEVEL: str = "info"
    DEBUG: bool = False

    # 安全
    CORS_ORIGINS: str = '["http://localhost:5173","http://localhost:80"]'
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCK_MINUTES: int = 30

    # 备份
    BACKUP_ENABLED: bool = True
    BACKUP_TIME: str = "02:00"
    BACKUP_RETAIN_DAYS: int = 30
    BACKUP_PATH: str = "/data/backup"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
