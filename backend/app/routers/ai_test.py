"""
AI Test Router - Direct testing of AI analysis
"""

from fastapi import APIRouter, HTTPException
from app.services.ai_vision_service import ai_vision_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/ai-test/{analysis_id}")
async def test_ai_analysis(analysis_id: str):
    """Test AI analysis directly"""
    try:
        logger.info(f"Testing AI analysis for {analysis_id}")
        
        # Force AI analysis for existing video
        result = await ai_vision_service.analyze_climbing_video(
            video_path=f"/videos/{analysis_id}",
            analysis_id=analysis_id,
            sport_type="climbing"
        )
        
        return {
            "status": "success",
            "analysis_id": analysis_id,
            "ai_result": result,
            "has_overlay": result.get("overlay_data", {}).get("has_overlay", False),
            "overlay_elements": len(result.get("overlay_data", {}).get("elements", [])),
            "ai_confidence": result.get("ai_confidence", "N/A")
        }
        
    except Exception as e:
        logger.error(f"AI test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "analysis_id": analysis_id
        }