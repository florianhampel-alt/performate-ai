"""
Development environment configuration
"""

from app.config.base import Settings


class DevelopmentSettings(Settings):
    """Development-specific settings"""
    
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
    # Development-friendly CORS
    ALLOWED_HOSTS: list = ["localhost", "127.0.0.1", "localhost:3000", "127.0.0.1:3000"]
    
    # Use local services for development
    REDIS_HOST: str = "localhost"
    S3_BUCKET: str = "performate-ai-dev-uploads"
    
    # Development database
    DATABASE_URL: str = "sqlite:///./performate-ai-dev.db"
    
    # Relaxed timeouts for development
    ANALYSIS_TIMEOUT: int = 600  # 10 minutes
    
    # Local file storage fallback
    USE_LOCAL_STORAGE: bool = True
    LOCAL_UPLOAD_DIR: str = "./uploads"
    
    class Config:
        env_file = ".env.development"


# Development settings instance
dev_settings = DevelopmentSettings()
