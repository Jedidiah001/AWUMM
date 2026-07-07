"""
AI Director Reign Goal Awareness
Makes booking decisions consider wrestler reign goals.

STEP 30: Championship Reign Goals
"""

from typing import Dict, Any, Optional
from persistence.reign_goal_db import get_active_reign_goals, get_unfulfilled_title_promises


def should_extend_reign(db, wrestler_id: str, title_id: str, current_reign_days: int) -> Dict[str, Any]:
    """
    Determine if a reign should be extended based on goals.
    
    Returns:
        {
            'extend': bool,
            'reason': str,
            'recommended_additional_days': int,
            'urgency': int (0-100)
        }
    """
    goals = get_active_reign_goals(db, wrestler_id)
    
    if not goals:
        return {'extend': False, 'reason': 'No active goals', 'recommended_additional_days': 0, 'urgency': 0}
    
    # Filter goals for this title
    title_goals = [g for g in goals if g['title_id'] == title_id]
    
    if not title_goals:
        return {'extend': False, 'reason': 'No goals for this title', 'recommended_additional_days': 0, 'urgency': 0}
    
    # Check minimum days goals
    for goal in title_goals:
        if goal['goal_type'] == 'minimum_days':
            if current_reign_days < goal['target_value']:
                shortfall = goal['target_value'] - current_reign_days
                urgency = int((goal['importance'] / 100) * 100)
                
                return {
                    'extend': True,
                    'reason': f"Needs {shortfall} more days to meet minimum goal ({goal['target_value']} days)",
                    'recommended_additional_days': shortfall,
                    'urgency': urgency
                }
        
        elif goal['goal_type'] == 'historic_reign':
            if current_reign_days < goal['target_value']:
                shortfall = goal['target_value'] - current_reign_days
                urgency = int((goal['importance'] / 100) * 100)
                
                return {
                    'extend': True,
                    'reason': f"Pursuing record-breaking reign ({goal['target_value']} days)",
                    'recommended_additional_days': shortfall,
                    'urgency': urgency
                }
    
    return {'extend': False, 'reason': 'Goals on track', 'recommended_additional_days': 0, 'urgency': 0}


def get_ideal_title_loss_timing(db, wrestler_id: str, title_id: str, current_reign_days: int) -> Dict[str, Any]:
    """
    Determine the ideal time for a champion to lose their title based on goals.
    
    Returns:
        {
            'ready_to_lose': bool,
            'ideal_loss_show': str (PPV name or None),
            'minimum_additional_days': int,
            'reasons': list[str]
        }
    """
    goals = get_active_reign_goals(db, wrestler_id)
    title_goals = [g for g in goals if g['title_id'] == title_id]
    
    if not title_goals:
        return {
            'ready_to_lose': True,
            'ideal_loss_show': None,
            'minimum_additional_days': 0,
            'reasons': ['No active goals']
        }
    
    ready = True
    ideal_show = None
    min_days = 0
    reasons = []
    
    for goal in title_goals:
        if goal['goal_type'] == 'minimum_days':
            if current_reign_days < goal['target_value']:
                ready = False
                needed = goal['target_value'] - current_reign_days
                min_days = max(min_days, needed)
                reasons.append(f"Needs {needed} more days to reach {goal['target_value']} day goal")
        
        elif goal['goal_type'] == 'storyline_completion':
            if goal.get('must_end_at_show'):
                ideal_show = goal['must_end_at_show']
                reasons.append(f"Storyline calls for loss at {ideal_show}")
        
        elif goal['goal_type'] == 'minimum_defenses':
            # Would need to query defense count
            reasons.append(f"Needs {goal['target_value']} total defenses")
    
    if ready and not reasons:
        reasons.append('All goals met, ready for transition')
    
    return {
        'ready_to_lose': ready,
        'ideal_loss_show': ideal_show,
        'minimum_additional_days': min_days,
        'reasons': reasons
    }


def get_wrestlers_owed_title_shots(db) -> list[Dict[str, Any]]:
    """
    Get all wrestlers with unfulfilled title promises.
    Useful for AI Director to prioritize title matches.
    """
    promises = get_unfulfilled_title_promises(db)
    
    wrestlers_owed = []
    for promise in promises:
        wrestlers_owed.append({
            'wrestler_id': promise['wrestler_id'],
            'wrestler_name': promise['wrestler_name'],
            'title_id': promise.get('title_id'),
            'title_tier': promise.get('title_tier'),
            'promised_days': promise['promised_min_days'],
            'promised_defenses': promise['promised_min_defenses'],
            'promise_age_weeks': promise.get('weeks_since_promise', 0),
            'urgency': 'high' if promise.get('weeks_remaining', 999) <= 8 else 'normal'
        })
    
    return wrestlers_owed


def adjust_booking_bias_for_reign_goals(
    db,
    champion_id: str,
    title_id: str,
    current_reign_days: int,
    base_bias: str
) -> str:
    """
    Adjust booking bias based on reign goals.
    
    If champion is close to meeting important goals, increase their win probability.
    
    Args:
        base_bias: Original bias ('Strong Champion', 'Slight Champion', etc.)
    
    Returns:
        Adjusted bias string
    """
    extension_check = should_extend_reign(db, champion_id, title_id, current_reign_days)
    
    if extension_check['extend'] and extension_check['urgency'] >= 70:
        # High urgency to keep title
        if base_bias == 'Even':
            return 'Slight Champion'
        elif base_bias == 'Slight Champion':
            return 'Strong Champion'
        else:
            return base_bias  # Already favors champion
    
    return base_bias