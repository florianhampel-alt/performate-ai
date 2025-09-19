"""
Route Analysis Service
Separates route color identification from difficulty assessment
Implements core climbing analysis requirements
"""

from typing import List, Dict, Any, Tuple
import statistics
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RouteAnalysisService:
    """Service for analyzing climbing routes independent of color"""
    
    def __init__(self):
        # Difficulty mapping based on hold characteristics (NOT color)
        self.hold_difficulty_map = {
            'jug': 2.0,      # Large, positive holds - easy
            'crimp': 6.0,    # Small finger holds - hard
            'sloper': 7.0,   # Slopey holds - very hard
            'pinch': 5.0,    # Pinch grips - moderate-hard
            'pocket': 6.5,   # Finger pockets - hard
            'gaston': 7.5,   # Gaston positions - very hard
            'undercling': 6.0 # Undercling holds - hard
        }
        
        # Wall angle difficulty modifiers
        self.angle_difficulty_map = {
            'vertical': 1.0,
            'slight_overhang': 1.3,
            'overhang': 1.8,
            'steep_overhang': 2.2
        }
        
        # Size difficulty modifiers
        self.size_difficulty_map = {
            'large': 0.7,
            'medium': 1.0,
            'small': 1.4,
            'tiny': 1.8
        }
    
    def analyze_route_from_frames(
        self, 
        frame_analyses: List[Dict[str, Any]],
        video_duration: float
    ) -> Dict[str, Any]:
        """
        Analyze climbing route from frame data
        CRITICAL: Separates route color from difficulty assessment
        
        Args:
            frame_analyses: List of AI frame analysis results
            video_duration: Total video duration in seconds
            
        Returns:
            Route analysis with color and difficulty separated
        """
        if not frame_analyses:
            logger.warning("No frame analyses provided for route analysis")
            return self._create_fallback_route_analysis()
        
        logger.info(f"🧗 Analyzing route from {len(frame_analyses)} frames over {video_duration:.1f}s")
        
        # 1. Extract route color (orientation only, consensus across frames)
        route_color = self._determine_route_color(frame_analyses)
        
        # 2. Assess difficulty based on holds, angles, technique (NOT color)
        difficulty_assessment = self._assess_difficulty_from_holds(frame_analyses)
        
        # 3. Calculate total moves from frame progression
        total_moves = self._estimate_total_moves(frame_analyses, video_duration)
        
        # 4. Generate performance segments based on technique scores
        performance_segments = self._create_performance_segments(frame_analyses, video_duration)
        
        # 5. Extract key insights focusing on technique
        key_insights = self._generate_technique_insights(frame_analyses, difficulty_assessment)
        
        # 6. Generate recommendations based on analysis
        recommendations = self._generate_recommendations(frame_analyses, difficulty_assessment)
        
        route_analysis = {
            "route_detected": True,
            "route_color": route_color,  # For orientation only
            "difficulty_estimated": difficulty_assessment["grade"],
            "difficulty_reasoning": difficulty_assessment["reasoning"],
            "total_moves": total_moves,
            "wall_angle": self._determine_wall_angle(frame_analyses),
            "hold_characteristics": difficulty_assessment["hold_summary"],
            "performance_segments": performance_segments,
            "overall_score": int(statistics.mean([fa.get('technique_score', 70) for fa in frame_analyses])),
            "key_insights": key_insights,
            "recommendations": recommendations,
            "analysis_method": "hold_based_difficulty_assessment"
        }
        
        logger.warning(f"🎯 ROUTE ANALYSIS COMPLETE:")
        logger.warning(f"   Route Color: {route_color} (orientation only)")
        logger.warning(f"   Difficulty: {difficulty_assessment['grade']} (based on holds/technique)")
        logger.warning(f"   Total Moves: {total_moves}")
        logger.warning(f"   Reasoning: {difficulty_assessment['reasoning']}")
        
        return route_analysis
    
    def _determine_route_color(self, frame_analyses: List[Dict[str, Any]]) -> str:
        """Determine route color from consensus across frames (orientation only)"""
        colors = []
        for analysis in frame_analyses:
            color = analysis.get('route_color')
            if color and color != 'unbekannt':
                colors.append(color)
        
        if not colors:
            return 'unbekannt'
        
        # Find most common color (consensus)
        from collections import Counter
        color_counts = Counter(colors)
        most_common = color_counts.most_common(1)[0][0]
        
        logger.warning(f"🎨 Route color consensus: {most_common} (from {colors})")
        return most_common
    
    def _assess_difficulty_from_holds(self, frame_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess difficulty based on hold characteristics, wall angle, and technique
        CRITICAL: Does NOT use route color for difficulty assessment
        """
        difficulty_factors = []
        hold_types = []
        hold_sizes = []
        wall_angles = []
        reasoning_parts = []
        
        for analysis in frame_analyses:
            # Extract hold analysis data
            hold_analysis = analysis.get('hold_analysis', {})
            if isinstance(hold_analysis, dict):
                types = hold_analysis.get('types', [])
                sizes = hold_analysis.get('sizes', [])
                hold_types.extend(types)
                hold_sizes.extend(sizes)
            
            # Extract wall angle
            wall_angle = analysis.get('wall_angle', 'vertical')
            wall_angles.append(wall_angle)
            
            # Extract difficulty indicators
            indicators = analysis.get('difficulty_indicators', [])
            if indicators:
                reasoning_parts.extend(indicators)
        
        # Calculate base difficulty from hold types
        base_difficulty = 5.0  # Default moderate difficulty
        if hold_types:
            hold_difficulties = [self.hold_difficulty_map.get(hold_type, 5.0) for hold_type in hold_types]
            base_difficulty = statistics.mean(hold_difficulties)
            reasoning_parts.append(f"Hold types: {', '.join(set(hold_types))}")
        
        # Apply wall angle modifier
        angle_modifier = 1.0
        if wall_angles:
            most_common_angle = max(set(wall_angles), key=wall_angles.count)
            angle_modifier = self.angle_difficulty_map.get(most_common_angle.replace(' ', '_'), 1.0)
            if angle_modifier > 1.0:
                reasoning_parts.append(f"Wall angle: {most_common_angle}")
        
        # Apply size modifier
        size_modifier = 1.0
        if hold_sizes:
            avg_size_difficulty = statistics.mean([self.size_difficulty_map.get(size, 1.0) for size in hold_sizes])
            size_modifier = avg_size_difficulty
            if size_modifier > 1.0:
                reasoning_parts.append(f"Hold sizes: {', '.join(set(hold_sizes))}")
        
        # Calculate final difficulty
        final_difficulty = base_difficulty * angle_modifier * size_modifier
        final_difficulty = max(1.0, min(10.0, final_difficulty))  # Clamp to 1-10 range
        
        # Convert to climbing grade
        grade = self._difficulty_to_grade(final_difficulty)
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Based on visual assessment"
        
        return {
            "difficulty": final_difficulty,
            "grade": grade,
            "reasoning": reasoning,
            "hold_summary": {
                "types": list(set(hold_types)),
                "sizes": list(set(hold_sizes)),
                "primary_angle": max(set(wall_angles), key=wall_angles.count) if wall_angles else "vertical"
            }
        }
    
    def _difficulty_to_grade(self, difficulty: float) -> str:
        """Convert numerical difficulty to climbing grade"""
        # French sport climbing grades (most common)
        if difficulty >= 9.0:
            return "7a+"
        elif difficulty >= 8.0:
            return "6c+"
        elif difficulty >= 7.0:
            return "6b"
        elif difficulty >= 6.0:
            return "6a"
        elif difficulty >= 5.0:
            return "5c"
        elif difficulty >= 4.0:
            return "5a"
        else:
            return "4a"
    
    def _estimate_total_moves(self, frame_analyses: List[Dict[str, Any]], video_duration: float) -> int:
        """Estimate total moves for the route based on frame analysis"""
        # Get move counts from frames
        frame_moves = []
        for analysis in frame_analyses:
            moves = analysis.get('move_count', 0)
            if moves > 0:
                frame_moves.append(moves)
        
        if not frame_moves:
            # Fallback based on video duration
            return max(4, min(12, int(video_duration / 3)))
        
        # Use conservative estimation
        avg_moves_per_frame = statistics.mean(frame_moves)
        
        # Estimate total based on video duration and visible moves
        if video_duration <= 15:
            total_estimate = int(avg_moves_per_frame * 1.5)  # Short routes
        elif video_duration <= 30:
            total_estimate = int(avg_moves_per_frame * 2.0)  # Medium routes
        else:
            total_estimate = int(avg_moves_per_frame * 2.5)  # Long routes
        
        # Clamp to reasonable range
        total_moves = max(4, min(15, total_estimate))
        
        logger.warning(f"🔢 Move estimation: {avg_moves_per_frame:.1f} avg per frame → {total_moves} total moves")
        return total_moves
    
    def _determine_wall_angle(self, frame_analyses: List[Dict[str, Any]]) -> str:
        """Determine predominant wall angle"""
        angles = []
        for analysis in frame_analyses:
            angle = analysis.get('wall_angle')
            if angle:
                angles.append(angle)
        
        if not angles:
            return 'vertical'
        
        # Return most common angle
        from collections import Counter
        return Counter(angles).most_common(1)[0][0]
    
    def _create_performance_segments(self, frame_analyses: List[Dict[str, Any]], video_duration: float) -> List[Dict[str, Any]]:
        """Create performance segments based on technique scores"""
        if len(frame_analyses) < 2:
            # Single frame - create one segment
            score = frame_analyses[0].get('technique_score', 70) / 100
            return [{
                "time_start": 0.0,
                "time_end": video_duration,
                "score": score,
                "issue": None if score >= 0.7 else "technique_improvement_needed"
            }]
        
        segments = []
        for i, analysis in enumerate(frame_analyses):
            timestamp = analysis.get('timestamp', 0)
            score = analysis.get('technique_score', 70) / 100
            
            # Calculate segment boundaries
            if i == 0:
                start_time = 0.0
                end_time = (timestamp + frame_analyses[i + 1].get('timestamp', video_duration)) / 2
            elif i == len(frame_analyses) - 1:
                start_time = (frame_analyses[i - 1].get('timestamp', 0) + timestamp) / 2
                end_time = video_duration
            else:
                start_time = (frame_analyses[i - 1].get('timestamp', 0) + timestamp) / 2
                end_time = (timestamp + frame_analyses[i + 1].get('timestamp', video_duration)) / 2
            
            segments.append({
                "time_start": start_time,
                "time_end": end_time,
                "score": score,
                "issue": None if score >= 0.7 else "technique_improvement_needed"
            })
        
        return segments
    
    def _generate_technique_insights(self, frame_analyses: List[Dict[str, Any]], difficulty_assessment: Dict[str, Any]) -> List[str]:
        """Generate technique-focused insights"""
        insights = []
        
        # Analyze technique scores
        technique_scores = [fa.get('technique_score', 70) for fa in frame_analyses]
        avg_technique = statistics.mean(technique_scores)
        
        if avg_technique >= 80:
            insights.append("Ausgezeichnete Klettertechnik mit konsistenter Ausführung")
        elif avg_technique >= 70:
            insights.append("Solide Grundtechnik mit Verbesserungspotential")
        else:
            insights.append("Techniktraining empfohlen für bessere Effizienz")
        
        # Analyze difficulty vs performance
        difficulty = difficulty_assessment["difficulty"]
        if avg_technique >= 75 and difficulty >= 7:
            insights.append(f"Gute Performance auf schwierigem Terrain (Schwierigkeit: {difficulty:.1f}/10)")
        elif avg_technique < 65 and difficulty <= 5:
            insights.append("Fokus auf Grundtechnik auch bei moderaten Schwierigkeiten")
        
        # Add hold-specific insights
        hold_types = difficulty_assessment["hold_summary"]["types"]
        if "crimp" in hold_types:
            insights.append("Gute Fingerführung bei Crimps erkennbar")
        if "sloper" in hold_types:
            insights.append("Körperspannung bei Slopern wichtig für Verbesserung")
        
        return insights[:4]  # Limit to 4 insights
    
    def _generate_recommendations(self, frame_analyses: List[Dict[str, Any]], difficulty_assessment: Dict[str, Any]) -> List[str]:
        """Generate technique-focused recommendations"""
        recommendations = []
        
        # Analyze technique scores for recommendations
        technique_scores = [fa.get('technique_score', 70) for fa in frame_analyses]
        avg_technique = statistics.mean(technique_scores)
        
        if avg_technique < 70:
            recommendations.append("Arbeite an der Grundtechnik: Körperposition und Gewichtsverteilung")
        
        # Hold-specific recommendations
        hold_types = difficulty_assessment["hold_summary"]["types"]
        if "crimp" in hold_types:
            recommendations.append("Übe Fingertraining für bessere Crimp-Kraft")
        if "sloper" in hold_types:
            recommendations.append("Stärke die Körperspannung für Sloper-Griffe")
        if "pinch" in hold_types:
            recommendations.append("Trainiere Daumen- und Pinch-Kraft")
        
        # Wall angle recommendations
        primary_angle = difficulty_assessment["hold_summary"]["primary_angle"]
        if "overhang" in primary_angle:
            recommendations.append("Fokus auf Rumpfkraft für Überhänge")
        
        # General recommendations
        recommendations.extend([
            "Übe Routenplanung vor dem Klettern",
            "Arbeite an flüssigen Bewegungsübergängen"
        ])
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _create_fallback_route_analysis(self) -> Dict[str, Any]:
        """Create fallback route analysis when no frame data available"""
        return {
            "route_detected": False,
            "route_color": "unbekannt",
            "difficulty_estimated": "5a",
            "difficulty_reasoning": "Insufficient data for assessment",
            "total_moves": 8,
            "wall_angle": "vertical",
            "hold_characteristics": {"types": [], "sizes": [], "primary_angle": "vertical"},
            "performance_segments": [],
            "overall_score": 65,
            "key_insights": ["Nicht genügend Daten für detaillierte Analyse"],
            "recommendations": ["Bessere Videoqualität für genauere Analyse"],
            "analysis_method": "fallback"
        }

# Global service instance
route_analysis_service = RouteAnalysisService()