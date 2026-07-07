"""
Milestone Detection System
Checks for career milestones after each show.
"""

from typing import List, Tuple
from models.show import ShowResult
from models.stats import MilestoneType
from persistence.database import Database


def check_milestones_for_show(show_result: ShowResult, universe_state, database: Database):
    """
    Check all wrestlers who appeared on a show for milestone achievements.
    Called automatically after show simulation.
    """
    
    # Get all wrestlers who appeared
    wrestler_ids = set()
    
    # From matches
    for match_result in show_result.match_results:
        wrestler_ids.update(match_result.side_a.wrestler_ids)
        wrestler_ids.update(match_result.side_b.wrestler_ids)
    
    # From segments
    for segment_result in show_result.segment_results:
        for participant in segment_result.participants:
            if isinstance(participant, dict):
                wrestler_id = participant.get('wrestler_id')
            else:
                wrestler_id = getattr(participant, 'wrestler_id', None)
            
            if wrestler_id and wrestler_id not in ['interviewer', 'authority']:
                wrestler_ids.add(wrestler_id)
    
    # Check each wrestler for milestones
    milestones_found = []
    
    for wrestler_id in wrestler_ids:
        # Get updated stats
        stats_dict = database.calculate_wrestler_stats(wrestler_id)
        
        if not stats_dict:
            continue
        
        # Check for specific milestones based on the stats
        milestones = check_wrestler_milestones(
            wrestler_id=wrestler_id,
            stats_dict=stats_dict,
            show_result=show_result,
            database=database
        )
        
        milestones_found.extend(milestones)
    
    # Check for match-specific milestones (5-star matches)
    for match_result in show_result.match_results:
        if match_result.star_rating >= 5.0:
            # All participants get the 5-star milestone
            all_participants = match_result.side_a.wrestler_ids + match_result.side_b.wrestler_ids
            
            for wrestler_id in all_participants:
                wrestler = universe_state.get_wrestler_by_id(wrestler_id)
                if wrestler:
                    database.record_milestone(
                        wrestler_id=wrestler_id,
                        wrestler_name=wrestler.name,
                        milestone_type=MilestoneType.FIVE_STAR_MATCH,
                        description=f"{wrestler.name} competed in a 5-star classic!",
                        show_id=show_result.show_id,
                        show_name=show_result.show_name,
                        year=show_result.year,
                        week=show_result.week
                    )
                    
                    milestones_found.append((
                        wrestler.name,
                        MilestoneType.FIVE_STAR_MATCH,
                        "5-star match!"
                    ))
    
    # Add milestone events to show result
    for wrestler_name, milestone_type, description in milestones_found:
        show_result.add_event(
            'milestone',
            f"🏆 MILESTONE: {wrestler_name} - {description}"
        )
    
    return milestones_found


def check_wrestler_milestones(
    wrestler_id: str,
    stats_dict: dict,
    show_result: ShowResult,
    database: Database
) -> List[Tuple[str, str, str]]:
    """
    Check if a wrestler has achieved any milestones based on their stats.
    Returns list of (wrestler_name, milestone_type, description) tuples.
    """
    
    milestones = []
    wrestler_name = stats_dict['wrestler_name']
    
    # Get existing milestones to avoid duplicates
    existing_milestones = database.get_wrestler_milestones(wrestler_id)
    existing_types = {m['milestone_type'] for m in existing_milestones}
    
    # Match count milestones
    total_matches = stats_dict['record']['total_matches']
    
    if total_matches == 1 and MilestoneType.DEBUT not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.DEBUT,
            description=f"{wrestler_name} made their in-ring debut!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.DEBUT, "In-ring debut!"))
    
    elif total_matches == 100 and MilestoneType.MATCH_100 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.MATCH_100,
            description=f"{wrestler_name} competed in their 100th match!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.MATCH_100, "100th match!"))
    
    elif total_matches == 250 and MilestoneType.MATCH_250 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.MATCH_250,
            description=f"{wrestler_name} competed in their 250th match!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.MATCH_250, "250th match!"))
    
    elif total_matches == 500 and MilestoneType.MATCH_500 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.MATCH_500,
            description=f"{wrestler_name} competed in their 500th match!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.MATCH_500, "500th match!"))
    
    # Win milestones
    wins = stats_dict['record']['wins']
    
    if wins == 1 and MilestoneType.FIRST_WIN not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.FIRST_WIN,
            description=f"{wrestler_name} earned their first victory!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.FIRST_WIN, "First victory!"))
    
    elif wins == 100 and MilestoneType.WIN_100 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.WIN_100,
            description=f"{wrestler_name} earned their 100th victory!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.WIN_100, "100th victory!"))
    
    elif wins == 250 and MilestoneType.WIN_250 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.WIN_250,
            description=f"{wrestler_name} earned their 250th victory!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.WIN_250, "250th victory!"))
    
    # Streak milestones
    current_win_streak = stats_dict['streaks']['current_win_streak']
    
    if current_win_streak == 10 and MilestoneType.STREAK_10 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.STREAK_10,
            description=f"{wrestler_name} is on a 10-match winning streak!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.STREAK_10, "10-match winning streak!"))
    
    elif current_win_streak == 25 and MilestoneType.STREAK_25 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.STREAK_25,
            description=f"{wrestler_name} is on an incredible 25-match winning streak!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.STREAK_25, "25-match winning streak!"))
    
    # Title milestones
    total_reigns = stats_dict['title_history']['total_reigns']
    
    if total_reigns == 1 and stats_dict['title_history'].get('current_reign_days', 0) > 0:
        if MilestoneType.FIRST_TITLE not in existing_types:
            database.record_milestone(
                wrestler_id=wrestler_id,
                wrestler_name=wrestler_name,
                milestone_type=MilestoneType.FIRST_TITLE,
                description=f"{wrestler_name} won their first championship!",
                show_id=show_result.show_id,
                show_name=show_result.show_name,
                year=show_result.year,
                week=show_result.week
            )
            milestones.append((wrestler_name, MilestoneType.FIRST_TITLE, "First championship!"))
    
    # Main event milestones
    main_events = stats_dict['achievements']['main_events']
    
    if main_events == 50 and MilestoneType.MAIN_EVENT_50 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.MAIN_EVENT_50,
            description=f"{wrestler_name} has main evented 50 shows!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.MAIN_EVENT_50, "50 main events!"))
    
    # PPV milestones
    ppv_matches = stats_dict['achievements']['ppv_matches']
    
    if ppv_matches == 50 and MilestoneType.PPV_50 not in existing_types:
        database.record_milestone(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            milestone_type=MilestoneType.PPV_50,
            description=f"{wrestler_name} has competed in 50 PPV matches!",
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week
        )
        milestones.append((wrestler_name, MilestoneType.PPV_50, "50 PPV matches!"))
    
    return milestones


def check_retirement_milestone(wrestler_id: str, wrestler_name: str, show_result: ShowResult, database: Database):
    """
    Record retirement milestone when a wrestler retires.
    Called from aging system when retirement occurs.
    """
    database.record_milestone(
        wrestler_id=wrestler_id,
        wrestler_name=wrestler_name,
        milestone_type=MilestoneType.RETIREMENT,
        description=f"{wrestler_name} has retired from in-ring competition!",
        show_id=show_result.show_id,
        show_name=show_result.show_name,
        year=show_result.year,
        week=show_result.week
    )