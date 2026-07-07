"""
Milestone Checker
Checks for and records wrestler milestones after shows.
"""

from typing import List, Dict, Any


def check_milestones_for_show(show_result, universe_state, database):
    """
    Check for milestones achieved during a show.
    Called after all matches are simulated.
    
    Args:
        show_result: The ShowResult object with all match results
        universe_state: Current universe state
        database: Database object for recording milestones
    """
    
    # Collect all wrestlers who competed
    all_wrestler_ids = set()
    
    for match_result in show_result.match_results:
        all_wrestler_ids.update(match_result.side_a.wrestler_ids)
        all_wrestler_ids.update(match_result.side_b.wrestler_ids)
    
    # Check milestones for each wrestler
    for wrestler_id in all_wrestler_ids:
        wrestler = universe_state.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            continue
        
        # Get current stats
        stats = database.get_wrestler_stats(wrestler_id)
        
        if not stats:
            # First match - will be recorded by stats_tracker
            continue
        
        # Check for specific milestones that might have been achieved
        # Most milestone checking is done in stats_tracker._check_milestones()
        # This function is for any show-level milestone checks
        
        pass  # Additional show-level checks can be added here


def check_career_milestones(wrestler_id: str, wrestler_name: str, database) -> List[Dict[str, Any]]:
    """
    Check if a wrestler has achieved any career milestones.
    Returns list of newly achieved milestones.
    
    This is called periodically to check for milestones that
    might have been missed or need recalculation.
    """
    
    milestones = []
    
    # Get current stats
    stats = database.calculate_wrestler_stats(wrestler_id)
    
    if not stats:
        return milestones
    
    # Get existing milestones
    existing = database.get_wrestler_milestones(wrestler_id)
    existing_types = {m['milestone_type'] for m in existing}
    
    # Check match milestones
    match_thresholds = [
        (10, '10_matches', 'Competed in 10 matches'),
        (25, '25_matches', 'Competed in 25 matches'),
        (50, '50_matches', 'Competed in 50 matches'),
        (100, '100_matches', 'Competed in 100 matches'),
        (250, '250_matches', 'Competed in 250 matches'),
        (500, '500_matches', 'Competed in 500 matches'),
        (1000, '1000_matches', 'Competed in 1000 matches'),
    ]
    
    total_matches = stats['record']['total_matches']
    
    for threshold, milestone_type, description in match_thresholds:
        if total_matches >= threshold and milestone_type not in existing_types:
            milestones.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler_name,
                'milestone_type': milestone_type,
                'description': description
            })
    
    # Check win milestones
    win_thresholds = [
        (10, '10_wins', 'Won 10 matches'),
        (25, '25_wins', 'Won 25 matches'),
        (50, '50_wins', 'Won 50 matches'),
        (100, '100_wins', 'Won 100 matches'),
        (250, '250_wins', 'Won 250 matches'),
        (500, '500_wins', 'Won 500 matches'),
    ]
    
    wins = stats['record']['wins']
    
    for threshold, milestone_type, description in win_thresholds:
        if wins >= threshold and milestone_type not in existing_types:
            milestones.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler_name,
                'milestone_type': milestone_type,
                'description': description
            })
    
    # Check title milestones
    title_thresholds = [
        (1, 'first_title', 'Won their first championship'),
        (5, '5_title_reigns', 'Won 5 championship reigns'),
        (10, '10_title_reigns', 'Won 10 championship reigns'),
    ]
    
    title_reigns = stats['title_history']['total_reigns']
    
    for threshold, milestone_type, description in title_thresholds:
        if title_reigns >= threshold and milestone_type not in existing_types:
            milestones.append({
                'wrestler_id': wrestler_id,
                'wrestler_name': wrestler_name,
                'milestone_type': milestone_type,
                'description': description
            })
    
    # Check 5-star match milestone
    five_star = stats['match_quality']['five_star_matches']
    if five_star >= 1 and 'first_5_star' not in existing_types:
        milestones.append({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler_name,
            'milestone_type': 'first_5_star',
            'description': 'Had their first 5-star match'
        })
    
    return milestones