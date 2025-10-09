"""
Simplified FastAPI application for successful deployment
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import sys

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Performate AI API",
    description="AI-powered sports performance analysis (Simplified)",
    version="1.0.0-simple"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Simplified for now
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Performate AI API", 
        "version": "1.0.0-simple",
        "status": "operational",
        "environment": os.getenv("DEBUG", "production")
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0-simple",
        "python_version": sys.version,
        "environment_vars": {
            "DEBUG": os.getenv("DEBUG"),
            "OPENAI_API_KEY": "configured" if os.getenv("OPENAI_API_KEY") else "missing",
            "AWS_ACCESS_KEY_ID": "configured" if os.getenv("AWS_ACCESS_KEY_ID") else "missing"
        }
    }

@app.get("/test")
async def test_endpoint():
    return {"test": "successful", "deployment": "working"}

# Try to include complex routers if possible
try:
    logger.info("Attempting to load complex services...")
    
    # Try AI test router
    try:
        from app.routers.ai_test import router as ai_test_router
        app.include_router(ai_test_router, tags=["AI Testing"])
        logger.info("✅ AI test router included")
    except Exception as e:
        logger.warning(f"AI test router failed: {e}")
    
    logger.info("Complex services loading completed")
    
except Exception as e:
    logger.warning(f"Complex services failed to load: {e}")
    # Continue with simple version

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)