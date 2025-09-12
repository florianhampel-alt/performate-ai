"""
Base analyzer abstract class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from app.models.analysis import AnalysisResult


class BaseAnalyzer(ABC):
    """Abstract base class for all analyzers"""

    def __init__(self, analyzer_type: str):
        self.analyzer_type = analyzer_type

    @abstractmethod
    async def analyze(self, video_data: Any, sport_type: str) -> Dict:
        """
        Analyze video data and return results
        
        Args:
            video_data: Video data (frames, URL, etc.)
            sport_type: Type of sport being analyzed
            
        Returns:
            Dict containing analysis results
        """
        pass

    @abstractmethod
    async def validate_input(self, video_data: Any) -> bool:
        """
        Validate input data before analysis
        
        Args:
            video_data: Video data to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        pass

    def get_analyzer_info(self) -> Dict:
        """Get information about this analyzer"""
        return {
            "type": self.analyzer_type,
            "name": self.__class__.__name__,
            "version": "1.0.0"
        }

    async def preprocess_data(self, video_data: Any) -> Any:
        """
        Preprocess data before analysis
        Override in subclasses if needed
        """
        return video_data

    async def postprocess_results(self, results: Dict) -> Dict:
        """
        Postprocess results after analysis
        Override in subclasses if needed
        """
        return results
