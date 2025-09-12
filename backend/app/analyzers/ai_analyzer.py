"""
AI-powered analyzer using OpenAI services
"""

from typing import Dict, List, Any
from app.analyzers.base_analyzer import BaseAnalyzer
from app.services.openai_service import openai_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIAnalyzer(BaseAnalyzer):
    """AI-powered analyzer using OpenAI GPT-4 Vision"""

    def __init__(self):
        super().__init__("ai")

    async def analyze(self, video_data: Any, sport_type: str) -> Dict:
        """
        Perform AI analysis on video data using OpenAI services
        """
        try:
            if not await self.validate_input(video_data):
                return {"error": "Invalid input data"}

            # Extract frames for AI analysis
            frames = await self._extract_frames(video_data)
            
            # Perform AI analysis
            ai_results = await openai_service.analyze_video_frames(frames, sport_type)
            
            # Generate feedback
            feedback = await openai_service.generate_feedback(ai_results, sport_type)

            results = {
                "analyzer_type": self.analyzer_type,
                "sport_type": sport_type,
                "ai_analysis": ai_results.get("analysis", ""),
                "confidence_score": ai_results.get("confidence", 0.0),
                "recommendations": ai_results.get("recommendations", []),
                "feedback": feedback,
                "insights": await self._extract_insights(ai_results, sport_type)
            }

            return await self.postprocess_results(results)

        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            return {"error": str(e)}

    async def validate_input(self, video_data: Any) -> bool:
        """Validate video data for AI analysis"""
        if not video_data:
            return False
        
        # Check if we have frames or video URL
        if not (hasattr(video_data, 'frames') or hasattr(video_data, 'url')):
            return False
        
        return True

    async def _extract_frames(self, video_data: Any) -> List[str]:
        """Extract frames from video data for AI analysis"""
        # Placeholder - would extract actual frames as base64 or URLs
        mock_frames = [
            "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",  # Mock frame 1
            "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",  # Mock frame 2
            "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",  # Mock frame 3
        ]
        
        return mock_frames

    async def _extract_insights(self, ai_results: Dict, sport_type: str) -> List[Dict]:
        """Extract structured insights from AI analysis"""
        insights = []
        
        analysis_text = ai_results.get("analysis", "")
        
        # Extract technique insights
        if "technique" in analysis_text.lower():
            insights.append({
                "category": "technique",
                "insight": "Technique analysis available",
                "priority": "high"
            })
        
        # Extract safety insights
        if any(word in analysis_text.lower() for word in ["safety", "risk", "injury"]):
            insights.append({
                "category": "safety",
                "insight": "Safety considerations identified",
                "priority": "high"
            })
        
        # Extract performance insights
        if any(word in analysis_text.lower() for word in ["performance", "improve", "better"]):
            insights.append({
                "category": "performance",
                "insight": "Performance improvement opportunities found",
                "priority": "medium"
            })
        
        return insights

    async def postprocess_results(self, results: Dict) -> Dict:
        """Post-process AI analysis results"""
        # Add metadata
        results["metadata"] = {
            "model_used": "gpt-4-vision-preview",
            "analysis_date": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "processing_time": 2.5  # Would track actual processing time
        }
        
        # Normalize confidence score
        if "confidence_score" in results:
            results["confidence_score"] = min(1.0, max(0.0, results["confidence_score"]))
        
        return results


ai_analyzer = AIAnalyzer()
