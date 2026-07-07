"""
Contract Incentive Engine
STEP 122: Advanced Contract Extension Incentives

Handles creation, validation, and management of contract incentives.
"""

from typing import Dict, Any, List, Optional, Tuple
from models.contract import Contract, ContractIncentive, IncentiveType, CreativeControlLevel
from models.wrestler import Wrestler
import random


class ContractIncentiveEngine:
    """
    Manages contract incentive creation, validation, and negotiation.
    
    Provides:
    - Pre-built incentive templates
    - Custom incentive creation
    - Package deal construction
    - Cost/benefit analysis
    - Acceptance probability calculation
    """
    
    def __init__(self):
        self.incentive_templates = self._initialize_templates()
    
    # ========================================================================
    # Incentive Templates
    # ========================================================================
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Pre-built incentive templates for quick use"""
        return {
            # Signing Bonuses
            'signing_bonus_small': {
                'type': IncentiveType.SIGNING_BONUS,
                'description': 'Small signing bonus',
                'value': 10000,
                'acceptance_modifier': 5  # +5% acceptance
            },
            'signing_bonus_medium': {
                'type': IncentiveType.SIGNING_BONUS,
                'description': 'Medium signing bonus',
                'value': 25000,
                'acceptance_modifier': 10
            },
            'signing_bonus_large': {
                'type': IncentiveType.SIGNING_BONUS,
                'description': 'Large signing bonus',
                'value': 50000,
                'acceptance_modifier': 15
            },
            'signing_bonus_superstar': {
                'type': IncentiveType.SIGNING_BONUS,
                'description': 'Superstar signing bonus',
                'value': 100000,
                'acceptance_modifier': 20
            },
            
            # Performance Escalators
            'escalator_popularity': {
                'type': IncentiveType.PERFORMANCE_ESCALATOR,
                'description': 'Salary increases if popularity reaches 80+',
                'value': '20%',  # 20% salary increase
                'conditions': {'min_popularity': 80},
                'acceptance_modifier': 8
            },
            'escalator_match_quality': {
                'type': IncentiveType.PERFORMANCE_ESCALATOR,
                'description': 'Salary increases if average match rating exceeds 4.0 stars',
                'value': '15%',
                'conditions': {'min_avg_rating': 4.0},
                'acceptance_modifier': 7
            },
            'escalator_title_reign': {
                'type': IncentiveType.PERFORMANCE_ESCALATOR,
                'description': 'Salary increases after winning any championship',
                'value': 5000,  # Flat $5k increase
                'conditions': {'min_title_reigns': 1},
                'acceptance_modifier': 10
            },
            'escalator_ppv': {
                'type': IncentiveType.PERFORMANCE_ESCALATOR,
                'description': 'Salary increases after 6+ PPV appearances in a year',
                'value': '10%',
                'conditions': {'min_ppv_appearances': 6},
                'acceptance_modifier': 6
            },
            
            # Merchandise Revenue Sharing
            'merch_standard': {
                'type': IncentiveType.MERCHANDISE_SHARE,
                'description': 'Standard merchandise split (30%)',
                'value': 30.0,
                'acceptance_modifier': 0  # Default, no bonus
            },
            'merch_improved': {
                'type': IncentiveType.MERCHANDISE_SHARE,
                'description': 'Improved merchandise split (40%)',
                'value': 40.0,
                'acceptance_modifier': 8
            },
            'merch_premium': {
                'type': IncentiveType.MERCHANDISE_SHARE,
                'description': 'Premium merchandise split (50%)',
                'value': 50.0,
                'acceptance_modifier': 15
            },
            'merch_elite': {
                'type': IncentiveType.MERCHANDISE_SHARE,
                'description': 'Elite merchandise split (60%)',
                'value': 60.0,
                'acceptance_modifier': 25
            },
            
            # PPV Guarantees
            'ppv_guarantee_6': {
                'type': IncentiveType.PPV_GUARANTEE,
                'description': 'Guaranteed 6 PPV appearances per year',
                'value': 6,
                'acceptance_modifier': 10
            },
            'ppv_guarantee_8': {
                'type': IncentiveType.PPV_GUARANTEE,
                'description': 'Guaranteed 8 PPV appearances per year',
                'value': 8,
                'acceptance_modifier': 15
            },
            'ppv_guarantee_all': {
                'type': IncentiveType.PPV_GUARANTEE,
                'description': 'Guaranteed appearance at all PPVs',
                'value': 12,
                'acceptance_modifier': 25
            },
            
            # Title Guarantees
            'title_shot_guarantee': {
                'type': IncentiveType.TITLE_GUARANTEE,
                'description': 'Guaranteed championship opportunity within 6 months',
                'value': {'timeframe_weeks': 26, 'title_tier': 'any'},
                'acceptance_modifier': 20
            },
            'world_title_shot': {
                'type': IncentiveType.TITLE_GUARANTEE,
                'description': 'Guaranteed World Championship match within 1 year',
                'value': {'timeframe_weeks': 52, 'title_tier': 'world'},
                'acceptance_modifier': 30
            },
            
            # No-Trade Clauses
            'no_trade_full': {
                'type': IncentiveType.NO_TRADE_CLAUSE,
                'description': 'Full no-trade clause (cannot be moved without consent)',
                'value': True,
                'acceptance_modifier': 12
            },
            'no_trade_limited': {
                'type': IncentiveType.NO_TRADE_CLAUSE,
                'description': 'Limited no-trade clause (can veto specific brands)',
                'value': {'veto_count': 1},
                'acceptance_modifier': 8
            },
            
            # Creative Control
            'creative_consultation': {
                'type': IncentiveType.CREATIVE_CONTROL,
                'description': 'Consulted on storylines (opinions heard)',
                'value': CreativeControlLevel.CONSULTATION.value,
                'acceptance_modifier': 5
            },
            'creative_approval': {
                'type': IncentiveType.CREATIVE_CONTROL,
                'description': 'Can approve/reject storyline ideas',
                'value': CreativeControlLevel.APPROVAL.value,
                'acceptance_modifier': 15
            },
            'creative_partnership': {
                'type': IncentiveType.CREATIVE_CONTROL,
                'description': 'Collaborative storyline development',
                'value': CreativeControlLevel.PARTNERSHIP.value,
                'acceptance_modifier': 25
            },
            'creative_full': {
                'type': IncentiveType.CREATIVE_CONTROL,
                'description': 'Full creative control over character',
                'value': CreativeControlLevel.FULL.value,
                'acceptance_modifier': 40
            },
            
            # Injury Protection
            'injury_protection_full': {
                'type': IncentiveType.INJURY_PROTECTION,
                'description': 'Full salary during injury recovery',
                'value': 100.0,
                'acceptance_modifier': 10
            },
            'injury_protection_partial': {
                'type': IncentiveType.INJURY_PROTECTION,
                'description': '75% salary during injury recovery',
                'value': 75.0,
                'acceptance_modifier': 6
            },
            
            # Option Years
            'option_year_1': {
                'type': IncentiveType.OPTION_YEAR,
                'description': 'Company option for 1 additional year',
                'value': 1,
                'acceptance_modifier': -5  # Negative (favors company)
            },
            'option_year_2': {
                'type': IncentiveType.OPTION_YEAR,
                'description': 'Company option for 2 additional years',
                'value': 2,
                'acceptance_modifier': -10
            },
            
            # Buy-Out Clauses
            'buyout_standard': {
                'type': IncentiveType.BUY_OUT_CLAUSE,
                'description': 'Standard buy-out penalty (50% of remaining contract)',
                'value': 0.5,  # 50% multiplier
                'acceptance_modifier': 8
            },
            'buyout_premium': {
                'type': IncentiveType.BUY_OUT_CLAUSE,
                'description': 'Premium buy-out penalty (100% of remaining contract)',
                'value': 1.0,
                'acceptance_modifier': 15
            },
            
            # Brand Placement
            'brand_alpha_only': {
                'type': IncentiveType.BRAND_PLACEMENT,
                'description': 'Exclusive to ROC Alpha',
                'value': {'preferred_brand': 'ROC Alpha', 'restricted_brands': ['ROC Velocity', 'ROC Vanguard']},
                'acceptance_modifier': 5
            },
            'brand_velocity_only': {
                'type': IncentiveType.BRAND_PLACEMENT,
                'description': 'Exclusive to ROC Velocity',
                'value': {'preferred_brand': 'ROC Velocity', 'restricted_brands': ['ROC Alpha', 'ROC Vanguard']},
                'acceptance_modifier': 5
            },
            'brand_vanguard_only': {
                'type': IncentiveType.BRAND_PLACEMENT,
                'description': 'Exclusive to ROC Vanguard',
                'value': {'preferred_brand': 'ROC Vanguard', 'restricted_brands': ['ROC Alpha', 'ROC Velocity']},
                'acceptance_modifier': 5
            },
            
            # Appearance Limits
            'appearances_reduced': {
                'type': IncentiveType.APPEARANCE_LIMIT,
                'description': 'Maximum 150 appearances per year',
                'value': 150,
                'acceptance_modifier': 10
            },
            'appearances_part_time': {
                'type': IncentiveType.APPEARANCE_LIMIT,
                'description': 'Part-time schedule (maximum 100 appearances per year)',
                'value': 100,
                'acceptance_modifier': 20
            },
            'appearances_legend': {
                'type': IncentiveType.APPEARANCE_LIMIT,
                'description': 'Legend schedule (maximum 50 appearances per year)',
                'value': 50,
                'acceptance_modifier': 30
            }
        }
    
    # ========================================================================
    # Incentive Creation
    # ========================================================================
    
    def create_incentive_from_template(self, template_name: str) -> ContractIncentive:
        """Create incentive from pre-built template"""
        if template_name not in self.incentive_templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        template = self.incentive_templates[template_name]
        
        return ContractIncentive(
            incentive_type=template['type'],
            description=template['description'],
            value=template['value'],
            conditions=template.get('conditions')
        )
    
    def create_custom_incentive(
        self,
        incentive_type: IncentiveType,
        description: str,
        value: Any,
        conditions: Optional[Dict[str, Any]] = None
    ) -> ContractIncentive:
        """Create custom incentive with validation"""
        # Validate value based on type
        self._validate_incentive_value(incentive_type, value)
        
        return ContractIncentive(
            incentive_type=incentive_type,
            description=description,
            value=value,
            conditions=conditions
        )
    
    def _validate_incentive_value(self, incentive_type: IncentiveType, value: Any):
        """Validate incentive value is appropriate for type"""
        if incentive_type == IncentiveType.SIGNING_BONUS:
            if not isinstance(value, int) or value < 0:
                raise ValueError("Signing bonus must be positive integer")
        
        elif incentive_type == IncentiveType.MERCHANDISE_SHARE:
            if not isinstance(value, (int, float)) or value < 0 or value > 100:
                raise ValueError("Merchandise share must be 0-100%")
        
        elif incentive_type == IncentiveType.PPV_GUARANTEE:
            if not isinstance(value, int) or value < 0 or value > 20:
                raise ValueError("PPV guarantee must be 0-20")
        
        elif incentive_type == IncentiveType.CREATIVE_CONTROL:
            if value not in [level.value for level in CreativeControlLevel]:
                raise ValueError(f"Invalid creative control level: {value}")
        
        elif incentive_type == IncentiveType.INJURY_PROTECTION:
            if not isinstance(value, (int, float)) or value < 0 or value > 100:
                raise ValueError("Injury protection must be 0-100%")
        
        elif incentive_type == IncentiveType.OPTION_YEAR:
            if not isinstance(value, int) or value < 0 or value > 5:
                raise ValueError("Option years must be 0-5")
    
    # ========================================================================
    # Package Deal Construction
    # ========================================================================
    
    def build_contract_package(
        self,
        wrestler: Wrestler,
        base_salary: int,
        contract_weeks: int,
        incentive_templates: List[str]
    ) -> Tuple[Contract, Dict[str, Any]]:
        """
        Build complete contract package with multiple incentives.
        
        Returns:
            (contract, package_analysis)
        """
        # Create base contract
        contract = Contract(
            salary_per_show=base_salary,
            total_length_weeks=contract_weeks,
            weeks_remaining=contract_weeks,
            signing_year=1,  # Would be current year in real usage
            signing_week=1
        )
        
        # Add incentives
        added_incentives = []
        conflicts = []
        
        for template_name in incentive_templates:
            try:
                incentive = self.create_incentive_from_template(template_name)
                contract.add_incentive(incentive)
                added_incentives.append(template_name)
            except ValueError as e:
                conflicts.append(f"{template_name}: {str(e)}")
        
        # Validate contract
        validation = contract.validate_contract()
        
        # Calculate costs and benefits
        total_cost = contract.calculate_total_value()
        acceptance_prob = self.calculate_package_acceptance_probability(
            wrestler,
            contract,
            incentive_templates
        )
        
        package_analysis = {
            'total_cost': total_cost,
            'base_contract_cost': base_salary * contract_weeks * 3,
            'incentive_cost': total_cost - (base_salary * contract_weeks * 3),
            'acceptance_probability': acceptance_prob,
            'added_incentives': added_incentives,
            'conflicts': conflicts,
            'validation': validation,
            'risk_level': self._calculate_risk_level(total_cost, acceptance_prob)
        }
        
        return contract, package_analysis
    
    def calculate_package_acceptance_probability(
        self,
        wrestler: Wrestler,
        contract: Contract,
        incentive_templates: List[str]
    ) -> float:
        """Calculate probability wrestler accepts contract package"""
        # Start with base probability
        from economy.contracts import contract_manager
        market_value = contract_manager.calculate_market_value(wrestler)
        
        salary_ratio = contract.salary_per_show / market_value if market_value > 0 else 1.0
        
        # Base probability from salary
        if salary_ratio >= 1.2:
            base_prob = 90.0
        elif salary_ratio >= 1.0:
            base_prob = 75.0
        elif salary_ratio >= 0.9:
            base_prob = 60.0
        elif salary_ratio >= 0.8:
            base_prob = 40.0
        else:
            base_prob = 20.0
        
        # Morale modifier
        morale_mod = (wrestler.morale / 100) * 20  # ±20%
        
        # Incentive modifiers
        incentive_mod = 0.0
        for template_name in incentive_templates:
            if template_name in self.incentive_templates:
                incentive_mod += self.incentive_templates[template_name].get('acceptance_modifier', 0)
        
        # Role-specific adjustments
        role_mod = 0
        if wrestler.role == 'Main Event':
            # Main eventers demand more
            if contract.has_incentive(IncentiveType.CREATIVE_CONTROL):
                role_mod += 10
            if contract.has_incentive(IncentiveType.PPV_GUARANTEE):
                role_mod += 5
        elif wrestler.role in ['Upper Midcard', 'Midcard']:
            # Midcarders love title guarantees
            if contract.has_incentive(IncentiveType.TITLE_GUARANTEE):
                role_mod += 15
        
        # Major superstar bonus for prestige incentives
        if wrestler.is_major_superstar:
            if contract.creative_control_level in [CreativeControlLevel.PARTNERSHIP, CreativeControlLevel.FULL]:
                role_mod += 10
            if contract.has_no_trade_clause:
                role_mod += 5
        
        # Calculate final probability
        final_prob = base_prob + morale_mod + incentive_mod + role_mod
        
        # Clamp to 5-98%
        return max(5.0, min(98.0, final_prob))
    
    def _calculate_risk_level(self, total_cost: int, acceptance_prob: float) -> str:
        """Determine risk level of contract offer"""
        if acceptance_prob >= 80:
            return 'LOW'
        elif acceptance_prob >= 60:
            if total_cost > 5000000:
                return 'MEDIUM'
            else:
                return 'LOW'
        elif acceptance_prob >= 40:
            return 'MEDIUM'
        elif acceptance_prob >= 20:
            return 'HIGH'
        else:
            return 'VERY HIGH'
    
    # ========================================================================
    # Recommended Packages
    # ========================================================================
    
    def get_recommended_incentives_for_wrestler(self, wrestler: Wrestler) -> List[str]:
        """Get recommended incentive templates based on wrestler attributes"""
        recommendations = []
        
        # Role-based recommendations
        if wrestler.role == 'Main Event':
            recommendations.extend([
                'signing_bonus_large',
                'creative_partnership',
                'ppv_guarantee_all',
                'merch_premium',
                'no_trade_full'
            ])
        
        elif wrestler.role == 'Upper Midcard':
            recommendations.extend([
                'signing_bonus_medium',
                'title_shot_guarantee',
                'ppv_guarantee_6',
                'merch_improved',
                'creative_consultation'
            ])
        
        elif wrestler.role == 'Midcard':
            recommendations.extend([
                'signing_bonus_small',
                'escalator_title_reign',
                'ppv_guarantee_6',
                'injury_protection_full'
            ])
        
        else:  # Lower card
            recommendations.extend([
                'injury_protection_full',
                'escalator_match_quality'
            ])
        
        # Major superstar additions
        if wrestler.is_major_superstar:
            recommendations.extend([
                'creative_approval',
                'buyout_premium',
                'appearances_reduced'
            ])
        
        # Age-based additions
        if wrestler.age >= 40:
            recommendations.extend([
                'appearances_part_time',
                'injury_protection_full'
            ])
        elif wrestler.age <= 25:
            recommendations.extend([
                'escalator_popularity',
                'option_year_1'
            ])
        
        # Performance-based additions
        if wrestler.popularity >= 80:
            recommendations.extend([
                'merch_elite',
                'ppv_guarantee_8'
            ])
        
        if wrestler.overall_rating >= 80:
            recommendations.extend([
                'escalator_match_quality',
                'world_title_shot'
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)
        
        return unique_recs[:10]  # Return top 10
    
    def get_budget_friendly_package(self, wrestler: Wrestler) -> List[str]:
        """Get incentive package that minimizes cash outlay"""
        return [
            'escalator_popularity',  # Only costs if they succeed
            'escalator_match_quality',  # Performance-based
            'injury_protection_partial',  # Cheaper than full
            'creative_consultation'  # Low cost
        ]
    
    def get_superstar_package(self, wrestler: Wrestler) -> List[str]:
        """Get premium package for major signings"""
        return [
            'signing_bonus_superstar',
            'creative_full',
            'ppv_guarantee_all',
            'merch_elite',
            'no_trade_full',
            'injury_protection_full',
            'buyout_premium',
            'world_title_shot'
        ]
    
    def get_long_term_security_package(self, wrestler: Wrestler) -> List[str]:
        """Get package emphasizing security and guarantees"""
        return [
            'signing_bonus_large',
            'injury_protection_full',
            'ppv_guarantee_6',
            'no_trade_full',
            'buyout_standard',
            'title_shot_guarantee'
        ]
    
    # ========================================================================
    # Incentive Comparison
    # ========================================================================
    
    def compare_incentive_packages(
        self,
        wrestler: Wrestler,
        base_salary: int,
        contract_weeks: int,
        package_a: List[str],
        package_b: List[str]
    ) -> Dict[str, Any]:
        """Compare two incentive packages side-by-side"""
        contract_a, analysis_a = self.build_contract_package(
            wrestler, base_salary, contract_weeks, package_a
        )
        
        contract_b, analysis_b = self.build_contract_package(
            wrestler, base_salary, contract_weeks, package_b
        )
        
        return {
            'package_a': {
                'incentives': package_a,
                'total_cost': analysis_a['total_cost'],
                'acceptance_probability': analysis_a['acceptance_probability'],
                'risk_level': analysis_a['risk_level']
            },
            'package_b': {
                'incentives': package_b,
                'total_cost': analysis_b['total_cost'],
                'acceptance_probability': analysis_b['acceptance_probability'],
                'risk_level': analysis_b['risk_level']
            },
            'comparison': {
                'cost_difference': analysis_b['total_cost'] - analysis_a['total_cost'],
                'acceptance_difference': analysis_b['acceptance_probability'] - analysis_a['acceptance_probability'],
                'better_value': 'package_a' if (
                    analysis_a['acceptance_probability'] / max(analysis_a['total_cost'], 1) >
                    analysis_b['acceptance_probability'] / max(analysis_b['total_cost'], 1)
                ) else 'package_b'
            }
        }


# Global incentive engine instance
incentive_engine = ContractIncentiveEngine()