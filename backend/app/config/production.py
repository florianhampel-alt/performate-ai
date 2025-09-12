"""
Production environment configuration
"""

from app.config.base import Settings


class ProductionSettings(Settings):
    """Production-specific settings"""
    
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    
    # Production security
    ALLOWED_HOSTS: list = ["performate-ai.com", "api.performate-ai.com"]
    
    # Production services
    S3_BUCKET: str = "performate-ai-prod-uploads"
    
    # Production database (would be PostgreSQL or similar)
    DATABASE_URL: str = "postgresql://user:pass@localhost/performate-ai"
    
    # Strict timeouts for production
    ANALYSIS_TIMEOUT: int = 180  # 3 minutes
    
    # Production file limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB for production
    MAX_ANALYSIS_FRAMES: int = 20  # Fewer frames for faster processing
    
    # Enhanced security
    SECRET_KEY: str = ""  # Must be set via environment variable
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    
    # Production monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    class Config:
        env_file = ".env.production"


# Production settings instance
prod_settings = ProductionSettings()
