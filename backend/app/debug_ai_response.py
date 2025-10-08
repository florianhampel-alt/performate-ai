# Global storage for last AI response debugging
_last_ai_responses = []
_max_responses = 5  # Keep last 5 responses

def store_ai_response(frame_num: int, analysis_text: str, parsing_result: dict):
    """Store AI response for debugging"""
    global _last_ai_responses
    
    response_data = {
        'frame_num': frame_num,
        'timestamp': str(__import__('datetime').datetime.now()),
        'response_text': analysis_text,
        'response_length': len(analysis_text),
        'enhanced_markers': {
            'routenidentifikation': '## Routenidentifikation' in analysis_text,
            'positive_aspekte': '## Positive' in analysis_text,
            'konkrete_tipps': '## Konkrete Tipps' in analysis_text,
            'farbe': '**Farbe:**' in analysis_text,
            'level': '**Level:**' in analysis_text,
            'checkmarks': '✅' in analysis_text,
            'lightbulb': '💡' in analysis_text
        },
        'parsing_success': parsing_result.get('enhanced_format', False),
        'parsed_level': parsing_result.get('climber_level', 'unknown'),
        'parsed_aspects_count': len(parsing_result.get('positive_aspects', []))
    }
    
    _last_ai_responses.append(response_data)
    
    # Keep only last N responses
    if len(_last_ai_responses) > _max_responses:
        _last_ai_responses = _last_ai_responses[-_max_responses:]

def get_last_ai_responses():
    """Get stored AI responses for debugging"""
    return _last_ai_responses