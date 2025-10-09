"""
Simplified FastAPI application for deployment debugging
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Application starting up...")
    try:
        # Basic startup without complex dependencies
        logger.info("✅ Simple startup completed")
        yield
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    finally:
        logger.info("🛑 Application shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Performate AI (Simplified)",
    description="Sports Performance Analysis Platform (Debug Mode)",
    version="1.0.0-debug",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Performate AI (Simplified)", "version": "1.0.0-debug", "status": "working"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "mode": "debug"}

@app.get("/debug/test")
async def debug_test():
    return {"test": "success", "message": "Simplified deployment working"}

# Basic error handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return {"error": "Internal server error", "debug": str(exc)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)