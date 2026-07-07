"""
Contract Management System
Handles contract negotiations, extensions, releases, and expirations.
STEP 119: Enhanced with Contract Countdown Tracking dashboard categories
STEP 120: Enhanced with contract alert generation
STEP 121: Enhanced with early renewal probability calculation, brand transfers, and loyalty discounts
"""

from typing import Dict, List, Tuple, Optional, Any
from models.wrestler import Wrestler, Contract
from models.contract_alert import contract_alert_manager
import random


class ContractManager:
    """
    Manages all contract-related operations.
    
    Features:
    - Contract extension negotiations
    - Salary adjustments based on performance
    - Contract release/termination
    - Free agent pool management
    - Automatic contract expiration warnings
    - STEP 119: Contract countdown tracking with dashboard categories
    - STEP 120: Contract alert generation for expiring contracts
    - STEP 121: Early renewal probability calculation
    - STEP 121: Brand transfer execution
    - STEP 121: Loyalty discount calculation
    """
    
    def __init__(self):
        self.free_agents = []  # List of Wrestler objects not under contract

    def _get_contract_weeks(self, wrestler: Wrestler) -> Optional[int]:
        """Return a normalized weeks remaining value for contract timelines."""
        contract = getattr(wrestler, 'contract', None)
        if contract is None:
            return None

        weeks_remaining = getattr(contract, 'weeks_remaining', None)
        if weeks_remaining in (None, ''):
            fallback = getattr(contract, 'total_length_weeks', None)
            if fallback in (None, ''):
                return None
            weeks_remaining = fallback

        try:
            return int(weeks_remaining)
        except (TypeError, ValueError):
            return None
    
    def calculate_market_value(self, wrestler: Wrestler) -> int:
        """
        Calculate a wrestler's fair market value based on:
        - Overall rating
        - Popularity
        - Role
        - Momentum
        - Age
        
        Returns suggested salary per show
        """
        base_value = 5000  # Minimum salary
        
        # Overall rating contribution (0-100 → $0-$15,000)
        rating_value = (wrestler.overall_rating / 100) * 15000
        
        # Popularity contribution (0-100 → $0-$10,000)
        popularity_value = (wrestler.popularity / 100) * 10000
        
        # Role multiplier
        role_multipliers = {
            'Main Event': 2.5,
            'Upper Midcard': 1.8,
            'Midcard': 1.3,
            'Lower Midcard': 1.0,
            'Jobber': 0.7
        }
        role_multiplier = role_multipliers.get(wrestler.role, 1.0)
        
        # Momentum bonus/penalty
        momentum_adjustment = (wrestler.momentum / 100) * 5000  # ±$5,000 max
        
        # Age penalty (veterans cost more due to experience, but decline after 40)
        if wrestler.age >= 40:
            age_penalty = -2000 * (wrestler.age - 40)  # -$2k per year over 40
        elif wrestler.age >= 30:
            age_penalty = 0  # Prime years
        else:
            age_penalty = -1000 * (30 - wrestler.age)  # Young talent costs less
        
        # Calculate total
        total = base_value + rating_value + popularity_value + momentum_adjustment + age_penalty
        total *= role_multiplier
        
        # Major superstar premium
        if wrestler.is_major_superstar:
            total *= 1.3
        
        # Round to nearest $500
        total = round(total / 500) * 500
        
        return max(5000, int(total))  # Never less than $5,000
    
    def negotiate_extension(
        self,
        wrestler: Wrestler,
        offered_salary: int,
        offered_weeks: int,
        current_balance: int
    ) -> Tuple[bool, str]:
        """
        Attempt to extend a wrestler's contract.
        
        Returns:
            (success: bool, message: str)
        """
        market_value = self.calculate_market_value(wrestler)
        
        # Check if promotion can afford it
        estimated_cost = offered_salary * (offered_weeks / 52)  # Rough annual estimate
        if estimated_cost > current_balance * 0.5:
            return False, "⚠️ Cannot afford this contract - would exceed 50% of current balance"
        
        # Wrestler acceptance logic
        acceptance_threshold = market_value * 0.85  # Will accept 85% of market value
        
        if offered_salary >= acceptance_threshold:
            # Accept!
            wrestler.contract.salary_per_show = offered_salary
            wrestler.contract.weeks_remaining += offered_weeks
            wrestler.contract.total_length_weeks += offered_weeks
            
            # Morale boost for fair/good deals
            if offered_salary >= market_value:
                wrestler.adjust_morale(10)
                message = f"✅ {wrestler.name} ACCEPTED! Very happy with the offer (+10 morale)"
            else:
                wrestler.adjust_morale(5)
                message = f"✅ {wrestler.name} accepted the contract extension (+5 morale)"
            
            return True, message
        else:
            # Reject
            wrestler.adjust_morale(-5)
            shortfall = market_value - offered_salary
            return False, f"❌ {wrestler.name} REJECTED the offer (-5 morale). Wants ${shortfall:,} more per show (Market value: ${market_value:,})"
    
    def calculate_early_renewal_probability(
        self,
        wrestler: Wrestler,
        offered_salary: int,
        offered_weeks: int,
        signing_bonus: int = 0,
        title_promise: bool = False,
        brand_transfer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        STEP 121: Calculate probability of early renewal acceptance.
        
        Returns detailed breakdown of acceptance probability with all modifiers.
        """
        market_value = self.calculate_market_value(wrestler)
        
        # Base probability from salary ratio
        salary_ratio = offered_salary / market_value if market_value > 0 else 1.0
        
        if salary_ratio >= 1.2:
            base_probability = 90.0
        elif salary_ratio >= 1.0:
            base_probability = 75.0
        elif salary_ratio >= 0.9:
            base_probability = 60.0
        elif salary_ratio >= 0.8:
            base_probability = 40.0
        else:
            base_probability = 20.0
        
        # Morale modifier (-20 to +20)
        morale_modifier = ((wrestler.morale - 50) / 100) * 40
        
        # Early renewal bonus (10-15% for renewing early)
        weeks_remaining = wrestler.contract.weeks_remaining
        if weeks_remaining > 26:
            early_bonus = 15.0  # Very early renewal
        elif weeks_remaining > 13:
            early_bonus = 12.0  # Early renewal
        else:
            early_bonus = 5.0   # Standard renewal window
        
        # Loyalty modifier (based on renewal attempts history)
        renewal_attempts = getattr(wrestler.contract, 'renewal_attempts', 0)
        if renewal_attempts == 0:
            loyalty_modifier = 10.0  # First renewal - wrestler feels valued
        elif renewal_attempts <= 2:
            loyalty_modifier = 5.0   # Loyal veteran
        else:
            loyalty_modifier = 0.0   # Multiple renewals - standard
        
        # Salary modifier (comparing to current)
        salary_increase_pct = ((offered_salary - wrestler.contract.salary_per_show) / 
                               wrestler.contract.salary_per_show * 100)
        
        if salary_increase_pct >= 20:
            salary_modifier = 15.0
        elif salary_increase_pct >= 10:
            salary_modifier = 10.0
        elif salary_increase_pct >= 0:
            salary_modifier = 5.0
        elif salary_increase_pct >= -10:
            salary_modifier = 0.0
        else:
            salary_modifier = -10.0  # Pay cut
        
        # Incentive modifiers
        incentive_modifier = 0.0
        
        # Signing bonus (scales with amount)
        if signing_bonus > 0:
            bonus_value_weeks = signing_bonus / market_value if market_value > 0 else 0
            if bonus_value_weeks >= 10:
                incentive_modifier += 15.0  # Huge bonus
            elif bonus_value_weeks >= 5:
                incentive_modifier += 10.0  # Large bonus
            elif bonus_value_weeks >= 2:
                incentive_modifier += 5.0   # Medium bonus
            else:
                incentive_modifier += 2.0   # Small bonus
        
        # Title opportunity promise
        if title_promise:
            if wrestler.role in ['Main Event', 'Upper Midcard']:
                incentive_modifier += 20.0  # Very important to top stars
            elif wrestler.role == 'Midcard':
                incentive_modifier += 25.0  # Even more important to midcarders
            else:
                incentive_modifier += 15.0  # Important to everyone
        
        # Brand transfer promise
        if brand_transfer and brand_transfer != wrestler.primary_brand:
            # Check if wrestler wants to move
            if wrestler.morale < 50:
                incentive_modifier += 15.0  # Unhappy wrestler wants fresh start
            else:
                incentive_modifier += 8.0   # Change of scenery appeal
        
        # Calculate final probability
        final_probability = (
            base_probability + 
            morale_modifier + 
            early_bonus + 
            loyalty_modifier + 
            salary_modifier + 
            incentive_modifier
        )
        
        # Clamp to 5-98%
        final_probability = max(5.0, min(98.0, final_probability))
        
        # Determine risk level
        if final_probability >= 80:
            risk_level = 'LOW'
        elif final_probability >= 60:
            risk_level = 'MEDIUM'
        elif final_probability >= 40:
            risk_level = 'HIGH'
        else:
            risk_level = 'VERY HIGH'
        
        # Generate recommendation
        if final_probability >= 75:
            recommendation = "Excellent offer - very likely to accept"
        elif final_probability >= 60:
            recommendation = "Good offer - likely to accept"
        elif final_probability >= 40:
            recommendation = "Risky offer - consider improving terms"
        else:
            recommendation = "Poor offer - significant improvements needed"
        
        return {
            'final_probability': round(final_probability, 1),
            'risk_level': risk_level,
            'recommendation': recommendation,
            'breakdown': {
                'base_probability': round(base_probability, 1),
                'morale_modifier': round(morale_modifier, 1),
                'early_bonus': round(early_bonus, 1),
                'loyalty_modifier': round(loyalty_modifier, 1),
                'salary_modifier': round(salary_modifier, 1),
                'incentive_modifier': round(incentive_modifier, 1)
            },
            'salary_ratio': round(salary_ratio, 2),
            'market_value': market_value,
            'offered_salary': offered_salary
        }
    
    def calculate_loyalty_discount(self, wrestler: Wrestler, market_value: int) -> Dict[str, Any]:
        """
        Calculate loyalty discount for long-term wrestlers.
        Wrestlers who have renewed multiple times get discounts.
        """
        # Count renewal history (simplified - you'd track this in database)
        renewal_count = getattr(wrestler.contract, 'renewal_attempts', 0)
        
        # Calculate loyalty tier
        if renewal_count >= 5:
            loyalty_tier = 'PLATINUM'
            discount_pct = 15.0
        elif renewal_count >= 3:
            loyalty_tier = 'GOLD'
            discount_pct = 10.0
        elif renewal_count >= 1:
            loyalty_tier = 'SILVER'
            discount_pct = 5.0
        else:
            loyalty_tier = 'BRONZE'
            discount_pct = 0.0
        
        discounted_salary = int(market_value * (1 - discount_pct / 100))
        annual_savings = (market_value - discounted_salary) * 52 * 3  # 52 weeks, 3 shows/week
        
        return {
            'loyalty_tier': loyalty_tier,
            'renewal_count': renewal_count,
            'discount_percentage': discount_pct,
            'market_value': market_value,
            'discounted_salary': discounted_salary,
            'annual_savings': annual_savings
        }
    
    def execute_brand_transfer(self, wrestler: Wrestler, target_brand: str, reason: str = "Management decision") -> Dict[str, Any]:
        """Execute a brand transfer for a wrestler"""
        old_brand = wrestler.primary_brand
        
        if old_brand == target_brand:
            return {
                'success': False,
                'error': f'{wrestler.name} is already on {target_brand}'
            }
        
        # Check for no-trade clause
        if hasattr(wrestler.contract, 'has_no_trade_clause') and wrestler.contract.has_no_trade_clause:
            return {
                'success': False,
                'error': f'{wrestler.name} has a no-trade clause and cannot be transferred without consent'
            }
        
        # Execute transfer
        wrestler.primary_brand = target_brand
        
        # Morale impact (small positive if promised, neutral otherwise)
        if 'promised' in reason.lower() or 'request' in reason.lower():
            wrestler.adjust_morale(5)
            morale_impact = '+5 (transfer was requested)'
        else:
            morale_impact = '0 (neutral)'
        
        return {
            'success': True,
            'message': f'{wrestler.name} transferred from {old_brand} to {target_brand}',
            'old_brand': old_brand,
            'new_brand': target_brand,
            'reason': reason,
            'morale_impact': morale_impact
        }
    
    def auto_extend(self, wrestler: Wrestler, weeks: int = 52) -> Dict:
        """
        Automatically extend a contract at current salary.
        Simple extension without negotiation.
        """
        wrestler.contract.weeks_remaining += weeks
        wrestler.contract.total_length_weeks += weeks
        
        return {
            'success': True,
            'wrestler': wrestler.name,
            'weeks_added': weeks,
            'new_weeks_remaining': wrestler.contract.weeks_remaining,
            'salary_per_show': wrestler.contract.salary_per_show
        }
    
    def release_wrestler(self, wrestler: Wrestler) -> Dict:
        """
        Release a wrestler from their contract.
        Moves them to free agent pool AND departed wrestlers (for potential return).
        """
        # Mark as retired (in this context = released/inactive)
        wrestler.is_retired = True
        wrestler.contract.weeks_remaining = 0
        
        # Add to free agent pool
        self.free_agents.append(wrestler)
        
        # Add to events manager's departed pool (for potential surprise signing later)
        from simulation.events import events_manager
        events_manager.add_departed_wrestler(wrestler)
        
        return {
            'success': True,
            'wrestler': wrestler.name,
            'message': f"{wrestler.name} has been released from their contract and moved to free agents"
        }
    
    def get_expiring_contracts(self, wrestlers: List[Wrestler], weeks_threshold: int = 4) -> List[Wrestler]:
        """
        Get list of wrestlers whose contracts expire within threshold weeks.
        """
        expiring = []
        for wrestler in wrestlers:
            weeks_remaining = self._get_contract_weeks(wrestler)
            if wrestler.is_retired or weeks_remaining is None:
                continue
            if 0 < weeks_remaining <= weeks_threshold:
                expiring.append(wrestler)
        return expiring
    
    def get_expired_contracts(self, wrestlers: List[Wrestler]) -> List[Wrestler]:
        """
        Get list of wrestlers whose contracts have expired (0 weeks remaining).
        """
        expired = []
        for wrestler in wrestlers:
            weeks_remaining = self._get_contract_weeks(wrestler)
            if wrestler.is_retired or weeks_remaining is None:
                continue
            if weeks_remaining <= 0:
                expired.append(wrestler)
        return expired
    
    # ========================================================================
    # STEP 119: Contract Countdown Tracking
    # ========================================================================
    
    def get_contract_countdown_categories(self, wrestlers: List[Wrestler]) -> Dict[str, List[Wrestler]]:
        """
        STEP 119: Categorize all wrestlers by contract expiration timeline.
        
        Categories:
        - Critical: Expiring within 30 days (4 weeks)
        - Negotiate Soon: Expiring within 90 days (13 weeks)
        - Monitor: Expiring within 6 months (26 weeks)
        - Secure: Over 6 months remaining
        - Expired: Already expired (0 weeks)
        
        Returns dict with categorized wrestler lists
        """
        categories = {
            'critical': [],      # <= 4 weeks
            'negotiate_soon': [], # 5-13 weeks
            'monitor': [],       # 14-26 weeks
            'secure': [],        # > 26 weeks
            'expired': []        # 0 weeks
        }
        
        for wrestler in wrestlers:
            if wrestler.is_retired:
                continue
                
            weeks = self._get_contract_weeks(wrestler)
            if weeks is None:
                continue
            
            if weeks == 0:
                categories['expired'].append(wrestler)
            elif weeks <= 4:
                categories['critical'].append(wrestler)
            elif weeks <= 13:
                categories['negotiate_soon'].append(wrestler)
            elif weeks <= 26:
                categories['monitor'].append(wrestler)
            else:
                categories['secure'].append(wrestler)
        
        # Sort each category by weeks remaining (ascending)
        for category in categories:
            categories[category].sort(
                key=lambda wrestler: self._get_contract_weeks(wrestler) or 9999
            )
        
        return categories
    
    def get_contract_status_summary(self, wrestlers: List[Wrestler]) -> Dict[str, Any]:
        """
        STEP 119: Get summary statistics for contract statuses.
        
        Returns summary with counts and percentages for each category.
        """
        categories = self.get_contract_countdown_categories(wrestlers)
        total_active = sum(len(cats) for cat, cats in categories.items() if cat != 'expired')
        
        summary = {
            'total_active_contracts': total_active,
            'categories': {}
        }
        
        for category, wrestler_list in categories.items():
            count = len(wrestler_list)
            percentage = (count / total_active * 100) if total_active > 0 else 0
            
            summary['categories'][category] = {
                'count': count,
                'percentage': round(percentage, 1),
                'wrestlers': wrestler_list
            }
        
        # Add urgency indicators
        summary['requires_immediate_action'] = (
            len(categories['critical']) + len(categories['expired'])
        )
        summary['requires_planning'] = len(categories['negotiate_soon'])
        
        return summary
    
    def get_contract_timeline_report(self, wrestlers: List[Wrestler]) -> List[Dict]:
        """
        STEP 119: Generate detailed timeline report for all contracts.
        
        Returns list of contract details sorted by urgency.
        """
        report = []
        
        for wrestler in wrestlers:
            if wrestler.is_retired:
                continue
            
            weeks = self._get_contract_weeks(wrestler)
            if weeks is None:
                continue
            
            # Determine status
            if weeks == 0:
                status = 'EXPIRED'
                urgency = 0
            elif weeks <= 4:
                status = 'CRITICAL'
                urgency = 1
            elif weeks <= 13:
                status = 'NEGOTIATE_SOON'
                urgency = 2
            elif weeks <= 26:
                status = 'MONITOR'
                urgency = 3
            else:
                status = 'SECURE'
                urgency = 4
            
            # Calculate re-signing probability based on morale
            if wrestler.morale >= 70:
                resign_probability = 'High'
            elif wrestler.morale >= 30:
                resign_probability = 'Medium'
            else:
                resign_probability = 'Low'
            
            report.append({
                'wrestler_id': wrestler.id,
                'wrestler_name': wrestler.name,
                'brand': wrestler.primary_brand,
                'role': wrestler.role,
                'weeks_remaining': weeks,
                'status': status,
                'urgency': urgency,
                'current_salary': wrestler.contract.salary_per_show,
                'market_value': self.calculate_market_value(wrestler),
                'morale': wrestler.morale,
                'resign_probability': resign_probability,
                'is_major_superstar': wrestler.is_major_superstar
            })
        
        # Sort by urgency (lower number = more urgent), then by weeks remaining
        report.sort(key=lambda x: (x['urgency'], x['weeks_remaining']))
        
        return report
    
    # ========================================================================
    # STEP 120: Contract Alert Generation
    # ========================================================================
    
    def generate_alerts_for_contracts(
        self,
        wrestlers: List[Wrestler],
        current_week: int,
        current_year: int
    ) -> List:
        """
        STEP 120: Generate contract expiration alerts for all wrestlers.
        
        Creates alerts for contracts that are expiring or have expired.
        Returns list of newly created or updated alerts.
        """
        from models.contract_alert import contract_alert_manager
        
        alerts_generated = []
        
        for wrestler in wrestlers:
            if wrestler.is_retired:
                continue
            
            weeks = self._get_contract_weeks(wrestler)
            if weeks is None:
                continue
            
            # Only create alerts for valid non-negative contracts <= 26 weeks (including 0/expired)
            if 0 <= weeks <= 26:
                market_value = self.calculate_market_value(wrestler)
                
                # Determine re-signing probability
                if wrestler.morale >= 70:
                    resign_prob = 'High'
                elif wrestler.morale >= 30:
                    resign_prob = 'Medium'
                else:
                    resign_prob = 'Low'
                
                alert = contract_alert_manager.create_alert(
                    wrestler_id=wrestler.id,
                    wrestler_name=wrestler.name,
                    brand=wrestler.primary_brand,
                    weeks_remaining=weeks,
                    current_salary=wrestler.contract.salary_per_show,
                    market_value=market_value,
                    morale=wrestler.morale,
                    resign_probability=resign_prob,
                    current_week=current_week,
                    current_year=current_year
                )
                
                if alert:
                    alerts_generated.append(alert)
        
        return alerts_generated
    
    def to_dict(self) -> Dict:
        """Serialize contract manager state"""
        return {
            'free_agents_count': len(self.free_agents),
            'free_agents': [w.to_dict() for w in self.free_agents]
        }
    
    

# Global contract manager instance
contract_manager = ContractManager()
