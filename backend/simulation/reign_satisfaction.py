"""
Reign Satisfaction Calculator
Evaluates wrestler satisfaction when championship reigns end.

STEP 30: Championship Reign Goals
"""

from typing import Dict, Any, List
from models.reign_goal import ReignGoal, ReignGoalPreset, calculate_reign_satisfaction
from persistence.reign_goal_db import (
    save_reign_goals, get_reign_goals, save_reign_satisfaction,
    get_unfulfilled_title_promises, fulfill_title_promise
)


def create_reign_goals_on_title_win(
    db,
    wrestler,
    championship,
    year: int,
    week: int,
    contract_promises: List[Dict[str, Any]] = None
) -> List[ReignGoal]:
    """
    Create reign goals when a wrestler wins a championship.
    
    Args:
        db: Database instance
        wrestler: Wrestler object
        championship: Championship object
        year: Current year
        week: Current week
        contract_promises: Optional list of promises from contract
    
    Returns:
        List of ReignGoal objects
    """
    goals = []
    
    # Check for unfulfilled contract promises
    promises = get_unfulfilled_title_promises(db, wrestler.id)
    matching_promise = None
    
    for promise in promises:
        # Match if specific title or title tier matches
        if (promise.get('title_id') == championship.id or 
            promise.get('title_tier') == championship.title_type):
            matching_promise = promise
            break
    
    if matching_promise:
        # Create goals based on contract promise
        goals = ReignGoalPreset.create_promised_reign(
            days=matching_promise['promised_min_days'],
            defenses=matching_promise['promised_min_defenses'],
            importance=85  # High importance for contract promises
        )
        
        # Fulfill the promise
        fulfill_title_promise(db, matching_promise['id'], year, week)
        
        print(f"📋 {wrestler.name} has contract promise for {championship.name}: "
              f"{matching_promise['promised_min_days']} days, {matching_promise['promised_min_defenses']} defenses")
    
    else:
        # Generate default goals based on role and title tier
        default_goals = ReignGoalPreset.get_default_goals_for_role(
            role=wrestler.role,
            title_tier=championship.title_type
        )
        goals.extend(default_goals)
    
    # Check if wrestler wants to break records
    if wrestler.is_major_superstar and championship.title_type == 'World':
        # Get longest reign for this title
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT MAX(days_held) as longest
            FROM title_reigns
            WHERE title_id = ?
        ''', (championship.id,))
        
        result = cursor.fetchone()
        if result and result['longest']:
            longest_reign = result['longest']
            
            # Major stars want to break records
            if longest_reign > 60:  # Only if there's a meaningful record
                record_goal = ReignGoalPreset.create_record_breaking_reign(longest_reign)
                goals.append(record_goal)
                print(f"🎯 {wrestler.name} wants to break {championship.name} record ({longest_reign} days)")
    
    # Save goals to database
    save_reign_goals(db, wrestler.id, championship.id, year, week, goals)
    
    return goals


def evaluate_reign_satisfaction_on_title_loss(
    db,
    former_champion,
    championship,
    reign_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate reign satisfaction when a wrestler loses a championship.
    
    Args:
        db: Database instance
        former_champion: Wrestler object who lost title
        championship: Championship object
        reign_data: Dict containing:
            - reign_start_year: int
            - reign_start_week: int
            - reign_end_year: int
            - reign_end_week: int
            - days_held: int
            - successful_defenses: int
            - avg_star_rating: float
            - loss_type: str ('clean', 'dirty', 'screwjob', etc.)
            - end_show_name: str
    
    Returns:
        Satisfaction result dict
    """
    # Get reign goals for this championship run
    goals = get_reign_goals(
        db,
        former_champion.id,
        championship.id,
        reign_data['reign_start_year'],
        reign_data['reign_start_week']
    )
    
    if not goals:
        # No goals set - create default ones retroactively
        goals = ReignGoalPreset.get_default_goals_for_role(
            role=former_champion.role,
            title_tier=championship.title_type
        )
        print(f"⚠️ No reign goals found for {former_champion.name}, using defaults")
    
    # Calculate satisfaction
    satisfaction = calculate_reign_satisfaction(
        reign_data=reign_data,
        goals=goals,
        wrestler_role=former_champion.role
    )
    
    # Apply morale change to wrestler
    former_champion.adjust_morale(satisfaction['morale_change'])
    
    # Save satisfaction history
    satisfaction_record = {
        'wrestler_id': former_champion.id,
        'wrestler_name': former_champion.name,
        'title_id': championship.id,
        'title_name': championship.name,
        'reign_start_year': reign_data['reign_start_year'],
        'reign_start_week': reign_data['reign_start_week'],
        'reign_end_year': reign_data['reign_end_year'],
        'reign_end_week': reign_data['reign_end_week'],
        'days_held': reign_data['days_held'],
        'successful_defenses': reign_data.get('successful_defenses', 0),
        'avg_star_rating': reign_data.get('avg_star_rating', 0),
        'loss_type': reign_data.get('loss_type', 'clean'),
        'total_satisfaction': satisfaction['total_satisfaction'],
        'morale_change': satisfaction['morale_change'],
        'goals_met': satisfaction['goals_met'],
        'goals_failed': satisfaction['goals_failed'],
        'satisfaction_breakdown': satisfaction['satisfaction_breakdown']
    }
    
    save_reign_satisfaction(db, satisfaction_record)
    
    # Log result
    if satisfaction['morale_change'] > 0:
        print(f"😊 {former_champion.name} is satisfied with {championship.name} reign "
              f"({reign_data['days_held']} days, {satisfaction['goals_met']}/{len(goals)} goals met) "
              f"[Morale: {satisfaction['morale_change']:+d}]")
    elif satisfaction['morale_change'] < 0:
        print(f"😠 {former_champion.name} is unhappy with {championship.name} reign "
              f"({reign_data['days_held']} days, {satisfaction['goals_failed']}/{len(goals)} goals failed) "
              f"[Morale: {satisfaction['morale_change']:+d}]")
    else:
        print(f"😐 {former_champion.name} is neutral about {championship.name} reign")
    
    return satisfaction