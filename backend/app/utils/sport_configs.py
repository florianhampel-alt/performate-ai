"""
Sport-specific configurations and settings
"""

from typing import Dict, List

# Sport-specific configuration data
SPORT_CONFIGS: Dict[str, Dict] = {
    "climbing": {
        "key_metrics": ["grip_strength", "body_positioning", "route_planning", "energy_efficiency"],
        "technique_focus": ["footwork", "handholds", "body_positioning", "dynamic_movement"],
        "analysis_points": [
            "Grip positioning and strength",
            "Foot placement accuracy",
            "Center of gravity management",
            "Movement flow and rhythm",
            "Energy conservation techniques"
        ],
        "safety_tips": [
            "Always check harness and rope connections",
            "Maintain three points of contact when possible",
            "Communicate clearly with belayer",
            "Know your limits and climb within them"
        ],
        "common_mistakes": [
            "Over-gripping holds",
            "Poor foot placement",
            "Not planning the route ahead",
            "Rushing through movements"
        ]
    },
    
    "bouldering": {
        "key_metrics": ["problem_solving", "power", "technique", "fall_recovery"],
        "technique_focus": ["dynamic_movement", "static_holds", "heel_hooks", "mantling"],
        "analysis_points": [
            "Problem reading and sequence planning",
            "Power-to-weight ratio utilization",
            "Technique precision on small holds",
            "Fall technique and safety"
        ],
        "safety_tips": [
            "Always have proper crash pad placement",
            "Practice safe falling techniques",
            "Warm up thoroughly before attempting hard problems",
            "Have a spotter when needed"
        ],
        "common_mistakes": [
            "Not reading the problem completely",
            "Improper fall technique",
            "Inadequate warm-up",
            "Rushing through sequences"
        ]
    },
    
    "skiing": {
        "key_metrics": ["balance", "edge_control", "turn_technique", "speed_control"],
        "technique_focus": ["parallel_turns", "carving", "mogul_technique", "powder_skiing"],
        "analysis_points": [
            "Weight distribution and balance",
            "Edge engagement and release",
            "Turn initiation and completion",
            "Stance and posture",
            "Rhythm and flow"
        ],
        "safety_tips": [
            "Always wear appropriate protective gear",
            "Check weather and snow conditions",
            "Stay within designated ski areas",
            "Maintain control of speed and direction"
        ],
        "common_mistakes": [
            "Leaning back instead of forward",
            "Not engaging edges properly",
            "Poor weight distribution",
            "Inconsistent turn rhythm"
        ]
    },
    
    "motocross": {
        "key_metrics": ["body_position", "throttle_control", "jumping_technique", "cornering"],
        "technique_focus": ["standing_position", "cornering", "jumping", "braking"],
        "analysis_points": [
            "Body positioning on the bike",
            "Throttle and brake control",
            "Jump takeoff and landing technique",
            "Cornering line selection",
            "Overall bike control"
        ],
        "safety_tips": [
            "Always wear full protective gear",
            "Inspect bike before riding",
            "Ride within skill level",
            "Be aware of track conditions and other riders"
        ],
        "common_mistakes": [
            "Poor body positioning",
            "Inconsistent throttle control",
            "Bad cornering lines",
            "Inadequate safety gear"
        ]
    },
    
    "mountainbike": {
        "key_metrics": ["bike_handling", "line_choice", "braking_technique", "climbing_efficiency"],
        "technique_focus": ["descending", "climbing", "technical_sections", "flow"],
        "analysis_points": [
            "Bike handling and control",
            "Line selection and planning",
            "Braking technique and timing",
            "Climbing efficiency and technique",
            "Overall flow and rhythm"
        ],
        "safety_tips": [
            "Always wear helmet and protective gear",
            "Check bike condition before riding",
            "Ride within your skill level",
            "Be aware of trail conditions and other users"
        ],
        "common_mistakes": [
            "Poor line selection",
            "Over-braking or wrong braking technique",
            "Inadequate body positioning",
            "Not maintaining momentum"
        ]
    }
}

# Analysis scoring weights for different sports
SPORT_SCORING_WEIGHTS: Dict[str, Dict[str, float]] = {
    "climbing": {
        "technique": 0.4,
        "strength": 0.3,
        "efficiency": 0.2,
        "safety": 0.1
    },
    "bouldering": {
        "technique": 0.3,
        "power": 0.4,
        "problem_solving": 0.2,
        "safety": 0.1
    },
    "skiing": {
        "technique": 0.4,
        "balance": 0.3,
        "control": 0.2,
        "safety": 0.1
    },
    "motocross": {
        "technique": 0.3,
        "control": 0.4,
        "speed": 0.2,
        "safety": 0.1
    },
    "mountainbike": {
        "technique": 0.35,
        "bike_handling": 0.35,
        "efficiency": 0.2,
        "safety": 0.1
    }
}

# Performance level descriptions
PERFORMANCE_LEVELS: Dict[str, Dict[str, str]] = {
    "beginner": {
        "description": "Learning basic techniques and building foundation",
        "score_range": "0.0 - 0.4",
        "focus_areas": ["Safety", "Basic technique", "Confidence building"]
    },
    "intermediate": {
        "description": "Developing consistent technique and expanding skills",
        "score_range": "0.4 - 0.7",
        "focus_areas": ["Technique refinement", "Consistency", "Skill expansion"]
    },
    "advanced": {
        "description": "Fine-tuning performance and tackling challenging terrain/routes",
        "score_range": "0.7 - 0.9",
        "focus_areas": ["Performance optimization", "Advanced techniques", "Mental game"]
    },
    "expert": {
        "description": "Mastery level with exceptional skill and technique",
        "score_range": "0.9 - 1.0",
        "focus_areas": ["Innovation", "Teaching others", "Pushing boundaries"]
    }
}

def get_sport_config(sport_type: str) -> Dict:
    """Get configuration for specific sport type"""
    return SPORT_CONFIGS.get(sport_type.lower(), {})

def get_sport_scoring_weights(sport_type: str) -> Dict[str, float]:
    """Get scoring weights for specific sport type"""
    return SPORT_SCORING_WEIGHTS.get(sport_type.lower(), {
        "technique": 0.4,
        "performance": 0.4,
        "safety": 0.2
    })

def get_performance_level(score: float) -> Dict[str, str]:
    """Get performance level based on score"""
    if score < 0.4:
        return PERFORMANCE_LEVELS["beginner"]
    elif score < 0.7:
        return PERFORMANCE_LEVELS["intermediate"]
    elif score < 0.9:
        return PERFORMANCE_LEVELS["advanced"]
    else:
        return PERFORMANCE_LEVELS["expert"]

def get_supported_sports() -> List[str]:
    """Get list of supported sports"""
    return list(SPORT_CONFIGS.keys())

def validate_sport_type(sport_type: str) -> bool:
    """Validate if sport type is supported"""
    return sport_type.lower() in SPORT_CONFIGS
