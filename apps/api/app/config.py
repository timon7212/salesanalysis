from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Security
    admin_api_key: str
    app_encryption_key: str
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Storage
    storage_mode: str = "local"
    local_storage_path: str = "/storage"
    s3_endpoint: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_region: Optional[str] = None
    
    # Kommo
    kommo_base_url: str
    kommo_client_id: str
    kommo_client_secret: str
    kommo_redirect_uri: str
    kommo_access_token: Optional[str] = None
    kommo_refresh_token: Optional[str] = None
    kommo_expires_at: Optional[str] = None
    
    # Transcription
    transcribe_provider: str = "assemblyai"
    assemblyai_api_key: Optional[str] = None
    
    # LLM
    llm_provider: str = "openai"
    llm_api_base_url: str
    llm_api_key: str
    llm_model: str
    
    # Upload
    max_upload_mb: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


