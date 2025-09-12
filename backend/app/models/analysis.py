"""
Analysis data models
"""

from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class AnalysisRequest(BaseModel):
    video_url: str
    sport_type: str
    analysis_type: str = "comprehensive"
    user_id: Optional[str] = None


class AnalysisResult(BaseModel):
    id: str
    video_url: str
    sport_type: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: Optional[Dict] = None
    feedback: Optional[List[Dict]] = None
    confidence_score: Optional[float] = None


class BiomechanicsAnalysis(BaseModel):
    joint_angles: Dict[str, List[float]]
    movement_patterns: List[str]
    technique_score: float
    recommendations: List[str]


class PerformanceMetrics(BaseModel):
    speed: Optional[float] = None
    power: Optional[float] = None
    efficiency: Optional[float] = None
    balance: Optional[float] = None
