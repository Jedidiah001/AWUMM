"""
Show Template Models
Defines templates for different show types with time slots, segment structure, and production values.

STEPS 58-72 IMPLEMENTATION:
✅ Step 58: Weekly TV Show Management
✅ Step 59: Monthly PPV Events
✅ Step 60: House Show Tours
✅ Step 61: Supercard Special Events
✅ Step 64: Time Slot Allocation
✅ Step 68: Commercial Break Strategy
✅ Step 71: Dark Match Booking
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class ShowType(Enum):
    """Types of wrestling shows"""
    WEEKLY_TV = "weekly_tv"
    MINOR_PPV = "minor_ppv"
    MAJOR_PPV = "major_ppv"
    HOUSE_SHOW = "house_show"
    SUPERCARD = "supercard"
    SPECIAL_EVENT = "special_event"


class SegmentSlotType(Enum):
    """Types of segment slots in a show template"""
    OPENING = "opening"
    MATCH = "match"
    SEGMENT = "segment"
    COMMERCIAL = "commercial"
    MAIN_EVENT = "main_event"
    COOL_DOWN = "cool_down"
    DARK_MATCH = "dark_match"


@dataclass
class TimeSlot:
    """
    A time slot in a show template.
    Defines what can go in each portion of the show.
    """
    slot_id: str
    slot_type: SegmentSlotType
    position: int  # Order in the show (1 = first)
    
    # Time allocation
    min_duration_minutes: int = 5
    max_duration_minutes: int = 20
    target_duration_minutes: int = 10
    
    # Slot properties
    is_flexible: bool = True  # Can be extended/shortened
    can_overrun: bool = False  # Allowed to go over time
    is_required: bool = True  # Must be filled
    
    # Content restrictions
    allowed_segment_types: List[str] = field(default_factory=list)
    importance_level: str = "normal"  # 'opening', 'feature', 'main_event', 'filler'
    
    # Commercial break placement
    commercial_after: bool = False
    commercial_duration: int = 3  # Minutes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'slot_id': self.slot_id,
            'slot_type': self.slot_type.value,
            'position': self.position,
            'min_duration_minutes': self.min_duration_minutes,
            'max_duration_minutes': self.max_duration_minutes,
            'target_duration_minutes': self.target_duration_minutes,
            'is_flexible': self.is_flexible,
            'can_overrun': self.can_overrun,
            'is_required': self.is_required,
            'allowed_segment_types': self.allowed_segment_types,
            'importance_level': self.importance_level,
            'commercial_after': self.commercial_after,
            'commercial_duration': self.commercial_duration
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TimeSlot':
        return TimeSlot(
            slot_id=data.get('slot_id', str(uuid.uuid4())[:8]),
            slot_type=SegmentSlotType(data.get('slot_type', 'match')),
            position=data.get('position', 1),
            min_duration_minutes=data.get('min_duration_minutes', 5),
            max_duration_minutes=data.get('max_duration_minutes', 20),
            target_duration_minutes=data.get('target_duration_minutes', 10),
            is_flexible=data.get('is_flexible', True),
            can_overrun=data.get('can_overrun', False),
            is_required=data.get('is_required', True),
            allowed_segment_types=data.get('allowed_segment_types', []),
            importance_level=data.get('importance_level', 'normal'),
            commercial_after=data.get('commercial_after', False),
            commercial_duration=data.get('commercial_duration', 3)
        )


@dataclass
class DarkMatchConfig:
    """Configuration for dark matches at a show"""
    pre_show_count: int = 0
    post_show_count: int = 0
    
    # Purpose
    allow_tryouts: bool = True
    allow_developmental: bool = True
    allow_crowd_warmup: bool = True
    allow_crowd_cooldown: bool = True
    
    # Duration
    max_duration_per_match: int = 10  # Minutes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pre_show_count': self.pre_show_count,
            'post_show_count': self.post_show_count,
            'allow_tryouts': self.allow_tryouts,
            'allow_developmental': self.allow_developmental,
            'allow_crowd_warmup': self.allow_crowd_warmup,
            'allow_crowd_cooldown': self.allow_crowd_cooldown,
            'max_duration_per_match': self.max_duration_per_match
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DarkMatchConfig':
        return DarkMatchConfig(
            pre_show_count=data.get('pre_show_count', 0),
            post_show_count=data.get('post_show_count', 0),
            allow_tryouts=data.get('allow_tryouts', True),
            allow_developmental=data.get('allow_developmental', True),
            allow_crowd_warmup=data.get('allow_crowd_warmup', True),
            allow_crowd_cooldown=data.get('allow_crowd_cooldown', True),
            max_duration_per_match=data.get('max_duration_per_match', 10)
        )


@dataclass
class ShowTemplate:
    """
    Template defining the structure of a show type.
    Used by AI Director to generate appropriately structured cards.
    """
    template_id: str
    show_type: ShowType
    template_name: str
    
    # ========================================================================
    # DURATION SETTINGS (Step 64: Time Slot Allocation)
    # ========================================================================
    
    total_duration_minutes: int = 120  # Total show length
    match_time_budget: int = 80  # Minutes for matches
    segment_time_budget: int = 25  # Minutes for segments
    commercial_time_budget: int = 15  # Minutes for commercials (TV only)
    
    # Buffer time for overruns/transitions
    buffer_time_minutes: int = 5
    
    # ========================================================================
    # CARD STRUCTURE
    # ========================================================================
    
    target_match_count: int = 5
    min_match_count: int = 3
    max_match_count: int = 8
    
    target_segment_count: int = 3
    min_segment_count: int = 1
    max_segment_count: int = 5
    
    # Time slots (ordered structure)
    time_slots: List[TimeSlot] = field(default_factory=list)
    
    # ========================================================================
    # COMMERCIAL BREAKS (Step 68)
    # ========================================================================
    
    has_commercials: bool = True
    commercial_break_count: int = 4
    commercial_break_duration: int = 3  # Minutes per break
    
    # Positioning rules
    max_time_between_commercials: int = 20  # Minutes
    never_cut_during: List[str] = field(default_factory=lambda: ['main_event', 'title_match'])
    
    # ========================================================================
    # DARK MATCHES (Step 71)
    # ========================================================================
    
    dark_match_config: DarkMatchConfig = field(default_factory=DarkMatchConfig)
    
    # ========================================================================
    # PRODUCTION VALUES
    # ========================================================================
    
    ticket_price_base: int = 50
    production_cost_multiplier: float = 1.0
    expected_attendance_multiplier: float = 1.0
    
    # Quality expectations
    target_show_rating: float = 3.0  # Stars
    min_acceptable_rating: float = 2.0
    
    # ========================================================================
    # PACING REQUIREMENTS (Step 63)
    # ========================================================================
    
    requires_strong_opening: bool = True
    requires_strong_main_event: bool = True
    allow_back_to_back_matches: bool = True
    max_consecutive_matches: int = 3
    
    # Crowd energy management
    target_energy_curve: str = "build_to_main"  # 'build_to_main', 'peaks_and_valleys', 'constant_high'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'template_id': self.template_id,
            'show_type': self.show_type.value,
            'template_name': self.template_name,
            'total_duration_minutes': self.total_duration_minutes,
            'match_time_budget': self.match_time_budget,
            'segment_time_budget': self.segment_time_budget,
            'commercial_time_budget': self.commercial_time_budget,
            'buffer_time_minutes': self.buffer_time_minutes,
            'target_match_count': self.target_match_count,
            'min_match_count': self.min_match_count,
            'max_match_count': self.max_match_count,
            'target_segment_count': self.target_segment_count,
            'min_segment_count': self.min_segment_count,
            'max_segment_count': self.max_segment_count,
            'time_slots': [slot.to_dict() for slot in self.time_slots],
            'has_commercials': self.has_commercials,
            'commercial_break_count': self.commercial_break_count,
            'commercial_break_duration': self.commercial_break_duration,
            'max_time_between_commercials': self.max_time_between_commercials,
            'never_cut_during': self.never_cut_during,
            'dark_match_config': self.dark_match_config.to_dict(),
            'ticket_price_base': self.ticket_price_base,
            'production_cost_multiplier': self.production_cost_multiplier,
            'expected_attendance_multiplier': self.expected_attendance_multiplier,
            'target_show_rating': self.target_show_rating,
            'min_acceptable_rating': self.min_acceptable_rating,
            'requires_strong_opening': self.requires_strong_opening,
            'requires_strong_main_event': self.requires_strong_main_event,
            'allow_back_to_back_matches': self.allow_back_to_back_matches,
            'max_consecutive_matches': self.max_consecutive_matches,
            'target_energy_curve': self.target_energy_curve
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ShowTemplate':
        template = ShowTemplate(
            template_id=data.get('template_id', str(uuid.uuid4())[:8]),
            show_type=ShowType(data.get('show_type', 'weekly_tv')),
            template_name=data.get('template_name', 'Default Template')
        )
        
        # Duration
        template.total_duration_minutes = data.get('total_duration_minutes', 120)
        template.match_time_budget = data.get('match_time_budget', 80)
        template.segment_time_budget = data.get('segment_time_budget', 25)
        template.commercial_time_budget = data.get('commercial_time_budget', 15)
        template.buffer_time_minutes = data.get('buffer_time_minutes', 5)
        
        # Card structure
        template.target_match_count = data.get('target_match_count', 5)
        template.min_match_count = data.get('min_match_count', 3)
        template.max_match_count = data.get('max_match_count', 8)
        template.target_segment_count = data.get('target_segment_count', 3)
        template.min_segment_count = data.get('min_segment_count', 1)
        template.max_segment_count = data.get('max_segment_count', 5)
        
        # Time slots
        template.time_slots = [TimeSlot.from_dict(slot) for slot in data.get('time_slots', [])]
        
        # Commercials
        template.has_commercials = data.get('has_commercials', True)
        template.commercial_break_count = data.get('commercial_break_count', 4)
        template.commercial_break_duration = data.get('commercial_break_duration', 3)
        template.max_time_between_commercials = data.get('max_time_between_commercials', 20)
        template.never_cut_during = data.get('never_cut_during', ['main_event', 'title_match'])
        
        # Dark matches
        if 'dark_match_config' in data:
            template.dark_match_config = DarkMatchConfig.from_dict(data['dark_match_config'])
        
        # Production
        template.ticket_price_base = data.get('ticket_price_base', 50)
        template.production_cost_multiplier = data.get('production_cost_multiplier', 1.0)
        template.expected_attendance_multiplier = data.get('expected_attendance_multiplier', 1.0)
        template.target_show_rating = data.get('target_show_rating', 3.0)
        template.min_acceptable_rating = data.get('min_acceptable_rating', 2.0)
        
        # Pacing
        template.requires_strong_opening = data.get('requires_strong_opening', True)
        template.requires_strong_main_event = data.get('requires_strong_main_event', True)
        template.allow_back_to_back_matches = data.get('allow_back_to_back_matches', True)
        template.max_consecutive_matches = data.get('max_consecutive_matches', 3)
        template.target_energy_curve = data.get('target_energy_curve', 'build_to_main')
        
        return template
    
    # ========================================================================
    # TIME SLOT HELPERS
    # ========================================================================
    
    def get_remaining_time(self, used_time: int) -> int:
        """Calculate remaining time in the show"""
        return self.total_duration_minutes - used_time - self.commercial_time_budget
    
    def get_average_match_time(self) -> int:
        """Calculate expected average match duration"""
        if self.target_match_count == 0:
            return 15
        return self.match_time_budget // self.target_match_count
    
    def get_average_segment_time(self) -> int:
        """Calculate expected average segment duration"""
        if self.target_segment_count == 0:
            return 5
        return self.segment_time_budget // self.target_segment_count
    
    def validate_card_timing(self, matches: list, segments: list) -> Dict[str, Any]:
        """
        Validate that a card fits within the time budget.
        Returns validation result with warnings/errors.
        """
        total_match_time = sum(getattr(m, 'expected_duration', 15) for m in matches)
        total_segment_time = sum(getattr(s, 'duration_minutes', 5) for s in segments)
        total_time = total_match_time + total_segment_time
        
        available_time = self.total_duration_minutes - self.commercial_time_budget - self.buffer_time_minutes
        
        result = {
            'is_valid': True,
            'total_match_time': total_match_time,
            'total_segment_time': total_segment_time,
            'total_content_time': total_time,
            'available_time': available_time,
            'buffer_remaining': available_time - total_time,
            'warnings': [],
            'errors': []
        }
        
        # Check overrun
        if total_time > available_time:
            overrun = total_time - available_time
            if overrun > self.buffer_time_minutes:
                result['is_valid'] = False
                result['errors'].append(f"Show overruns by {overrun} minutes (exceeds buffer)")
            else:
                result['warnings'].append(f"Show is tight - only {self.buffer_time_minutes - overrun} minutes buffer")
        
        # Check underrun
        elif total_time < available_time - 15:
            underrun = available_time - total_time
            result['warnings'].append(f"Show has {underrun} minutes of dead air")
        
        # Check match count
        if len(matches) < self.min_match_count:
            result['warnings'].append(f"Only {len(matches)} matches (minimum: {self.min_match_count})")
        elif len(matches) > self.max_match_count:
            result['warnings'].append(f"{len(matches)} matches exceeds maximum of {self.max_match_count}")
        
        return result


# ============================================================================
# DEFAULT SHOW TEMPLATES
# ============================================================================

class ShowTemplateFactory:
    """Factory for creating standard show templates"""
    
    @staticmethod
    def create_weekly_tv_template(brand: str = "ROC Alpha") -> ShowTemplate:
        """
        STEP 58: Weekly TV Show Template
        - 2 hours (120 minutes)
        - 4-5 matches
        - 2-3 segments
        - 4 commercial breaks
        - 1-2 dark matches (pre-show)
        """
        template = ShowTemplate(
            template_id=f"weekly_tv_{brand.lower().replace(' ', '_')}",
            show_type=ShowType.WEEKLY_TV,
            template_name=f"{brand} Weekly TV",
            
            # 2-hour show
            total_duration_minutes=120,
            match_time_budget=70,
            segment_time_budget=25,
            commercial_time_budget=20,
            buffer_time_minutes=5,
            
            # Card structure
            target_match_count=5,
            min_match_count=4,
            max_match_count=6,
            target_segment_count=3,
            min_segment_count=2,
            max_segment_count=4,
            
            # Commercials
            has_commercials=True,
            commercial_break_count=4,
            commercial_break_duration=5,
            max_time_between_commercials=20,
            
            # Dark matches
            dark_match_config=DarkMatchConfig(
                pre_show_count=1,
                post_show_count=0,
                allow_crowd_warmup=True
            ),
            
            # Production
            ticket_price_base=40,
            production_cost_multiplier=1.0,
            expected_attendance_multiplier=0.8,
            
            # Pacing
            requires_strong_opening=True,
            requires_strong_main_event=True,
            target_energy_curve="build_to_main"
        )
        
        # Define time slots
        template.time_slots = [
            TimeSlot(
                slot_id="opening",
                slot_type=SegmentSlotType.OPENING,
                position=1,
                min_duration_minutes=5,
                max_duration_minutes=10,
                target_duration_minutes=7,
                importance_level="opening",
                commercial_after=True
            ),
            TimeSlot(
                slot_id="match_1",
                slot_type=SegmentSlotType.MATCH,
                position=2,
                min_duration_minutes=8,
                max_duration_minutes=15,
                target_duration_minutes=12,
                importance_level="feature",
                commercial_after=True
            ),
            TimeSlot(
                slot_id="segment_1",
                slot_type=SegmentSlotType.SEGMENT,
                position=3,
                min_duration_minutes=3,
                max_duration_minutes=8,
                target_duration_minutes=5,
                commercial_after=False
            ),
            TimeSlot(
                slot_id="match_2",
                slot_type=SegmentSlotType.MATCH,
                position=4,
                min_duration_minutes=6,
                max_duration_minutes=12,
                target_duration_minutes=10,
                importance_level="normal",
                commercial_after=True
            ),
            TimeSlot(
                slot_id="match_3",
                slot_type=SegmentSlotType.MATCH,
                position=5,
                min_duration_minutes=6,
                max_duration_minutes=12,
                target_duration_minutes=10,
                importance_level="normal",
                commercial_after=False
            ),
            TimeSlot(
                slot_id="segment_2",
                slot_type=SegmentSlotType.SEGMENT,
                position=6,
                min_duration_minutes=3,
                max_duration_minutes=8,
                target_duration_minutes=5,
                commercial_after=True
            ),
            TimeSlot(
                slot_id="match_4",
                slot_type=SegmentSlotType.MATCH,
                position=7,
                min_duration_minutes=8,
                max_duration_minutes=15,
                target_duration_minutes=12,
                importance_level="feature",
                commercial_after=False
            ),
            TimeSlot(
                slot_id="main_event",
                slot_type=SegmentSlotType.MAIN_EVENT,
                position=8,
                min_duration_minutes=15,
                max_duration_minutes=25,
                target_duration_minutes=20,
                importance_level="main_event",
                can_overrun=True,
                commercial_after=False
            )
        ]
        
        return template
    
    @staticmethod
    def create_minor_ppv_template(ppv_name: str = "Clash of Titans") -> ShowTemplate:
        """
        STEP 59: Minor PPV Template
        - 2.5 hours (150 minutes)
        - 6-7 matches
        - 3-4 segments
        - 2 commercial breaks (during pre-show only)
        - 2 dark matches
        """
        template = ShowTemplate(
            template_id=f"minor_ppv_{ppv_name.lower().replace(' ', '_')}",
            show_type=ShowType.MINOR_PPV,
            template_name=f"{ppv_name}",
            
            total_duration_minutes=150,
            match_time_budget=110,
            segment_time_budget=30,
            commercial_time_budget=5,  # Minimal - PPV
            buffer_time_minutes=5,
            
            target_match_count=6,
            min_match_count=5,
            max_match_count=8,
            target_segment_count=3,
            min_segment_count=2,
            max_segment_count=5,
            
            has_commercials=False,  # PPV - no mid-show commercials
            commercial_break_count=0,
            
            dark_match_config=DarkMatchConfig(
                pre_show_count=2,
                post_show_count=1,
                allow_developmental=True,
                allow_crowd_warmup=True,
                allow_crowd_cooldown=True
            ),
            
            ticket_price_base=75,
            production_cost_multiplier=1.5,
            expected_attendance_multiplier=1.2,
            
            target_show_rating=3.5,
            requires_strong_opening=True,
            requires_strong_main_event=True,
            target_energy_curve="peaks_and_valleys"
        )
        
        return template
    
    @staticmethod
    def create_major_ppv_template(ppv_name: str = "Victory Dome") -> ShowTemplate:
        """
        STEP 59 + STEP 61: Major PPV / Supercard Template
        - 4 hours (240 minutes)
        - 8-10 matches
        - 4-6 segments
        - No commercials
        - 3 dark matches
        """
        template = ShowTemplate(
            template_id=f"major_ppv_{ppv_name.lower().replace(' ', '_')}",
            show_type=ShowType.MAJOR_PPV,
            template_name=f"{ppv_name}",
            
            total_duration_minutes=240,
            match_time_budget=180,
            segment_time_budget=50,
            commercial_time_budget=0,
            buffer_time_minutes=10,
            
            target_match_count=8,
            min_match_count=7,
            max_match_count=10,
            target_segment_count=5,
            min_segment_count=3,
            max_segment_count=6,
            
            has_commercials=False,
            commercial_break_count=0,
            
            dark_match_config=DarkMatchConfig(
                pre_show_count=3,
                post_show_count=1,
                allow_developmental=True,
                allow_tryouts=True,
                allow_crowd_warmup=True,
                allow_crowd_cooldown=True
            ),
            
            ticket_price_base=150,
            production_cost_multiplier=2.5,
            expected_attendance_multiplier=1.5,
            
            target_show_rating=4.0,
            min_acceptable_rating=3.0,
            requires_strong_opening=True,
            requires_strong_main_event=True,
            max_consecutive_matches=2,
            target_energy_curve="peaks_and_valleys"
        )
        
        return template
    
    @staticmethod
    def create_house_show_template(tour_name: str = "Regional Tour") -> ShowTemplate:
        """
        STEP 60: House Show Template
        - 2 hours (120 minutes)
        - 5-6 matches
        - 1-2 segments
        - No commercials (non-televised)
        - Lower production values
        """
        template = ShowTemplate(
            template_id=f"house_show_{tour_name.lower().replace(' ', '_')}",
            show_type=ShowType.HOUSE_SHOW,
            template_name=f"House Show - {tour_name}",
            
            total_duration_minutes=120,
            match_time_budget=95,
            segment_time_budget=15,
            commercial_time_budget=0,
            buffer_time_minutes=10,
            
            target_match_count=6,
            min_match_count=5,
            max_match_count=7,
            target_segment_count=2,
            min_segment_count=1,
            max_segment_count=3,
            
            has_commercials=False,
            commercial_break_count=0,
            
            dark_match_config=DarkMatchConfig(
                pre_show_count=0,
                post_show_count=0
            ),
            
            ticket_price_base=30,
            production_cost_multiplier=0.4,  # Lower production
            expected_attendance_multiplier=0.5,
            
            target_show_rating=2.5,
            min_acceptable_rating=2.0,
            requires_strong_opening=False,
            requires_strong_main_event=True,
            allow_back_to_back_matches=True,
            max_consecutive_matches=4,
            target_energy_curve="constant_high"
        )
        
        return template
    
    @staticmethod
    def create_supercard_template(event_name: str = "Anniversary Show") -> ShowTemplate:
        """
        STEP 61: Supercard Special Event Template
        - 5 hours (300 minutes)
        - 10-12 matches
        - 6-8 segments
        - Celebrity involvement
        - Maximum production
        """
        template = ShowTemplate(
            template_id=f"supercard_{event_name.lower().replace(' ', '_')}",
            show_type=ShowType.SUPERCARD,
            template_name=f"{event_name}",
            
            total_duration_minutes=300,
            match_time_budget=220,
            segment_time_budget=65,
            commercial_time_budget=0,
            buffer_time_minutes=15,
            
            target_match_count=10,
            min_match_count=9,
            max_match_count=12,
            target_segment_count=7,
            min_segment_count=5,
            max_segment_count=8,
            
            has_commercials=False,
            commercial_break_count=0,
            
            dark_match_config=DarkMatchConfig(
                pre_show_count=4,
                post_show_count=2,
                allow_developmental=True,
                allow_tryouts=True
            ),
            
            ticket_price_base=250,
            production_cost_multiplier=4.0,
            expected_attendance_multiplier=2.0,
            
            target_show_rating=4.5,
            min_acceptable_rating=3.5,
            requires_strong_opening=True,
            requires_strong_main_event=True,
            max_consecutive_matches=2,
            target_energy_curve="peaks_and_valleys"
        )
        
        return template
    
    @staticmethod
    def get_template_for_show_type(show_type: str, **kwargs) -> ShowTemplate:
        """Get the appropriate template for a show type"""
        if show_type == 'weekly_tv':
            return ShowTemplateFactory.create_weekly_tv_template(
                brand=kwargs.get('brand', 'ROC Alpha')
            )
        elif show_type == 'minor_ppv':
            return ShowTemplateFactory.create_minor_ppv_template(
                ppv_name=kwargs.get('name', 'Premium Live Event')
            )
        elif show_type == 'major_ppv':
            return ShowTemplateFactory.create_major_ppv_template(
                ppv_name=kwargs.get('name', 'Major Event')
            )
        elif show_type == 'house_show':
            return ShowTemplateFactory.create_house_show_template(
                tour_name=kwargs.get('tour', 'Regional Tour')
            )
        elif show_type == 'supercard':
            return ShowTemplateFactory.create_supercard_template(
                event_name=kwargs.get('name', 'Supercard')
            )
        else:
            # Default to weekly TV
            return ShowTemplateFactory.create_weekly_tv_template()


# Global template manager
class ShowTemplateManager:
    """Manages show templates and provides easy access"""
    
    def __init__(self):
        self.templates: Dict[str, ShowTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load all default templates"""
        # Weekly TV for each brand
        for brand in ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']:
            template = ShowTemplateFactory.create_weekly_tv_template(brand)
            self.templates[template.template_id] = template
        
        # PPV templates
        minor_ppv = ShowTemplateFactory.create_minor_ppv_template()
        major_ppv = ShowTemplateFactory.create_major_ppv_template()
        house_show = ShowTemplateFactory.create_house_show_template()
        supercard = ShowTemplateFactory.create_supercard_template()
        
        self.templates[minor_ppv.template_id] = minor_ppv
        self.templates[major_ppv.template_id] = major_ppv
        self.templates[house_show.template_id] = house_show
        self.templates[supercard.template_id] = supercard
    
    def get_template(self, show_type: str, **kwargs) -> ShowTemplate:
        """Get template for a show type"""
        return ShowTemplateFactory.get_template_for_show_type(show_type, **kwargs)
    
    def get_template_by_id(self, template_id: str) -> Optional[ShowTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def add_custom_template(self, template: ShowTemplate):
        """Add a custom template"""
        self.templates[template.template_id] = template
    
    def get_all_templates(self) -> List[ShowTemplate]:
        """Get all templates"""
        return list(self.templates.values())


# Global instance
show_template_manager = ShowTemplateManager()