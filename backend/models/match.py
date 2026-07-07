"""
Match Models
Defines match drafts (pre-simulation) and match results (post-simulation).

STEP 14: Enhanced with referee assignments and special match types.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class BookingBias(Enum):
    """Booking bias determines win probability"""
    STRONG_A = "strong_a"      # 85% chance for Side A
    SLIGHT_A = "slight_a"      # 65% chance for Side A
    EVEN = "even"              # 50/50
    SLIGHT_B = "slight_b"      # 65% chance for Side B
    STRONG_B = "strong_b"      # 85% chance for Side B


class MatchImportance(Enum):
    """Match importance affects post-match effects"""
    NORMAL = "normal"          # Standard match
    PROTECT_BOTH = "protect_both"  # Minimize losses for both (DQ/countout likely)
    HIGH_DRAMA = "high_drama"  # Major match, bigger stat swings


class FinishType(Enum):
    """How the match ended"""
    CLEAN_PIN = "clean_pin"
    SUBMISSION = "submission"
    CHEATING = "cheating"      # Heel tactics (low blow, weapon, etc.)
    ROLLUP = "rollup"          # Surprise small package/inside cradle
    DQ = "dq"
    COUNTOUT = "countout"
    NO_CONTEST = "no_contest"


@dataclass
class MatchParticipant:
    """One side of a match (can be singles or tag team)"""
    wrestler_ids: List[str]  # Single ID for singles, multiple for tag
    wrestler_names: List[str]
    is_tag_team: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'wrestler_ids': self.wrestler_ids,
            'wrestler_names': self.wrestler_names,
            'is_tag_team': self.is_tag_team
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MatchParticipant':
        return MatchParticipant(
            wrestler_ids=data['wrestler_ids'],
            wrestler_names=data['wrestler_names'],
            is_tag_team=data.get('is_tag_team', False)
        )


@dataclass
class MatchDraft:
    """
    Pre-simulation match definition.
    Created by AI Creative Director or manual booking.
    
    STEP 14 ENHANCEMENTS:
    - referee_id: Assigned referee
    - special_match_type: Cage, ladder, etc.
    """
    match_id: str
    side_a: MatchParticipant
    side_b: MatchParticipant
    match_type: str  # 'singles', 'tag', 'triple_threat', 'fatal_4way', 'triple_threat_tag', 'fatal_4way_tag', 'battle_royal', 'rumble', 'casino_battle_royal'
    is_title_match: bool = False
    title_id: Optional[str] = None
    title_name: Optional[str] = None
    card_position: int = 1  # 1 = opener, higher = main event
    booking_bias: BookingBias = BookingBias.EVEN
    importance: MatchImportance = MatchImportance.NORMAL
    feud_id: Optional[str] = None
    stipulation: Optional[str] = None  # 'No DQ', 'Cage Match', etc.
    gender_division: Optional[str] = None  # 'male', 'female', 'intergender'
    
    # STEP 14: New fields
    referee_id: Optional[str] = None
    special_match_type: Optional[str] = None  # 'steel_cage', 'ladder_match', etc.
    planned_duration_minutes: Optional[int] = None
    
    # FIX: Add booked_winner field
    booked_winner: Optional[str] = None  # wrestler id or None for random
    booked_runner_up: Optional[str] = None
    booked_iron_man: Optional[str] = None
    booked_most_eliminations: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'match_id': self.match_id,
            'side_a': self.side_a.to_dict(),
            'side_b': self.side_b.to_dict(),
            'match_type': self.match_type,
            'is_title_match': self.is_title_match,
            'title_id': self.title_id,
            'title_name': self.title_name,
            'card_position': self.card_position,
            'booking_bias': self.booking_bias.value,
            'importance': self.importance.value,
            'feud_id': self.feud_id,
            'stipulation': self.stipulation,
            'gender_division': self.gender_division,
            'referee_id': self.referee_id,
            'special_match_type': self.special_match_type,
            'planned_duration_minutes': self.planned_duration_minutes,
            'booked_winner': self.booked_winner,
            'booked_runner_up': self.booked_runner_up,
            'booked_iron_man': self.booked_iron_man,
            'booked_most_eliminations': self.booked_most_eliminations
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MatchDraft':
        return MatchDraft(
            match_id=data['match_id'],
            side_a=MatchParticipant.from_dict(data['side_a']),
            side_b=MatchParticipant.from_dict(data['side_b']),
            match_type=data['match_type'],
            is_title_match=data.get('is_title_match', False),
            title_id=data.get('title_id'),
            title_name=data.get('title_name'),
            card_position=data.get('card_position', 1),
            booking_bias=BookingBias(data.get('booking_bias', 'even')),
            importance=MatchImportance(data.get('importance', 'normal')),
            feud_id=data.get('feud_id'),
            stipulation=data.get('stipulation'),
            gender_division=data.get('gender_division'),
            referee_id=data.get('referee_id'),
            special_match_type=data.get('special_match_type'),
            planned_duration_minutes=data.get('planned_duration_minutes'),
            booked_winner=data.get('booked_winner'),
            booked_runner_up=data.get('booked_runner_up'),
            booked_iron_man=data.get('booked_iron_man'),
            booked_most_eliminations=data.get('booked_most_eliminations')
        )


@dataclass
class MatchHighlight:
    """A single moment/beat in the match"""
    timestamp: str  # e.g., "2:34"
    description: str
    highlight_type: str  # 'opening', 'nearfall', 'signature', 'comeback', 'finish'


@dataclass
class MatchResult:
    """
    Post-simulation match result with all details.
    
    STEP 14 ENHANCEMENTS:
    - referee_name: Referee who officiated
    - crowd_energy: Final crowd heat level
    - special_match_type: If special stipulation was used
    """
    match_id: str
    
    # Participants
    side_a: MatchParticipant
    side_b: MatchParticipant
    match_type: str
    
    # Outcome
    winner: str  # 'side_a', 'side_b', 'draw', 'no_contest'
    winner_names: List[str]
    loser_names: List[str]
    finish_type: FinishType
    
    # Match Quality
    duration_minutes: int
    star_rating: float  # 0.0 - 5.0
    
    # Narrative
    highlights: List[MatchHighlight] = field(default_factory=list)
    match_summary: str = ""
    
    # Special Events
    is_upset: bool = False
    title_changed_hands: bool = False
    new_champion_id: Optional[str] = None
    new_champion_name: Optional[str] = None
    
    # Injuries sustained
    injuries: List[Dict[str, Any]] = field(default_factory=list)  # {'wrestler_id', 'severity', 'description'}
    
    # Metadata
    card_position: int = 1
    is_title_match: bool = False
    title_name: Optional[str] = None
    title_id: Optional[str] = None  # ADD THIS - needed for title change processing
    
    # STEP 14: New fields
    referee_name: Optional[str] = None
    crowd_energy: int = 50  # 0-100
    crowd_pacing_grade: str = "Good"  # Excellent/Great/Good/Average/Poor
    special_match_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'match_id': self.match_id,
            'side_a': self.side_a.to_dict(),
            'side_b': self.side_b.to_dict(),
            'match_type': self.match_type,
            'winner': self.winner,
            'winner_names': self.winner_names,
            'loser_names': self.loser_names,
            'finish_type': self.finish_type.value,
            'duration_minutes': self.duration_minutes,
            'star_rating': self.star_rating,
            'highlights': [
                {'timestamp': h.timestamp, 'description': h.description, 'type': h.highlight_type}
                for h in self.highlights
            ],
            'match_summary': self.match_summary,
            'is_upset': self.is_upset,
            'title_changed_hands': self.title_changed_hands,
            'new_champion_id': self.new_champion_id,
            'new_champion_name': self.new_champion_name,
            'injuries': self.injuries,
            'card_position': self.card_position,
            'is_title_match': self.is_title_match,
            'title_name': self.title_name,
            'title_id': self.title_id,  # ADD THIS
            'referee_name': self.referee_name,
            'crowd_energy': self.crowd_energy,
            'crowd_pacing_grade': self.crowd_pacing_grade,
            'special_match_type': self.special_match_type
        }
