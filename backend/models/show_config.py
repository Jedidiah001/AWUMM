"""
Show Configuration Models (Steps 58-72)
Defines show types, pacing management, and production elements
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class ShowType(Enum):
    """Show type categories"""
    WEEKLY_TV = "weekly_tv"
    HOUSE_SHOW = "house_show"
    MINOR_PPV = "minor_ppv"
    MAJOR_PPV = "major_ppv"
    SUPERCARD = "supercard"


class ShowTheme(Enum):
    """Show theme types (Step 72)"""
    STANDARD = "standard"
    ANNIVERSARY = "anniversary"
    TRIBUTE = "tribute"
    WILDCARD = "wildcard"
    EXTREME = "extreme"
    PRIDE = "pride"
    DRAFT = "draft"
    HALLOWEEN = "halloween"
    HOLIDAY = "holiday"
    SEASON_PREMIERE = "season_premiere"
    SEASON_FINALE = "season_finale"
    CHAMPIONSHIP_GALA = "championship_gala"
    LEGENDS_NIGHT = "legends_night"
    GRUDGE_NIGHT = "grudge_night"


class PacingGrade(Enum):
    """Pacing quality grades (Step 63)"""
    EXCELLENT = "Excellent"
    GREAT = "Great"
    GOOD = "Good"
    AVERAGE = "Average"
    POOR = "Poor"
    TERRIBLE = "Terrible"


class ShowCategory(Enum):
    """Broad production categories used by the production planner."""
    WEEKLY = "weekly"
    SPECIAL = "special"
    PPV = "ppv"
    HOUSE_SHOW = "house_show"


class OpeningSegmentType(Enum):
    HOT_MATCH = "hot_match"
    PROMO_IN_RING = "promo_in_ring"
    AUTHORITY_OPENS = "authority_opens"
    COLD_OPEN_VIDEO = "cold_open_video"
    DARK_RETURN = "dark_return"
    CHAMPIONSHIP_ANNOUNCEMENT = "championship_announcement"


class CommercialBreakStrategy(Enum):
    STANDARD = "standard"
    MINIMAL = "minimal"
    HEAVY = "heavy"


@dataclass
class BrandTimeSlot:
    brand: str
    day: str
    start_time: str
    duration_minutes: int
    commercial_breaks: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'brand': self.brand,
            'day': self.day,
            'start_time': self.start_time,
            'duration_minutes': self.duration_minutes,
            'commercial_breaks': self.commercial_breaks,
        }


BRAND_TIME_SLOTS = {
    'ROC Alpha': BrandTimeSlot('ROC Alpha', 'Monday', '8:00 PM', 120, 8),
    'ROC Velocity': BrandTimeSlot('ROC Velocity', 'Friday', '9:00 PM', 120, 8),
    'ROC Vanguard': BrandTimeSlot('ROC Vanguard', 'Saturday', '7:00 PM', 90, 6),
    'Cross-Brand': BrandTimeSlot('Cross-Brand', 'Sunday', '8:00 PM', 180, 3),
}


SHOW_TYPE_DURATIONS = {
    'weekly_tv': 120,
    'house_show': 150,
    'minor_ppv': 180,
    'major_ppv': 240,
    'supercard': 240,
}


TARGET_MATCH_COUNTS = {
    'weekly_tv': {'min': 4, 'target': 5, 'max': 6},
    'house_show': {'min': 5, 'target': 6, 'max': 7},
    'minor_ppv': {'min': 6, 'target': 7, 'max': 8},
    'major_ppv': {'min': 8, 'target': 9, 'max': 10},
    'supercard': {'min': 8, 'target': 10, 'max': 11},
}


@dataclass
class SegmentTypeConfig:
    segment_type: str
    display_name: str
    description: str
    suitable_for_opening: bool = False
    ppv_only: bool = False
    can_end_in_brawl: bool = False
    can_cause_injury: bool = False
    typical_duration: int = 5
    crowd_energy_impact: int = 0
    advances_feud: bool = False
    creates_heat: bool = False
    creates_pop: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'segment_type': self.segment_type,
            'type': self.segment_type,
            'display_name': self.display_name,
            'description': self.description,
            'suitable_for_opening': self.suitable_for_opening,
            'ppv_only': self.ppv_only,
            'can_end_in_brawl': self.can_end_in_brawl,
            'can_cause_injury': self.can_cause_injury,
            'typical_duration': self.typical_duration,
            'crowd_energy_impact': self.crowd_energy_impact,
            'advances_feud': self.advances_feud,
            'creates_heat': self.creates_heat,
            'creates_pop': self.creates_pop,
        }


SEGMENT_TYPE_CATALOGUE = {
    'promo': SegmentTypeConfig(
        'promo', 'Promo Segment',
        'In-ring microphone segment to advance characters or feuds.',
        suitable_for_opening=True,
        typical_duration=6,
        crowd_energy_impact=5,
        advances_feud=True,
        creates_pop=True,
    ),
    'interview': SegmentTypeConfig(
        'interview', 'Backstage Interview',
        'Backstage update or confrontation that cools the crowd slightly.',
        typical_duration=4,
        crowd_energy_impact=-2,
        advances_feud=True,
    ),
    'vignette': SegmentTypeConfig(
        'vignette', 'Vignette',
        'Pre-produced package for hype, debuts, or character building.',
        suitable_for_opening=True,
        typical_duration=3,
        crowd_energy_impact=3,
        creates_pop=True,
    ),
    'contract_signing': SegmentTypeConfig(
        'contract_signing', 'Contract Signing',
        'High-tension signing segment that can end in chaos.',
        suitable_for_opening=True,
        can_end_in_brawl=True,
        typical_duration=8,
        crowd_energy_impact=7,
        advances_feud=True,
        creates_heat=True,
    ),
    'talk_show': SegmentTypeConfig(
        'talk_show', 'Talk Show Segment',
        'Hosted in-ring interview or panel segment with personality focus.',
        typical_duration=7,
        crowd_energy_impact=2,
        advances_feud=True,
        creates_heat=True,
    ),
    'backstage_attack': SegmentTypeConfig(
        'backstage_attack', 'Backstage Attack',
        'Ambush segment that spikes energy and can escalate violence.',
        can_end_in_brawl=True,
        can_cause_injury=True,
        typical_duration=4,
        crowd_energy_impact=10,
        advances_feud=True,
        creates_heat=True,
    ),
    'announcement': SegmentTypeConfig(
        'announcement', 'Authority Announcement',
        'Formal update about titles, drafts, or management decisions.',
        suitable_for_opening=True,
        typical_duration=5,
        crowd_energy_impact=-4,
    ),
    'run_in': SegmentTypeConfig(
        'run_in', 'Run-In Angle',
        'Interference or surprise involvement to push a feud forward.',
        ppv_only=True,
        can_end_in_brawl=True,
        typical_duration=4,
        crowd_energy_impact=9,
        advances_feud=True,
        creates_heat=True,
        creates_pop=True,
    ),
}


@dataclass
class ShowProductionConfig:
    show_type: str
    brand: str
    show_theme: ShowTheme = ShowTheme.STANDARD
    opening_segment_type: OpeningSegmentType = OpeningSegmentType.HOT_MATCH
    commercial_break_strategy: CommercialBreakStrategy = CommercialBreakStrategy.STANDARD
    has_surprise_debut: bool = False
    has_surprise_return: bool = False
    has_run_ins: bool = False
    run_in_count: int = 0
    has_dark_matches: bool = True
    dark_match_count: int = 1

    @classmethod
    def from_scheduled_show(cls, scheduled_show) -> 'ShowProductionConfig':
        show_type = getattr(scheduled_show, 'show_type', 'weekly_tv')
        brand = getattr(scheduled_show, 'brand', 'ROC Alpha')
        is_ppv = getattr(scheduled_show, 'is_ppv', False)
        tier = getattr(scheduled_show, 'tier', '')
        is_house_show = show_type == 'house_show'
        is_supercard = show_type == 'supercard' or tier == 'major'
        return cls(
            show_type=show_type,
            brand=brand,
            commercial_break_strategy=CommercialBreakStrategy.MINIMAL if is_ppv else CommercialBreakStrategy.STANDARD,
            has_dark_matches=not is_ppv,
            dark_match_count=0 if is_ppv else (2 if is_house_show or is_supercard else 1),
        )

    def get_theme_config(self):
        return SHOW_THEME_CONFIGS.get(self.show_theme, SHOW_THEME_CONFIGS[ShowTheme.STANDARD])


@dataclass
class ShowTemplate:
    """Template configuration for show types (Steps 58-61)"""
    template_id: str
    show_type: ShowType
    template_name: str
    brand: str
    
    # Timing
    default_duration_minutes: int = 120
    default_match_count: int = 5
    default_segment_count: int = 3
    
    # Production
    has_intermission: bool = False
    intermission_minutes: int = 0
    allows_commercials: bool = True
    commercial_break_count: int = 0
    
    # Economics
    ticket_price_base: int = 50
    production_cost_base: int = 10000
    
    # Status
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'template_id': self.template_id,
            'show_type': self.show_type.value,
            'template_name': self.template_name,
            'brand': self.brand,
            'default_duration_minutes': self.default_duration_minutes,
            'default_match_count': self.default_match_count,
            'default_segment_count': self.default_segment_count,
            'has_intermission': self.has_intermission,
            'intermission_minutes': self.intermission_minutes,
            'allows_commercials': self.allows_commercials,
            'commercial_break_count': self.commercial_break_count,
            'ticket_price_base': self.ticket_price_base,
            'production_cost_base': self.production_cost_base,
            'is_active': self.is_active
        }


@dataclass
class ShowPacingManager:
    """
    Manages show pacing and crowd energy (Step 63)
    Tracks energy throughout the show and grades pacing quality
    """
    show_type: str
    brand: str
    total_available_minutes: int = 120
    commercial_breaks_planned: int = 3
    
    # Runtime tracking
    elapsed_minutes: int = 0
    items_processed: int = 0
    
    # Crowd energy tracking
    crowd_energy: int = 50  # 0-100 scale
    energy_history: List[int] = field(default_factory=list)
    peak_energy: int = 50
    
    # Pacing metrics
    dead_spots: int = 0  # Segments where energy drops significantly
    hot_stretches: int = 0  # Sustained high energy periods
    commercial_breaks_taken: int = 0
    commercial_break_positions: List[int] = field(default_factory=list)
    snapshots: List[Dict[str, Any]] = field(default_factory=list)
    commercial_break_strategy: str = "standard"
    
    def __post_init__(self):
        """Initialize based on show type"""
        if self.show_type in ['major_ppv', 'supercard']:
            self.total_available_minutes = 240
            self.commercial_breaks_planned = 0
        elif self.show_type == 'minor_ppv':
            self.total_available_minutes = 180
            self.commercial_breaks_planned = 0
        elif self.show_type == 'house_show':
            self.total_available_minutes = 150
            self.commercial_breaks_planned = 0

        if self.commercial_breaks_planned == 0:
            self.commercial_break_strategy = "none"
        elif self.commercial_breaks_planned <= 2:
            self.commercial_break_strategy = "minimal"
        else:
            self.commercial_break_strategy = "standard"

        self.energy_history.append(self.crowd_energy)
    
    def record_item(
        self,
        position: int,
        item_type: str,
        item_name: str,
        duration_minutes: int,
        star_rating: float = 0.0,
        segment_type: str = None
    ):
        """
        Record a match or segment and update crowd energy
        
        Args:
            position: Card position (1-based)
            item_type: 'match' or 'segment'
            item_name: Display name
            duration_minutes: Length in minutes
            star_rating: Match quality (0-5) or segment quality
            segment_type: If segment, the type (promo, interview, etc)
        """
        self.items_processed += 1
        self.elapsed_minutes += duration_minutes
        
        # Calculate energy impact
        if item_type == 'match':
            energy_change = self._calculate_match_energy_impact(
                star_rating, position, duration_minutes
            )
        else:
            energy_change = self._calculate_segment_energy_impact(
                segment_type, position, duration_minutes
            )
        
        # Apply energy change
        old_energy = self.crowd_energy
        self.crowd_energy = max(0, min(100, self.crowd_energy + energy_change))
        
        # Track peak
        if self.crowd_energy > self.peak_energy:
            self.peak_energy = self.crowd_energy
        
        # Record in history
        self.energy_history.append(self.crowd_energy)
        
        # Detect dead spots (energy drop > 20 points)
        if old_energy - self.crowd_energy > 20:
            self.dead_spots += 1
        
        # Detect hot stretches (sustained 75+ energy for 3+ items)
        if len(self.energy_history) >= 3:
            if all(e >= 75 for e in self.energy_history[-3:]):
                self.hot_stretches += 1

        self.snapshots.append({
            'position': position,
            'item_type': item_type,
            'item_name': item_name,
            'duration_minutes': duration_minutes,
            'segment_type': segment_type,
            'star_rating': float(star_rating or 0.0),
            'crowd_energy_before': old_energy,
            'crowd_energy_after': self.crowd_energy,
            'energy_change': energy_change,
        })
    
    def _calculate_match_energy_impact(
        self,
        star_rating: float,
        position: int,
        duration: int
    ) -> int:
        """Calculate how match quality affects crowd energy"""
        base_impact = 0
        
        # Quality-based impact
        if star_rating >= 4.5:
            base_impact = 15
        elif star_rating >= 4.0:
            base_impact = 12
        elif star_rating >= 3.5:
            base_impact = 8
        elif star_rating >= 3.0:
            base_impact = 5
        elif star_rating >= 2.5:
            base_impact = 2
        elif star_rating >= 2.0:
            base_impact = -2
        else:
            base_impact = -5
        
        # Position modifier (main event area gets boost)
        if position >= 7:  # Main event area
            base_impact += 3
        elif position <= 2:  # Opener
            base_impact += 2
        
        # Duration modifier (very long matches can tire crowd)
        if duration > 25:
            base_impact -= 3
        elif duration > 20:
            base_impact -= 1
        
        return base_impact
    
    def _calculate_segment_energy_impact(
        self,
        segment_type: str,
        position: int,
        duration: int
    ) -> int:
        """Calculate how segments affect crowd energy"""
        # Segments generally provide rest but can be engaging
        base_impact = 0
        
        if segment_type in ['promo', 'confrontation', 'contract_signing']:
            base_impact = 5  # Exciting verbal exchanges
        elif segment_type in ['promo_battle']:
            base_impact = 8  # High drama
        elif segment_type in ['backstage_attack', 'in_ring_attack']:
            base_impact = 10  # Chaos!
        elif segment_type in ['interview']:
            base_impact = -2  # Cooldown
        elif segment_type in ['announcement']:
            base_impact = -5  # Usually boring
        else:
            base_impact = 0
        
        # Opening segments are important
        if position == 1:
            base_impact += 3
        
        # Too long = crowd loses interest
        if duration > 10:
            base_impact -= 5
        
        return base_impact
    
    def should_take_commercial_break(self) -> bool:
        """Determine if it's time for a commercial break (Step 68)"""
        if not self.commercial_breaks_planned:
            return False
        
        if self.commercial_breaks_taken >= self.commercial_breaks_planned:
            return False
        
        # Take break after cooldown segments or low-energy matches
        if self.crowd_energy < 60:
            return True
        
        # Take break at regular intervals
        items_per_break = max(2, self.items_processed // self.commercial_breaks_planned)
        if self.items_processed % items_per_break == 0:
            return True
        
        return False
    
    def take_commercial_break(self):
        """Process a commercial break"""
        self.commercial_breaks_taken += 1
        self.commercial_break_positions.append(self.items_processed)
        self.elapsed_minutes += 3  # Standard 3-minute break

        # Slight energy recovery during break
        self.crowd_energy = min(100, self.crowd_energy + 5)
        self.energy_history.append(self.crowd_energy)
    
    @property
    def is_overrunning(self) -> bool:
        """Check if show is exceeding planned runtime (Step 64)"""
        return self.elapsed_minutes > self.total_available_minutes
    
    @property
    def overrun_minutes(self) -> int:
        """How many minutes over time"""
        return max(0, self.elapsed_minutes - self.total_available_minutes)
    
    def get_pacing_grade(self) -> PacingGrade:
        """Calculate overall pacing quality (Step 63)"""
        score = 0
        
        # Peak energy achievement
        if self.peak_energy >= 90:
            score += 30
        elif self.peak_energy >= 80:
            score += 25
        elif self.peak_energy >= 70:
            score += 20
        elif self.peak_energy >= 60:
            score += 10
        
        # Final energy (send them home happy)
        final_energy = self.energy_history[-1] if self.energy_history else 50
        if final_energy >= 80:
            score += 25
        elif final_energy >= 70:
            score += 20
        elif final_energy >= 60:
            score += 15
        elif final_energy >= 50:
            score += 10
        
        # Hot stretches (sustained excitement)
        score += min(20, self.hot_stretches * 5)
        
        # Dead spots penalty
        score -= self.dead_spots * 10
        
        # Runtime management
        if not self.is_overrunning:
            score += 10
        elif self.overrun_minutes <= 5:
            score += 5
        else:
            score -= 15
        
        # Grade based on score
        if score >= 85:
            return PacingGrade.EXCELLENT
        elif score >= 70:
            return PacingGrade.GREAT
        elif score >= 55:
            return PacingGrade.GOOD
        elif score >= 40:
            return PacingGrade.AVERAGE
        elif score >= 25:
            return PacingGrade.POOR
        else:
            return PacingGrade.TERRIBLE
    
    def to_dict(self) -> Dict[str, Any]:
        """Export pacing report"""
        return {
            'show_type': self.show_type,
            'brand': self.brand,
            'total_available_minutes': self.total_available_minutes,
            'elapsed_minutes': self.elapsed_minutes,
            'is_overrunning': self.is_overrunning,
            'overrun_minutes': self.overrun_minutes,
            'items_processed': self.items_processed,
            'opening_energy': self.energy_history[0] if self.energy_history else 50,
            'peak_energy': self.peak_energy,
            'final_crowd_energy': self.energy_history[-1] if self.energy_history else 50,
            'energy_curve': self.energy_history,
            'dead_spots': self.dead_spots,
            'hot_stretches': self.hot_stretches,
            'commercial_breaks_planned': self.commercial_breaks_planned,
            'commercial_breaks_taken': self.commercial_breaks_taken,
            'commercial_break_positions': self.commercial_break_positions,
            'commercial_break_strategy': self.commercial_break_strategy,
            'snapshots': self.snapshots,
            'pacing_grade': self.get_pacing_grade().value
        }


# ============================================================================
# STEP 72: Show Theme Configurations
# ============================================================================

@dataclass
class ShowThemeConfig:
    """Configuration for themed shows (Step 72)"""
    theme_id: str
    theme_name: str
    display_name: str
    description: str
    
    # Bonuses
    bonus_match_quality: float = 0.0  # Added to star ratings
    bonus_attendance_pct: float = 0.0  # Attendance multiplier
    bonus_revenue_pct: float = 0.0  # Revenue multiplier
    
    # Special rules
    special_stipulation: Optional[str] = None  # Applied to all matches
    extra_event_log_prefix: str = ""  # Added to event descriptions
    required_segment_types: List[str] = field(default_factory=list)
    preferred_match_stipulations: List[str] = field(default_factory=list)
    
    # Activation
    trigger_condition: str = "manual"  # When this theme activates
    is_active: bool = True

    @property
    def label(self) -> str:
        return self.display_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            'theme_id': self.theme_id,
            'theme_name': self.theme_name,
            'value': self.theme_id,
            'display_name': self.display_name,
            'description': self.description,
            'bonus_match_quality': self.bonus_match_quality,
            'bonus_attendance_pct': self.bonus_attendance_pct,
            'bonus_revenue_pct': self.bonus_revenue_pct,
            'special_stipulation': self.special_stipulation,
            'extra_event_log_prefix': self.extra_event_log_prefix,
            'required_segments': self.required_segment_types,
            'required_segment_types': self.required_segment_types,
            'preferred_stipulations': self.preferred_match_stipulations,
            'preferred_match_stipulations': self.preferred_match_stipulations,
            'trigger_condition': self.trigger_condition,
            'is_active': self.is_active,
        }


# Predefined show themes
SHOW_THEME_CONFIGS = {
    ShowTheme.STANDARD: ShowThemeConfig(
        theme_id="standard",
        theme_name="Standard Show",
        display_name="Standard Show",
        description="Regular show with no special theme"
    ),
    
    ShowTheme.ANNIVERSARY: ShowThemeConfig(
        theme_id="anniversary",
        theme_name="Anniversary Special",
        display_name="🎉 ANNIVERSARY CELEBRATION",
        description="Celebrating the promotion's anniversary with nostalgia and legends",
        bonus_match_quality=0.25,
        bonus_attendance_pct=0.10,
        bonus_revenue_pct=0.15,
        extra_event_log_prefix="🎉 ANNIVERSARY"
    ),
    
    ShowTheme.TRIBUTE: ShowThemeConfig(
        theme_id="tribute",
        theme_name="Tribute Night",
        display_name="🕊️ TRIBUTE NIGHT",
        description="Honoring a retired or deceased wrestling legend",
        bonus_match_quality=0.15,
        bonus_attendance_pct=0.05,
        bonus_revenue_pct=0.05,
        extra_event_log_prefix="🕊️ TRIBUTE"
    ),
    
    ShowTheme.WILDCARD: ShowThemeConfig(
        theme_id="wildcard",
        theme_name="Wildcard Night",
        display_name="🎲 WILDCARD CHAOS",
        description="Cross-brand chaos with unexpected matchups and surprises",
        bonus_match_quality=0.10,
        bonus_attendance_pct=0.08,
        bonus_revenue_pct=0.10,
        special_stipulation="No DQ",
        extra_event_log_prefix="🎲 WILDCARD"
    ),
    
    ShowTheme.EXTREME: ShowThemeConfig(
        theme_id="extreme",
        theme_name="Extreme Rules",
        display_name="⚡ EXTREME RULES",
        description="All matches have relaxed rules - hardcore wrestling showcase",
        bonus_match_quality=0.20,
        bonus_attendance_pct=0.12,
        bonus_revenue_pct=0.18,
        special_stipulation="No Disqualification",
        extra_event_log_prefix="⚡ EXTREME"
    ),
    
    ShowTheme.PRIDE: ShowThemeConfig(
        theme_id="pride",
        theme_name="Pride Celebration",
        display_name="🏳️‍🌈 PRIDE CELEBRATION",
        description="Celebrating diversity, inclusion, and equality",
        bonus_match_quality=0.05,
        bonus_attendance_pct=0.15,
        bonus_revenue_pct=0.10,
        extra_event_log_prefix="🏳️‍🌈 PRIDE"
    ),
    
    ShowTheme.DRAFT: ShowThemeConfig(
        theme_id="draft",
        theme_name="Draft Night",
        display_name="📋 DRAFT NIGHT",
        description="Annual brand draft with surprise roster shakeups",
        bonus_match_quality=0.10,
        bonus_attendance_pct=0.20,
        bonus_revenue_pct=0.15,
        extra_event_log_prefix="📋 DRAFT"
    ),
    
    ShowTheme.HALLOWEEN: ShowThemeConfig(
        theme_id="halloween",
        theme_name="Halloween Havoc",
        display_name="🎃 HALLOWEEN HAVOC",
        description="Spooky themed show with special decorations and gimmick matches",
        bonus_match_quality=0.15,
        bonus_attendance_pct=0.10,
        bonus_revenue_pct=0.12,
        extra_event_log_prefix="🎃 HALLOWEEN"
    ),
    
    ShowTheme.HOLIDAY: ShowThemeConfig(
        theme_id="holiday",
        theme_name="Holiday Special",
        display_name="🎄 HOLIDAY SPECIAL",
        description="End-of-year celebration with festive atmosphere",
        bonus_match_quality=0.10,
        bonus_attendance_pct=0.18,
        bonus_revenue_pct=0.15,
        extra_event_log_prefix="🎄 HOLIDAY"
    )
}
