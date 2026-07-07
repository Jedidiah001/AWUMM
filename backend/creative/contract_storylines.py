"""
Contract Expiration Storyline Engine
STEP 125: Automatically generates compelling angles for wrestlers with expiring contracts.

Storyline Types:
1. "Will They Stay or Go?" - Weekly vignettes building tension
2. "Contract on a Pole" - High-stakes match for contract extension
3. Farewell Tour - Retirement/departure angle with multiple matches
4. Surprise Re-Signing - Shock announcement for returning stars
5. Bidding War - Rival promotions angle
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import random


class StorylineType(Enum):
    WILL_THEY_STAY = "will_they_stay"
    CONTRACT_ON_POLE = "contract_on_pole"
    FAREWELL_TOUR = "farewell_tour"
    SURPRISE_RESIGN = "surprise_resign"
    BIDDING_WAR = "bidding_war"
    LAST_CHANCE = "last_chance"
    RETIREMENT_CONSIDERATION = "retirement_consideration"


class StorylineStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PROGRESSING = "progressing"
    CLIMAX = "climax"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


@dataclass
class ContractStoryline:
    """Represents a contract expiration storyline"""
    storyline_id: str
    storyline_type: StorylineType
    wrestler_id: str
    wrestler_name: str
    status: StorylineStatus
    
    trigger_year: int
    trigger_week: int
    
    planned_resolution_show: Optional[str] = None
    planned_resolution_week: Optional[int] = None
    
    current_beat: int = 0
    total_beats: int = 4
    
    description: str = ""
    weekly_segments: List[str] = None
    
    # Outcome tracking
    outcome: Optional[str] = None  # 'stayed', 'left', 'retired', 'cancelled'
    resolution_details: Optional[str] = None
    
    def __post_init__(self):
        if self.weekly_segments is None:
            self.weekly_segments = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'storyline_id': self.storyline_id,
            'storyline_type': self.storyline_type.value,
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'status': self.status.value,
            'trigger_year': self.trigger_year,
            'trigger_week': self.trigger_week,
            'planned_resolution_show': self.planned_resolution_show,
            'planned_resolution_week': self.planned_resolution_week,
            'current_beat': self.current_beat,
            'total_beats': self.total_beats,
            'description': self.description,
            'weekly_segments': self.weekly_segments,
            'outcome': self.outcome,
            'resolution_details': self.resolution_details
        }


class ContractStorylineEngine:
    """
    Manages contract expiration storylines.
    Generates appropriate angles based on wrestler status and time remaining.
    """
    
    def __init__(self):
        self.active_storylines: List[ContractStoryline] = []
        self._next_storyline_id = 1
    
    # ========================================================================
    # Storyline Generation
    # ========================================================================
    
    def should_generate_storyline(self, wrestler, current_year: int, current_week: int) -> bool:
        """
        Determine if wrestler qualifies for contract storyline.
        
        Criteria:
        - Contract ≤ 13 weeks remaining
        - Not already in a contract storyline
        - Popularity ≥ 40 (worth featuring)
        - Not retired or injured
        """
        # Check basic eligibility
        if wrestler.is_retired or wrestler.contract.weeks_remaining > 13:
            return False
        
        # Check if already has active storyline
        if self._has_active_storyline(wrestler.id):
            return False
        
        # Popularity threshold (lower for major stars)
        min_popularity = 30 if wrestler.is_major_superstar else 40
        if wrestler.popularity < min_popularity:
            return False
        
        # Don't generate for severe injuries
        if wrestler.injury.severity in ['Major', 'Severe']:
            return False
        
        return True
    
    def generate_storyline_for_wrestler(
        self,
        wrestler,
        current_year: int,
        current_week: int,
        next_major_ppv: Optional[Dict] = None
    ) -> Optional[ContractStoryline]:
        """
        Generate appropriate storyline based on wrestler's situation.
        """
        weeks_remaining = wrestler.contract.weeks_remaining
        
        # Determine storyline type
        storyline_type = self._determine_storyline_type(wrestler, weeks_remaining)
        
        if not storyline_type:
            return None
        
        # Create storyline
        storyline = ContractStoryline(
            storyline_id=f"contract_story_{self._next_storyline_id}",
            storyline_type=storyline_type,
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            status=StorylineStatus.PENDING,
            trigger_year=current_year,
            trigger_week=current_week
        )
        
        self._next_storyline_id += 1
        
        # Configure storyline based on type
        self._configure_storyline(storyline, wrestler, next_major_ppv, weeks_remaining)
        
        # Add to active storylines
        self.active_storylines.append(storyline)
        
        return storyline
    
    def _determine_storyline_type(self, wrestler, weeks_remaining: int) -> Optional[StorylineType]:
        """Choose appropriate storyline type"""
        
        # Age-based logic
        if wrestler.age >= 45 and wrestler.morale < 50:
            return StorylineType.RETIREMENT_CONSIDERATION
        
        # Critical expiration (≤4 weeks)
        if weeks_remaining <= 4:
            if wrestler.is_major_superstar:
                return StorylineType.BIDDING_WAR
            else:
                return StorylineType.LAST_CHANCE
        
        # Soon expiring (5-8 weeks)
        elif weeks_remaining <= 8:
            if wrestler.morale < 40:
                return StorylineType.WILL_THEY_STAY
            elif wrestler.is_major_superstar:
                return StorylineType.CONTRACT_ON_POLE
            else:
                return StorylineType.WILL_THEY_STAY
        
        # Monitor (9-13 weeks)
        elif weeks_remaining <= 13:
            if wrestler.age >= 40:
                return StorylineType.FAREWELL_TOUR
            else:
                return StorylineType.WILL_THEY_STAY
        
        return None
    
    def _configure_storyline(
        self,
        storyline: ContractStoryline,
        wrestler,
        next_major_ppv: Optional[Dict],
        weeks_remaining: int
    ):
        """Configure storyline beats and description"""
        
        if storyline.storyline_type == StorylineType.WILL_THEY_STAY:
            self._configure_will_they_stay(storyline, wrestler, weeks_remaining)
        
        elif storyline.storyline_type == StorylineType.CONTRACT_ON_POLE:
            self._configure_contract_on_pole(storyline, wrestler, next_major_ppv)
        
        elif storyline.storyline_type == StorylineType.FAREWELL_TOUR:
            self._configure_farewell_tour(storyline, wrestler, weeks_remaining)
        
        elif storyline.storyline_type == StorylineType.SURPRISE_RESIGN:
            self._configure_surprise_resign(storyline, wrestler)
        
        elif storyline.storyline_type == StorylineType.BIDDING_WAR:
            self._configure_bidding_war(storyline, wrestler, weeks_remaining)
        
        elif storyline.storyline_type == StorylineType.LAST_CHANCE:
            self._configure_last_chance(storyline, wrestler)
        
        elif storyline.storyline_type == StorylineType.RETIREMENT_CONSIDERATION:
            self._configure_retirement(storyline, wrestler)
    
    # ========================================================================
    # Storyline Type Configurations
    # ========================================================================
    
    def _configure_will_they_stay(self, storyline: ContractStoryline, wrestler, weeks_remaining: int):
        """
        "Will They Stay or Go?" - Build weekly tension
        """
        storyline.total_beats = min(weeks_remaining, 6)
        storyline.description = f"{wrestler.name}'s contract expires in {weeks_remaining} weeks. Will they re-sign or leave?"
        
        storyline.weekly_segments = [
            f"Week 1: {wrestler.name} addresses the crowd about their uncertain future",
            f"Week 2: Backstage segment - contract negotiations happening behind closed doors",
            f"Week 3: {wrestler.name} has a standout match, reminding everyone of their value",
            f"Week 4: Rival promotion rumored to be interested (dirt sheet 'leak')",
            f"Week 5: Contract deadline approaches - {wrestler.name} appears conflicted",
            f"Week 6: Decision time - will they sign or walk away?"
        ]
    
    def _configure_contract_on_pole(self, storyline: ContractStoryline, wrestler, next_major_ppv: Optional[Dict]):
        """
        "Contract on a Pole" - High-stakes match
        """
        storyline.total_beats = 3
        storyline.description = f"{wrestler.name}'s contract extension hangs above the ring in a high-stakes match!"
        
        if next_major_ppv:
            storyline.planned_resolution_show = next_major_ppv.get('show_id')
            storyline.planned_resolution_week = next_major_ppv.get('week')
        
        storyline.weekly_segments = [
            f"Week 1: Contract on a Pole match announced - {wrestler.name} must win to secure extension",
            f"Week 2: Build-up promos and hype packages showing what's at stake",
            f"Week 3: THE MATCH - {wrestler.name} fights for their future"
        ]
    
    def _configure_farewell_tour(self, storyline: ContractStoryline, wrestler, weeks_remaining: int):
        """
        Farewell Tour - Multiple special matches
        """
        storyline.total_beats = min(weeks_remaining // 2, 5)
        storyline.description = f"{wrestler.name} announces this could be their final run - a farewell tour begins"
        
        storyline.weekly_segments = [
            f"Week 1: {wrestler.name} announces potential retirement, farewell tour begins",
            f"Week 2: Dream match #1 - facing a legend from the past",
            f"Week 3: Dream match #2 - facing their greatest rival",
            f"Week 4: Dream match #3 - facing the next generation",
            f"Week 5: Final match and decision - retirement or one more year?"
        ]
    
    def _configure_surprise_resign(self, storyline: ContractStoryline, wrestler):
        """
        Surprise Re-Signing - Shock announcement
        """
        storyline.total_beats = 1
        storyline.description = f"Surprise! {wrestler.name} shocks the world with immediate re-signing"
        
        storyline.weekly_segments = [
            f"{wrestler.name} interrupts the show to announce they've re-signed for multiple years!"
        ]
    
    def _configure_bidding_war(self, storyline: ContractStoryline, wrestler, weeks_remaining: int):
        """
        Bidding War - Rival promotions competing
        """
        storyline.total_beats = 4
        storyline.description = f"{wrestler.name} is being courted by multiple promotions - who will sign them?"
        
        storyline.weekly_segments = [
            f"Week 1: Rival promotion makes public offer to {wrestler.name}",
            f"Week 2: Current promotion counters with improved offer",
            f"Week 3: Rival promotion increases bid - bidding war intensifies",
            f"Week 4: {wrestler.name} makes final decision on live TV"
        ]
    
    def _configure_last_chance(self, storyline: ContractStoryline, wrestler):
        """
        Last Chance - Prove yourself or leave
        """
        storyline.total_beats = 2
        storyline.description = f"{wrestler.name} has one last chance to prove they deserve a new contract"
        
        storyline.weekly_segments = [
            f"Week 1: Management gives {wrestler.name} ultimatum - win or you're gone",
            f"Week 2: {wrestler.name} fights for their career in a must-win match"
        ]
    
    def _configure_retirement(self, storyline: ContractStoryline, wrestler):
        """
        Retirement Consideration - Veteran contemplates hanging up the boots
        """
        storyline.total_beats = 3
        storyline.description = f"{wrestler.name}, a veteran of {wrestler.years_experience} years, considers retirement"
        
        storyline.weekly_segments = [
            f"Week 1: {wrestler.name} opens up about considering retirement",
            f"Week 2: Legends and peers weigh in on {wrestler.name}'s potential retirement",
            f"Week 3: {wrestler.name} makes final decision - retire or continue?"
        ]
    
    # ========================================================================
    # Storyline Progression
    # ========================================================================
    
    def progress_storyline(self, storyline_id: str, segment_summary: str) -> bool:
        """
        Progress storyline to next beat.
        Returns True if storyline advances, False if complete.
        """
        storyline = self._get_storyline_by_id(storyline_id)
        if not storyline:
            return False
        
        # Update status
        if storyline.status == StorylineStatus.PENDING:
            storyline.status = StorylineStatus.ACTIVE
        
        # Progress beat
        storyline.current_beat += 1
        
        # Update status based on progress
        if storyline.current_beat >= storyline.total_beats - 1:
            storyline.status = StorylineStatus.CLIMAX
        elif storyline.current_beat > 1:
            storyline.status = StorylineStatus.PROGRESSING
        
        # Check if complete
        if storyline.current_beat >= storyline.total_beats:
            return False
        
        return True
    
    def resolve_storyline(
        self,
        storyline_id: str,
        outcome: str,
        resolution_details: str
    ):
        """
        Mark storyline as resolved with outcome.
        
        Outcomes:
        - 'stayed' - Wrestler re-signed
        - 'left' - Wrestler departed
        - 'retired' - Wrestler retired
        - 'cancelled' - Storyline abandoned
        """
        storyline = self._get_storyline_by_id(storyline_id)
        if not storyline:
            return
        
        storyline.status = StorylineStatus.RESOLVED
        storyline.outcome = outcome
        storyline.resolution_details = resolution_details
    
    def get_current_segment(self, storyline_id: str) -> Optional[str]:
        """Get current week's segment for storyline"""
        storyline = self._get_storyline_by_id(storyline_id)
        if not storyline:
            return None
        
        if storyline.current_beat < len(storyline.weekly_segments):
            return storyline.weekly_segments[storyline.current_beat]
        
        return None
    
    # ========================================================================
    # Storyline Management
    # ========================================================================
    
    def get_active_storylines(self) -> List[ContractStoryline]:
        """Get all active storylines"""
        return [
            s for s in self.active_storylines
            if s.status in [StorylineStatus.PENDING, StorylineStatus.ACTIVE, StorylineStatus.PROGRESSING, StorylineStatus.CLIMAX]
        ]
    
    def get_storylines_for_wrestler(self, wrestler_id: str) -> List[ContractStoryline]:
        """Get all storylines for a wrestler"""
        return [s for s in self.active_storylines if s.wrestler_id == wrestler_id]
    
    def get_storylines_needing_resolution(self, current_week: int) -> List[ContractStoryline]:
        """Get storylines that should resolve this week"""
        return [
            s for s in self.active_storylines
            if s.status == StorylineStatus.CLIMAX and s.planned_resolution_week == current_week
        ]
    
    def cancel_storyline(self, storyline_id: str, reason: str = "Cancelled"):
        """Cancel a storyline (e.g., wrestler signed early)"""
        storyline = self._get_storyline_by_id(storyline_id)
        if storyline:
            storyline.status = StorylineStatus.CANCELLED
            storyline.resolution_details = reason
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _has_active_storyline(self, wrestler_id: str) -> bool:
        """Check if wrestler already has active contract storyline"""
        return any(
            s.wrestler_id == wrestler_id and s.status in [
                StorylineStatus.PENDING,
                StorylineStatus.ACTIVE,
                StorylineStatus.PROGRESSING,
                StorylineStatus.CLIMAX
            ]
            for s in self.active_storylines
        )
    
    def _get_storyline_by_id(self, storyline_id: str) -> Optional[ContractStoryline]:
        """Get storyline by ID"""
        for storyline in self.active_storylines:
            if storyline.storyline_id == storyline_id:
                return storyline
        return None
    
    # ========================================================================
    # Serialization
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize engine state"""
        return {
            'active_storylines': [s.to_dict() for s in self.active_storylines],
            'next_storyline_id': self._next_storyline_id
        }
    
    def load_from_dict(self, data: Dict[str, Any]):
        """Load engine state"""
        self._next_storyline_id = data.get('next_storyline_id', 1)
        
        self.active_storylines = []
        for s_data in data.get('active_storylines', []):
            storyline = ContractStoryline(
                storyline_id=s_data['storyline_id'],
                storyline_type=StorylineType(s_data['storyline_type']),
                wrestler_id=s_data['wrestler_id'],
                wrestler_name=s_data['wrestler_name'],
                status=StorylineStatus(s_data['status']),
                trigger_year=s_data['trigger_year'],
                trigger_week=s_data['trigger_week'],
                planned_resolution_show=s_data.get('planned_resolution_show'),
                planned_resolution_week=s_data.get('planned_resolution_week'),
                current_beat=s_data.get('current_beat', 0),
                total_beats=s_data.get('total_beats', 4),
                description=s_data.get('description', ''),
                weekly_segments=s_data.get('weekly_segments', []),
                outcome=s_data.get('outcome'),
                resolution_details=s_data.get('resolution_details')
            )
            self.active_storylines.append(storyline)


# Singleton instance
contract_storyline_engine = ContractStorylineEngine()