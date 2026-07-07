"""
Wrestler Negotiation AI
Simulates realistic negotiation behavior based on wrestler personality,
career stage, market conditions, and psychological factors.
"""

from typing import Dict, Any, List, Tuple
from models.wrestler import Wrestler
from economy.contracts import contract_manager
import random


class WrestlerPersonality:
    """Wrestler personality archetypes affecting negotiation"""
    
    GREEDY = "greedy"              # Always wants more money
    LOYAL = "loyal"                # Values stability and history
    AMBITIOUS = "ambitious"        # Wants titles and spotlight
    PRAGMATIC = "pragmatic"        # Balanced, reasonable
    PRIDEFUL = "prideful"          # Needs respect and status
    INSECURE = "insecure"          # Easily pressured
    MERCENARY = "mercenary"        # Goes to highest bidder
    LEGACY_FOCUSED = "legacy_focused"  # Cares about career legacy


class NegotiationAI:
    """
    AI system that simulates wrestler decision-making during contract negotiations.
    
    Factors considered:
    - Wrestler personality type
    - Career stage (rookie, rising, peak, declining, veteran)
    - Market value vs offer
    - Recent booking/push
    - Relationship with promotion
    - Outside offers (simulated)
    - Family/personal factors
    """
    
    def __init__(self):
        self.personality_modifiers = {
            WrestlerPersonality.GREEDY: {'money_weight': 2.0, 'creative_weight': 0.5, 'loyalty_weight': 0.3},
            WrestlerPersonality.LOYAL: {'money_weight': 0.7, 'creative_weight': 0.8, 'loyalty_weight': 2.5},
            WrestlerPersonality.AMBITIOUS: {'money_weight': 0.9, 'creative_weight': 1.5, 'loyalty_weight': 0.6},
            WrestlerPersonality.PRAGMATIC: {'money_weight': 1.0, 'creative_weight': 1.0, 'loyalty_weight': 1.0},
            WrestlerPersonality.PRIDEFUL: {'money_weight': 1.2, 'creative_weight': 1.8, 'loyalty_weight': 0.4},
            WrestlerPersonality.INSECURE: {'money_weight': 0.8, 'creative_weight': 0.6, 'loyalty_weight': 1.5},
            WrestlerPersonality.MERCENARY: {'money_weight': 2.5, 'creative_weight': 0.3, 'loyalty_weight': 0.1},
            WrestlerPersonality.LEGACY_FOCUSED: {'money_weight': 0.6, 'creative_weight': 2.0, 'loyalty_weight': 1.2}
        }
    
    def assign_personality(self, wrestler: Wrestler) -> str:
        """Assign personality based on wrestler attributes and career"""
        # Age-based defaults
        if wrestler.age >= 40:
            return random.choice([WrestlerPersonality.LOYAL, WrestlerPersonality.LEGACY_FOCUSED])
        elif wrestler.age <= 25:
            return random.choice([WrestlerPersonality.AMBITIOUS, WrestlerPersonality.INSECURE])
        
        # Role-based defaults
        if wrestler.role == 'Main Event':
            return random.choice([WrestlerPersonality.PRIDEFUL, WrestlerPersonality.GREEDY, WrestlerPersonality.AMBITIOUS])
        elif wrestler.role in ['Jobber', 'Lower Midcard']:
            return random.choice([WrestlerPersonality.INSECURE, WrestlerPersonality.PRAGMATIC])
        
        # Morale-based
        if wrestler.morale < 30:
            return random.choice([WrestlerPersonality.MERCENARY, WrestlerPersonality.GREEDY])
        elif wrestler.morale > 70:
            return WrestlerPersonality.LOYAL
        
        # Default
        return WrestlerPersonality.PRAGMATIC
    
    def simulate_counter_offer(
        self,
        wrestler: Wrestler,
        your_offer: Dict[str, Any],
        personality: str = None
    ) -> Dict[str, Any]:
        """
        Wrestler AI generates a counter-offer.
        
        Args:
            wrestler: Wrestler object
            your_offer: Dict with 'salary', 'weeks', 'incentives', etc.
            personality: Override personality (optional)
        
        Returns:
            Counter-offer dict with demands
        """
        if personality is None:
            personality = self.assign_personality(wrestler)
        
        market_value = contract_manager.calculate_market_value(wrestler)
        offered_salary = your_offer.get('salary_per_show', 0)
        
        # Get personality modifiers
        modifiers = self.personality_modifiers.get(personality, self.personality_modifiers[WrestlerPersonality.PRAGMATIC])
        
        # Calculate counter salary
        if offered_salary < market_value * 0.8:
            # Lowball offer - demand more
            counter_salary = int(market_value * (1.1 + random.uniform(0, 0.1)))
            response_tone = "insulted"
        elif offered_salary < market_value:
            # Below market - counter at market or slightly above
            counter_salary = int(market_value * (1.0 + random.uniform(0, 0.05)))
            response_tone = "disappointed"
        elif offered_salary >= market_value * 1.2:
            # Generous offer - accept or minor counter
            counter_salary = offered_salary
            response_tone = "pleased"
        else:
            # Fair offer - slight counter
            counter_salary = int(market_value * (1.0 + random.uniform(-0.05, 0.05)))
            response_tone = "neutral"
        
        # Personality adjustments
        counter_salary = int(counter_salary * modifiers['money_weight'])
        
        # Generate demands
        demands = self._generate_demands(wrestler, personality, your_offer, modifiers)
        
        return {
            'counter_salary': counter_salary,
            'demanded_weeks': self._counter_weeks(your_offer.get('weeks', 52), personality),
            'demanded_incentives': demands['incentives'],
            'demanded_creative_control': demands['creative_control'],
            'response_tone': response_tone,
            'personality': personality,
            'explanation': self._generate_explanation(wrestler, personality, response_tone, counter_salary, market_value)
        }
    
    def _generate_demands(
        self,
        wrestler: Wrestler,
        personality: str,
        your_offer: Dict[str, Any],
        modifiers: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate specific demands based on personality"""
        demands = {
            'incentives': [],
            'creative_control': None
        }
        
        # Greedy personality - wants cash incentives
        if personality == WrestlerPersonality.GREEDY:
            demands['incentives'].extend([
                'signing_bonus_large',
                'merch_elite',
                'escalator_popularity'
            ])
        
        # Ambitious - wants titles and spotlight
        elif personality == WrestlerPersonality.AMBITIOUS:
            demands['incentives'].extend([
                'title_shot_guarantee',
                'ppv_guarantee_8',
                'escalator_title_reign'
            ])
            demands['creative_control'] = 'approval'
        
        # Prideful - wants control and respect
        elif personality == WrestlerPersonality.PRIDEFUL:
            demands['incentives'].extend([
                'creative_partnership',
                'no_trade_full',
                'ppv_main_event_bonus'
            ])
            demands['creative_control'] = 'partnership'
        
        # Loyal - wants security
        elif personality == WrestlerPersonality.LOYAL:
            demands['incentives'].extend([
                'injury_protection_full',
                'loyalty_year_bonus',
                'no_trade_full'
            ])
        
        # Insecure - wants guarantees
        elif personality == WrestlerPersonality.INSECURE:
            demands['incentives'].extend([
                'injury_protection_full',
                'ppv_guarantee_6',
                'tenure_milestone_bonus'
            ])
        
        # Legacy-focused - wants creative freedom
        elif personality == WrestlerPersonality.LEGACY_FOCUSED:
            demands['incentives'].extend([
                'creative_full',
                'title_rematch_clause',
                'image_rights_retained'
            ])
            demands['creative_control'] = 'full'
        
        # Mercenary - all about money
        elif personality == WrestlerPersonality.MERCENARY:
            demands['incentives'].extend([
                'signing_bonus_superstar',
                'merch_royalty_bonus',
                'escalator_match_quality'
            ])
        
        # Pragmatic - balanced mix
        else:
            demands['incentives'].extend([
                'signing_bonus_medium',
                'merch_improved',
                'ppv_guarantee_6'
            ])
            demands['creative_control'] = 'consultation'
        
        # Career stage adjustments
        if wrestler.age >= 35:
            demands['incentives'].append('appearances_reduced')
        
        if wrestler.role == 'Main Event':
            if 'ppv_guarantee_all' not in demands['incentives']:
                demands['incentives'].append('ppv_guarantee_all')
        
        return demands
    
    def _counter_weeks(self, offered_weeks: int, personality: str) -> int:
        """Counter with preferred contract length"""
        if personality in [WrestlerPersonality.LOYAL, WrestlerPersonality.INSECURE]:
            # Wants long-term security
            return max(offered_weeks, 104)  # 2+ years
        elif personality in [WrestlerPersonality.MERCENARY, WrestlerPersonality.AMBITIOUS]:
            # Wants flexibility
            return min(offered_weeks, 52)  # 1 year max
        else:
            return offered_weeks
    
    def _generate_explanation(
        self,
        wrestler: Wrestler,
        personality: str,
        tone: str,
        counter_salary: int,
        market_value: int
    ) -> str:
        """Generate explanation text for counter-offer"""
        explanations = {
            'insulted': [
                f"That offer is disrespectful to someone of my caliber. I deserve at least ${counter_salary:,}/show.",
                f"Are you serious? I'm worth way more than that. ${counter_salary:,} is the minimum I'll consider.",
                f"I'm insulted by that offer. My market value is ${market_value:,} and I expect to be paid accordingly."
            ],
            'disappointed': [
                f"I was hoping for better. I think ${counter_salary:,}/show is fair given my contributions.",
                f"That's below what I expected. Can we discuss ${counter_salary:,}?",
                f"I appreciate the offer, but I need ${counter_salary:,} to make this work."
            ],
            'neutral': [
                f"Let's meet in the middle at ${counter_salary:,}/show.",
                f"I'm thinking ${counter_salary:,} is more appropriate for this role.",
                f"How about we adjust to ${counter_salary:,} and we can move forward?"
            ],
            'pleased': [
                f"That's a great offer! I'm ready to sign at ${counter_salary:,}.",
                f"I appreciate the respect you're showing. ${counter_salary:,} works for me.",
                f"This is exactly what I was hoping for. Let's do ${counter_salary:,} and we have a deal."
            ]
        }
        
        return random.choice(explanations.get(tone, explanations['neutral']))
    
    def evaluate_offer(
        self,
        wrestler: Wrestler,
        offer: Dict[str, Any],
        personality: str = None
    ) -> Dict[str, Any]:
        """
        Evaluate an offer and return detailed analysis.
        
        Returns:
            - acceptance_score (0-100)
            - will_accept (bool)
            - concerns (list of strings)
            - positives (list of strings)
        """
        if personality is None:
            personality = self.assign_personality(wrestler)
        
        market_value = contract_manager.calculate_market_value(wrestler)
        offered_salary = offer.get('salary_per_show', 0)
        modifiers = self.personality_modifiers[personality]
        
        # Start with base score
        score = 50.0
        concerns = []
        positives = []
        
        # Salary evaluation
        salary_ratio = offered_salary / market_value if market_value > 0 else 1.0
        
        if salary_ratio >= 1.2:
            score += 30 * modifiers['money_weight']
            positives.append(f"Salary ${offered_salary:,}/show exceeds expectations")
        elif salary_ratio >= 1.0:
            score += 20 * modifiers['money_weight']
            positives.append("Salary meets market value")
        elif salary_ratio >= 0.9:
            score += 10 * modifiers['money_weight']
        elif salary_ratio >= 0.8:
            score -= 10 * modifiers['money_weight']
            concerns.append(f"Salary is below market value (${market_value:,})")
        else:
            score -= 30 * modifiers['money_weight']
            concerns.append(f"Salary is significantly below market value (${market_value:,})")
        
        # Incentive evaluation
        incentive_count = len(offer.get('incentives', []))
        if incentive_count >= 5:
            score += 15
            positives.append(f"Strong incentive package ({incentive_count} incentives)")
        elif incentive_count >= 3:
            score += 10
            positives.append("Good incentive package")
        elif incentive_count >= 1:
            score += 5
        else:
            score -= 5
            concerns.append("No incentives offered")
        
        # Creative control evaluation
        creative = offer.get('creative_control', 'none')
        creative_value = {
            'none': 0,
            'consultation': 5,
            'approval': 10,
            'partnership': 15,
            'full': 20
        }.get(creative, 0)
        
        score += creative_value * modifiers['creative_weight']
        if creative != 'none':
            positives.append(f"Creative control: {creative.upper()}")
        
        # Morale factor
        morale_modifier = (wrestler.morale / 100) * 20
        score += morale_modifier
        
        # Loyalty factor (years with promotion)
        loyalty_bonus = min(wrestler.years_experience * 2, 20) * modifiers['loyalty_weight']
        score += loyalty_bonus
        
        # Age/career stage factor
        if wrestler.age >= 40:
            # Veterans want security
            if offer.get('weeks', 52) >= 104:
                score += 10
                positives.append("Long-term security offered")
        elif wrestler.age <= 25:
            # Young talent wants opportunity
            title_incentives = [i for i in offer.get('incentives', []) if 'title' in i.lower()]
            if title_incentives:
                score += 15
                positives.append("Title opportunities included")
        
        # Role-appropriate booking
        if wrestler.role == 'Main Event':
            ppv_incentives = [i for i in offer.get('incentives', []) if 'ppv' in i.lower()]
            if ppv_incentives:
                score += 10
                positives.append("PPV guarantees match main event status")
            else:
                score -= 10
                concerns.append("No PPV guarantees for main eventer")
        
        # Clamp score
        score = max(0, min(100, score))
        
        return {
            'acceptance_score': round(score, 1),
            'will_accept': score >= 60,
            'personality': personality,
            'concerns': concerns,
            'positives': positives,
            'counter_offer_likely': 40 <= score < 60,
            'recommendation': self._get_recommendation(score)
        }
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation text based on score"""
        if score >= 80:
            return "Excellent offer - wrestler will likely accept immediately"
        elif score >= 60:
            return "Good offer - wrestler will probably accept"
        elif score >= 40:
            return "Fair offer - expect a counter-offer"
        elif score >= 20:
            return "Weak offer - wrestler will likely reject or demand major changes"
        else:
            return "Poor offer - wrestler will almost certainly reject"


# Global AI instance
negotiation_ai = NegotiationAI()