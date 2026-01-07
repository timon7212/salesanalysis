from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Storage
    storage_mode: str = "local"
    local_storage_path: str = "/storage"
    
    # Transcription
    transcribe_provider: str = "assemblyai"
    assemblyai_api_key: Optional[str] = None
    
    # LLM
    llm_provider: str = "openai"
    llm_api_base_url: str
    llm_api_key: str
    llm_model: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


