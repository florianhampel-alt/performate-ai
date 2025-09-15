"""
Base configuration settings
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Base settings configuration"""
    
    # Application settings
    APP_NAME: str = "Performate AI"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ALLOWED_HOSTS_STR: str = "localhost,127.0.0.1,*.vercel.app,performate-ai.vercel.app"
    
    # Database settings (if needed in future)
    DATABASE_URL: str = "sqlite:///./performate-ai.db"
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # Upstash Redis settings (cloud Redis service)
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    
    # AWS S3 settings
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "performate-ai-uploads"
    AWS_ENDPOINT_URL: Optional[str] = None
    
    # OpenAI settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-vision-preview"
    
    # File upload settings
    MAX_FILE_SIZE: int = 120 * 1024 * 1024  # 120MB
    ALLOWED_EXTENSIONS_STR: str = ".mp4,.avi,.mov,.mkv,.wmv"
    
    # Analysis settings
    MAX_ANALYSIS_FRAMES: int = 30
    ANALYSIS_TIMEOUT: int = 300  # 5 minutes
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "performate-ai.log"
    
    # Worker settings (for Celery/Redis)
    BROKER_URL: str = "redis://localhost:6379/0"
    RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Development settings
    USE_LOCAL_STORAGE: bool = False
    LOCAL_UPLOAD_DIR: str = "./uploads"
    
    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """Parse allowed hosts from string"""
        hosts_str = os.getenv('ALLOWED_HOSTS', self.ALLOWED_HOSTS_STR)
        return [host.strip() for host in hosts_str.split(',')]
    
    @property
    def ALLOWED_EXTENSIONS(self) -> List[str]:
        """Parse allowed extensions from string"""
        ext_str = os.getenv('ALLOWED_EXTENSIONS', self.ALLOWED_EXTENSIONS_STR)
        return [ext.strip() for ext in ext_str.split(',')]
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra fields from .env
    }


# Create settings instance
settings = Settings()
