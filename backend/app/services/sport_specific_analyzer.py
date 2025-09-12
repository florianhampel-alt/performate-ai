"""
Sport-specific analysis service
"""

from typing import Dict, List
from app.utils.sport_configs import SPORT_CONFIGS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SportSpecificAnalyzer:
    def __init__(self):
        self.sport_configs = SPORT_CONFIGS

    async def analyze_sport_specific(self, sport_type: str, analysis_data: Dict) -> Dict:
        """Perform sport-specific analysis"""
        try:
            if sport_type not in self.sport_configs:
                logger.warning(f"Unknown sport type: {sport_type}")
                return self._generic_analysis(analysis_data)

            config = self.sport_configs[sport_type]
            
            analysis_result = {
                "sport_type": sport_type,
                "key_metrics": self._analyze_key_metrics(config["key_metrics"], analysis_data),
                "technique_points": self._analyze_technique(config["technique_focus"], analysis_data),
                "safety_considerations": config["safety_tips"],
                "training_recommendations": self._generate_training_recommendations(sport_type, analysis_data)
            }

            return analysis_result

        except Exception as e:
            logger.error(f"Sport-specific analysis failed: {str(e)}")
            return {"error": str(e)}

    def _analyze_key_metrics(self, metrics: List[str], data: Dict) -> Dict:
        """Analyze key performance metrics for the sport"""
        results = {}
        
        for metric in metrics:
            if metric.lower() in data:
                results[metric] = {
                    "value": data[metric.lower()],
                    "status": "good" if data[metric.lower()] > 0.7 else "needs_improvement"
                }
            else:
                results[metric] = {"status": "not_analyzed"}
        
        return results

    def _analyze_technique(self, focus_areas: List[str], data: Dict) -> List[Dict]:
        """Analyze technique based on sport-specific focus areas"""
        technique_analysis = []
        
        for area in focus_areas:
            technique_analysis.append({
                "area": area,
                "score": data.get(f"{area.lower()}_score", 0.0),
                "feedback": f"Focus on improving {area.lower()} technique"
            })
        
        return technique_analysis

    def _generate_training_recommendations(self, sport_type: str, data: Dict) -> List[str]:
        """Generate sport-specific training recommendations"""
        base_recommendations = [
            f"Practice {sport_type} fundamentals daily",
            "Focus on strength and conditioning",
            "Work on flexibility and mobility"
        ]

        # Add sport-specific recommendations based on analysis
        if sport_type == "climbing":
            base_recommendations.extend([
                "Practice grip strength exercises",
                "Work on route reading skills",
                "Focus on footwork precision"
            ])
        elif sport_type == "skiing":
            base_recommendations.extend([
                "Practice parallel turns",
                "Work on edge control",
                "Improve balance and stability"
            ])

        return base_recommendations

    def _generic_analysis(self, data: Dict) -> Dict:
        """Fallback generic analysis for unknown sports"""
        return {
            "sport_type": "generic",
            "analysis": "Generic movement analysis performed",
            "recommendations": [
                "Focus on proper form and technique",
                "Work on strength and conditioning",
                "Practice regularly with proper rest"
            ]
        }


sport_analyzer = SportSpecificAnalyzer()
