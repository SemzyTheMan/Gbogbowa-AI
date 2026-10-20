from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "My API"
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str
    OPENAI_API_KEY: str
    LLM_MODEL: str = "gpt-4o-mini"
    INTRON_API_KEY: str
    DEFAULT_STT_LANGUAGE:str = "en"
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    PUBLIC_BASE_URL: str

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def DATABASE_URL(self) -> str:
        password = quote_plus(self.DB_PASSWORD)  # handles special characters
        return (
            f"mysql+pymysql://{self.DB_USER}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()