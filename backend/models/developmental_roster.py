"""
Developmental Roster System - ROC Vanguard Developmental Brand
Handles ROC Vanguard call-up mechanics to ROC Alpha and ROC Velocity.
Integrates with prospect_system.py for talent pipeline management.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import random


# ============================================================================
# DEVELOPMENTAL BRAND CONFIGURATION
# ============================================================================

class DevelopmentalBrand(Enum):
    """The developmental brand."""
    ROC_VANGUARD = "ROC Vanguard"
    ROC_NEXUS = "ROC Vanguard"  # Backward-compatible enum alias.
    
    @property
    def label(self) -> str:
        return self.value
    
    @property
    def display_name(self) -> str:
        return "Vanguard"


# ============================================================================
# CALL-UP STATUS TRACKING
# ============================================================================

class CallUpStatus(Enum):
    """Status of a developmental talent in the call-up pipeline"""
    DEVELOPMENTAL = "developmental"      # Currently in developmental
    READY_FOR_CALLUP = "ready_for_callup"  # Ready to be called up
    CALLED_UP_PENDING = "called_up_pending"  # Called up, awaiting brand assignment
    ON_MAIN_ROSTER = "on_main_roster"   # Successfully on main roster
    RETURNED_TO_DEV = "returned_to_dev"  # Returned to developmental after call-up
    RELEASED = "released"               # Released from contract
    
    @property
    def label(self) -> str:
        labels = {
            "developmental": "In Developmental",
            "ready_for_callup": "Ready for Call-Up",
            "called_up_pending": "Call-Up Pending",
            "on_main_roster": "On Main Roster",
            "returned_to_dev": "Returned to Developmental",
            "released": "Released"
        }
        return labels.get(self.value, self.value.title())


class CallUpReason(Enum):
    """Reasons for calling up a developmental talent"""
    BREAKTHROUGH_PERFORMANCE = "breakthrough_performance"
    INJURY_REPLACEMENT = "injury_replacement"
    ROSTER_EXPANSION = "roster_expansion"
    BRAND_NEED = "brand_need"
    FAN_DEMAND = "fan_demand"
    STORYLINE_OPPORTUNITY = "storyline_opportunity"
    DRAFT_PICK = "draft_pick"
    
    @property
    def label(self) -> str:
        labels = {
            "breakthrough_performance": "Breakthrough Performance",
            "injury_replacement": "Injury Replacement",
            "roster_expansion": "Roster Expansion",
            "brand_need": "Brand Need",
            "fan_demand": "Fan Demand",
            "storyline_opportunity": "Storyline Opportunity",
            "draft_pick": "Draft Pick"
        }
        return labels.get(self.value, self.value.replace("_", " ").title())


# ============================================================================
# DEVELOPMENTAL ROSTER ENTRY
# ============================================================================

@dataclass
class DevelopmentalRosterEntry:
    """
    Represents a wrestler on the developmental roster.
    Tracks their progress, call-up readiness, and history.
    """
    wrestler_id: str
    wrestler_name: str
    join_date_year: int
    join_date_week: int
    
    # Current status
    status: CallUpStatus = CallUpStatus.DEVELOPMENTAL
    
    # Developmental performance metrics
    developmental_rating: int = 50  # 0-100, separate from overall
    match_quality_avg: float = 0.0
    crowd_reaction_avg: float = 0.0
    coach_evaluation: int = 50  # Coach's assessment of readiness
    
    # Call-up tracking
    weeks_in_developmental: int = 0
    call_up_eligible_week: int = 8  # Minimum weeks before eligible
    times_called_up: int = 0
    last_call_up_year: Optional[int] = None
    last_call_up_week: Optional[int] = None
    last_call_up_brand: Optional[str] = None
    call_up_success_rate: float = 0.0  # Success rate of previous call-ups
    
    # Main roster assignment (if called up)
    assigned_brand: Optional[str] = None
    assigned_brand_date_year: Optional[int] = None
    assigned_brand_date_week: Optional[int] = None
    
    # Performance milestones
    achievements: List[str] = field(default_factory=list)
    # e.g., ["nxt_champion", "breakout_star_2024", "undefeated_streak_10"]
    
    # Training focus areas
    training_focus: List[str] = field(default_factory=list)
    # e.g., ["mic_skills", "selling", "character_work"]
    
    # Notes from coaching staff
    coaching_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id": self.wrestler_id,
            "wrestler_name": self.wrestler_name,
            "join_date_year": self.join_date_year,
            "join_date_week": self.join_date_week,
            "status": self.status.value,
            "status_label": self.status.label,
            "developmental_rating": self.developmental_rating,
            "match_quality_avg": round(self.match_quality_avg, 2),
            "crowd_reaction_avg": round(self.crowd_reaction_avg, 2),
            "coach_evaluation": self.coach_evaluation,
            "weeks_in_developmental": self.weeks_in_developmental,
            "call_up_eligible_week": self.call_up_eligible_week,
            "is_call_up_eligible": self.weeks_in_developmental >= self.call_up_eligible_week,
            "times_called_up": self.times_called_up,
            "last_call_up_year": self.last_call_up_year,
            "last_call_up_week": self.last_call_up_week,
            "last_call_up_brand": self.last_call_up_brand,
            "call_up_success_rate": round(self.call_up_success_rate, 2),
            "assigned_brand": self.assigned_brand,
            "assigned_brand_date_year": self.assigned_brand_date_year,
            "assigned_brand_date_week": self.assigned_brand_date_week,
            "achievements": self.achievements,
            "training_focus": self.training_focus,
            "coaching_notes": self.coaching_notes,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DevelopmentalRosterEntry':
        entry = DevelopmentalRosterEntry(
            wrestler_id=data.get("wrestler_id", ""),
            wrestler_name=data.get("wrestler_name", ""),
            join_date_year=data.get("join_date_year", 0),
            join_date_week=data.get("join_date_week", 0),
        )
        entry.status = CallUpStatus(data.get("status", "developmental"))
        entry.developmental_rating = data.get("developmental_rating", 50)
        entry.match_quality_avg = data.get("match_quality_avg", 0.0)
        entry.crowd_reaction_avg = data.get("crowd_reaction_avg", 0.0)
        entry.coach_evaluation = data.get("coach_evaluation", 50)
        entry.weeks_in_developmental = data.get("weeks_in_developmental", 0)
        entry.call_up_eligible_week = data.get("call_up_eligible_week", 8)
        entry.times_called_up = data.get("times_called_up", 0)
        entry.last_call_up_year = data.get("last_call_up_year")
        entry.last_call_up_week = data.get("last_call_up_week")
        entry.last_call_up_brand = data.get("last_call_up_brand")
        entry.call_up_success_rate = data.get("call_up_success_rate", 0.0)
        entry.assigned_brand = data.get("assigned_brand")
        entry.assigned_brand_date_year = data.get("assigned_brand_date_year")
        entry.assigned_brand_date_week = data.get("assigned_brand_date_week")
        entry.achievements = data.get("achievements", [])
        entry.training_focus = data.get("training_focus", [])
        entry.coaching_notes = data.get("coaching_notes", "")
        return entry
    
    def update_performance(self, match_quality: float, crowd_reaction: float):
        """Update performance metrics after a developmental match"""
        # Moving average calculation
        num_matches = max(1, self.weeks_in_developmental)
        self.match_quality_avg = (
            (self.match_quality_avg * (num_matches - 1) + match_quality) / num_matches
        )
        self.crowd_reaction_avg = (
            (self.crowd_reaction_avg * (num_matches - 1) + crowd_reaction) / num_matches
        )
        
        # Update developmental rating based on performance
        performance_score = (match_quality * 0.6 + crowd_reaction * 0.4)
        self.developmental_rating = min(100, max(0, 
            int(self.developmental_rating + (performance_score - 50) * 0.1)
        ))
    
    def check_readiness(self) -> bool:
        """Check if wrestler is ready for call-up"""
        if self.weeks_in_developmental < self.call_up_eligible_week:
            return False
        
        # Combined readiness score
        readiness_score = (
            self.developmental_rating * 0.3 +
            self.match_quality_avg * 0.3 +
            self.crowd_reaction_avg * 0.2 +
            self.coach_evaluation * 0.2
        )
        
        return readiness_score >= 70
    
    def record_call_up(self, brand: str, year: int, week: int):
        """Record a call-up event"""
        self.times_called_up += 1
        self.last_call_up_year = year
        self.last_call_up_week = week
        self.last_call_up_brand = brand
        self.status = CallUpStatus.CALLED_UP_PENDING
        self.assigned_brand = brand
        self.assigned_brand_date_year = year
        self.assigned_brand_date_week = week
    
    def record_main_roster_assignment(self, success: bool):
        """Record the outcome of a main roster assignment"""
        if success:
            self.status = CallUpStatus.ON_MAIN_ROSTER
            self.call_up_success_rate = (
                (self.call_up_success_rate * (self.times_called_up - 1) + 1.0) 
                / self.times_called_up
            )
        else:
            self.status = CallUpStatus.RETURNED_TO_DEV
            self.call_up_success_rate = (
                (self.call_up_success_rate * (self.times_called_up - 1) + 0.0) 
                / self.times_called_up
            )
            self.assigned_brand = None
    
    def add_achievement(self, achievement: str):
        """Add an achievement to the wrestler's record"""
        if achievement not in self.achievements:
            self.achievements.append(achievement)
    
    def get_readiness_summary(self) -> Dict[str, Any]:
        """Get a summary of call-up readiness"""
        is_eligible = self.weeks_in_developmental >= self.call_up_eligible_week
        is_ready = self.check_readiness()
        
        readiness_score = 0.0
        if is_eligible:
            readiness_score = (
                self.developmental_rating * 0.3 +
                self.match_quality_avg * 0.3 +
                self.crowd_reaction_avg * 0.2 +
                self.coach_evaluation * 0.2
            )
        
        return {
            "is_eligible": is_eligible,
            "is_ready": is_ready,
            "readiness_score": round(readiness_score, 2),
            "weeks_remaining": max(0, self.call_up_eligible_week - self.weeks_in_developmental),
            "strengths": self._identify_strengths(),
            "weaknesses": self._identify_weaknesses(),
        }
    
    def _identify_strengths(self) -> List[str]:
        """Identify the wrestler's strengths"""
        strengths = []
        if self.developmental_rating >= 75:
            strengths.append("High Developmental Rating")
        if self.match_quality_avg >= 75:
            strengths.append("Excellent Match Quality")
        if self.crowd_reaction_avg >= 75:
            strengths.append("Strong Crowd Connection")
        if self.coach_evaluation >= 75:
            strengths.append("Coach's Recommendation")
        return strengths
    
    def _identify_weaknesses(self) -> List[str]:
        """Identify areas needing improvement"""
        weaknesses = []
        if self.developmental_rating < 60:
            weaknesses.append("Needs more development")
        if self.match_quality_avg < 60:
            weaknesses.append("Match quality inconsistent")
        if self.crowd_reaction_avg < 60:
            weaknesses.append("Crowd connection weak")
        if self.coach_evaluation < 60:
            weaknesses.append("Not yet coach-approved")
        return weaknesses


# ============================================================================
# CALL-UP HISTORY TRACKING
# ============================================================================

@dataclass
class CallUpHistory:
    """Tracks the history of a single call-up event"""
    wrestler_id: str
    wrestler_name: str
    call_up_year: int
    call_up_week: int
    source_brand: str  # Always ROC Vanguard
    destination_brand: str  # Alpha, Velocity, or Vanguard
    reason: CallUpReason
    initiating_gm: Optional[str] = None  # GM who requested the call-up
    success_outcome: Optional[bool] = None  # Whether the call-up was successful
    return_date_year: Optional[int] = None  # If returned to developmental
    return_date_week: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id": self.wrestler_id,
            "wrestler_name": self.wrestler_name,
            "call_up_year": self.call_up_year,
            "call_up_week": self.call_up_week,
            "source_brand": self.source_brand,
            "destination_brand": self.destination_brand,
            "reason": self.reason.value,
            "reason_label": self.reason.label,
            "initiating_gm": self.initiating_gm,
            "success_outcome": self.success_outcome,
            "return_date_year": self.return_date_year,
            "return_date_week": self.return_date_week,
            "was_successful": self.success_outcome is True,
            "was_returned": self.return_date_year is not None,
        }


# ============================================================================
# DEVELOPMENTAL CHAMPIONSHIP TRACKING
# ============================================================================

@dataclass
class DevelopmentalChampionship:
    """Tracks the developmental brand championship"""
    championship_id: str = "vanguard_prospects_championship"
    name: str = "ROC Vanguard Prospects Championship"
    current_holder_id: Optional[str] = None
    current_holder_name: Optional[str] = None
    won_date_year: Optional[int] = None
    won_date_week: Optional[int] = None
    days_held: int = 0
    defense_count: int = 0
    history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "championship_id": self.championship_id,
            "name": self.name,
            "current_holder_id": self.current_holder_id,
            "current_holder_name": self.current_holder_name,
            "won_date_year": self.won_date_year,
            "won_date_week": self.won_date_week,
            "days_held": self.days_held,
            "defense_count": self.defense_count,
            "history": self.history,
        }


# ============================================================================
# DEVELOPMENTAL ROSTER MANAGER
# ============================================================================

class DevelopmentalRosterManager:
    """
    Manages the developmental roster and call-up mechanics.
    Handles talent pipeline from prospects to main roster.
    """
    
    def __init__(self):
        self.developmental_roster: Dict[str, DevelopmentalRosterEntry] = {}
        self.call_up_history: List[CallUpHistory] = []
        self.nexus_championship = DevelopmentalChampionship()
        
        # Brand assignments tracking
        self.pending_call_ups: List[Dict] = []  # Call-ups awaiting processing
        
        # Statistics
        self.total_call_ups = 0
        self.successful_call_ups = 0
        self.returned_talents = 0
    
    def add_to_developmental(
        self,
        wrestler_id: str,
        wrestler_name: str,
        current_year: int,
        current_week: int,
        initial_rating: int = 50,
        coaching_notes: str = ""
    ) -> DevelopmentalRosterEntry:
        """Add a wrestler to the developmental roster"""
        if wrestler_id in self.developmental_roster:
            # Already in developmental, just update notes
            entry = self.developmental_roster[wrestler_id]
            if coaching_notes:
                entry.coaching_notes = coaching_notes
            return entry
        
        entry = DevelopmentalRosterEntry(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            join_date_year=current_year,
            join_date_week=current_week,
            developmental_rating=initial_rating,
            coaching_notes=coaching_notes,
        )
        
        self.developmental_roster[wrestler_id] = entry
        return entry
    
    def remove_from_developmental(self, wrestler_id: str, reason: str = "call_up"):
        """Remove a wrestler from developmental roster"""
        if wrestler_id in self.developmental_roster:
            if reason == "call_up":
                self.developmental_roster[wrestler_id].status = CallUpStatus.CALLED_UP_PENDING
            elif reason == "release":
                self.developmental_roster[wrestler_id].status = CallUpStatus.RELEASED
                del self.developmental_roster[wrestler_id]
    
    def get_entry(self, wrestler_id: str) -> Optional[DevelopmentalRosterEntry]:
        """Get a developmental roster entry"""
        return self.developmental_roster.get(wrestler_id)
    
    def get_all_entries(self) -> List[DevelopmentalRosterEntry]:
        """Get all developmental roster entries"""
        return list(self.developmental_roster.values())
    
    def get_ready_for_call_up(self) -> List[DevelopmentalRosterEntry]:
        """Get all wrestlers ready for call-up"""
        return [
            entry for entry in self.developmental_roster.values()
            if entry.status == CallUpStatus.DEVELOPMENTAL and entry.check_readiness()
        ]
    
    def update_weekly_progress(self, current_year: int, current_week: int):
        """Update weekly progress for all developmental wrestlers"""
        for entry in self.developmental_roster.values():
            if entry.status == CallUpStatus.DEVELOPMENTAL:
                entry.weeks_in_developmental += 1
                
                # Natural rating improvement over time (small amount)
                if entry.weeks_in_developmental % 4 == 0:  # Every 4 weeks
                    entry.developmental_rating = min(100, entry.developmental_rating + 1)
    
    def initiate_call_up(
        self,
        wrestler_id: str,
        destination_brand: str,
        reason: CallUpReason,
        initiating_gm: Optional[str] = None,
        current_year: Optional[int] = None,
        current_week: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Initiate a call-up from developmental to main roster.
        Returns result dict with success status and message.
        """
        entry = self.developmental_roster.get(wrestler_id)
        if not entry:
            return {
                "success": False,
                "error": "Wrestler not found in developmental roster"
            }
        
        if not entry.check_readiness():
            return {
                "success": False,
                "error": f"Wrestler not ready for call-up. {entry.weeks_in_developmental} weeks in developmental (need {entry.call_up_eligible_week})"
            }
        
        # Record the call-up
        entry.record_call_up(destination_brand, current_year or 0, current_week or 0)
        
        # Create history record
        history = CallUpHistory(
            wrestler_id=wrestler_id,
            wrestler_name=entry.wrestler_name,
            call_up_year=current_year or 0,
            call_up_week=current_week or 0,
            source_brand=DevelopmentalBrand.ROC_VANGUARD.value,
            destination_brand=destination_brand,
            reason=reason,
            initiating_gm=initiating_gm,
        )
        self.call_up_history.append(history)
        self.total_call_ups += 1
        
        # Add to pending call-ups for processing
        self.pending_call_ups.append({
            "wrestler_id": wrestler_id,
            "destination_brand": destination_brand,
            "reason": reason.value,
            "year": current_year,
            "week": current_week,
        })
        
        return {
            "success": True,
            "message": f"{entry.wrestler_name} called up to {destination_brand}",
            "wrestler_name": entry.wrestler_name,
            "destination_brand": destination_brand,
            "reason": reason.label,
            "readiness_score": entry.get_readiness_summary()["readiness_score"],
        }
    
    def process_call_up_outcome(
        self,
        wrestler_id: str,
        success: bool,
        return_to_developmental: bool = False
    ):
        """Process the outcome of a call-up attempt"""
        entry = self.developmental_roster.get(wrestler_id)
        if not entry:
            return
        
        entry.record_main_roster_assignment(success)
        
        if success:
            self.successful_call_ups += 1
        elif return_to_developmental:
            self.returned_talents += 1
            entry.status = CallUpStatus.RETURNED_TO_DEV
        else:
            entry.status = CallUpStatus.RELEASED
            del self.developmental_roster[wrestler_id]
    
    def get_call_up_statistics(self) -> Dict[str, Any]:
        """Get overall call-up statistics"""
        success_rate = (
            (self.successful_call_ups / self.total_call_ups * 100) 
            if self.total_call_ups > 0 else 0.0
        )
        
        return {
            "total_call_ups": self.total_call_ups,
            "successful_call_ups": self.successful_call_ups,
            "returned_talents": self.returned_talents,
            "success_rate": round(success_rate, 2),
            "current_developmental_count": len(self.developmental_roster),
            "ready_for_call_up_count": len(self.get_ready_for_call_up()),
        }
    
    def get_recent_call_ups(self, limit: int = 10) -> List[Dict]:
        """Get recent call-up history"""
        sorted_history = sorted(
            self.call_up_history,
            key=lambda x: (x.call_up_year, x.call_up_week),
            reverse=True
        )
        return [h.to_dict() for h in sorted_history[:limit]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire developmental roster system"""
        return {
            "developmental_roster": [
                entry.to_dict() for entry in self.developmental_roster.values()
            ],
            "call_up_history": self.get_recent_call_ups(20),
            "statistics": self.get_call_up_statistics(),
            "pending_call_ups": self.pending_call_ups,
            "nexus_championship": self.nexus_championship.to_dict(),
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DevelopmentalRosterManager':
        """Deserialize from dictionary"""
        manager = DevelopmentalRosterManager()
        
        # Load roster entries
        for entry_data in data.get("developmental_roster", []):
            entry = DevelopmentalRosterEntry.from_dict(entry_data)
            manager.developmental_roster[entry.wrestler_id] = entry
        
        # Load call-up history
        for history_data in data.get("call_up_history", []):
            history = CallUpHistory(
                wrestler_id=history_data["wrestler_id"],
                wrestler_name=history_data["wrestler_name"],
                call_up_year=history_data["call_up_year"],
                call_up_week=history_data["call_up_week"],
                source_brand=history_data["source_brand"],
                destination_brand=history_data["destination_brand"],
                reason=CallUpReason(history_data["reason"]),
                initiating_gm=history_data.get("initiating_gm"),
                success_outcome=history_data.get("success_outcome"),
                return_date_year=history_data.get("return_date_year"),
                return_date_week=history_data.get("return_date_week"),
            )
            manager.call_up_history.append(history)
        
        # Load statistics
        stats = data.get("statistics", {})
        manager.total_call_ups = stats.get("total_call_ups", 0)
        manager.successful_call_ups = stats.get("successful_call_ups", 0)
        manager.returned_talents = stats.get("returned_talents", 0)
        
        # Load pending call-ups
        manager.pending_call_ups = data.get("pending_call_ups", [])
        
        # Load championship
        champ_data = data.get("nexus_championship", {})
        if champ_data:
            manager.nexus_championship = DevelopmentalChampionship(
                championship_id=champ_data.get("championship_id", "nexus_championship"),
                name=champ_data.get("name", "ROC Vanguard Prospects Championship"),
                current_holder_id=champ_data.get("current_holder_id"),
                current_holder_name=champ_data.get("current_holder_name"),
                won_date_year=champ_data.get("won_date_year"),
                won_date_week=champ_data.get("won_date_week"),
                days_held=champ_data.get("days_held", 0),
                defense_count=champ_data.get("defense_count", 0),
                history=champ_data.get("history", []),
            )
        
        return manager
