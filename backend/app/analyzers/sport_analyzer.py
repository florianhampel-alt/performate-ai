"""
Comprehensive sport analyzer combining multiple analysis methods
"""

from typing import Dict, List, Any
from app.analyzers.base_analyzer import BaseAnalyzer
from app.analyzers.biomechanics_analyzer import biomechanics_analyzer
from app.analyzers.ai_analyzer import ai_analyzer
from app.services.sport_specific_analyzer import sport_analyzer as sport_specific_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SportAnalyzer(BaseAnalyzer):
    """Comprehensive analyzer that combines multiple analysis methods"""

    def __init__(self):
        super().__init__("comprehensive_sport")
        self.analyzers = {
            "biomechanics": biomechanics_analyzer,
            "ai": ai_analyzer
        }

    async def analyze(self, video_data: Any, sport_type: str) -> Dict:
        """
        Perform comprehensive sport analysis using multiple analyzers
        """
        try:
            if not await self.validate_input(video_data):
                return {"error": "Invalid input data"}

            results = {
                "analyzer_type": self.analyzer_type,
                "sport_type": sport_type,
                "comprehensive_analysis": {}
            }

            # Run all analyzers
            analysis_results = {}
            
            for analyzer_name, analyzer in self.analyzers.items():
                try:
                    logger.info(f"Running {analyzer_name} analysis for {sport_type}")
                    analyzer_result = await analyzer.analyze(video_data, sport_type)
                    analysis_results[analyzer_name] = analyzer_result
                except Exception as e:
                    logger.error(f"Error in {analyzer_name} analysis: {str(e)}")
                    analysis_results[analyzer_name] = {"error": str(e)}

            # Combine results from all analyzers
            results["comprehensive_analysis"] = analysis_results

            # Run sport-specific analysis
            sport_specific_data = await self._prepare_sport_specific_data(analysis_results)
            sport_specific_result = await sport_specific_service.analyze_sport_specific(
                sport_type, sport_specific_data
            )
            results["sport_specific_analysis"] = sport_specific_result

            # Generate comprehensive insights
            results["comprehensive_insights"] = await self._generate_comprehensive_insights(
                analysis_results, sport_specific_result, sport_type
            )

            # Calculate overall performance score
            results["overall_performance_score"] = await self._calculate_overall_score(analysis_results)

            # Generate unified recommendations
            results["unified_recommendations"] = await self._generate_unified_recommendations(
                analysis_results, sport_specific_result, sport_type
            )

            return await self.postprocess_results(results)

        except Exception as e:
            logger.error(f"Comprehensive sport analysis failed: {str(e)}")
            return {"error": str(e)}

    async def validate_input(self, video_data: Any) -> bool:
        """Validate video data for comprehensive analysis"""
        if not video_data:
            return False
        
        # Validate with each analyzer
        for analyzer in self.analyzers.values():
            if not await analyzer.validate_input(video_data):
                return False
        
        return True

    async def _prepare_sport_specific_data(self, analysis_results: Dict) -> Dict:
        """Prepare data for sport-specific analysis"""
        sport_data = {}
        
        # Extract biomechanics data
        if "biomechanics" in analysis_results and "error" not in analysis_results["biomechanics"]:
            biomech_data = analysis_results["biomechanics"]
            sport_data.update({
                "stability_score": biomech_data.get("performance_metrics", {}).get("stability_score", 0),
                "efficiency_score": biomech_data.get("performance_metrics", {}).get("efficiency_score", 0),
                "technique_score": biomech_data.get("performance_metrics", {}).get("technique_score", 0),
                "biomechanical_score": biomech_data.get("biomechanical_score", 0)
            })

        # Extract AI analysis data
        if "ai" in analysis_results and "error" not in analysis_results["ai"]:
            ai_data = analysis_results["ai"]
            sport_data.update({
                "ai_confidence": ai_data.get("confidence_score", 0),
                "ai_insights_count": len(ai_data.get("insights", []))
            })

        return sport_data

    async def _generate_comprehensive_insights(self, analysis_results: Dict, sport_specific: Dict, sport_type: str) -> List[Dict]:
        """Generate comprehensive insights from all analyses"""
        insights = []

        # Biomechanics insights
        if "biomechanics" in analysis_results and "error" not in analysis_results["biomechanics"]:
            biomech_score = analysis_results["biomechanics"].get("biomechanical_score", 0)
            if biomech_score < 0.6:
                insights.append({
                    "category": "biomechanics",
                    "level": "warning",
                    "message": "Biomechanical analysis indicates areas for improvement in movement efficiency",
                    "priority": "high"
                })
            elif biomech_score > 0.8:
                insights.append({
                    "category": "biomechanics",
                    "level": "success",
                    "message": "Excellent biomechanical performance detected",
                    "priority": "low"
                })

        # AI insights
        if "ai" in analysis_results and "error" not in analysis_results["ai"]:
            ai_insights = analysis_results["ai"].get("insights", [])
            for insight in ai_insights:
                insights.append({
                    "category": "ai_analysis",
                    "level": "info",
                    "message": insight.get("insight", ""),
                    "priority": insight.get("priority", "medium")
                })

        # Sport-specific insights
        if "error" not in sport_specific:
            key_metrics = sport_specific.get("key_metrics", {})
            for metric, data in key_metrics.items():
                if data.get("status") == "needs_improvement":
                    insights.append({
                        "category": "sport_specific",
                        "level": "warning",
                        "message": f"{metric} needs improvement for optimal {sport_type} performance",
                        "priority": "medium"
                    })

        return insights

    async def _calculate_overall_score(self, analysis_results: Dict) -> float:
        """Calculate overall performance score from all analyses"""
        scores = []
        
        # Biomechanics score
        if "biomechanics" in analysis_results and "error" not in analysis_results["biomechanics"]:
            biomech_score = analysis_results["biomechanics"].get("biomechanical_score", 0)
            scores.append(biomech_score * 0.4)  # 40% weight
        
        # AI confidence score
        if "ai" in analysis_results and "error" not in analysis_results["ai"]:
            ai_confidence = analysis_results["ai"].get("confidence_score", 0)
            scores.append(ai_confidence * 0.3)  # 30% weight
        
        # Technical execution (derived from performance metrics)
        if "biomechanics" in analysis_results and "error" not in analysis_results["biomechanics"]:
            perf_metrics = analysis_results["biomechanics"].get("performance_metrics", {})
            tech_score = (
                perf_metrics.get("technique_score", 0) + 
                perf_metrics.get("efficiency_score", 0)
            ) / 2
            scores.append(tech_score * 0.3)  # 30% weight
        
        return sum(scores) if scores else 0.5

    async def _generate_unified_recommendations(self, analysis_results: Dict, sport_specific: Dict, sport_type: str) -> List[str]:
        """Generate unified recommendations from all analyses"""
        recommendations = []
        
        # Collect recommendations from all analyzers
        all_recommendations = set()
        
        # Biomechanics recommendations
        if "biomechanics" in analysis_results and "error" not in analysis_results["biomechanics"]:
            biomech_recs = analysis_results["biomechanics"].get("recommendations", [])
            all_recommendations.update(biomech_recs)
        
        # AI recommendations
        if "ai" in analysis_results and "error" not in analysis_results["ai"]:
            ai_recs = analysis_results["ai"].get("recommendations", [])
            all_recommendations.update(ai_recs)
        
        # Sport-specific recommendations
        if "error" not in sport_specific:
            sport_recs = sport_specific.get("training_recommendations", [])
            all_recommendations.update(sport_recs)
        
        # Prioritize and format recommendations
        recommendations = list(all_recommendations)[:8]  # Limit to top 8
        
        # Add unified recommendations based on combined analysis
        if len(recommendations) == 0:
            recommendations.append(f"Continue practicing {sport_type} with focus on technique improvement")
        
        return recommendations

    async def postprocess_results(self, results: Dict) -> Dict:
        """Post-process comprehensive analysis results"""
        # Add summary statistics
        results["analysis_summary"] = {
            "analyzers_used": len([a for a in results["comprehensive_analysis"].values() if "error" not in a]),
            "total_insights": len(results.get("comprehensive_insights", [])),
            "recommendations_count": len(results.get("unified_recommendations", [])),
            "overall_score": results.get("overall_performance_score", 0)
        }
        
        # Add processing metadata
        results["metadata"] = {
            "analysis_type": "comprehensive",
            "sport_type": results.get("sport_type", "unknown"),
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }
        
        return results


comprehensive_sport_analyzer = SportAnalyzer()
