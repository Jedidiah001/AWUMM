"""
Championship Factory
Handles creation and validation of custom championships.

STEP 22: Custom Championship Creation
- Custom title names and prestige levels
- Division restrictions (Men's, Women's, Tag Team, Open)
- Brand assignment or cross-brand designation
- Weight class restrictions
- Defense requirements configuration
- Belt appearance customization
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re
from datetime import datetime

from models.championship import Championship
from models.championship_hierarchy import TitleTier, DefenseRequirement


class DivisionRestriction(Enum):
    """Division restrictions for championships"""
    MENS = "mens"
    WOMENS = "womens"
    TAG_TEAM = "tag_team"
    OPEN = "open"  # Anyone can compete
    INTERGENDER = "intergender"  # Specifically for intergender matches


class WeightClass(Enum):
    """Weight class restrictions"""
    HEAVYWEIGHT = "heavyweight"
    CRUISERWEIGHT = "cruiserweight"  # Speed-based division
    LIGHT_HEAVYWEIGHT = "light_heavyweight"
    SUPER_HEAVYWEIGHT = "super_heavyweight"
    OPEN = "open"  # No weight restriction


class BeltStyle(Enum):
    """Visual style of the championship belt"""
    CLASSIC = "classic"  # Traditional gold/leather
    MODERN = "modern"  # Contemporary design
    BIG_GOLD = "big_gold"  # Large ornate center plate
    SPINNER = "spinner"  # Rotating center plate
    CUSTOM = "custom"  # Unique design
    VINTAGE = "vintage"  # Old-school leather strap
    PRESTIGIOUS = "prestigious"  # Highly decorated


class BeltColor(Enum):
    """Primary color scheme of the belt"""
    GOLD = "gold"
    SILVER = "silver"
    BLACK = "black"
    WHITE = "white"
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    PURPLE = "purple"
    BRONZE = "bronze"
    PLATINUM = "platinum"


@dataclass
class BeltAppearance:
    """Visual appearance configuration for a championship belt"""
    style: BeltStyle = BeltStyle.CLASSIC
    primary_color: BeltColor = BeltColor.GOLD
    secondary_color: Optional[BeltColor] = None
    strap_color: str = "black"  # Leather strap color
    has_side_plates: bool = True
    has_nameplate: bool = True
    custom_logo: Optional[str] = None  # Path to custom logo
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'style': self.style.value,
            'primary_color': self.primary_color.value,
            'secondary_color': self.secondary_color.value if self.secondary_color else None,
            'strap_color': self.strap_color,
            'has_side_plates': self.has_side_plates,
            'has_nameplate': self.has_nameplate,
            'custom_logo': self.custom_logo,
            'description': self.description
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'BeltAppearance':
        return BeltAppearance(
            style=BeltStyle(data.get('style', 'classic')),
            primary_color=BeltColor(data.get('primary_color', 'gold')),
            secondary_color=BeltColor(data['secondary_color']) if data.get('secondary_color') else None,
            strap_color=data.get('strap_color', 'black'),
            has_side_plates=data.get('has_side_plates', True),
            has_nameplate=data.get('has_nameplate', True),
            custom_logo=data.get('custom_logo'),
            description=data.get('description', '')
        )
    
    @staticmethod
    def get_default_for_tier(tier: TitleTier) -> 'BeltAppearance':
        """Get default belt appearance based on title tier"""
        defaults = {
            TitleTier.WORLD: BeltAppearance(
                style=BeltStyle.BIG_GOLD,
                primary_color=BeltColor.GOLD,
                secondary_color=BeltColor.BLACK,
                description="Ornate world championship belt with large gold center plate"
            ),
            TitleTier.SECONDARY: BeltAppearance(
                style=BeltStyle.CLASSIC,
                primary_color=BeltColor.SILVER,
                secondary_color=BeltColor.GOLD,
                description="Classic design with silver and gold accents"
            ),
            TitleTier.MIDCARD: BeltAppearance(
                style=BeltStyle.MODERN,
                primary_color=BeltColor.GOLD,
                description="Modern sleek design"
            ),
            TitleTier.TAG_TEAM: BeltAppearance(
                style=BeltStyle.CLASSIC,
                primary_color=BeltColor.GOLD,
                has_side_plates=True,
                description="Matching tag team championship belts"
            ),
            TitleTier.WOMENS: BeltAppearance(
                style=BeltStyle.PRESTIGIOUS,
                primary_color=BeltColor.GOLD,
                secondary_color=BeltColor.PURPLE,
                description="Elegant championship with purple accents"
            ),
            TitleTier.DEVELOPMENTAL: BeltAppearance(
                style=BeltStyle.VINTAGE,
                primary_color=BeltColor.BRONZE,
                description="Vintage-style developmental championship"
            )
        }
        return defaults.get(tier, BeltAppearance())


@dataclass
class CustomDefenseRequirements:
    """Custom defense requirements for a championship"""
    max_days_between_defenses: int = 30
    min_defenses_per_year: int = 12
    ppv_defense_required: bool = True
    weekly_tv_defense_allowed: bool = True
    must_defend_on_brand_shows: bool = True
    can_defend_cross_brand: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_days_between_defenses': self.max_days_between_defenses,
            'min_defenses_per_year': self.min_defenses_per_year,
            'ppv_defense_required': self.ppv_defense_required,
            'weekly_tv_defense_allowed': self.weekly_tv_defense_allowed,
            'must_defend_on_brand_shows': self.must_defend_on_brand_shows,
            'can_defend_cross_brand': self.can_defend_cross_brand
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'CustomDefenseRequirements':
        return CustomDefenseRequirements(
            max_days_between_defenses=data.get('max_days_between_defenses', 30),
            min_defenses_per_year=data.get('min_defenses_per_year', 12),
            ppv_defense_required=data.get('ppv_defense_required', True),
            weekly_tv_defense_allowed=data.get('weekly_tv_defense_allowed', True),
            must_defend_on_brand_shows=data.get('must_defend_on_brand_shows', True),
            can_defend_cross_brand=data.get('can_defend_cross_brand', False)
        )
    
    @staticmethod
    def get_default_for_tier(tier: TitleTier) -> 'CustomDefenseRequirements':
        """Get default defense requirements based on title tier"""
        req = DefenseRequirement.get_requirements(tier)
        return CustomDefenseRequirements(
            max_days_between_defenses=req.max_days_between_defenses,
            min_defenses_per_year=req.min_defenses_per_year,
            ppv_defense_required=req.ppv_defense_required,
            weekly_tv_defense_allowed=req.weekly_tv_defense_allowed
        )


@dataclass
class ChampionshipTemplate:
    """Template for creating a custom championship"""
    name: str
    assigned_brand: str
    title_type: str  # Maps to TitleTier
    division: DivisionRestriction = DivisionRestriction.OPEN
    weight_class: WeightClass = WeightClass.OPEN
    initial_prestige: int = 50
    is_tag_team: bool = False
    tag_team_size: int = 2  # For tag titles (2 = standard, 3 = trios, etc.)
    appearance: BeltAppearance = field(default_factory=BeltAppearance)
    defense_requirements: CustomDefenseRequirements = field(default_factory=CustomDefenseRequirements)
    description: str = ""
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'assigned_brand': self.assigned_brand,
            'title_type': self.title_type,
            'division': self.division.value,
            'weight_class': self.weight_class.value,
            'initial_prestige': self.initial_prestige,
            'is_tag_team': self.is_tag_team,
            'tag_team_size': self.tag_team_size,
            'appearance': self.appearance.to_dict(),
            'defense_requirements': self.defense_requirements.to_dict(),
            'description': self.description,
            'active': self.active
        }


class ChampionshipValidator:
    """Validates custom championship data"""
    
    # Valid brands
    VALID_BRANDS = ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard', 'Cross-Brand']
    
    # Valid title types
    VALID_TITLE_TYPES = ['World', 'Secondary', 'Midcard', 'Tag Team', 'Women', 'Developmental']
    
    # Name constraints
    MIN_NAME_LENGTH = 3
    MAX_NAME_LENGTH = 50
    
    # Prestige constraints
    MIN_PRESTIGE = 10
    MAX_PRESTIGE = 100
    
    @classmethod
    def validate_name(cls, name: str, existing_names: List[str] = None) -> Tuple[bool, List[str]]:
        """Validate championship name"""
        errors = []
        
        if not name or not name.strip():
            errors.append("Championship name is required")
            return False, errors
        
        name = name.strip()
        
        # Length check
        if len(name) < cls.MIN_NAME_LENGTH:
            errors.append(f"Name must be at least {cls.MIN_NAME_LENGTH} characters")
        
        if len(name) > cls.MAX_NAME_LENGTH:
            errors.append(f"Name must be no more than {cls.MAX_NAME_LENGTH} characters")
        
        # Character validation (allow letters, numbers, spaces, apostrophes, hyphens, ampersands)
        if not re.match(r"^[a-zA-Z0-9\s'\-&]+$", name):
            errors.append("Name can only contain letters, numbers, spaces, apostrophes, hyphens, and ampersands")
        
        # Check for duplicate names
        if existing_names:
            if name.lower() in [n.lower() for n in existing_names]:
                errors.append(f"A championship named '{name}' already exists")
        
        # Check for reserved words
        reserved = ['vacant', 'none', 'null', 'undefined', 'test']
        if name.lower() in reserved:
            errors.append(f"'{name}' is a reserved word and cannot be used")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_brand(cls, brand: str) -> Tuple[bool, List[str]]:
        """Validate brand assignment"""
        errors = []
        
        if not brand:
            errors.append("Brand assignment is required")
            return False, errors
        
        if brand not in cls.VALID_BRANDS:
            errors.append(f"Invalid brand. Must be one of: {', '.join(cls.VALID_BRANDS)}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_title_type(cls, title_type: str) -> Tuple[bool, List[str]]:
        """Validate title type"""
        errors = []
        
        if not title_type:
            errors.append("Title type is required")
            return False, errors
        
        if title_type not in cls.VALID_TITLE_TYPES:
            errors.append(f"Invalid title type. Must be one of: {', '.join(cls.VALID_TITLE_TYPES)}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_prestige(cls, prestige: int) -> Tuple[bool, List[str]]:
        """Validate initial prestige"""
        errors = []
        
        if not isinstance(prestige, int):
            try:
                prestige = int(prestige)
            except (ValueError, TypeError):
                errors.append("Prestige must be a number")
                return False, errors
        
        if prestige < cls.MIN_PRESTIGE:
            errors.append(f"Prestige must be at least {cls.MIN_PRESTIGE}")
        
        if prestige > cls.MAX_PRESTIGE:
            errors.append(f"Prestige cannot exceed {cls.MAX_PRESTIGE}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_division(cls, division: str) -> Tuple[bool, List[str]]:
        """Validate division restriction"""
        errors = []
        
        valid_divisions = [d.value for d in DivisionRestriction]
        
        if division and division not in valid_divisions:
            errors.append(f"Invalid division. Must be one of: {', '.join(valid_divisions)}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_weight_class(cls, weight_class: str) -> Tuple[bool, List[str]]:
        """Validate weight class restriction"""
        errors = []
        
        valid_classes = [w.value for w in WeightClass]
        
        if weight_class and weight_class not in valid_classes:
            errors.append(f"Invalid weight class. Must be one of: {', '.join(valid_classes)}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_tag_team_settings(cls, is_tag_team: bool, tag_team_size: int, title_type: str) -> Tuple[bool, List[str]]:
        """Validate tag team championship settings"""
        errors = []
        
        if is_tag_team:
            if tag_team_size < 2:
                errors.append("Tag team size must be at least 2")
            
            if tag_team_size > 5:
                errors.append("Tag team size cannot exceed 5")
            
            if title_type and title_type != 'Tag Team':
                errors.append("Tag team championships must have 'Tag Team' title type")
        
        if title_type == 'Tag Team' and not is_tag_team:
            errors.append("Tag Team title type requires is_tag_team to be true")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_defense_requirements(cls, requirements: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate defense requirement settings"""
        errors = []
        
        if not requirements:
            return True, []  # Use defaults
        
        max_days = requirements.get('max_days_between_defenses')
        if max_days is not None:
            if not isinstance(max_days, int) or max_days < 14:
                errors.append("Max days between defenses must be at least 14")
            if max_days > 90:
                errors.append("Max days between defenses cannot exceed 90")
        
        min_defenses = requirements.get('min_defenses_per_year')
        if min_defenses is not None:
            if not isinstance(min_defenses, int) or min_defenses < 4:
                errors.append("Minimum defenses per year must be at least 4")
            if min_defenses > 52:
                errors.append("Minimum defenses per year cannot exceed 52")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_all(cls, data: Dict[str, Any], existing_names: List[str] = None) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Validate all championship creation data.
        Returns (is_valid, errors_dict)
        """
        all_errors = {}
        
        # Validate name
        valid, errors = cls.validate_name(data.get('name', ''), existing_names)
        if not valid:
            all_errors['name'] = errors
        
        # Validate brand
        valid, errors = cls.validate_brand(data.get('assigned_brand', ''))
        if not valid:
            all_errors['assigned_brand'] = errors
        
        # Validate title type
        valid, errors = cls.validate_title_type(data.get('title_type', ''))
        if not valid:
            all_errors['title_type'] = errors
        
        # Validate prestige
        valid, errors = cls.validate_prestige(data.get('initial_prestige', 50))
        if not valid:
            all_errors['prestige'] = errors
        
        # Validate division
        valid, errors = cls.validate_division(data.get('division', 'open'))
        if not valid:
            all_errors['division'] = errors
        
        # Validate weight class
        valid, errors = cls.validate_weight_class(data.get('weight_class', 'open'))
        if not valid:
            all_errors['weight_class'] = errors
        
        # Validate tag team settings
        valid, errors = cls.validate_tag_team_settings(
            data.get('is_tag_team', False),
            data.get('tag_team_size', 2),
            data.get('title_type', '')
        )
        if not valid:
            all_errors['tag_team'] = errors
        
        # Validate defense requirements
        valid, errors = cls.validate_defense_requirements(data.get('defense_requirements', {}))
        if not valid:
            all_errors['defense_requirements'] = errors
        
        is_valid = len(all_errors) == 0
        return is_valid, all_errors


class ChampionshipFactory:
    """Factory for creating custom championships"""
    
    @staticmethod
    def generate_championship_id(database) -> str:
        """Generate unique championship ID"""
        cursor = database.conn.cursor()
        cursor.execute('SELECT id FROM championships ORDER BY id DESC')
        rows = cursor.fetchall()
        
        if not rows:
            return 'title001'
        
        # Find highest numeric ID
        max_num = 0
        for row in rows:
            title_id = row['id']
            if title_id.startswith('title'):
                try:
                    num = int(title_id.replace('title', ''))
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        
        return f'title{max_num + 1:03d}'
    
    @staticmethod
    def get_tier_from_type(title_type: str) -> TitleTier:
        """Convert title type string to TitleTier enum"""
        mapping = {
            'World': TitleTier.WORLD,
            'Secondary': TitleTier.SECONDARY,
            'Midcard': TitleTier.MIDCARD,
            'Tag Team': TitleTier.TAG_TEAM,
            'Women': TitleTier.WOMENS,
            'Developmental': TitleTier.DEVELOPMENTAL
        }
        return mapping.get(title_type, TitleTier.MIDCARD)
    
    @staticmethod
    def get_suggested_prestige(title_type: str, brand: str) -> int:
        """Get suggested initial prestige based on title type and brand"""
        base_prestige = {
            'World': 85,
            'Secondary': 65,
            'Midcard': 50,
            'Tag Team': 55,
            'Women': 70,
            'Developmental': 40
        }.get(title_type, 50)
        
        # Cross-brand titles get slight boost
        if brand == 'Cross-Brand':
            base_prestige += 5
        
        # ROC Alpha (main brand) titles slightly more prestigious
        if brand == 'ROC Alpha':
            base_prestige += 3
        
        return min(100, base_prestige)
    
    @classmethod
    def create_championship(
        cls,
        data: Dict[str, Any],
        championship_id: str,
        current_year: int,
        current_week: int
    ) -> Championship:
        """
        Create a new Championship object from validated data.
        
        Args:
            data: Validated championship data
            championship_id: Pre-generated unique ID
            current_year: Current game year
            current_week: Current game week
        
        Returns:
            Championship object ready to be saved
        """
        # Get title type and tier
        title_type = data['title_type']
        tier = cls.get_tier_from_type(title_type)
        
        # Get prestige (use suggested if not provided)
        prestige = data.get('initial_prestige')
        if prestige is None:
            prestige = cls.get_suggested_prestige(title_type, data['assigned_brand'])
        
        # Create championship
        championship = Championship(
            title_id=championship_id,
            name=data['name'].strip(),
            assigned_brand=data['assigned_brand'],
            title_type=title_type,
            prestige=prestige,
            current_holder_id=None,
            current_holder_name=None
        )
        
        # Championship starts vacant
        championship.vacancy_reason = "Newly created championship"
        
        # STEP 22: Mark as custom
        championship.is_custom = True
        championship.created_year = current_year
        championship.created_week = current_week
        
        return championship
    
    @classmethod
    def create_from_template(
        cls,
        template: ChampionshipTemplate,
        championship_id: str,
        current_year: int,
        current_week: int
    ) -> Championship:
        """Create championship from a template"""
        return cls.create_championship(
            data=template.to_dict(),
            championship_id=championship_id,
            current_year=current_year,
            current_week=current_week
        )


class ChampionshipPresets:
    """Pre-defined championship templates"""
    
    @staticmethod
    def get_all_presets() -> List[Dict[str, Any]]:
        """Get all available championship presets"""
        return [
            {
                'id': 'world_heavyweight',
                'name': 'World Heavyweight Championship',
                'description': 'The top prize for heavyweight competitors',
                'title_type': 'World',
                'division': 'mens',
                'weight_class': 'heavyweight',
                'suggested_prestige': 90,
                'is_tag_team': False
            },
            {
                'id': 'womens_world',
                'name': "Women's World Championship",
                'description': 'The premier championship for women',
                'title_type': 'Women',
                'division': 'womens',
                'weight_class': 'open',
                'suggested_prestige': 85,
                'is_tag_team': False
            },
            {
                'id': 'intercontinental',
                'name': 'Intercontinental Championship',
                'description': 'Secondary singles championship',
                'title_type': 'Secondary',
                'division': 'open',
                'weight_class': 'open',
                'suggested_prestige': 70,
                'is_tag_team': False
            },
            {
                'id': 'tag_team',
                'name': 'Tag Team Championship',
                'description': 'Standard tag team championship',
                'title_type': 'Tag Team',
                'division': 'open',
                'weight_class': 'open',
                'suggested_prestige': 60,
                'is_tag_team': True,
                'tag_team_size': 2
            },
            {
                'id': 'womens_tag',
                'name': "Women's Tag Team Championship",
                'description': 'Tag team championship for women',
                'title_type': 'Tag Team',
                'division': 'womens',
                'weight_class': 'open',
                'suggested_prestige': 55,
                'is_tag_team': True,
                'tag_team_size': 2
            },
            {
                'id': 'cruiserweight',
                'name': 'Cruiserweight Championship',
                'description': 'High-flying action for lighter competitors',
                'title_type': 'Midcard',
                'division': 'open',
                'weight_class': 'cruiserweight',
                'suggested_prestige': 55,
                'is_tag_team': False
            },
            {
                'id': 'television',
                'name': 'Television Championship',
                'description': 'Defended weekly on TV broadcasts',
                'title_type': 'Midcard',
                'division': 'open',
                'weight_class': 'open',
                'suggested_prestige': 45,
                'is_tag_team': False,
                'defense_requirements': {
                    'max_days_between_defenses': 14,
                    'weekly_tv_defense_allowed': True,
                    'ppv_defense_required': False
                }
            },
            {
                'id': 'hardcore',
                'name': 'Hardcore Championship',
                'description': 'Defended under 24/7 rules',
                'title_type': 'Midcard',
                'division': 'open',
                'weight_class': 'open',
                'suggested_prestige': 35,
                'is_tag_team': False
            },
            {
                'id': 'trios',
                'name': 'Trios Championship',
                'description': 'Three-person tag team championship',
                'title_type': 'Tag Team',
                'division': 'open',
                'weight_class': 'open',
                'suggested_prestige': 50,
                'is_tag_team': True,
                'tag_team_size': 3
            },
            {
                'id': 'developmental',
                'name': 'Developmental Championship',
                'description': 'Proving ground for up-and-coming talent',
                'title_type': 'Developmental',
                'division': 'open',
                'weight_class': 'open',
                'suggested_prestige': 35,
                'is_tag_team': False
            },
            {
                'id': 'openweight',
                'name': 'Openweight Championship',
                'description': 'Open to all genders and weight classes',
                'title_type': 'Secondary',
                'division': 'intergender',
                'weight_class': 'open',
                'suggested_prestige': 70,
                'is_tag_team': False
            },
            {
                'id': 'pure',
                'name': 'Pure Wrestling Championship',
                'description': 'Technical wrestling only - strict rules',
                'title_type': 'Midcard',
                'division': 'open',
                'weight_class': 'open',
                'suggested_prestige': 60,
                'is_tag_team': False
            }
        ]
    
    @staticmethod
    def get_preset_by_id(preset_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific preset by ID"""
        presets = ChampionshipPresets.get_all_presets()
        for preset in presets:
            if preset['id'] == preset_id:
                return preset
        return None