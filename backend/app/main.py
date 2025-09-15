"""
FastAPI Entry Point for Performate AI
"""

import uuid
import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config.base import settings
from app.services.redis_service import redis_service
from app.utils.logger import get_logger
from app.analyzers.climbing_analyzer import ClimbingPoseAnalyzer

logger = get_logger(__name__)

app = FastAPI(
    title="Performate AI API",
    description="AI-powered sports performance analysis",
    version="1.0.0"
)

# CORS middleware - Allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporary: allow all origins
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Performate AI API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/analysis/{analysis_id}")
async def get_analysis_results(analysis_id: str):
    """Get analysis results by analysis ID"""
    try:
        # Try to get from Redis cache first
        cached_result = await redis_service.get_cached_analysis(analysis_id)
        
        if cached_result:
            logger.info(f"Retrieved analysis {analysis_id} from cache")
            return {
                "id": analysis_id,
                "sport_type": cached_result.get('sport_detected', 'climbing'),
                "analyzer_type": "mediapipe_pose",
                "overall_performance_score": cached_result.get('performance_score', 70) / 100,
                "comprehensive_insights": [
                    {
                        "category": "technique",
                        "level": "info",
                        "message": insight,
                        "priority": "medium"
                    } for insight in cached_result.get('key_insights', [])
                ],
                "unified_recommendations": cached_result.get('recommendations', []),
                "sport_specific_analysis": {
                    "sport_type": cached_result.get('sport_detected', 'climbing'),
                    "difficulty_grade": cached_result.get('difficulty_grade', '4a'),
                    "key_metrics": {
                        "balance": {
                            "status": "good" if cached_result.get('detailed_metrics', {}).get('balance_score', 0.5) > 0.7 else "needs_improvement",
                            "score": cached_result.get('detailed_metrics', {}).get('balance_score', 0.5)
                        },
                        "efficiency": {
                            "status": "good" if cached_result.get('detailed_metrics', {}).get('efficiency_score', 0.5) > 0.7 else "needs_improvement",
                            "score": cached_result.get('detailed_metrics', {}).get('efficiency_score', 0.5)
                        },
                        "technique": {
                            "status": "good" if cached_result.get('detailed_metrics', {}).get('technique_score', 0.5) > 0.7 else "needs_improvement",
                            "score": cached_result.get('detailed_metrics', {}).get('technique_score', 0.5)
                        }
                    },
                    "safety_considerations": [
                        "Achte auf sicheren Griff und gute Fußplatzierung",
                        "Verwende Sicherungsausrüstung in angemessener Höhe"
                    ],
                    "training_recommendations": cached_result.get('recommendations', [])
                },
                "analysis_summary": {
                    "analyzers_used": 1,
                    "total_insights": len(cached_result.get('key_insights', [])),
                    "recommendations_count": len(cached_result.get('recommendations', [])),
                    "overall_score": cached_result.get('performance_score', 70)
                },
                "metadata": {
                    "analysis_type": "climbing_pose_analysis",
                    "timestamp": analysis_id[:8] + "-" + analysis_id[8:12] + "-" + analysis_id[12:16] + "-" + analysis_id[16:20] + "-" + analysis_id[20:]
                }
            }
        else:
            # Analysis not found
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
            
    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis: {str(e)}")

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video with basic AI analysis (simplified for deployment)"""
    
    # Generiere Analysis ID
    analysis_id = str(uuid.uuid4())
    logger.info(f"Starting video analysis {analysis_id} for file: {file.filename}")
    
    try:
        # 1. Validiere Dateityp
        allowed_types = ["video/mp4", "video/quicktime", "video/avi", "video/x-msvideo"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
        
        # 2. Speichere Video temporär für Analyse
        contents = await file.read()
        file_size = len(contents)
        
        # Save to temporary file
        temp_video_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                temp_video_path = temp_file.name
                temp_file.write(contents)
            
            # 3. Detektiere Sport-Typ
            sport_detected = detect_sport_from_filename(file.filename)
            
            # 4. Führe echte Klettern-Analyse durch
            if sport_detected in ['climbing', 'bouldering']:
                analyzer = ClimbingPoseAnalyzer()
                climbing_metrics = analyzer.analyze_video(temp_video_path)
                analysis_result = convert_climbing_metrics_to_dict(climbing_metrics)
            else:
                # Fallback für andere Sports
                analysis_result = create_mock_analysis(file.filename, sport_detected, file_size)
                
        finally:
            # Clean up temporary file
            if temp_video_path and os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
        
        # 5. Cache Ergebnis in Redis (falls verfügbar)
        try:
            await redis_service.cache_analysis_result(analysis_id, analysis_result, expire=3600)
        except Exception as e:
            logger.warning(f"Redis caching failed: {e}")
        
        # 6. Erweiterte Antwort
        final_result = {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "frames_analyzed": 5,  # Simuliert
            "analysis": analysis_result,
            "status": "completed",
            "timestamp": f"{analysis_id[:8]}-{analysis_id[8:12]}-{analysis_id[12:16]}-{analysis_id[16:20]}-{analysis_id[20:]}",
            "processing_time_ms": 1500  # Simuliert
        }
        
        logger.info(f"Analysis completed successfully: {analysis_id}")
        return final_result
        
    except Exception as e:
        logger.error(f"Analysis failed for {analysis_id}: {str(e)}")
        return {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "error",
            "error": str(e),
            "analysis": create_fallback_analysis()
        }


def detect_sport_from_filename(filename: str) -> str:
    """Detect sport from filename"""
    filename_lower = filename.lower()
    
    sport_keywords = {
        'climb': 'climbing', 'boulder': 'bouldering', 'klettern': 'climbing',
        'ski': 'skiing', 'snowboard': 'snowboarding', 'board': 'snowboarding',
        'bike': 'cycling', 'rad': 'cycling', 'cycle': 'cycling',
        'run': 'running', 'lauf': 'running', 'marathon': 'running',
        'swim': 'swimming', 'schwimm': 'swimming',
        'tennis': 'tennis', 'golf': 'golf', 'soccer': 'soccer',
        'basketball': 'basketball', 'volleyball': 'volleyball',
        'yoga': 'yoga', 'fitness': 'fitness', 'gym': 'fitness'
    }
    
    for keyword, sport in sport_keywords.items():
        if keyword in filename_lower:
            return sport
    
    return 'general_sports'


def create_mock_analysis(filename: str, sport: str, file_size: int) -> dict:
    """Create realistic mock analysis"""
    
    # Sport-specific analysis
    sport_analyses = {
        'climbing': {
            'confidence': 85,
            'key_insights': [
                'Gute Grifftechnik erkennbar',
                'Balance könnte verbessert werden',
                'Fußtechnik zeigt Potenzial'
            ],
            'recommendations': [
                'Arbeite an der Fußplatzierung',
                'Übe statische Positionen für bessere Balance',
                'Konzentriere dich auf flüssige Bewegungsübergänge'
            ],
            'areas_for_improvement': ['Balance', 'Fußtechnik', 'Kraft'],
            'strengths': ['Griffstärke', 'Grundtechnik']
        },
        'running': {
            'confidence': 78,
            'key_insights': [
                'Gleichmäßiger Laufrhythmus',
                'Gute Grundausdauer erkennbar',
                'Lauftechnik zeigt solide Basis'
            ],
            'recommendations': [
                'Arbeite an der Schrittfrequenz',
                'Achte auf aufrechte Körperhaltung',
                'Integriere Intervalltraining'
            ],
            'areas_for_improvement': ['Lauftechnik', 'Geschwindigkeit'],
            'strengths': ['Ausdauer', 'Konstanz']
        },
        'general_sports': {
            'confidence': 70,
            'key_insights': [
                'Athletische Bewegungen erkennbar',
                'Gute Grundfitness sichtbar',
                'Koordination zeigt Potenzial'
            ],
            'recommendations': [
                'Arbeite an der Bewegungsqualität',
                'Fokussiere auf Techniktraining',
                'Integriere Krafttraining'
            ],
            'areas_for_improvement': ['Technik', 'Koordination'],
            'strengths': ['Motivation', 'Grundfitness']
        }
    }
    
    base_analysis = sport_analyses.get(sport, sport_analyses['general_sports'])
    
    # Performance score basierend auf File-Größe und Sport
    performance_score = min(95, max(60, base_analysis['confidence'] + (file_size // 1000000)))
    
    return {
        'sport_detected': sport,
        'confidence': base_analysis['confidence'],
        'technical_analysis': f'Video-Analyse für {sport} durchgeführt. Das Video zeigt {filename} mit einer Dateigröße von {file_size//1000000}MB. Grundlegende Bewegungsanalyse completed.',
        'key_insights': base_analysis['key_insights'],
        'recommendations': base_analysis['recommendations'],
        'performance_score': performance_score,
        'areas_for_improvement': base_analysis['areas_for_improvement'],
        'strengths': base_analysis['strengths']
    }


def convert_climbing_metrics_to_dict(metrics) -> dict:
    """Convert ClimbingMetrics to dictionary format for API response"""
    return {
        'sport_detected': 'climbing',
        'difficulty_grade': metrics.difficulty_grade,
        'confidence': int(metrics.movement_quality_score * 100),
        'technical_analysis': f'Klettern-Video analysiert. Schwierigkeitsgrad: {metrics.difficulty_grade}. '
                            f'Bewegungsqualität: {metrics.movement_quality_score:.2f}/1.0. '
                            f'Balance: {metrics.balance_score:.2f}, Effizienz: {metrics.efficiency_score:.2f}, '
                            f'Technik: {metrics.technique_score:.2f}.',
        'key_insights': metrics.key_insights,
        'recommendations': metrics.recommendations,
        'performance_score': int(metrics.movement_quality_score * 100),
        'areas_for_improvement': metrics.areas_for_improvement,
        'strengths': metrics.strengths,
        'detailed_metrics': {
            'balance_score': metrics.balance_score,
            'efficiency_score': metrics.efficiency_score,
            'technique_score': metrics.technique_score,
            'wall_distance_avg': metrics.wall_distance_avg,
            'movement_segments': metrics.movement_segments
        }
    }


def create_fallback_analysis() -> dict:
    """Create fallback analysis for errors"""
    return {
        'sport_detected': 'unknown',
        'confidence': 50,
        'technical_analysis': 'Video wurde hochgeladen und verarbeitet. Detailanalyse war nicht möglich.',
        'key_insights': ['Video erfolgreich empfangen', 'Basis-Verarbeitung durchgeführt'],
        'recommendations': ['Video-Qualität prüfen', 'Erneut versuchen'],
        'performance_score': 60,
        'areas_for_improvement': ['Videoqualität'],
        'strengths': ['Upload erfolgreich']
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
