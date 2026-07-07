"""
Feud Model
Tracks rivalries and storylines between wrestlers.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class FeudType(Enum):
    """Types of feuds/storylines"""
    PERSONAL = "personal"              # Personal rivalry
    TITLE = "title"                    # Championship feud
    FACTION = "faction"                # Stable vs stable
    MENTOR_VS_PROTEGE = "mentor_vs_protege"  # Teacher vs student
    TAG_TEAM_BREAKUP = "tag_team_breakup"    # Former partners clash


class FeudStatus(Enum):
    """Current state of the feud"""
    BUILDING = "building"      # Intensity growing
    HOT = "hot"               # Peak intensity, ready for payoff
    COOLING = "cooling"       # After initial payoff, could reignite
    RESOLVED = "resolved"     # Fully concluded


@dataclass
class FeudSegment:
    """A segment/interaction in the feud (match, promo, attack, etc.)"""
    show_id: str
    show_name: str
    year: int
    week: int
    segment_type: str  # 'match', 'promo', 'attack', 'contract_signing', etc.
    description: str
    intensity_change: int  # How much intensity changed (+/- points)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'show_id': self.show_id,
            'show_name': self.show_name,
            'year': self.year,
            'week': self.week,
            'segment_type': self.segment_type,
            'description': self.description,
            'intensity_change': self.intensity_change
        }


class Feud:
    """
    Represents an ongoing rivalry/storyline.
    
    Feuds track intensity (0-100), have types, and can involve titles.
    They build over time through matches and segments, culminating in a payoff.
    """
    
    def __init__(
        self,
        feud_id: str,
        feud_type: FeudType,
        participant_ids: List[str],  # 2+ wrestler IDs
        participant_names: List[str],
        title_id: Optional[str] = None,
        title_name: Optional[str] = None,
        intensity: int = 20,  # 0-100
        start_year: int = 1,
        start_week: int = 1,
        start_show_id: Optional[str] = None,
        planned_payoff_show_id: Optional[str] = None,
        planned_payoff_event: Optional[str] = None,  # e.g., "Victory Dome"
        status: FeudStatus = FeudStatus.BUILDING
    ):
        self.id = feud_id
        self.feud_type = feud_type
        self.participant_ids = participant_ids
        self.participant_names = participant_names
        self.title_id = title_id
        self.title_name = title_name
        self.intensity = intensity
        self.start_year = start_year
        self.start_week = start_week
        self.start_show_id = start_show_id
        self.last_segment_show_id: Optional[str] = None
        self.last_segment_year: Optional[int] = None
        self.last_segment_week: Optional[int] = None
        self.planned_payoff_show_id = planned_payoff_show_id
        self.planned_payoff_event = planned_payoff_event
        self.status = status
        self.segments: List[FeudSegment] = []
        
        # Track wins/losses in the feud
        self.match_count = 0
        self.wins_by_participant: Dict[str, int] = {pid: 0 for pid in participant_ids}
    
    def add_segment(
        self,
        show_id: str,
        show_name: str,
        year: int,
        week: int,
        segment_type: str,
        description: str,
        intensity_change: int = 0
    ):
        """Add a new segment to the feud"""
        segment = FeudSegment(
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week,
            segment_type=segment_type,
            description=description,
            intensity_change=intensity_change
        )
        
        self.segments.append(segment)
        self.adjust_intensity(intensity_change)
        
        self.last_segment_show_id = show_id
        self.last_segment_year = year
        self.last_segment_week = week
        
        if segment_type == 'match':
            self.match_count += 1
    
    def adjust_intensity(self, delta: int):
        """Adjust feud intensity, clamped to 0-100"""
        self.intensity = max(0, min(100, self.intensity + delta))
        
        # Update status based on intensity
        if self.intensity >= 80:
            self.status = FeudStatus.HOT
        elif self.intensity >= 40:
            self.status = FeudStatus.BUILDING
        elif self.intensity > 0:
            self.status = FeudStatus.COOLING
        else:
            self.status = FeudStatus.RESOLVED
    
    def record_match_result(self, winner_id: str):
        """Record a match result in the feud"""
        if winner_id in self.wins_by_participant:
            self.wins_by_participant[winner_id] += 1
    
    def get_series_record(self, wrestler_id: str) -> str:
        """Get win-loss record for a wrestler in this feud"""
        if wrestler_id not in self.wins_by_participant:
            return "0-0"
        
        wins = self.wins_by_participant[wrestler_id]
        losses = self.match_count - wins
        return f"{wins}-{losses}"
    
    def is_ready_for_payoff(self) -> bool:
        """Check if feud is hot enough for a major payoff"""
        return self.intensity >= 70 and self.match_count >= 2
    
    def resolve(self):
        """Mark the feud as resolved"""
        self.status = FeudStatus.RESOLVED
        self.intensity = 0
    
    def reignite(self, intensity: int = 50):
        """Bring back a resolved feud"""
        if self.status == FeudStatus.RESOLVED:
            self.intensity = intensity
            self.status = FeudStatus.BUILDING
    
    @property
    def is_active(self) -> bool:
        """Check if feud is currently active (not resolved)"""
        return self.status != FeudStatus.RESOLVED
    
    @property
    def intensity_level(self) -> str:
        """Human-readable intensity level"""
        if self.intensity >= 80:
            return "White Hot"
        elif self.intensity >= 60:
            return "Intense"
        elif self.intensity >= 40:
            return "Heating Up"
        elif self.intensity >= 20:
            return "Brewing"
        else:
            return "Cooling Off"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize feud to dictionary"""
        return {
            'id': self.id,
            'feud_type': self.feud_type.value,
            'participant_ids': self.participant_ids,
            'participant_names': self.participant_names,
            'title_id': self.title_id,
            'title_name': self.title_name,
            'intensity': self.intensity,
            'intensity_level': self.intensity_level,
            'start_year': self.start_year,
            'start_week': self.start_week,
            'start_show_id': self.start_show_id,
            'last_segment_show_id': self.last_segment_show_id,
            'last_segment_year': self.last_segment_year,
            'last_segment_week': self.last_segment_week,
            'planned_payoff_show_id': self.planned_payoff_show_id,
            'planned_payoff_event': self.planned_payoff_event,
            'status': self.status.value,
            'segments': [seg.to_dict() for seg in self.segments],
            'match_count': self.match_count,
            'wins_by_participant': self.wins_by_participant,
            'is_active': self.is_active,
            'is_ready_for_payoff': self.is_ready_for_payoff()
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Feud':
        """Create feud from dictionary"""
        feud = Feud(
            feud_id=data['id'],
            feud_type=FeudType(data['feud_type']),
            participant_ids=data['participant_ids'],
            participant_names=data['participant_names'],
            title_id=data.get('title_id'),
            title_name=data.get('title_name'),
            intensity=data.get('intensity', 20),
            start_year=data.get('start_year', 1),
            start_week=data.get('start_week', 1),
            start_show_id=data.get('start_show_id'),
            planned_payoff_show_id=data.get('planned_payoff_show_id'),
            planned_payoff_event=data.get('planned_payoff_event'),
            status=FeudStatus(data.get('status', 'building'))
        )
        
        feud.last_segment_show_id = data.get('last_segment_show_id')
        feud.last_segment_year = data.get('last_segment_year')
        feud.last_segment_week = data.get('last_segment_week')
        feud.match_count = data.get('match_count', 0)
        feud.wins_by_participant = data.get('wins_by_participant', {})
        
        # Load segments
        for seg_data in data.get('segments', []):
            feud.segments.append(FeudSegment(
                show_id=seg_data['show_id'],
                show_name=seg_data['show_name'],
                year=seg_data['year'],
                week=seg_data['week'],
                segment_type=seg_data['segment_type'],
                description=seg_data['description'],
                intensity_change=seg_data.get('intensity_change', 0)
            ))
        
        return feud
    
    def __repr__(self):
        participants = " vs ".join(self.participant_names)
        return f"<Feud {self.id}: {participants} ({self.intensity_level})>"


class FeudManager:
    """Manages all feuds in the universe"""
    
    def __init__(self):
        self.feuds: List[Feud] = []
        self._next_feud_id = 1
    
    def create_feud(
        self,
        feud_type: FeudType,
        participant_ids: List[str],
        participant_names: List[str],
        year: int,
        week: int,
        show_id: Optional[str] = None,
        title_id: Optional[str] = None,
        title_name: Optional[str] = None,
        initial_intensity: int = 20
    ) -> Feud:
        """Create a new feud"""
        feud_id = f"feud_{self._next_feud_id:04d}"
        self._next_feud_id += 1
        
        feud = Feud(
            feud_id=feud_id,
            feud_type=feud_type,
            participant_ids=participant_ids,
            participant_names=participant_names,
            title_id=title_id,
            title_name=title_name,
            intensity=initial_intensity,
            start_year=year,
            start_week=week,
            start_show_id=show_id
        )
        
        self.feuds.append(feud)
        return feud
    
    def get_feud_by_id(self, feud_id: str) -> Optional[Feud]:
        """Get feud by ID"""
        for feud in self.feuds:
            if feud.id == feud_id:
                return feud
        return None
    
    def get_active_feuds(self) -> List[Feud]:
        """Get all active (not resolved) feuds"""
        return [f for f in self.feuds if f.is_active]
    
    def get_feuds_involving(self, wrestler_id: str) -> List[Feud]:
        """Get all feuds involving a specific wrestler"""
        return [f for f in self.feuds if wrestler_id in f.participant_ids and f.is_active]
    
    def get_feud_between(self, wrestler_a_id: str, wrestler_b_id: str) -> Optional[Feud]:
        """Get active feud between two specific wrestlers"""
        for feud in self.get_active_feuds():
            if wrestler_a_id in feud.participant_ids and wrestler_b_id in feud.participant_ids:
                return feud
        return None
    
    def get_hot_feuds(self, min_intensity: int = 70) -> List[Feud]:
        """Get feuds above a certain intensity threshold"""
        return [f for f in self.get_active_feuds() if f.intensity >= min_intensity]
    
    def auto_create_from_upset(
        self,
        winner_id: str,
        winner_name: str,
        loser_id: str,
        loser_name: str,
        year: int,
        week: int,
        show_id: str
    ) -> Feud:
        """
        Auto-create a personal feud from an upset victory.
        Called by match simulation when an upset is detected.
        """
        # Check if feud already exists
        existing = self.get_feud_between(winner_id, loser_id)
        if existing:
            # Intensify existing feud
            existing.add_segment(
                show_id=show_id,
                show_name="Recent Show",
                year=year,
                week=week,
                segment_type='match',
                description=f"UPSET: {winner_name} shocked {loser_name}!",
                intensity_change=15
            )
            return existing
        
        # Create new feud
        feud = self.create_feud(
            feud_type=FeudType.PERSONAL,
            participant_ids=[winner_id, loser_id],
            participant_names=[winner_name, loser_name],
            year=year,
            week=week,
            show_id=show_id,
            initial_intensity=40  # Upsets start hot
        )
        
        feud.add_segment(
            show_id=show_id,
            show_name="Recent Show",
            year=year,
            week=week,
            segment_type='match',
            description=f"MAJOR UPSET: {winner_name} defeated {loser_name}, sparking a rivalry!",
            intensity_change=0  # Already set initial intensity
        )
        
        return feud
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize all feuds"""
        return {
            'total_feuds': len(self.feuds),
            'active_feuds': len(self.get_active_feuds()),
            'hot_feuds': len(self.get_hot_feuds()),
            'next_feud_id': self._next_feud_id,
            'feuds': [f.to_dict() for f in self.feuds]
        }
    
    def load_from_dict(self, data: Dict[str, Any]):
        """Load feuds from dictionary"""
        self._next_feud_id = data.get('next_feud_id', 1)
        self.feuds = []
        
        for feud_data in data.get('feuds', []):
            feud = Feud.from_dict(feud_data)
            self.feuds.append(feud)