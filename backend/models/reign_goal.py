"""
Reign Goal Model
Tracks wrestler expectations and satisfaction regarding championship reigns.

STEP 30: Championship Reign Goals
Wrestlers have preferences about their title reigns affecting morale and contract negotiations.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ReignGoalType(Enum):
    """Types of reign goals wrestlers can have"""
    MINIMUM_DAYS = "minimum_days"  # Want at least X days
    MINIMUM_DEFENSES = "minimum_defenses"  # Want at least X defenses
    HISTORIC_REIGN = "historic_reign"  # Want to break records
    TRANSITIONAL = "transitional"  # Accept short reign for push
    STORYLINE_COMPLETION = "storyline_completion"  # Reign must end at specific event
    QUALITY_DEFENSES = "quality_defenses"  # Want high-rated matches
    CLEAN_LOSS = "clean_loss"  # Want to lose title with dignity


@dataclass
class ReignGoal:
    """
    Represents a wrestler's goals/expectations for a championship reign.
    
    Created when:
    - Wrestler wins a title
    - Contract negotiation includes title promises
    - Storyline requires specific reign parameters
    """
    
    goal_type: ReignGoalType
    target_value: int  # Days, defenses, or rating threshold
    importance: int  # 0-100, how much this matters to the wrestler
    
    # Optional constraints
    must_end_at_show: Optional[str] = None  # Specific PPV name
    must_end_by_week: Optional[int] = None  # Deadline
    minimum_match_rating: float = 3.0  # Minimum avg star rating
    
    # Satisfaction tracking
    is_met: bool = False
    satisfaction_bonus: int = 0  # Morale bonus if met
    satisfaction_penalty: int = 0  # Morale penalty if not met
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'goal_type': self.goal_type.value,
            'target_value': self.target_value,
            'importance': self.importance,
            'must_end_at_show': self.must_end_at_show,
            'must_end_by_week': self.must_end_by_week,
            'minimum_match_rating': self.minimum_match_rating,
            'is_met': self.is_met,
            'satisfaction_bonus': self.satisfaction_bonus,
            'satisfaction_penalty': self.satisfaction_penalty
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ReignGoal':
        return ReignGoal(
            goal_type=ReignGoalType(data['goal_type']),
            target_value=data['target_value'],
            importance=data['importance'],
            must_end_at_show=data.get('must_end_at_show'),
            must_end_by_week=data.get('must_end_by_week'),
            minimum_match_rating=data.get('minimum_match_rating', 3.0),
            is_met=data.get('is_met', False),
            satisfaction_bonus=data.get('satisfaction_bonus', 0),
            satisfaction_penalty=data.get('satisfaction_penalty', 0)
        )


class ReignGoalPreset:
    """
    Pre-defined reign goal templates based on wrestler role and circumstances.
    """
    
    @staticmethod
    def get_default_goals_for_role(role: str, title_tier: str) -> list[ReignGoal]:
        """
        Generate default reign goals based on wrestler's role and title importance.
        
        Args:
            role: 'Main Event', 'Upper Midcard', etc.
            title_tier: 'World', 'Secondary', 'Midcard', etc.
        
        Returns:
            List of ReignGoal objects
        """
        goals = []
        
        if role == 'Main Event':
            if title_tier == 'World':
                # Main eventers want long, prestigious world title reigns
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.MINIMUM_DAYS,
                    target_value=90,  # 3+ months
                    importance=80,
                    satisfaction_bonus=20,
                    satisfaction_penalty=-25
                ))
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.MINIMUM_DEFENSES,
                    target_value=5,
                    importance=70,
                    satisfaction_bonus=15,
                    satisfaction_penalty=-20
                ))
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.QUALITY_DEFENSES,
                    target_value=4,  # 4.0 avg star rating
                    importance=60,
                    minimum_match_rating=4.0,
                    satisfaction_bonus=10,
                    satisfaction_penalty=-10
                ))
            
            elif title_tier in ['Secondary', 'Midcard']:
                # Main eventers see midcard titles as transitional
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.TRANSITIONAL,
                    target_value=30,  # 1 month minimum
                    importance=40,
                    satisfaction_bonus=5,
                    satisfaction_penalty=-10
                ))
        
        elif role == 'Upper Midcard':
            if title_tier == 'World':
                # Upper midcarders treasure world title reigns
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.MINIMUM_DAYS,
                    target_value=60,  # 2 months
                    importance=90,
                    satisfaction_bonus=25,
                    satisfaction_penalty=-30
                ))
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.MINIMUM_DEFENSES,
                    target_value=3,
                    importance=80,
                    satisfaction_bonus=20,
                    satisfaction_penalty=-25
                ))
            
            elif title_tier == 'Secondary':
                # Perfect tier for upper midcarders
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.MINIMUM_DAYS,
                    target_value=45,
                    importance=70,
                    satisfaction_bonus=15,
                    satisfaction_penalty=-20
                ))
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.MINIMUM_DEFENSES,
                    target_value=3,
                    importance=60,
                    satisfaction_bonus=12,
                    satisfaction_penalty=-15
                ))
        
        elif role == 'Midcard':
            if title_tier in ['Midcard', 'Secondary']:
                # Midcarders want respectable reigns
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.MINIMUM_DAYS,
                    target_value=30,
                    importance=60,
                    satisfaction_bonus=12,
                    satisfaction_penalty=-15
                ))
                goals.append(ReignGoal(
                    goal_type=ReignGoalType.MINIMUM_DEFENSES,
                    target_value=2,
                    importance=50,
                    satisfaction_bonus=10,
                    satisfaction_penalty=-12
                ))
        
        elif role in ['Lower Midcard', 'Jobber']:
            # Lower card wrestlers are grateful for any title reign
            goals.append(ReignGoal(
                goal_type=ReignGoalType.MINIMUM_DAYS,
                target_value=14,  # 2 weeks
                importance=40,
                satisfaction_bonus=15,
                satisfaction_penalty=-10
            ))
        
        # All champions want clean losses (unless heel)
        goals.append(ReignGoal(
            goal_type=ReignGoalType.CLEAN_LOSS,
            target_value=1,  # Boolean: 1 = clean, 0 = dirty
            importance=50,
            satisfaction_bonus=8,
            satisfaction_penalty=-12
        ))
        
        return goals
    
    @staticmethod
    def create_promised_reign(days: int, defenses: int, importance: int = 80) -> list[ReignGoal]:
        """
        Create reign goals based on contract promises.
        
        Used when player or AI promises a wrestler a specific type of title run.
        """
        return [
            ReignGoal(
                goal_type=ReignGoalType.MINIMUM_DAYS,
                target_value=days,
                importance=importance,
                satisfaction_bonus=20,
                satisfaction_penalty=-25
            ),
            ReignGoal(
                goal_type=ReignGoalType.MINIMUM_DEFENSES,
                target_value=defenses,
                importance=importance - 10,
                satisfaction_bonus=15,
                satisfaction_penalty=-20
            )
        ]
    
    @staticmethod
    def create_record_breaking_reign(current_record_days: int) -> ReignGoal:
        """Create goal to break the existing title reign record."""
        return ReignGoal(
            goal_type=ReignGoalType.HISTORIC_REIGN,
            target_value=current_record_days + 1,
            importance=95,
            satisfaction_bonus=30,
            satisfaction_penalty=-35
        )
    
    @staticmethod
    def create_storyline_reign(end_show: str, end_week: int) -> ReignGoal:
        """Create goal for storyline-mandated reign ending."""
        return ReignGoal(
            goal_type=ReignGoalType.STORYLINE_COMPLETION,
            target_value=end_week,
            importance=75,
            must_end_at_show=end_show,
            must_end_by_week=end_week,
            satisfaction_bonus=18,
            satisfaction_penalty=-22
        )


def calculate_reign_satisfaction(
    reign_data: Dict[str, Any],
    goals: list[ReignGoal],
    wrestler_role: str
) -> Dict[str, Any]:
    """
    Calculate how satisfied a wrestler is with their completed championship reign.
    
    Args:
        reign_data: Dict with keys:
            - days_held: int
            - successful_defenses: int
            - avg_star_rating: float
            - loss_type: str ('clean', 'dirty', 'screwjob', etc.)
            - end_show_name: str
            - end_week: int
        goals: List of ReignGoal objects
        wrestler_role: Current role of wrestler
    
    Returns:
        Dict with:
            - total_satisfaction: int (-100 to +100)
            - morale_change: int
            - goals_met: int
            - goals_failed: int
            - satisfaction_breakdown: dict
    """
    total_satisfaction = 0
    morale_change = 0
    goals_met = 0
    goals_failed = 0
    breakdown = {}
    
    for goal in goals:
        goal_satisfied = False
        contribution = 0
        
        if goal.goal_type == ReignGoalType.MINIMUM_DAYS:
            if reign_data['days_held'] >= goal.target_value:
                goal_satisfied = True
                contribution = goal.satisfaction_bonus
            else:
                # Penalty scales with how far they missed
                shortfall = (goal.target_value - reign_data['days_held']) / goal.target_value
                contribution = int(goal.satisfaction_penalty * shortfall)
        
        elif goal.goal_type == ReignGoalType.MINIMUM_DEFENSES:
            if reign_data['successful_defenses'] >= goal.target_value:
                goal_satisfied = True
                contribution = goal.satisfaction_bonus
            else:
                shortfall = (goal.target_value - reign_data['successful_defenses']) / max(goal.target_value, 1)
                contribution = int(goal.satisfaction_penalty * shortfall)
        
        elif goal.goal_type == ReignGoalType.QUALITY_DEFENSES:
            if reign_data.get('avg_star_rating', 0) >= goal.minimum_match_rating:
                goal_satisfied = True
                contribution = goal.satisfaction_bonus
            else:
                contribution = int(goal.satisfaction_penalty * 0.5)  # Half penalty for quality
        
        elif goal.goal_type == ReignGoalType.CLEAN_LOSS:
            if reign_data.get('loss_type') == 'clean':
                goal_satisfied = True
                contribution = goal.satisfaction_bonus
            elif reign_data.get('loss_type') == 'screwjob':
                contribution = goal.satisfaction_penalty * 2  # Screwjobs hurt more
            else:
                contribution = goal.satisfaction_penalty
        
        elif goal.goal_type == ReignGoalType.HISTORIC_REIGN:
            if reign_data['days_held'] >= goal.target_value:
                goal_satisfied = True
                contribution = goal.satisfaction_bonus
            else:
                contribution = goal.satisfaction_penalty
        
        elif goal.goal_type == ReignGoalType.STORYLINE_COMPLETION:
            if (reign_data.get('end_show_name') == goal.must_end_at_show and
                reign_data.get('end_week') == goal.must_end_by_week):
                goal_satisfied = True
                contribution = goal.satisfaction_bonus
            else:
                contribution = goal.satisfaction_penalty
        
        elif goal.goal_type == ReignGoalType.TRANSITIONAL:
            # Transitional champions are happy with short reigns
            if reign_data['days_held'] >= goal.target_value:
                goal_satisfied = True
                contribution = goal.satisfaction_bonus
            else:
                contribution = int(goal.satisfaction_penalty * 0.5)  # Less penalty
        
        # Weight by importance
        weighted_contribution = int(contribution * (goal.importance / 100))
        total_satisfaction += weighted_contribution
        
        breakdown[goal.goal_type.value] = {
            'met': goal_satisfied,
            'contribution': weighted_contribution
        }
        
        if goal_satisfied:
            goals_met += 1
        else:
            goals_failed += 1
        
        goal.is_met = goal_satisfied
    
    # Overall morale change (clamped)
    morale_change = max(-50, min(50, total_satisfaction))
    
    # Bonus for exceeding expectations
    if reign_data['days_held'] > 120 and wrestler_role in ['Main Event', 'Upper Midcard']:
        morale_change += 10
        breakdown['long_reign_bonus'] = {'met': True, 'contribution': 10}
    
    # Penalty for very short reigns (unless transitional)
    if reign_data['days_held'] < 7 and wrestler_role in ['Main Event', 'Upper Midcard']:
        has_transitional = any(g.goal_type == ReignGoalType.TRANSITIONAL for g in goals)
        if not has_transitional:
            morale_change -= 15
            breakdown['too_short_penalty'] = {'met': False, 'contribution': -15}
    
    return {
        'total_satisfaction': total_satisfaction,
        'morale_change': morale_change,
        'goals_met': goals_met,
        'goals_failed': goals_failed,
        'satisfaction_breakdown': breakdown
    }