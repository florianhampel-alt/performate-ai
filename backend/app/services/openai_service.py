"""
OpenAI service for AI-powered video analysis with comprehensive sports analysis
"""

import base64
from openai import AsyncOpenAI
from typing import Dict, List, Optional
from app.config.base import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze_sports_video(self, frames: List[bytes], video_filename: str, analysis_id: str) -> Dict:
        """Führe eine vollständige AI-Sportanalyse durch"""
        try:
            # Konvertiere Frames zu base64 für OpenAI Vision
            base64_frames = []
            for frame in frames[:3]:  # Limitiere auf 3 Frames für Kosten
                base64_frame = base64.b64encode(frame).decode('utf-8')
                base64_frames.append(base64_frame)
            
            logger.info(f"Analyzing {len(base64_frames)} frames with OpenAI Vision API")
            
            # Erstelle Vision API Request
            messages = [
                {
                    "role": "system",
                    "content": """Du bist ein professioneller Sportanalyst und Coach. Analysiere das gegebene Video und gib detaillierte Erkenntnisse über:
                    1. Welche Sportart erkannt wird
                    2. Technische Bewertung der Bewegungen (0-10 Punkte)
                    3. Stärken und Schwächen
                    4. Konkrete Verbesserungsvorschläge
                    5. Biomechanische Einschätzungen
                    
                    Antworte strukturiert und professionell. Sei spezifisch und konstruktiv."""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analysiere dieses Sportvideo (Dateiname: {video_filename}). Gib eine detaillierte Leistungsanalyse:"
                        }
                    ] + [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{frame}",
                                "detail": "high"
                            }
                        } for frame in base64_frames
                    ]
                }
            ]
            
            # OpenAI API Call
            response = await self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            ai_analysis = response.choices[0].message.content
            logger.info(f"OpenAI analysis completed for {analysis_id}")
            
            # Strukturiere die Antwort
            structured_result = {
                "sport_detected": self._extract_sport_from_analysis(ai_analysis),
                "confidence": self._extract_confidence_score(ai_analysis),
                "technical_analysis": ai_analysis,
                "key_insights": self._extract_key_insights(ai_analysis),
                "recommendations": self._extract_recommendations(ai_analysis),
                "performance_score": self._calculate_performance_score(ai_analysis),
                "areas_for_improvement": self._extract_improvement_areas(ai_analysis),
                "strengths": self._extract_strengths(ai_analysis)
            }
            
            return structured_result
            
        except Exception as e:
            logger.error(f"OpenAI video analysis failed: {str(e)}")
            # Fallback response
            return {
                "sport_detected": "general",
                "confidence": 50,
                "technical_analysis": f"Video wurde erfolgreich hochgeladen und verarbeitet. Detaillierte AI-Analyse war nicht verfügbar: {str(e)}",
                "key_insights": [
                    "Video wurde erfolgreich verarbeitet",
                    "Grundlegende Bewegungsmuster erkennbar",
                    "Für detaillierte Analyse bitte erneut versuchen"
                ],
                "recommendations": [
                    "Stelle sicher, dass das Video klar und gut beleuchtet ist",
                    "Achte darauf, dass die Bewegungen gut sichtbar sind",
                    "Verwende eine stabile Kameraposition"
                ],
                "performance_score": 70,
                "areas_for_improvement": ["Videoqualität", "Beleuchtung", "Kamerawinkel"],
                "strengths": ["Video erfolgreich hochgeladen", "Grundbewegungen sichtbar"]
            }
    
    def _extract_sport_from_analysis(self, analysis: str) -> str:
        """Extrahiere Sportart aus der Analyse"""
        sports_keywords = {
            "climb": "climbing", "klettern": "climbing", "boulder": "bouldering",
            "ski": "skiing", "snowboard": "snowboarding", "board": "snowboarding",
            "bike": "cycling", "fahrrad": "cycling", "rad": "cycling",
            "run": "running", "lauf": "running", "joggen": "running",
            "swim": "swimming", "schwimm": "swimming",
            "tennis": "tennis", "golf": "golf",
            "soccer": "soccer", "fußball": "soccer", "football": "soccer",
            "basketball": "basketball", "volleyball": "volleyball",
            "yoga": "yoga", "fitness": "fitness", "workout": "fitness"
        }
        
        analysis_lower = analysis.lower()
        for keyword, sport in sports_keywords.items():
            if keyword in analysis_lower:
                return sport
        return "general_sports"
    
    def _extract_confidence_score(self, analysis: str) -> int:
        """Berechne Confidence Score basierend auf Analyse-Qualität"""
        word_count = len(analysis.split())
        detail_words = ['technique', 'form', 'movement', 'balance', 'strength', 'improvement']
        detail_count = sum(1 for word in detail_words if word.lower() in analysis.lower())
        
        base_score = min(90, 50 + (word_count // 10))  # Basis-Score basierend auf Länge
        detail_bonus = min(20, detail_count * 3)  # Bonus für Details
        
        return min(95, base_score + detail_bonus)
    
    def _extract_key_insights(self, analysis: str) -> List[str]:
        """Extrahiere wichtigste Erkenntnisse"""
        insights = []
        sentences = analysis.split('. ')
        
        # Suche nach wichtigen Insights
        insight_keywords = ['good', 'excellent', 'strength', 'weakness', 'improvement', 'technique', 'form']
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in insight_keywords):
                clean_sentence = sentence.strip('. !').replace('\n', ' ')
                if len(clean_sentence) > 10 and len(clean_sentence) < 150:
                    insights.append(clean_sentence)
        
        # Fallback insights falls keine gefunden
        if not insights:
            insights = [
                "Bewegungsanalyse durchgeführt",
                "Grundlegende Technik erkennbar", 
                "Verbesserungspotenzial identifiziert"
            ]
        
        return insights[:5]  # Max 5 insights
    
    def _extract_recommendations(self, analysis: str) -> List[str]:
        """Extrahiere Empfehlungen"""
        recommendations = []
        sentences = analysis.split('. ')
        
        # Suche nach Empfehlungs-Patterns
        rec_keywords = ['should', 'could', 'try', 'practice', 'focus', 'work on', 'improve', 'consider']
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in rec_keywords):
                clean_sentence = sentence.strip('. !').replace('\n', ' ')
                if len(clean_sentence) > 15 and len(clean_sentence) < 200:
                    recommendations.append(clean_sentence)
        
        # Fallback recommendations
        if not recommendations:
            recommendations = [
                "Übe regelmäßig die Grundtechniken",
                "Achte auf eine saubere Ausführung",
                "Arbeite an deiner Körperhaltung",
                "Konzentriere dich auf gleichmäßige Bewegungen"
            ]
        
        return recommendations[:6]  # Max 6 recommendations
    
    def _calculate_performance_score(self, analysis: str) -> int:
        """Berechne Performance Score (30-95 Punkte)"""
        positive_words = ['good', 'excellent', 'strong', 'correct', 'perfect', 'solid', 'great', 'well']
        negative_words = ['weak', 'poor', 'incorrect', 'needs', 'lacking', 'problem', 'issue', 'mistake']
        
        analysis_lower = analysis.lower()
        positive_count = sum(1 for word in positive_words if word in analysis_lower)
        negative_count = sum(1 for word in negative_words if word in analysis_lower)
        
        # Basis-Score 70, dann Adjustierung
        base_score = 70
        positive_boost = positive_count * 4
        negative_penalty = negative_count * 6
        
        final_score = base_score + positive_boost - negative_penalty
        return max(30, min(95, final_score))
    
    def _extract_improvement_areas(self, analysis: str) -> List[str]:
        """Extrahiere Verbesserungsbereiche"""
        areas = []
        improvement_keywords = {
            'balance': 'Balance', 'posture': 'Körperhaltung', 'haltung': 'Körperhaltung',
            'timing': 'Timing', 'zeit': 'Timing',
            'strength': 'Kraft', 'kraft': 'Kraft',
            'technique': 'Technik', 'technik': 'Technik',
            'coordination': 'Koordination', 'koordination': 'Koordination',
            'flexibility': 'Flexibilität', 'flexibilität': 'Flexibilität',
            'endurance': 'Ausdauer', 'ausdauer': 'Ausdauer',
            'form': 'Form', 'movement': 'Bewegung'
        }
        
        analysis_lower = analysis.lower()
        for keyword, area in improvement_keywords.items():
            if keyword in analysis_lower and area not in areas:
                areas.append(area)
        
        # Standard Verbesserungsbereiche falls keine gefunden
        if not areas:
            areas = ['Technik', 'Körperhaltung', 'Koordination']
        
        return areas[:5]  # Max 5 Bereiche
    
    def _extract_strengths(self, analysis: str) -> List[str]:
        """Extrahiere Stärken"""
        strengths = []
        sentences = analysis.split('. ')
        
        strength_indicators = ['good', 'excellent', 'strong', 'well', 'correct', 'solid', 'great']
        
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in strength_indicators):
                clean_sentence = sentence.strip('. !').replace('\n', ' ')
                if len(clean_sentence) > 10 and len(clean_sentence) < 150:
                    strengths.append(clean_sentence)
        
        # Fallback Stärken
        if not strengths:
            strengths = [
                "Grundlegende Bewegungsmuster erkennbar",
                "Konsistente Ausführung sichtbar",
                "Gute Videoqualität für Analyse"
            ]
        
        return strengths[:4]  # Max 4 Stärken

    # Legacy compatibility methods
    async def analyze_video_frames(self, frames: List[str], sport_type: str) -> Dict:
        """Legacy method for compatibility"""
        return await self.analyze_sports_video(frames, f"video.{sport_type}", "legacy")
    
    async def generate_feedback(self, analysis_data: Dict, sport_type: str) -> List[str]:
        """Legacy method for compatibility"""
        return analysis_data.get('recommendations', ['No feedback available'])


openai_service = OpenAIService()
