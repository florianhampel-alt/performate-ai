"""
OpenAI service for AI-powered video analysis
"""

import openai
from typing import Dict, List, Optional
from app.config.base import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

openai.api_key = settings.OPENAI_API_KEY


class OpenAIService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze_video_frames(self, frames: List[str], sport_type: str) -> Dict:
        """Analyze video frames using GPT-4 Vision"""
        try:
            prompt = f"""
            Analyze these {sport_type} video frames for performance insights.
            Focus on:
            1. Technique and form
            2. Movement patterns
            3. Areas for improvement
            4. Safety considerations
            
            Provide structured feedback with specific recommendations.
            """

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        *[{"type": "image_url", "image_url": {"url": frame}} for frame in frames[:5]]  # Limit to 5 frames
                    ]
                }
            ]

            response = await self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=messages,
                max_tokens=1000
            )

            return {
                "analysis": response.choices[0].message.content,
                "confidence": 0.85,  # Placeholder confidence score
                "recommendations": self._extract_recommendations(response.choices[0].message.content)
            }

        except Exception as e:
            logger.error(f"OpenAI analysis failed: {str(e)}")
            return {"error": str(e)}

    async def generate_feedback(self, analysis_data: Dict, sport_type: str) -> List[str]:
        """Generate personalized feedback based on analysis"""
        try:
            prompt = f"""
            Based on this {sport_type} performance analysis data:
            {analysis_data}
            
            Generate 3-5 specific, actionable feedback points for improvement.
            """

            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            feedback = response.choices[0].message.content.strip().split('\n')
            return [f.strip('- ').strip() for f in feedback if f.strip()]

        except Exception as e:
            logger.error(f"Feedback generation failed: {str(e)}")
            return ["Unable to generate feedback at this time."]

    def _extract_recommendations(self, analysis_text: str) -> List[str]:
        """Extract key recommendations from analysis text"""
        # Simple extraction logic - could be enhanced with NLP
        lines = analysis_text.split('\n')
        recommendations = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['recommend', 'improve', 'focus', 'work on']):
                recommendations.append(line.strip())
        
        return recommendations[:5]  # Limit to 5 recommendations


openai_service = OpenAIService()
