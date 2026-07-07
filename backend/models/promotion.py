"""
Rival Promotion Model (STEP 126)
Represents a competing promotion that can bid on free agents.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class PromotionTier(Enum):
    """Size/importance of the promotion"""
    MAJOR = "major"
    MID = "mid"
    INDEPENDENT = "independent"
    INTERNATIONAL = "international"


@dataclass
class RivalPromotion:
    """
    A competing wrestling promotion that can show interest in free agents.
    """
    promotion_id: str
    name: str
    tier: PromotionTier
    
    # Financials
    budget: int = 500000  # Available budget for signings
    salary_range: tuple = (5000, 20000)  # (min, max) per show
    
    # Brand identity - affects which wrestlers they're interested in
    preferred_styles: List[str] = field(default_factory=list)  # e.g., ["technical", "high_flying", "powerhouse"]
    preferred_alignments: List[str] = field(default_factory=list)  # Face/Heel/Tweener
    target_regions: List[str] = field(default_factory=list)  # domestic, japan, mexico, etc.
    
    # Current needs (calculated dynamically)
    need_for_main_event: int = 50  # 0-100 urgency
    need_for_midcard: int = 50
    need_for_tag_teams: int = 50
    need_for_women: int = 50
    
    # Relationship with player promotion (affects bidding)
    relationship: int = 50  # 0=hostile, 50=neutral, 100=friendly
    
    # Historical data
    signings_this_year: int = 0
    total_roster_size: int = 30  # approximate
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'promotion_id': self.promotion_id,
            'name': self.name,
            'tier': self.tier.value,
            'budget': self.budget,
            'salary_range': self.salary_range,
            'preferred_styles': self.preferred_styles,
            'preferred_alignments': self.preferred_alignments,
            'target_regions': self.target_regions,
            'need_for_main_event': self.need_for_main_event,
            'need_for_midcard': self.need_for_midcard,
            'need_for_tag_teams': self.need_for_tag_teams,
            'need_for_women': self.need_for_women,
            'relationship': self.relationship,
            'signings_this_year': self.signings_this_year,
            'total_roster_size': self.total_roster_size
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'RivalPromotion':
        return RivalPromotion(
            promotion_id=data['promotion_id'],
            name=data['name'],
            tier=PromotionTier(data['tier']),
            budget=data.get('budget', 500000),
            salary_range=tuple(data.get('salary_range', (5000,20000))),
            preferred_styles=data.get('preferred_styles', []),
            preferred_alignments=data.get('preferred_alignments', []),
            target_regions=data.get('target_regions', []),
            need_for_main_event=data.get('need_for_main_event', 50),
            need_for_midcard=data.get('need_for_midcard', 50),
            need_for_tag_teams=data.get('need_for_tag_teams', 50),
            need_for_women=data.get('need_for_women', 50),
            relationship=data.get('relationship', 50),
            signings_this_year=data.get('signings_this_year', 0),
            total_roster_size=data.get('total_roster_size', 30)
        )