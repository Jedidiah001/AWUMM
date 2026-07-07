"""
Enhanced Contract Model with Advanced Incentive System
STEP 122: Contract Extension Incentives (Advanced)

Supports 10+ incentive types including:
- Long-term commitment bonuses
- Performance-based escalators
- No-trade clauses
- Creative control tiers
- Merchandise revenue sharing
- Guaranteed PPV appearances
- Injury protection
- Option years
- Buy-out clauses
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class CreativeControlLevel(Enum):
    """Levels of creative input a wrestler can have"""
    NONE = "none"  # No input, follow all booking
    CONSULTATION = "consultation"  # Opinions heard but not binding
    APPROVAL = "approval"  # Can reject ideas
    PARTNERSHIP = "partnership"  # Collaborative development
    FULL = "full"  # Complete control (rare, top stars only)


class IncentiveType(Enum):
    """Types of contract incentives"""
    SIGNING_BONUS = "signing_bonus"
    PERFORMANCE_ESCALATOR = "performance_escalator"
    MERCHANDISE_SHARE = "merchandise_share"
    PPV_GUARANTEE = "ppv_guarantee"
    TITLE_GUARANTEE = "title_guarantee"
    NO_TRADE_CLAUSE = "no_trade_clause"
    CREATIVE_CONTROL = "creative_control"
    INJURY_PROTECTION = "injury_protection"
    OPTION_YEAR = "option_year"
    BUY_OUT_CLAUSE = "buy_out_clause"
    BRAND_PLACEMENT = "brand_placement"
    APPEARANCE_LIMIT = "appearance_limit"


@dataclass
class ContractIncentive:
    """Individual contract incentive/clause"""
    incentive_type: IncentiveType
    description: str
    value: Any  # Type depends on incentive_type
    conditions: Optional[Dict[str, Any]] = None
    is_active: bool = True
    triggered_count: int = 0  # How many times this has activated
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'incentive_type': self.incentive_type.value,
            'description': self.description,
            'value': self.value,
            'conditions': self.conditions or {},
            'is_active': self.is_active,
            'triggered_count': self.triggered_count
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ContractIncentive':
        return ContractIncentive(
            incentive_type=IncentiveType(data['incentive_type']),
            description=data['description'],
            value=data['value'],
            conditions=data.get('conditions'),
            is_active=data.get('is_active', True),
            triggered_count=data.get('triggered_count', 0)
        )


@dataclass
class Contract:
    """
    Enhanced Contract with Advanced Incentive Support
    
    Base Fields:
    - salary_per_show: Base pay per appearance
    - total_length_weeks: Original contract length
    - weeks_remaining: Time until expiration
    - signing_year/week: When contract was signed
    
    STEP 121 Fields:
    - early_renewal_offered: Early renewal status
    - renewal_attempts: Number of negotiation attempts
    
    STEP 122 Fields:
    - incentives: List of active contract incentives
    - base_salary: Original salary before escalators
    - current_escalated_salary: Salary after performance bonuses
    - merchandise_share_percentage: % of merch revenue
    - creative_control_level: Level of booking input
    - guaranteed_ppv_appearances: Minimum PPV matches per year
    - has_no_trade_clause: Cannot be traded/moved without consent
    - has_injury_protection: Full pay during injuries
    - option_years_remaining: Team-controlled extensions
    - buy_out_penalty: Cost to terminate early
    """
    
    # Base contract fields
    salary_per_show: int
    total_length_weeks: int
    weeks_remaining: int
    signing_year: int
    signing_week: int
    
    # STEP 121: Early renewal fields
    early_renewal_offered: bool = False
    early_renewal_week: Optional[int] = None
    early_renewal_year: Optional[int] = None
    renewal_attempts: int = 0
    last_renewal_attempt_week: Optional[int] = None
    last_renewal_attempt_year: Optional[int] = None
    
    # STEP 122: Advanced incentive fields
    incentives: List[ContractIncentive] = field(default_factory=list)
    base_salary: Optional[int] = None  # Original salary before escalators
    current_escalated_salary: Optional[int] = None  # After bonuses
    
    # Specific incentive tracking
    merchandise_share_percentage: float = 30.0  # Default 30% to wrestler
    creative_control_level: CreativeControlLevel = CreativeControlLevel.NONE
    guaranteed_ppv_appearances: int = 0  # Minimum PPV matches per year
    has_no_trade_clause: bool = False
    has_injury_protection: bool = False
    injury_protection_percentage: float = 100.0  # % of salary during injury
    option_years_remaining: int = 0  # Company can extend automatically
    buy_out_penalty: int = 0  # Cost to release early
    restricted_brands: List[str] = field(default_factory=list)  # Brands wrestler won't work
    max_appearances_per_year: Optional[int] = None  # Appearance limit
    
    # Performance tracking for escalators
    ppv_appearances_this_year: int = 0
    title_reigns_this_contract: int = 0
    average_match_rating: float = 0.0
    total_matches_this_contract: int = 0
    
    def __post_init__(self):
        """Initialize computed fields"""
        raw_weeks_remaining = self.weeks_remaining
        self.salary_per_show = max(0, _coerce_int(self.salary_per_show, 0))
        self.total_length_weeks = max(
            0,
            _coerce_int(self.total_length_weeks, _coerce_int(raw_weeks_remaining, 0))
        )
        self.weeks_remaining = max(
            0,
            _coerce_int(raw_weeks_remaining, self.total_length_weeks)
        )

        if self.base_salary is None:
            self.base_salary = self.salary_per_show
        if self.current_escalated_salary is None:
            self.current_escalated_salary = self.salary_per_show

        self.base_salary = max(0, _coerce_int(self.base_salary, self.salary_per_show))
        self.current_escalated_salary = max(
            0,
            _coerce_int(self.current_escalated_salary, self.salary_per_show)
        )
        self.merchandise_share_percentage = max(
            0.0,
            min(100.0, _coerce_float(self.merchandise_share_percentage, 30.0))
        )
        self.injury_protection_percentage = max(
            0.0,
            min(100.0, _coerce_float(self.injury_protection_percentage, 100.0))
        )
        self.guaranteed_ppv_appearances = max(
            0,
            _coerce_int(self.guaranteed_ppv_appearances, 0)
        )
        self.option_years_remaining = max(0, _coerce_int(self.option_years_remaining, 0))
        self.buy_out_penalty = max(0, _coerce_int(self.buy_out_penalty, 0))
        self.ppv_appearances_this_year = max(
            0,
            _coerce_int(self.ppv_appearances_this_year, 0)
        )
        self.title_reigns_this_contract = max(
            0,
            _coerce_int(self.title_reigns_this_contract, 0)
        )
        self.total_matches_this_contract = max(
            0,
            _coerce_int(self.total_matches_this_contract, 0)
        )
        self.average_match_rating = _coerce_float(self.average_match_rating, 0.0)

        if isinstance(self.creative_control_level, str):
            self.creative_control_level = CreativeControlLevel(
                self.creative_control_level or CreativeControlLevel.NONE.value
            )
    
    # ========================================================================
    # Incentive Management
    # ========================================================================
    
    def add_incentive(self, incentive: ContractIncentive):
        """Add a new incentive to the contract"""
        # Check for conflicts
        conflicts = self.check_incentive_conflicts(incentive)
        if conflicts:
            raise ValueError(f"Incentive conflicts with existing clauses: {conflicts}")
        
        self.incentives.append(incentive)
        self._apply_incentive_effects(incentive)
    
    def remove_incentive(self, incentive_type: IncentiveType):
        """Remove an incentive by type"""
        self.incentives = [i for i in self.incentives if i.incentive_type != incentive_type]
    
    def get_incentive(self, incentive_type: IncentiveType) -> Optional[ContractIncentive]:
        """Get specific incentive by type"""
        for incentive in self.incentives:
            if incentive.incentive_type == incentive_type:
                return incentive
        return None
    
    def has_incentive(self, incentive_type: IncentiveType) -> bool:
        """Check if contract has specific incentive"""
        return self.get_incentive(incentive_type) is not None
    
    def check_incentive_conflicts(self, new_incentive: ContractIncentive) -> List[str]:
        """Check if new incentive conflicts with existing ones"""
        conflicts = []
        
        # No-trade clause conflicts with brand placement restrictions
        if new_incentive.incentive_type == IncentiveType.NO_TRADE_CLAUSE:
            if self.has_incentive(IncentiveType.BRAND_PLACEMENT):
                conflicts.append("No-trade clause conflicts with brand placement requirements")
        
        # Can't have multiple of certain types
        single_only_types = [
            IncentiveType.CREATIVE_CONTROL,
            IncentiveType.NO_TRADE_CLAUSE,
            IncentiveType.INJURY_PROTECTION,
            IncentiveType.MERCHANDISE_SHARE
        ]
        
        if new_incentive.incentive_type in single_only_types:
            if self.has_incentive(new_incentive.incentive_type):
                conflicts.append(f"Contract already has {new_incentive.incentive_type.value}")
        
        return conflicts
    
    def _apply_incentive_effects(self, incentive: ContractIncentive):
        """Apply immediate effects of adding an incentive"""
        if incentive.incentive_type == IncentiveType.CREATIVE_CONTROL:
            self.creative_control_level = CreativeControlLevel(incentive.value)
        
        elif incentive.incentive_type == IncentiveType.NO_TRADE_CLAUSE:
            self.has_no_trade_clause = True
        
        elif incentive.incentive_type == IncentiveType.INJURY_PROTECTION:
            self.has_injury_protection = True
            self.injury_protection_percentage = incentive.value
        
        elif incentive.incentive_type == IncentiveType.MERCHANDISE_SHARE:
            self.merchandise_share_percentage = incentive.value
        
        elif incentive.incentive_type == IncentiveType.PPV_GUARANTEE:
            self.guaranteed_ppv_appearances = incentive.value
        
        elif incentive.incentive_type == IncentiveType.OPTION_YEAR:
            self.option_years_remaining = incentive.value
        
        elif incentive.incentive_type == IncentiveType.BUY_OUT_CLAUSE:
            self.buy_out_penalty = incentive.value
        
        elif incentive.incentive_type == IncentiveType.BRAND_PLACEMENT:
            self.restricted_brands = incentive.value.get('restricted_brands', [])
        
        elif incentive.incentive_type == IncentiveType.APPEARANCE_LIMIT:
            self.max_appearances_per_year = incentive.value
    
    # ========================================================================
    # Performance Escalators
    # ========================================================================
    
    def check_performance_escalators(self):
        """Check if any performance escalators should trigger"""
        escalated = False
        
        for incentive in self.incentives:
            if incentive.incentive_type == IncentiveType.PERFORMANCE_ESCALATOR:
                if self._evaluate_escalator_condition(incentive):
                    self._trigger_escalator(incentive)
                    escalated = True
        
        return escalated
    
    def _evaluate_escalator_condition(self, incentive: ContractIncentive) -> bool:
        """Check if escalator conditions are met"""
        conditions = incentive.conditions or {}
        
        # Popularity threshold
        if 'min_popularity' in conditions:
            # Would need wrestler object to check
            pass
        
        # Match rating threshold
        if 'min_avg_rating' in conditions:
            if self.average_match_rating >= conditions['min_avg_rating']:
                return True
        
        # Title reign requirement
        if 'min_title_reigns' in conditions:
            if self.title_reigns_this_contract >= conditions['min_title_reigns']:
                return True
        
        # PPV appearances requirement
        if 'min_ppv_appearances' in conditions:
            if self.ppv_appearances_this_year >= conditions['min_ppv_appearances']:
                return True
        
        return False
    
    def _trigger_escalator(self, incentive: ContractIncentive):
        """Apply salary escalation"""
        increase_amount = incentive.value
        
        # Value can be flat amount or percentage
        if isinstance(increase_amount, str) and '%' in increase_amount:
            # Percentage increase
            pct = float(increase_amount.replace('%', '')) / 100
            self.current_escalated_salary = int(self.base_salary * (1 + pct))
        else:
            # Flat increase
            self.current_escalated_salary = self.base_salary + int(increase_amount)
        
        # Update actual salary
        self.salary_per_show = self.current_escalated_salary
        incentive.triggered_count += 1
    
    # ========================================================================
    # Contract Validation
    # ========================================================================
    
    def validate_contract(self) -> Dict[str, Any]:
        """Validate contract and return any issues"""
        issues = []
        warnings = []
        
        # Check for conflicting incentives
        for incentive in self.incentives:
            conflicts = self.check_incentive_conflicts(incentive)
            if conflicts:
                issues.extend(conflicts)
        
        # Warn about expensive contracts
        total_cost = self.calculate_total_value()
        if total_cost > 10000000:  # $10M
            warnings.append(f"Very expensive contract: ${total_cost:,}")
        
        # Check PPV guarantee feasibility
        if self.guaranteed_ppv_appearances > 12:
            warnings.append(f"PPV guarantee ({self.guaranteed_ppv_appearances}) exceeds typical annual PPVs")
        
        # Check merchandise share
        if self.merchandise_share_percentage > 60:
            warnings.append(f"High merch share: {self.merchandise_share_percentage}% (standard is 30%)")
        
        # Check appearance limits
        if self.max_appearances_per_year and self.max_appearances_per_year < 100:
            warnings.append(f"Low appearance limit: {self.max_appearances_per_year}/year")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def calculate_total_value(self) -> int:
        """Calculate total contract value including all incentives"""
        # Base contract value (assume 3 shows per week)
        base_value = self.salary_per_show * self.total_length_weeks * 3
        
        # Add signing bonuses
        signing_bonus = 0
        for incentive in self.incentives:
            if incentive.incentive_type == IncentiveType.SIGNING_BONUS:
                signing_bonus += incentive.value
        
        # Estimate escalator potential
        escalator_potential = 0
        for incentive in self.incentives:
            if incentive.incentive_type == IncentiveType.PERFORMANCE_ESCALATOR:
                # Conservative estimate: 50% chance of triggering
                if isinstance(incentive.value, str) and '%' in incentive.value:
                    pct = float(incentive.value.replace('%', '')) / 100
                    escalator_potential += int(base_value * pct * 0.5)
                else:
                    escalator_potential += int(incentive.value) * 156 * 0.5  # 3 years worth
        
        return base_value + signing_bonus + escalator_potential
    
    # ========================================================================
    # Serialization
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'salary_per_show': self.salary_per_show,
            'total_length_weeks': self.total_length_weeks,
            'weeks_remaining': self.weeks_remaining,
            'signing_year': self.signing_year,
            'signing_week': self.signing_week,
            
            # STEP 121
            'early_renewal_offered': self.early_renewal_offered,
            'early_renewal_week': self.early_renewal_week,
            'early_renewal_year': self.early_renewal_year,
            'renewal_attempts': self.renewal_attempts,
            'last_renewal_attempt_week': self.last_renewal_attempt_week,
            'last_renewal_attempt_year': self.last_renewal_attempt_year,
            
            # STEP 122
            'incentives': [i.to_dict() for i in self.incentives],
            'base_salary': self.base_salary,
            'current_escalated_salary': self.current_escalated_salary,
            'merchandise_share_percentage': self.merchandise_share_percentage,
            'creative_control_level': self.creative_control_level.value,
            'guaranteed_ppv_appearances': self.guaranteed_ppv_appearances,
            'has_no_trade_clause': self.has_no_trade_clause,
            'has_injury_protection': self.has_injury_protection,
            'injury_protection_percentage': self.injury_protection_percentage,
            'option_years_remaining': self.option_years_remaining,
            'buy_out_penalty': self.buy_out_penalty,
            'restricted_brands': self.restricted_brands,
            'max_appearances_per_year': self.max_appearances_per_year,
            
            # Performance tracking
            'ppv_appearances_this_year': self.ppv_appearances_this_year,
            'title_reigns_this_contract': self.title_reigns_this_contract,
            'average_match_rating': self.average_match_rating,
            'total_matches_this_contract': self.total_matches_this_contract
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Contract':
        """Create Contract from dictionary"""
        incentives = [
            ContractIncentive.from_dict(i) 
            for i in data.get('incentives', [])
        ]
        
        return Contract(
            salary_per_show=data['salary_per_show'],
            total_length_weeks=data['total_length_weeks'],
            weeks_remaining=data['weeks_remaining'],
            signing_year=data['signing_year'],
            signing_week=data['signing_week'],
            
            early_renewal_offered=data.get('early_renewal_offered', False),
            early_renewal_week=data.get('early_renewal_week'),
            early_renewal_year=data.get('early_renewal_year'),
            renewal_attempts=data.get('renewal_attempts', 0),
            last_renewal_attempt_week=data.get('last_renewal_attempt_week'),
            last_renewal_attempt_year=data.get('last_renewal_attempt_year'),
            
            incentives=incentives,
            base_salary=data.get('base_salary'),
            current_escalated_salary=data.get('current_escalated_salary'),
            merchandise_share_percentage=data.get('merchandise_share_percentage', 30.0),
            creative_control_level=CreativeControlLevel(data.get('creative_control_level', 'none')),
            guaranteed_ppv_appearances=data.get('guaranteed_ppv_appearances', 0),
            has_no_trade_clause=data.get('has_no_trade_clause', False),
            has_injury_protection=data.get('has_injury_protection', False),
            injury_protection_percentage=data.get('injury_protection_percentage', 100.0),
            option_years_remaining=data.get('option_years_remaining', 0),
            buy_out_penalty=data.get('buy_out_penalty', 0),
            restricted_brands=data.get('restricted_brands', []),
            max_appearances_per_year=data.get('max_appearances_per_year'),
            
            ppv_appearances_this_year=data.get('ppv_appearances_this_year', 0),
            title_reigns_this_contract=data.get('title_reigns_this_contract', 0),
            average_match_rating=data.get('average_match_rating', 0.0),
            total_matches_this_contract=data.get('total_matches_this_contract', 0)
        )
