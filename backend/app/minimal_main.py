"""
Minimal FastAPI Backend für schnelles Render Deployment
Fallback wenn das Hauptsystem Probleme hat
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Performate AI - Minimal Backend",
    description="Minimal backend for quick deployment",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://performate-ai.vercel.app",
        "https://performate-ai-frontend.vercel.app", 
        "http://localhost:3000",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Performate AI Minimal Backend", 
        "version": "1.0.0",
        "deployment": "render",
        "message": "Enhanced AI analysis system loading..."
    }

@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy",
        "timestamp": "2025-10-08T12:53:17Z",
        "service": "minimal-backend"
    }

@app.post("/api/analyze")
async def analyze_video():
    """Placeholder for video analysis"""
    return {
        "status": "success",
        "message": "Enhanced AI system is being deployed. Please try again in 5 minutes.",
        "analysis_id": "minimal-system",
        "retry_after": 300  # 5 minutes
    }

@app.get("/api/status")
async def get_status():
    """Status endpoint"""
    return {
        "backend_status": "minimal_mode",
        "full_system": "deploying",
        "estimated_ready": "5 minutes",
        "enhanced_prompt": "loaded",
        "ai_analysis": "pending_deployment"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)