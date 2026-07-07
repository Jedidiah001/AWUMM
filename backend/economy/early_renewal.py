"""
Early Renewal System
STEP 121: Early Renewal Window

Handles early contract renewal negotiations before expiration.
"""

from typing import Dict, Any, Tuple, Optional
from models.wrestler import Wrestler
import random


class EarlyRenewalCalculator:
    """
    Calculates renewal probability and handles early renewal negotiations.
    """
    
    @staticmethod
    def calculate_renewal_probability(
        wrestler: Wrestler,
        offered_salary: int,
        offered_weeks: int,
        market_value: int,
        include_incentives: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate the probability that a wrestler will accept an early renewal offer.
        
        Factors:
        - Morale (most important)
        - Salary offer vs market value
        - Current role satisfaction
        - Weeks remaining on current contract
        - Years with company
        - Age and career stage
        - Incentives offered
        
        Returns dict with:
        - base_probability: float (0-100)
        - morale_modifier: float
        - salary_modifier: float
        - loyalty_modifier: float
        - final_probability: float (0-100)
        - recommendation: str
        - risk_level: str
        """
        
        # Base probability starts at 50%
        base_probability = 50.0
        
        # MORALE MODIFIER (Most Important: -40 to +40)
        if wrestler.morale >= 80:
            morale_modifier = 40.0  # Very happy
        elif wrestler.morale >= 60:
            morale_modifier = 20.0  # Content
        elif wrestler.morale >= 40:
            morale_modifier = 0.0   # Neutral
        elif wrestler.morale >= 20:
            morale_modifier = -20.0  # Unhappy
        else:
            morale_modifier = -40.0  # Miserable
        
        # SALARY MODIFIER (-30 to +30)
        salary_ratio = offered_salary / market_value if market_value > 0 else 1.0
        
        if salary_ratio >= 1.2:
            salary_modifier = 30.0  # 120%+ of market value
        elif salary_ratio >= 1.0:
            salary_modifier = 15.0  # At or above market value
        elif salary_ratio >= 0.9:
            salary_modifier = 5.0   # 90-99% of market value
        elif salary_ratio >= 0.8:
            salary_modifier = -10.0  # 80-89% of market value
        else:
            salary_modifier = -30.0  # Below 80% of market value
        
        # LOYALTY MODIFIER (based on time with company: -10 to +20)
        if wrestler.years_experience <= 2:
            loyalty_modifier = -10.0  # New, wants to test market
        elif wrestler.years_experience <= 5:
            loyalty_modifier = 0.0   # Building career
        elif wrestler.years_experience <= 10:
            loyalty_modifier = 10.0  # Established
        else:
            loyalty_modifier = 20.0  # Veteran loyalty
        
        # CONTRACT LENGTH MODIFIER (-10 to +10)
        if offered_weeks >= 156:  # 3+ years
            length_modifier = 10.0  # Security valued
        elif offered_weeks >= 104:  # 2 years
            length_modifier = 5.0
        elif offered_weeks >= 52:  # 1 year
            length_modifier = 0.0
        else:
            length_modifier = -10.0  # Too short
        
        # EARLY RENEWAL BONUS (+10)
        # Wrestlers appreciate being offered renewal early (shows value)
        early_bonus = 10.0 if wrestler.contract.weeks_remaining > 26 else 5.0
        
        # ROLE SATISFACTION MODIFIER (-15 to +15)
        role_values = {
            'Main Event': 90,
            'Upper Midcard': 70,
            'Midcard': 50,
            'Lower Midcard': 30,
            'Jobber': 10
        }
        expected_pop = role_values.get(wrestler.role, 50)
        
        if wrestler.popularity >= expected_pop + 20:
            role_modifier = 15.0  # Overperforming, wants push/more money
        elif wrestler.popularity >= expected_pop:
            role_modifier = 5.0   # Performing well
        elif wrestler.popularity >= expected_pop - 10:
            role_modifier = 0.0   # Meeting expectations
        else:
            role_modifier = -15.0  # Underperforming, grateful to have job
        
        # AGE/CAREER STAGE MODIFIER (-10 to +10)
        if wrestler.age >= 40:
            age_modifier = 10.0  # Older, values security
        elif wrestler.age >= 35:
            age_modifier = 5.0   # Prime years ending
        elif wrestler.age <= 25:
            age_modifier = -5.0  # Young, wants to explore
        else:
            age_modifier = 0.0   # Prime years
        
        # INCENTIVES MODIFIER (+15 if offered)
        incentive_modifier = 15.0 if include_incentives else 0.0
        
        # MAJOR SUPERSTAR MODIFIER
        superstar_modifier = -10.0 if wrestler.is_major_superstar else 0.0
        # Stars are harder to re-sign, they know their value
        
        # Calculate final probability
        final_probability = (
            base_probability +
            morale_modifier +
            salary_modifier +
            loyalty_modifier +
            length_modifier +
            early_bonus +
            role_modifier +
            age_modifier +
            incentive_modifier +
            superstar_modifier
        )
        
        # Clamp to 0-100
        final_probability = max(0.0, min(100.0, final_probability))
        
        # Determine recommendation
        if final_probability >= 80:
            recommendation = "HIGHLY LIKELY - Excellent offer, wrestler very satisfied"
            risk_level = "LOW"
        elif final_probability >= 60:
            recommendation = "LIKELY - Good offer, should accept"
            risk_level = "LOW"
        elif final_probability >= 40:
            recommendation = "MODERATE - Uncertain, could go either way"
            risk_level = "MEDIUM"
        elif final_probability >= 20:
            recommendation = "UNLIKELY - Poor offer or wrestler unhappy"
            risk_level = "HIGH"
        else:
            recommendation = "VERY UNLIKELY - Wrestler will likely refuse"
            risk_level = "VERY HIGH"
        
        return {
            'base_probability': base_probability,
            'morale_modifier': morale_modifier,
            'salary_modifier': salary_modifier,
            'loyalty_modifier': loyalty_modifier,
            'length_modifier': length_modifier,
            'early_bonus': early_bonus,
            'role_modifier': role_modifier,
            'age_modifier': age_modifier,
            'incentive_modifier': incentive_modifier,
            'superstar_modifier': superstar_modifier,
            'final_probability': final_probability,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'salary_ratio': salary_ratio,
            'market_value': market_value,
            'offered_salary': offered_salary
        }
    
    @staticmethod
    def attempt_early_renewal(
        wrestler: Wrestler,
        offered_salary: int,
        offered_weeks: int,
        market_value: int,
        signing_bonus: int = 0,
        title_promise: bool = False,
        brand_transfer: Optional[str] = None,
        current_week: int = 1,
        current_year: int = 1
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Attempt to renew a wrestler's contract early.
        
        Args:
            wrestler: Wrestler object
            offered_salary: Salary per show offered
            offered_weeks: Contract length offered
            market_value: Calculated market value
            signing_bonus: One-time signing bonus
            title_promise: Promise of title opportunity
            brand_transfer: Requested brand transfer (if any)
            current_week: Current game week
            current_year: Current game year
        
        Returns:
            (success: bool, message: str, details: dict)
        """
        
        # Calculate base probability
        include_incentives = signing_bonus > 0 or title_promise or brand_transfer is not None
        probability_data = EarlyRenewalCalculator.calculate_renewal_probability(
            wrestler=wrestler,
            offered_salary=offered_salary,
            offered_weeks=offered_weeks,
            market_value=market_value,
            include_incentives=include_incentives
        )
        
        final_probability = probability_data['final_probability']
        
        # Additional modifiers for specific incentives
        bonus_probability = 0.0
        
        if signing_bonus > 0:
            # Signing bonus adds probability based on size
            bonus_ratio = signing_bonus / (offered_salary * 52)  # Bonus vs annual salary
            if bonus_ratio >= 0.5:
                bonus_probability += 10.0
            elif bonus_ratio >= 0.25:
                bonus_probability += 5.0
            else:
                bonus_probability += 2.0
        
        if title_promise:
            # Title opportunity is very attractive
            if wrestler.role in ['Main Event', 'Upper Midcard']:
                bonus_probability += 15.0
            elif wrestler.role == 'Midcard':
                bonus_probability += 20.0  # More meaningful for midcarders
            else:
                bonus_probability += 25.0  # Huge for lower card
        
        if brand_transfer:
            # Brand transfer request granted
            bonus_probability += 10.0
        
        final_probability = min(100.0, final_probability + bonus_probability)
        
        # Roll the dice
        roll = random.random() * 100
        success = roll <= final_probability
        
        # Update contract tracking
        wrestler.contract.renewal_attempts += 1
        wrestler.contract.last_renewal_attempt_week = current_week
        wrestler.contract.last_renewal_attempt_year = current_year
        
        if success:
            # Accept renewal
            old_salary = wrestler.contract.salary_per_show
            old_weeks = wrestler.contract.weeks_remaining
            
            # Update contract
            wrestler.contract.salary_per_show = offered_salary
            wrestler.contract.weeks_remaining += offered_weeks
            wrestler.contract.total_length_weeks += offered_weeks
            wrestler.contract.early_renewal_offered = True
            wrestler.contract.early_renewal_week = current_week
            wrestler.contract.early_renewal_year = current_year
            
            # Apply brand transfer if promised
            if brand_transfer:
                wrestler.primary_brand = brand_transfer
            
            # Morale boost for renewal
            if offered_salary >= market_value:
                wrestler.adjust_morale(15)  # Happy with fair/generous offer
            else:
                wrestler.adjust_morale(8)   # Content with renewal
            
            # Build success message
            message_parts = [
                f"✅ {wrestler.name} ACCEPTED the early renewal!",
                f"📝 New Contract: ${offered_salary:,}/show for {offered_weeks} weeks",
                f"📊 Previous: ${old_salary:,}/show, {old_weeks} weeks remaining"
            ]
            
            if signing_bonus > 0:
                message_parts.append(f"💰 Signing Bonus: ${signing_bonus:,}")
            
            if title_promise:
                message_parts.append(f"🏆 Title Opportunity Promised")
            
            if brand_transfer:
                message_parts.append(f"📺 Transferred to {brand_transfer}")
            
            message_parts.append(f"😊 Morale: {wrestler.morale} (+{15 if offered_salary >= market_value else 8})")
            
            message = "\n".join(message_parts)
            
            details = {
                'success': True,
                'probability': final_probability,
                'roll': roll,
                'old_salary': old_salary,
                'new_salary': offered_salary,
                'old_weeks': old_weeks,
                'new_weeks': wrestler.contract.weeks_remaining,
                'weeks_added': offered_weeks,
                'signing_bonus': signing_bonus,
                'title_promise': title_promise,
                'brand_transfer': brand_transfer,
                'morale_change': 15 if offered_salary >= market_value else 8
            }
            
        else:
            # Reject renewal
            wrestler.adjust_morale(-5)  # Slight morale hit for rejection
            
            # Build rejection message
            reasons = []
            
            if probability_data['salary_modifier'] < 0:
                reasons.append("💵 Salary offer too low")
            
            if probability_data['morale_modifier'] < -10:
                reasons.append("😠 Wrestler is unhappy")
            
            if wrestler.is_major_superstar:
                reasons.append("⭐ Superstar wants to test free agency")
            
            if probability_data['role_modifier'] > 10:
                reasons.append("📈 Wrestler feels undervalued for performance")
            
            if not reasons:
                reasons.append("🎲 Wrestler wants to explore options")
            
            message_parts = [
                f"❌ {wrestler.name} REJECTED the early renewal offer",
                f"📊 Probability: {final_probability:.1f}% (Rolled: {roll:.1f})",
                "",
                "Possible reasons:"
            ] + [f"  • {r}" for r in reasons] + [
                "",
                f"💡 Suggestions:",
                f"  • Market Value: ${market_value:,}/show (You offered: ${offered_salary:,})",
                f"  • Current Morale: {wrestler.morale}/100"
            ]
            
            if wrestler.morale < 50:
                message_parts.append(f"  • 🚨 Improve morale through better booking")
            
            if offered_salary < market_value:
                shortfall = market_value - offered_salary
                message_parts.append(f"  • 💰 Consider increasing offer by ${shortfall:,}/show")
            
            message = "\n".join(message_parts)
            
            details = {
                'success': False,
                'probability': final_probability,
                'roll': roll,
                'reasons': reasons,
                'market_value': market_value,
                'offered_salary': offered_salary,
                'morale': wrestler.morale,
                'morale_change': -5
            }
        
        return success, message, details


# Global instance
early_renewal_calculator = EarlyRenewalCalculator()