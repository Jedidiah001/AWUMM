"""
Awards Models
End-of-year award categories and winners.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class AwardCategory(Enum):
    """Award categories for end-of-year ceremony"""
    # Wrestler Awards
    WRESTLER_OF_THE_YEAR = "wrestler_of_the_year"
    BREAKOUT_STAR = "breakout_star"
    MOST_IMPROVED = "most_improved"
    COMEBACK_OF_THE_YEAR = "comeback_of_the_year"
    
    # Match Awards
    MATCH_OF_THE_YEAR = "match_of_the_year"
    FEUD_OF_THE_YEAR = "feud_of_the_year"
    MOMENT_OF_THE_YEAR = "moment_of_the_year"
    
    # Championship Awards
    CHAMPION_OF_THE_YEAR = "champion_of_the_year"
    TITLE_REIGN_OF_THE_YEAR = "title_reign_of_the_year"
    
    # Tag Team Awards
    TAG_TEAM_OF_THE_YEAR = "tag_team_of_the_year"
    TAG_MATCH_OF_THE_YEAR = "tag_match_of_the_year"
    
    # Performance Awards
    BEST_TECHNICAL_WRESTLER = "best_technical_wrestler"
    BEST_HIGH_FLYER = "best_high_flyer"
    BEST_BRAWLER = "best_brawler"
    
    # Microphone Awards
    PROMO_OF_THE_YEAR = "promo_of_the_year"
    BEST_ON_THE_MIC = "best_on_the_mic"
    
    # Negative Awards
    BIGGEST_DISAPPOINTMENT = "biggest_disappointment"
    WORST_FEUD = "worst_feud"
    
    # Special Awards
    BEST_BRAND = "best_brand"
    SHOW_OF_THE_YEAR = "show_of_the_year"


@dataclass
class AwardNominee:
    """A nominee for an award"""
    nominee_id: str
    nominee_name: str
    nominee_type: str  # 'wrestler', 'match', 'show', 'feud', 'tag_team'
    stats: Dict[str, Any]
    reason: str
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'nominee_id': self.nominee_id,
            'nominee_name': self.nominee_name,
            'nominee_type': self.nominee_type,
            'stats': self.stats,
            'reason': self.reason,
            'score': round(self.score, 2)
        }


@dataclass
class Award:
    """An award with nominees and winner"""
    category: AwardCategory
    year: int
    nominees: List[AwardNominee]
    winner_id: str
    winner_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'category': self.category.value,
            'category_display': self._get_display_name(),
            'year': self.year,
            'nominees': [n.to_dict() for n in self.nominees],
            'winner_id': self.winner_id,
            'winner_name': self.winner_name
        }
    
    def _get_display_name(self) -> str:
        """Convert enum to display name"""
        name_map = {
            AwardCategory.WRESTLER_OF_THE_YEAR: "Wrestler of the Year",
            AwardCategory.BREAKOUT_STAR: "Breakout Star of the Year",
            AwardCategory.MOST_IMPROVED: "Most Improved Wrestler",
            AwardCategory.COMEBACK_OF_THE_YEAR: "Comeback of the Year",
            AwardCategory.MATCH_OF_THE_YEAR: "Match of the Year",
            AwardCategory.FEUD_OF_THE_YEAR: "Feud of the Year",
            AwardCategory.MOMENT_OF_THE_YEAR: "Moment of the Year",
            AwardCategory.CHAMPION_OF_THE_YEAR: "Champion of the Year",
            AwardCategory.TITLE_REIGN_OF_THE_YEAR: "Title Reign of the Year",
            AwardCategory.TAG_TEAM_OF_THE_YEAR: "Tag Team of the Year",
            AwardCategory.TAG_MATCH_OF_THE_YEAR: "Tag Team Match of the Year",
            AwardCategory.BEST_TECHNICAL_WRESTLER: "Best Technical Wrestler",
            AwardCategory.BEST_HIGH_FLYER: "Best High-Flyer",
            AwardCategory.BEST_BRAWLER: "Best Brawler",
            AwardCategory.PROMO_OF_THE_YEAR: "Promo of the Year",
            AwardCategory.BEST_ON_THE_MIC: "Best on the Mic",
            AwardCategory.BIGGEST_DISAPPOINTMENT: "Biggest Disappointment",
            AwardCategory.WORST_FEUD: "Worst Feud of the Year",
            AwardCategory.BEST_BRAND: "Brand of the Year",
            AwardCategory.SHOW_OF_THE_YEAR: "Show of the Year"
        }
        return name_map.get(self.category, self.category.value.replace('_', ' ').title())


@dataclass
class AwardsCeremony:
    """Complete awards ceremony for a year"""
    year: int
    awards: List[Award]
    ceremony_date_week: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'year': self.year,
            'ceremony_date_week': self.ceremony_date_week,
            'total_awards': len(self.awards),
            'awards': [a.to_dict() for a in self.awards]
        }