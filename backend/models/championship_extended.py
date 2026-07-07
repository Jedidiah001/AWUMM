"""
Extended Championship Model
Wrapper for extended championship data with full OOP interface.

STEP 22: Provides OOP interface to extended championship features including:
- Division restrictions
- Weight class restrictions  
- Belt appearance
- Custom defense requirements
- Database persistence via DTO pattern
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from models.championship import Championship, TitleReign


# =============================================================================
# Data Transfer Object for Database Persistence
# =============================================================================

@dataclass
class ExtendedChampionshipData:
    """
    Data transfer object for extended championship data.
    Used for database serialization/deserialization.
    Stored in the championship_extended table.
    """
    title_id: str
    division: str = 'open'
    weight_class: str = 'open'
    is_tag_team: bool = False
    tag_team_size: int = 2
    description: str = ""
    is_custom: bool = False
    created_year: Optional[int] = None
    created_week: Optional[int] = None
    retired: bool = False
    retired_year: Optional[int] = None
    retired_week: Optional[int] = None
    appearance: Optional[Dict[str, Any]] = None
    defense_requirements: Optional[Dict[str, Any]] = None
    brand_exclusive: bool = True
    status: str = 'active'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'title_id': self.title_id,
            'division': self.division,
            'weight_class': self.weight_class,
            'is_tag_team': self.is_tag_team,
            'tag_team_size': self.tag_team_size,
            'description': self.description,
            'is_custom': self.is_custom,
            'created_year': self.created_year,
            'created_week': self.created_week,
            'retired': self.retired,
            'retired_year': self.retired_year,
            'retired_week': self.retired_week,
            'appearance': self.appearance,
            'defense_requirements': self.defense_requirements,
            'brand_exclusive': self.brand_exclusive,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtendedChampionshipData':
        """Create from dictionary (database row)."""
        return cls(
            title_id=data['title_id'],
            division=data.get('division', 'open'),
            weight_class=data.get('weight_class', 'open'),
            is_tag_team=data.get('is_tag_team', False),
            tag_team_size=data.get('tag_team_size', 2),
            description=data.get('description', ''),
            is_custom=data.get('is_custom', False),
            created_year=data.get('created_year'),
            created_week=data.get('created_week'),
            retired=data.get('retired', False),
            retired_year=data.get('retired_year'),
            retired_week=data.get('retired_week'),
            appearance=data.get('appearance'),
            defense_requirements=data.get('defense_requirements'),
            brand_exclusive=data.get('brand_exclusive', True),
            status=data.get('status', 'active')
        )


# =============================================================================
# Enums and Value Objects (from championship_factory)
# =============================================================================

from enum import Enum


class DivisionRestriction(Enum):
    """Division restrictions for championship eligibility."""
    OPEN = 'open'
    MENS = 'mens'
    WOMENS = 'womens'
    TAG_TEAM = 'tag_team'
    MIXED = 'mixed'


class WeightClass(Enum):
    """Weight class restrictions for championship eligibility."""
    OPEN = 'open'
    CRUISERWEIGHT = 'cruiserweight'
    HEAVYWEIGHT = 'heavyweight'
    SUPER_HEAVYWEIGHT = 'super_heavyweight'
    LIGHT_HEAVYWEIGHT = 'light_heavyweight'


@dataclass
class BeltAppearance:
    """Visual appearance settings for a championship belt."""
    primary_color: str = 'gold'
    secondary_color: str = 'black'
    strap_color: str = 'black'
    plate_style: str = 'classic'
    gem_type: Optional[str] = None
    custom_logo: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'strap_color': self.strap_color,
            'plate_style': self.plate_style,
            'gem_type': self.gem_type,
            'custom_logo': self.custom_logo
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BeltAppearance':
        if data is None:
            return cls()
        return cls(
            primary_color=data.get('primary_color', 'gold'),
            secondary_color=data.get('secondary_color', 'black'),
            strap_color=data.get('strap_color', 'black'),
            plate_style=data.get('plate_style', 'classic'),
            gem_type=data.get('gem_type'),
            custom_logo=data.get('custom_logo')
        )
    
    @classmethod
    def get_default_for_tier(cls, tier: str) -> 'BeltAppearance':
        """Get default appearance based on championship tier."""
        tier_defaults = {
            'world': cls(primary_color='gold', plate_style='ornate', gem_type='diamond'),
            'major': cls(primary_color='gold', plate_style='classic'),
            'midcard': cls(primary_color='silver', plate_style='standard'),
            'minor': cls(primary_color='bronze', plate_style='simple'),
            'tag': cls(primary_color='gold', secondary_color='silver', plate_style='dual'),
        }
        return tier_defaults.get(tier, cls())


@dataclass
class CustomDefenseRequirements:
    """Custom defense requirement settings for a championship."""
    min_weeks_between_defenses: int = 4
    max_weeks_without_defense: int = 8
    ppv_defense_required: bool = True
    tv_defense_allowed: bool = True
    minimum_match_time: int = 10  # minutes
    rematch_clause_duration: int = 30  # days
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'min_weeks_between_defenses': self.min_weeks_between_defenses,
            'max_weeks_without_defense': self.max_weeks_without_defense,
            'ppv_defense_required': self.ppv_defense_required,
            'tv_defense_allowed': self.tv_defense_allowed,
            'minimum_match_time': self.minimum_match_time,
            'rematch_clause_duration': self.rematch_clause_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomDefenseRequirements':
        if data is None:
            return cls()
        return cls(
            min_weeks_between_defenses=data.get('min_weeks_between_defenses', 4),
            max_weeks_without_defense=data.get('max_weeks_without_defense', 8),
            ppv_defense_required=data.get('ppv_defense_required', True),
            tv_defense_allowed=data.get('tv_defense_allowed', True),
            minimum_match_time=data.get('minimum_match_time', 10),
            rematch_clause_duration=data.get('rematch_clause_duration', 30)
        )
    
    @classmethod
    def get_default_for_tier(cls, tier: str) -> 'CustomDefenseRequirements':
        """Get default requirements based on championship tier."""
        tier_defaults = {
            'world': cls(min_weeks_between_defenses=4, max_weeks_without_defense=6, ppv_defense_required=True),
            'major': cls(min_weeks_between_defenses=3, max_weeks_without_defense=8),
            'midcard': cls(min_weeks_between_defenses=2, max_weeks_without_defense=10),
            'minor': cls(min_weeks_between_defenses=2, max_weeks_without_defense=12, ppv_defense_required=False),
            'tag': cls(min_weeks_between_defenses=3, max_weeks_without_defense=10),
        }
        return tier_defaults.get(tier, cls())


# =============================================================================
# Extended Championship Model
# =============================================================================

class ExtendedChampionship:
    """
    Extended Championship with custom creation fields.
    
    This class can work in two modes:
    1. Standalone mode: All data self-contained
    2. Wrapper mode: Wraps a base Championship object with extended data
    
    The class uses the ExtendedChampionshipData DTO for database operations.
    """
    
    def __init__(
        self,
        title_id: str,
        name: str,
        assigned_brand: str,
        title_type: str,
        prestige: int = 50,
        current_holder_id: Optional[str] = None,
        current_holder_name: Optional[str] = None,
        division: DivisionRestriction = DivisionRestriction.OPEN,
        weight_class: WeightClass = WeightClass.OPEN,
        is_tag_team: bool = False,
        tag_team_size: int = 2,
        appearance: Optional[BeltAppearance] = None,
        defense_requirements: Optional[CustomDefenseRequirements] = None,
        description: str = "",
        is_custom: bool = False,
        brand_exclusive: bool = True,
        base_championship: Optional['Championship'] = None
    ):
        """
        Initialize an ExtendedChampionship.
        
        Args:
            title_id: Unique identifier for this championship
            name: Display name
            assigned_brand: Brand this title belongs to
            title_type: Type of championship (World, Major, etc.)
            prestige: Prestige value (0-100)
            current_holder_id: ID of current champion
            current_holder_name: Name of current champion
            division: Division restriction (mens/womens/open/etc.)
            weight_class: Weight class restriction
            is_tag_team: Whether this is a tag team championship
            tag_team_size: Number of members in tag team (if applicable)
            appearance: Belt appearance settings
            defense_requirements: Custom defense requirements
            description: Championship description
            is_custom: True if created by user, False if default
            brand_exclusive: Whether title is exclusive to one brand
            base_championship: Optional base Championship object to wrap
        """
        # Store reference to base championship if provided
        self._base_championship = base_championship
        
        # Core identity fields (used if no base championship)
        self._title_id = title_id
        self._name = name
        self._assigned_brand = assigned_brand
        self._title_type = title_type
        self._prestige = prestige
        self._current_holder_id = current_holder_id
        self._current_holder_name = current_holder_name
        
        # Extended fields (always stored here)
        self.division = division
        self.weight_class = weight_class
        self.is_tag_team = is_tag_team
        self.tag_team_size = tag_team_size
        self.appearance = appearance or BeltAppearance.get_default_for_tier(
            self._get_tier_from_type(title_type)
        )
        self.defense_requirements = defense_requirements or CustomDefenseRequirements.get_default_for_tier(
            self._get_tier_from_type(title_type)
        )
        self.description = description
        self.is_custom = is_custom
        self.brand_exclusive = brand_exclusive
        self.created_year: Optional[int] = None
        self.created_week: Optional[int] = None
        self.retired: bool = False
        self.retired_year: Optional[int] = None
        self.retired_week: Optional[int] = None
        self.status: str = 'active'
        
        # Fields only used in standalone mode
        self._history: list = []
        self._interim_holder_id: Optional[str] = None
        self._interim_holder_name: Optional[str] = None
        self._last_defense_year: Optional[int] = None
        self._last_defense_week: Optional[int] = None
        self._last_defense_show_id: Optional[str] = None
        self._vacancy_reason: Optional[str] = None
        self._total_defenses: int = 0
    
    # =========================================================================
    # Property Accessors - Delegate to base championship if available
    # =========================================================================
    
    @property
    def id(self) -> str:
        if self._base_championship:
            return self._base_championship.id
        return self._title_id
    
    @property
    def title_id(self) -> str:
        return self.id
    
    @property
    def name(self) -> str:
        if self._base_championship:
            return self._base_championship.name
        return self._name
    
    @name.setter
    def name(self, value: str):
        if self._base_championship:
            self._base_championship.name = value
        else:
            self._name = value
    
    @property
    def assigned_brand(self) -> str:
        if self._base_championship:
            return self._base_championship.assigned_brand
        return self._assigned_brand
    
    @assigned_brand.setter
    def assigned_brand(self, value: str):
        if self._base_championship:
            self._base_championship.assigned_brand = value
        else:
            self._assigned_brand = value
    
    @property
    def title_type(self) -> str:
        if self._base_championship:
            return self._base_championship.title_type
        return self._title_type
    
    @property
    def prestige(self) -> int:
        if self._base_championship:
            return self._base_championship.prestige
        return self._prestige
    
    @prestige.setter
    def prestige(self, value: int):
        if self._base_championship:
            self._base_championship.prestige = value
        else:
            self._prestige = value
    
    @property
    def current_holder_id(self) -> Optional[str]:
        if self._base_championship:
            return self._base_championship.current_holder_id
        return self._current_holder_id
    
    @current_holder_id.setter
    def current_holder_id(self, value: Optional[str]):
        if self._base_championship:
            self._base_championship.current_holder_id = value
        else:
            self._current_holder_id = value
    
    @property
    def current_holder_name(self) -> Optional[str]:
        if self._base_championship:
            return self._base_championship.current_holder_name
        return self._current_holder_name
    
    @current_holder_name.setter
    def current_holder_name(self, value: Optional[str]):
        if self._base_championship:
            self._base_championship.current_holder_name = value
        else:
            self._current_holder_name = value
    
    @property
    def history(self) -> list:
        if self._base_championship:
            return self._base_championship.history
        return self._history
    
    @history.setter
    def history(self, value: list):
        if self._base_championship:
            self._base_championship.history = value
        else:
            self._history = value
    
    @property
    def interim_holder_id(self) -> Optional[str]:
        if self._base_championship:
            return self._base_championship.interim_holder_id
        return self._interim_holder_id
    
    @interim_holder_id.setter
    def interim_holder_id(self, value: Optional[str]):
        if self._base_championship:
            self._base_championship.interim_holder_id = value
        else:
            self._interim_holder_id = value
    
    @property
    def interim_holder_name(self) -> Optional[str]:
        if self._base_championship:
            return self._base_championship.interim_holder_name
        return self._interim_holder_name
    
    @interim_holder_name.setter
    def interim_holder_name(self, value: Optional[str]):
        if self._base_championship:
            self._base_championship.interim_holder_name = value
        else:
            self._interim_holder_name = value
    
    @property
    def last_defense_year(self) -> Optional[int]:
        if self._base_championship:
            return self._base_championship.last_defense_year
        return self._last_defense_year
    
    @last_defense_year.setter
    def last_defense_year(self, value: Optional[int]):
        if self._base_championship:
            self._base_championship.last_defense_year = value
        else:
            self._last_defense_year = value
    
    @property
    def last_defense_week(self) -> Optional[int]:
        if self._base_championship:
            return self._base_championship.last_defense_week
        return self._last_defense_week
    
    @last_defense_week.setter
    def last_defense_week(self, value: Optional[int]):
        if self._base_championship:
            self._base_championship.last_defense_week = value
        else:
            self._last_defense_week = value
    
    @property
    def last_defense_show_id(self) -> Optional[str]:
        if self._base_championship:
            return self._base_championship.last_defense_show_id
        return self._last_defense_show_id
    
    @last_defense_show_id.setter
    def last_defense_show_id(self, value: Optional[str]):
        if self._base_championship:
            self._base_championship.last_defense_show_id = value
        else:
            self._last_defense_show_id = value
    
    @property
    def vacancy_reason(self) -> Optional[str]:
        if self._base_championship:
            return self._base_championship.vacancy_reason
        return self._vacancy_reason
    
    @vacancy_reason.setter
    def vacancy_reason(self, value: Optional[str]):
        if self._base_championship:
            self._base_championship.vacancy_reason = value
        else:
            self._vacancy_reason = value
    
    @property
    def total_defenses(self) -> int:
        if self._base_championship:
            return self._base_championship.total_defenses
        return self._total_defenses
    
    @total_defenses.setter
    def total_defenses(self, value: int):
        if self._base_championship:
            self._base_championship.total_defenses = value
        else:
            self._total_defenses = value
    
    @property
    def base_championship(self) -> Optional['Championship']:
        """Get the wrapped base championship, if any."""
        return self._base_championship
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    @staticmethod
    def _get_tier_from_type(title_type: str) -> str:
        """Convert title_type to tier for defaults."""
        type_to_tier = {
            'World': 'world',
            'Major': 'major',
            'Midcard': 'midcard',
            'Minor': 'minor',
            'Tag Team': 'tag',
            'Women': 'major',
            'Women\'s Tag': 'tag',
        }
        return type_to_tier.get(title_type, 'midcard')
    
    # =========================================================================
    # Business Logic Methods
    # =========================================================================
    
    def can_wrestler_compete(self, wrestler) -> tuple[bool, str]:
        """
        Check if a wrestler is eligible to compete for this championship.
        
        Args:
            wrestler: Wrestler object with gender, speed, brawling attributes
            
        Returns:
            (eligible, reason) tuple
        """
        # Check division restriction
        if self.division == DivisionRestriction.MENS:
            if getattr(wrestler, 'gender', None) != 'Male':
                return False, "This championship is for male competitors only"
        
        elif self.division == DivisionRestriction.WOMENS:
            if getattr(wrestler, 'gender', None) != 'Female':
                return False, "This championship is for female competitors only"
        
        elif self.division == DivisionRestriction.TAG_TEAM:
            # Tag team eligibility checked elsewhere
            pass
        
        # Check weight class
        if self.weight_class == WeightClass.CRUISERWEIGHT:
            if getattr(wrestler, 'speed', 0) < 60:
                return False, "Cruiserweight division requires high speed attribute"
        
        elif self.weight_class == WeightClass.SUPER_HEAVYWEIGHT:
            if getattr(wrestler, 'brawling', 0) < 70:
                return False, "Super heavyweight division requires high brawling"
        
        return True, "Eligible"
    
    def retire_championship(self, year: int, week: int):
        """Retire/deactivate this championship."""
        self.retired = True
        self.retired_year = year
        self.retired_week = week
        self.status = 'retired'
    
    def reactivate_championship(self):
        """Reactivate a retired championship."""
        self.retired = False
        self.retired_year = None
        self.retired_week = None
        self.status = 'active'
    
    def is_eligible_for_defense(self, current_year: int, current_week: int) -> tuple[bool, str]:
        """
        Check if the championship is due for a defense.
        
        Returns:
            (needs_defense, reason) tuple
        """
        if self.retired:
            return False, "Championship is retired"
        
        if not self.current_holder_id:
            return False, "Championship is vacant"
        
        if not self.last_defense_week or not self.last_defense_year:
            return True, "No recorded defense"
        
        # Calculate weeks since last defense
        weeks_since = ((current_year - self.last_defense_year) * 52 + 
                       (current_week - self.last_defense_week))
        
        req = self.defense_requirements
        if weeks_since >= req.max_weeks_without_defense:
            return True, f"Overdue by {weeks_since - req.max_weeks_without_defense} weeks"
        elif weeks_since >= req.min_weeks_between_defenses:
            return True, "Eligible for defense"
        else:
            return False, f"Too soon ({req.min_weeks_between_defenses - weeks_since} weeks until eligible)"
    
    # =========================================================================
    # Delegation to Base Championship Methods
    # =========================================================================
    
    def is_vacant(self) -> bool:
        """Check if the championship is vacant."""
        if self._base_championship and hasattr(self._base_championship, 'is_vacant'):
            return self._base_championship.is_vacant()
        return self.current_holder_id is None
    
    def award_title(self, wrestler_id: str, wrestler_name: str, year: int, week: int, 
                   won_from_id: Optional[str] = None, won_from_name: Optional[str] = None,
                   match_type: str = "Singles", event_name: str = ""):
        """Award the title to a new champion."""
        if self._base_championship and hasattr(self._base_championship, 'award_title'):
            return self._base_championship.award_title(
                wrestler_id, wrestler_name, year, week,
                won_from_id, won_from_name, match_type, event_name
            )
        # Standalone implementation
        self.current_holder_id = wrestler_id
        self.current_holder_name = wrestler_name
        self.last_defense_year = year
        self.last_defense_week = week
    
    def vacate_title(self, reason: str = "Vacated"):
        """Vacate the championship."""
        if self._base_championship and hasattr(self._base_championship, 'vacate_title'):
            return self._base_championship.vacate_title(reason)
        self.current_holder_id = None
        self.current_holder_name = None
        self.vacancy_reason = reason
    
    def record_defense(self, year: int, week: int, show_id: Optional[str] = None):
        """Record a successful title defense."""
        if self._base_championship and hasattr(self._base_championship, 'record_defense'):
            return self._base_championship.record_defense(year, week, show_id)
        self.last_defense_year = year
        self.last_defense_week = week
        self.last_defense_show_id = show_id
        self.total_defenses += 1
    
    # =========================================================================
    # Serialization Methods
    # =========================================================================
    
    def to_extended_data(self) -> ExtendedChampionshipData:
        """
        Convert extended fields to a DTO for database storage.
        This only contains the extended fields, not the base championship data.
        """
        return ExtendedChampionshipData(
            title_id=self.id,
            division=self.division.value if isinstance(self.division, DivisionRestriction) else self.division,
            weight_class=self.weight_class.value if isinstance(self.weight_class, WeightClass) else self.weight_class,
            is_tag_team=self.is_tag_team,
            tag_team_size=self.tag_team_size,
            description=self.description,
            is_custom=self.is_custom,
            created_year=self.created_year,
            created_week=self.created_week,
            retired=self.retired,
            retired_year=self.retired_year,
            retired_week=self.retired_week,
            appearance=self.appearance.to_dict() if self.appearance else None,
            defense_requirements=self.defense_requirements.to_dict() if self.defense_requirements else None,
            brand_exclusive=self.brand_exclusive,
            status=self.status
        )
    
    def apply_extended_data(self, data: ExtendedChampionshipData):
        """Apply extended data from a DTO to this championship."""
        self.division = DivisionRestriction(data.division) if data.division else DivisionRestriction.OPEN
        self.weight_class = WeightClass(data.weight_class) if data.weight_class else WeightClass.OPEN
        self.is_tag_team = data.is_tag_team
        self.tag_team_size = data.tag_team_size
        self.description = data.description
        self.is_custom = data.is_custom
        self.created_year = data.created_year
        self.created_week = data.created_week
        self.retired = data.retired
        self.retired_year = data.retired_year
        self.retired_week = data.retired_week
        self.brand_exclusive = data.brand_exclusive
        self.status = data.status
        
        if data.appearance:
            self.appearance = BeltAppearance.from_dict(data.appearance)
        if data.defense_requirements:
            self.defense_requirements = CustomDefenseRequirements.from_dict(data.defense_requirements)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including all fields."""
        # Get base championship dict if available
        if self._base_championship and hasattr(self._base_championship, 'to_dict'):
            base_dict = self._base_championship.to_dict()
        else:
            base_dict = {
                'id': self.id,
                'name': self.name,
                'assigned_brand': self.assigned_brand,
                'title_type': self.title_type,
                'prestige': self.prestige,
                'current_holder_id': self.current_holder_id,
                'current_holder_name': self.current_holder_name,
                'interim_holder_id': self.interim_holder_id,
                'interim_holder_name': self.interim_holder_name,
                'last_defense_year': self.last_defense_year,
                'last_defense_week': self.last_defense_week,
                'last_defense_show_id': self.last_defense_show_id,
                'vacancy_reason': self.vacancy_reason,
                'total_defenses': self.total_defenses,
                'history': [r.to_dict() if hasattr(r, 'to_dict') else r for r in self.history]
            }
        
        # Add extended fields
        base_dict.update({
            'division': self.division.value if isinstance(self.division, DivisionRestriction) else self.division,
            'weight_class': self.weight_class.value if isinstance(self.weight_class, WeightClass) else self.weight_class,
            'is_tag_team': self.is_tag_team,
            'tag_team_size': self.tag_team_size,
            'appearance': self.appearance.to_dict() if self.appearance else None,
            'defense_requirements': self.defense_requirements.to_dict() if self.defense_requirements else None,
            'description': self.description,
            'is_custom': self.is_custom,
            'brand_exclusive': self.brand_exclusive,
            'created_year': self.created_year,
            'created_week': self.created_week,
            'retired': self.retired,
            'retired_year': self.retired_year,
            'retired_week': self.retired_week,
            'status': self.status
        })
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtendedChampionship':
        """Create ExtendedChampionship from dictionary."""
        # Parse extended fields
        division = DivisionRestriction(data.get('division', 'open'))
        weight_class = WeightClass(data.get('weight_class', 'open'))
        
        appearance = None
        if data.get('appearance'):
            appearance = BeltAppearance.from_dict(data['appearance'])
        
        defense_requirements = None
        if data.get('defense_requirements'):
            defense_requirements = CustomDefenseRequirements.from_dict(data['defense_requirements'])
        
        championship = cls(
            title_id=data.get('id', data.get('title_id')),
            name=data['name'],
            assigned_brand=data['assigned_brand'],
            title_type=data['title_type'],
            prestige=data.get('prestige', 50),
            current_holder_id=data.get('current_holder_id'),
            current_holder_name=data.get('current_holder_name'),
            division=division,
            weight_class=weight_class,
            is_tag_team=data.get('is_tag_team', False),
            tag_team_size=data.get('tag_team_size', 2),
            appearance=appearance,
            defense_requirements=defense_requirements,
            description=data.get('description', ''),
            is_custom=data.get('is_custom', False),
            brand_exclusive=data.get('brand_exclusive', True)
        )
        
        # Load additional fields
        championship.created_year = data.get('created_year')
        championship.created_week = data.get('created_week')
        championship.retired = data.get('retired', False)
        championship.retired_year = data.get('retired_year')
        championship.retired_week = data.get('retired_week')
        championship.status = data.get('status', 'active')
        
        # Load base Championship fields (for standalone mode)
        championship._interim_holder_id = data.get('interim_holder_id')
        championship._interim_holder_name = data.get('interim_holder_name')
        championship._last_defense_year = data.get('last_defense_year')
        championship._last_defense_week = data.get('last_defense_week')
        championship._last_defense_show_id = data.get('last_defense_show_id')
        championship._vacancy_reason = data.get('vacancy_reason')
        championship._total_defenses = data.get('total_defenses', 0)
        
        # Load history if present
        if 'history' in data:
            # Try to import TitleReign for proper deserialization
            try:
                from models.championship import TitleReign
                championship._history = [
                    TitleReign.from_dict(reign_data) if isinstance(reign_data, dict) else reign_data
                    for reign_data in data.get('history', [])
                ]
            except ImportError:
                championship._history = data.get('history', [])
        
        return championship
    
    @classmethod
    def from_base_championship(
        cls, 
        championship: 'Championship',
        extended_data: Optional[ExtendedChampionshipData] = None
    ) -> 'ExtendedChampionship':
        """
        Create an ExtendedChampionship wrapping a base Championship.
        
        Args:
            championship: The base Championship object to wrap
            extended_data: Optional extended data DTO to apply
            
        Returns:
            ExtendedChampionship wrapping the base championship
        """
        # Determine default division based on title type
        default_division = DivisionRestriction.OPEN
        default_is_tag_team = False
        
        if championship.title_type == 'Women':
            default_division = DivisionRestriction.WOMENS
        elif championship.title_type == 'Tag Team':
            default_is_tag_team = True
        elif championship.title_type == "Women's Tag":
            default_division = DivisionRestriction.WOMENS
            default_is_tag_team = True
        
        extended = cls(
            title_id=championship.id,
            name=championship.name,
            assigned_brand=championship.assigned_brand,
            title_type=championship.title_type,
            prestige=championship.prestige,
            current_holder_id=championship.current_holder_id,
            current_holder_name=championship.current_holder_name,
            division=default_division,
            is_tag_team=default_is_tag_team,
            is_custom=False,
            base_championship=championship
        )
        
        # Apply extended data if provided
        if extended_data:
            extended.apply_extended_data(extended_data)
        
        return extended
    
    @classmethod
    def from_base_and_data(
        cls,
        championship: 'Championship',
        data: ExtendedChampionshipData
    ) -> 'ExtendedChampionship':
        """
        Convenience method combining base championship with extended data.
        Alias for from_base_championship with extended_data parameter.
        """
        return cls.from_base_championship(championship, data)
    
    # =========================================================================
    # String Representation
    # =========================================================================
    
    def __repr__(self) -> str:
        holder = self.current_holder_name or "Vacant"
        return f"ExtendedChampionship({self.name}, holder={holder}, division={self.division.value})"
    
    def __str__(self) -> str:
        return self.name


# =============================================================================
# Backwards Compatibility Alias
# =============================================================================

# Keep the old name available for code that imports it
ExtendedChampionshipDTO = ExtendedChampionshipData