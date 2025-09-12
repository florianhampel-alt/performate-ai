"""
FastAPI Entry Point for Performate AI
"""

import uuid
import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config.base import settings
from app.services.s3_service import s3_service
from app.services.openai_service import openai_service
from app.services.redis_service import redis_service
from app.utils.video_processor import extract_frames_from_video
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Performate AI API",
    description="AI-powered sports performance analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Performate AI API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload und analysiere ein Sportvideo mit AI"""
    
    # Generiere Analysis ID
    analysis_id = str(uuid.uuid4())
    logger.info(f"Starting video analysis {analysis_id} for file: {file.filename}")
    
    try:
        # 1. Validiere Dateityp
        allowed_types = ["video/mp4", "video/quicktime", "video/avi", "video/x-msvideo"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
        
        # 2. Speichere Video temporär
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            contents = await file.read()
            tmp_file.write(contents)
            temp_path = tmp_file.name
        
        try:
            # 3. Upload zu S3 (falls konfiguriert)
            video_url = None
            try:
                video_url = await s3_service.upload_file(temp_path, f"videos/{analysis_id}/{file.filename}")
                logger.info(f"Video uploaded to S3: {video_url}")
            except Exception as e:
                logger.warning(f"S3 upload failed: {e}, continuing with local analysis")
            
            # 4. Extrahiere Frames für Analyse
            frames = extract_frames_from_video(temp_path, max_frames=5)
            logger.info(f"Extracted {len(frames)} frames for analysis")
            
            # 5. AI-Analyse mit OpenAI Vision
            analysis_result = await openai_service.analyze_sports_video(
                frames=frames,
                video_filename=file.filename,
                analysis_id=analysis_id
            )
            
            # 6. Cache Ergebnis in Redis
            await redis_service.cache_analysis_result(analysis_id, analysis_result, expire=3600)
            
            # 7. Erweitere Ergebnis mit Metadaten
            final_result = {
                "analysis_id": analysis_id,
                "filename": file.filename,
                "content_type": file.content_type,
                "video_url": video_url,
                "frames_analyzed": len(frames),
                "analysis": analysis_result,
                "status": "completed",
                "timestamp": f"{analysis_id[:8]}-{analysis_id[8:12]}-{analysis_id[12:16]}-{analysis_id[16:20]}-{analysis_id[20:]}"
            }
            
            logger.info(f"Analysis completed successfully: {analysis_id}")
            return final_result
            
        finally:
            # Cleanup temporäre Datei
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        logger.error(f"Analysis failed for {analysis_id}: {str(e)}")
        return {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "error",
            "error": str(e),
            "analysis": {
                "sport_detected": "unknown",
                "confidence": 0,
                "key_insights": ["Analysis failed, please try again with a different video"],
                "technical_analysis": "Unable to process video",
                "recommendations": ["Ensure video is clear and shows sporting activity"]
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
