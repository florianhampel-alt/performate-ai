"""
Pytest configuration and fixtures for testing
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Create a test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def sample_video_data():
    """Sample video data for testing"""
    return {
        "frames": ["frame1", "frame2", "frame3"],
        "url": "https://example.com/test-video.mp4",
        "sport_type": "climbing"
    }


@pytest.fixture
def sample_analysis_request():
    """Sample analysis request data"""
    return {
        "video_url": "https://example.com/test-climbing.mp4",
        "sport_type": "climbing",
        "analysis_type": "comprehensive",
        "user_id": "test-user-123"
    }


@pytest.fixture
def mock_analysis_result():
    """Mock analysis result for testing"""
    return {
        "id": "test-analysis-123",
        "sport_type": "climbing",
        "analyzer_type": "comprehensive_sport",
        "overall_performance_score": 0.75,
        "comprehensive_insights": [
            {
                "category": "technique",
                "level": "info",
                "message": "Good footwork technique observed",
                "priority": "medium"
            }
        ],
        "unified_recommendations": [
            "Focus on grip strength improvement",
            "Work on route planning skills"
        ],
        "analysis_summary": {
            "analyzers_used": 2,
            "total_insights": 1,
            "recommendations_count": 2,
            "overall_score": 0.75
        }
    }
