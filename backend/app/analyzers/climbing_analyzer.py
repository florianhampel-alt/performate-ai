"""
Climbing-specific pose analysis using MediaPipe
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ClimbingMetrics:
    """Container for climbing-specific metrics"""
    difficulty_grade: str
    movement_quality_score: float
    balance_score: float
    efficiency_score: float
    technique_score: float
    wall_distance_avg: float
    movement_segments: List[Dict]
    key_insights: List[str]
    recommendations: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]


class ClimbingPoseAnalyzer:
    """Analyze climbing videos using MediaPipe pose detection"""
    
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
    def analyze_video(self, video_path: str) -> ClimbingMetrics:
        """Analyze a climbing video and return metrics"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video file: {video_path}")
            
            # Extract pose landmarks from all frames
            pose_data = self._extract_pose_landmarks(cap)
            cap.release()
            
            if not pose_data:
                raise ValueError("No pose landmarks detected in video")
            
            # Calculate climbing-specific metrics
            metrics = self._calculate_climbing_metrics(pose_data)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing climbing video: {e}")
            raise
    
    def _extract_pose_landmarks(self, cap) -> List[Dict]:
        """Extract pose landmarks from video frames"""
        pose_data = []
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                # Extract key landmarks for climbing analysis
                landmarks = self._extract_key_landmarks(results.pose_landmarks)
                pose_data.append({
                    'frame': frame_count,
                    'landmarks': landmarks,
                    'timestamp': frame_count / 30.0  # Assuming 30 FPS
                })
            
            frame_count += 1
            
            # Limit processing for performance (analyze every 3rd frame)
            if frame_count % 3 != 0:
                continue
                
        logger.info(f"Extracted pose data from {len(pose_data)} frames")
        return pose_data
    
    def _extract_key_landmarks(self, pose_landmarks) -> Dict:
        """Extract key body landmarks for climbing analysis"""
        landmarks = {}
        
        # Key points for climbing analysis
        key_points = {
            'nose': 0,
            'left_shoulder': 11, 'right_shoulder': 12,
            'left_elbow': 13, 'right_elbow': 14,
            'left_wrist': 15, 'right_wrist': 16,
            'left_hip': 23, 'right_hip': 24,
            'left_knee': 25, 'right_knee': 26,
            'left_ankle': 27, 'right_ankle': 28
        }
        
        for name, idx in key_points.items():
            if idx < len(pose_landmarks.landmark):
                landmark = pose_landmarks.landmark[idx]
                landmarks[name] = {
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                }
        
        return landmarks
    
    def _calculate_climbing_metrics(self, pose_data: List[Dict]) -> ClimbingMetrics:
        """Calculate climbing-specific performance metrics"""
        
        # Calculate center of mass movement
        com_trajectory = self._calculate_center_of_mass_trajectory(pose_data)
        
        # Analyze movement segments
        movement_segments = self._analyze_movement_segments(pose_data)
        
        # Calculate scores
        balance_score = self._calculate_balance_score(pose_data)
        efficiency_score = self._calculate_efficiency_score(com_trajectory)
        technique_score = self._calculate_technique_score(pose_data)
        wall_distance = self._estimate_wall_distance(pose_data)
        
        # Estimate difficulty grade based on movement patterns
        difficulty_grade = self._estimate_difficulty_grade(
            balance_score, efficiency_score, technique_score, movement_segments
        )
        
        # Generate insights and recommendations
        insights = self._generate_insights(balance_score, efficiency_score, technique_score, wall_distance)
        recommendations = self._generate_recommendations(balance_score, efficiency_score, technique_score)
        strengths, improvements = self._identify_strengths_and_improvements(
            balance_score, efficiency_score, technique_score
        )
        
        return ClimbingMetrics(
            difficulty_grade=difficulty_grade,
            movement_quality_score=(balance_score + efficiency_score + technique_score) / 3,
            balance_score=balance_score,
            efficiency_score=efficiency_score,
            technique_score=technique_score,
            wall_distance_avg=wall_distance,
            movement_segments=movement_segments,
            key_insights=insights,
            recommendations=recommendations,
            strengths=strengths,
            areas_for_improvement=improvements
        )
    
    def _calculate_center_of_mass_trajectory(self, pose_data: List[Dict]) -> List[Tuple[float, float]]:
        """Calculate center of mass trajectory"""
        trajectory = []
        
        for frame_data in pose_data:
            landmarks = frame_data['landmarks']
            
            # Simplified COM calculation using hip midpoint
            if 'left_hip' in landmarks and 'right_hip' in landmarks:
                left_hip = landmarks['left_hip']
                right_hip = landmarks['right_hip']
                
                com_x = (left_hip['x'] + right_hip['x']) / 2
                com_y = (left_hip['y'] + right_hip['y']) / 2
                
                trajectory.append((com_x, com_y))
        
        return trajectory
    
    def _analyze_movement_segments(self, pose_data: List[Dict]) -> List[Dict]:
        """Analyze movement segments for quality assessment"""
        segments = []
        segment_size = len(pose_data) // 5  # Divide into 5 segments
        
        for i in range(0, len(pose_data), segment_size):
            segment_data = pose_data[i:i + segment_size]
            if len(segment_data) < 3:
                continue
                
            # Analyze this segment
            segment_stability = self._calculate_segment_stability(segment_data)
            segment_quality = "good" if segment_stability > 0.7 else "needs_improvement"
            
            segments.append({
                'start_frame': i,
                'end_frame': min(i + segment_size, len(pose_data)),
                'quality': segment_quality,
                'stability_score': segment_stability,
                'duration': len(segment_data) / 30.0  # Convert to seconds
            })
        
        return segments
    
    def _calculate_balance_score(self, pose_data: List[Dict]) -> float:
        """Calculate balance/stability score"""
        stability_scores = []
        
        for frame_data in pose_data:
            landmarks = frame_data['landmarks']
            
            # Check if key stability points are visible and well-positioned
            stability = 0.0
            count = 0
            
            # Hip alignment
            if 'left_hip' in landmarks and 'right_hip' in landmarks:
                hip_level_diff = abs(landmarks['left_hip']['y'] - landmarks['right_hip']['y'])
                stability += max(0, 1 - hip_level_diff * 5)  # Penalize uneven hips
                count += 1
            
            # Shoulder alignment
            if 'left_shoulder' in landmarks and 'right_shoulder' in landmarks:
                shoulder_level_diff = abs(landmarks['left_shoulder']['y'] - landmarks['right_shoulder']['y'])
                stability += max(0, 1 - shoulder_level_diff * 3)
                count += 1
            
            if count > 0:
                stability_scores.append(stability / count)
        
        return np.mean(stability_scores) if stability_scores else 0.5
    
    def _calculate_efficiency_score(self, com_trajectory: List[Tuple[float, float]]) -> float:
        """Calculate movement efficiency score"""
        if len(com_trajectory) < 5:
            return 0.5
        
        # Calculate total path length
        total_distance = 0
        for i in range(1, len(com_trajectory)):
            dx = com_trajectory[i][0] - com_trajectory[i-1][0]
            dy = com_trajectory[i][1] - com_trajectory[i-1][1]
            total_distance += np.sqrt(dx*dx + dy*dy)
        
        # Calculate direct distance (start to end)
        start = com_trajectory[0]
        end = com_trajectory[-1]
        direct_distance = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        
        # Efficiency is inverse of path deviation
        if total_distance > 0:
            efficiency = min(1.0, direct_distance / total_distance * 2)
        else:
            efficiency = 0.5
        
        return efficiency
    
    def _calculate_technique_score(self, pose_data: List[Dict]) -> float:
        """Calculate climbing technique score"""
        technique_scores = []
        
        for frame_data in pose_data:
            landmarks = frame_data['landmarks']
            score = 0.0
            count = 0
            
            # Arm positioning (not over-extended)
            if all(k in landmarks for k in ['left_shoulder', 'left_elbow', 'left_wrist']):
                # Check left arm angle
                arm_angle = self._calculate_arm_angle(
                    landmarks['left_shoulder'], landmarks['left_elbow'], landmarks['left_wrist']
                )
                # Good technique: arms not fully extended (30-150 degrees)
                if 30 <= arm_angle <= 150:
                    score += 1.0
                else:
                    score += 0.3
                count += 1
            
            # Similar for right arm
            if all(k in landmarks for k in ['right_shoulder', 'right_elbow', 'right_wrist']):
                arm_angle = self._calculate_arm_angle(
                    landmarks['right_shoulder'], landmarks['right_elbow'], landmarks['right_wrist']
                )
                if 30 <= arm_angle <= 150:
                    score += 1.0
                else:
                    score += 0.3
                count += 1
            
            if count > 0:
                technique_scores.append(score / count)
        
        return np.mean(technique_scores) if technique_scores else 0.5
    
    def _calculate_arm_angle(self, shoulder, elbow, wrist) -> float:
        """Calculate arm angle at elbow"""
        # Vector from elbow to shoulder
        v1 = np.array([shoulder['x'] - elbow['x'], shoulder['y'] - elbow['y']])
        # Vector from elbow to wrist  
        v2 = np.array([wrist['x'] - elbow['x'], wrist['y'] - elbow['y']])
        
        # Calculate angle
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle) * 180 / np.pi
        
        return angle
    
    def _estimate_wall_distance(self, pose_data: List[Dict]) -> float:
        """Estimate average distance from wall"""
        distances = []
        
        for frame_data in pose_data:
            landmarks = frame_data['landmarks']
            
            # Use nose or hip position as body reference
            if 'nose' in landmarks:
                # Assuming climber faces the wall, x=0 is wall
                distance = landmarks['nose']['x']
                distances.append(distance)
        
        return np.mean(distances) if distances else 0.5
    
    def _calculate_segment_stability(self, segment_data: List[Dict]) -> float:
        """Calculate stability score for a movement segment"""
        if len(segment_data) < 3:
            return 0.5
        
        # Calculate variance in hip position
        hip_positions = []
        for frame_data in segment_data:
            landmarks = frame_data['landmarks']
            if 'left_hip' in landmarks and 'right_hip' in landmarks:
                hip_x = (landmarks['left_hip']['x'] + landmarks['right_hip']['x']) / 2
                hip_y = (landmarks['left_hip']['y'] + landmarks['right_hip']['y']) / 2
                hip_positions.append((hip_x, hip_y))
        
        if len(hip_positions) < 3:
            return 0.5
        
        # Low variance = high stability
        x_variance = np.var([pos[0] for pos in hip_positions])
        y_variance = np.var([pos[1] for pos in hip_positions])
        
        # Convert variance to stability score (0-1)
        stability = max(0, 1 - (x_variance + y_variance) * 10)
        return min(1.0, stability)
    
    def _estimate_difficulty_grade(self, balance: float, efficiency: float, technique: float, segments: List[Dict]) -> str:
        """Estimate climbing difficulty grade"""
        overall_score = (balance + efficiency + technique) / 3
        
        # Count segments with good quality
        good_segments = sum(1 for seg in segments if seg['quality'] == 'good')
        total_segments = len(segments)
        quality_ratio = good_segments / total_segments if total_segments > 0 else 0
        
        # Grade estimation based on performance
        if overall_score >= 0.85 and quality_ratio >= 0.8:
            return "6a+"  # Advanced
        elif overall_score >= 0.75 and quality_ratio >= 0.7:
            return "5c"   # Intermediate-Advanced
        elif overall_score >= 0.65 and quality_ratio >= 0.6:
            return "5a"   # Intermediate
        elif overall_score >= 0.55:
            return "4c"   # Beginner-Intermediate
        elif overall_score >= 0.45:
            return "4b"   # Beginner
        else:
            return "4a"   # Absolute Beginner
    
    def _generate_insights(self, balance: float, efficiency: float, technique: float, wall_distance: float) -> List[str]:
        """Generate key insights based on analysis"""
        insights = []
        
        if balance >= 0.75:
            insights.append("Sehr gute Balance und Körperstabilität erkennbar")
        elif balance >= 0.5:
            insights.append("Grundlegende Balance vorhanden, Verbesserungspotenzial bei Stabilität")
        else:
            insights.append("Balance und Stabilität benötigen deutliche Verbesserung")
        
        if efficiency >= 0.7:
            insights.append("Effiziente Bewegungsführung mit direkten Kletterpfaden")
        elif efficiency >= 0.5:
            insights.append("Bewegungseffizienz ist akzeptabel, aber optimierbar")
        else:
            insights.append("Viele unnötige Bewegungen, Fokus auf direktere Routen empfohlen")
        
        if technique >= 0.7:
            insights.append("Solide Grundtechnik mit guter Armpositionierung")
        else:
            insights.append("Techniktraining empfohlen, besonders bei Armhaltung")
        
        if wall_distance > 0.6:
            insights.append("Zu großer Abstand zur Wand - näher an die Wand lehnen")
        elif wall_distance < 0.3:
            insights.append("Sehr gute Wandnähe, effiziente Körperpositionierung")
        
        return insights
    
    def _generate_recommendations(self, balance: float, efficiency: float, technique: float) -> List[str]:
        """Generate specific recommendations"""
        recommendations = []
        
        if balance < 0.6:
            recommendations.append("Übe statische Positionen und Körperspannung")
            recommendations.append("Arbeite an der Rumpfstabilität durch Planks und Core-Training")
        
        if efficiency < 0.6:
            recommendations.append("Plane deine Route im Voraus und visualisiere Bewegungen")
            recommendations.append("Übe bewusstes, langsames Klettern für bessere Kontrolle")
        
        if technique < 0.6:
            recommendations.append("Fokussiere auf entspannte Armhaltung, vermeide Überstreckung")
            recommendations.append("Integriere Technikübungen in dein Training")
        
        # General recommendations
        recommendations.append("Arbeite an der Fußtechnik für bessere Gewichtsverteilung")
        recommendations.append("Übe verschiedene Griffarten für vielseitigere Technik")
        
        return recommendations
    
    def _identify_strengths_and_improvements(self, balance: float, efficiency: float, technique: float) -> Tuple[List[str], List[str]]:
        """Identify strengths and areas for improvement"""
        strengths = []
        improvements = []
        
        if balance >= 0.7:
            strengths.append("Ausgezeichnete Balance")
        else:
            improvements.append("Balance und Stabilität")
        
        if efficiency >= 0.7:
            strengths.append("Effiziente Bewegungsführung")
        else:
            improvements.append("Bewegungseffizienz")
        
        if technique >= 0.7:
            strengths.append("Solide Klettertechnik")
        else:
            improvements.append("Grundtechnik und Armhaltung")
        
        # Always include these areas for comprehensive feedback
        if not improvements:
            improvements.append("Kontinuierliche Verfeinerung der Technik")
        
        if not strengths:
            strengths.append("Engagement und Motivation")
        
        return strengths, improvements
