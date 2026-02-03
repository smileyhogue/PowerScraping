import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SMARTHUB_EMAIL: str
    SMARTHUB_PASSWORD: str
    SMARTHUB_TOKEN: str | None = None
    
    INFLUXDB_URL: str
    INFLUXDB_TOKEN: str
    INFLUXDB_ORG: str
    INFLUXDB_BUCKET: str
    
    DISCORD_WEBHOOK_URL: str

    HOLSTON_RATES_URL: str = "https://holstonelectric.com/rates"
    SMARTHUB_LOGIN_URL: str = "https://holston.smarthub.coop/Login.html"
    SMARTHUB_API_URL: str = "https://holston.smarthub.coop/services/secured/utility-usage/poll"
    
    SMARTHUB_SERVICE_LOCATION: str
    SMARTHUB_ACCOUNT_NUMBER: str

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
