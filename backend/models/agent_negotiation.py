"""
Agent Negotiation Mechanics (STEP 118)
Handles agent-specific negotiation behavior and tactics.
"""

from typing import Dict, Any, Optional, Tuple
from models.free_agent import FreeAgent, AgentType, AgentInfo
from models.free_agent_moods import MoodEffects
import random


class AgentNegotiationTactics:
    """
    Agent-specific negotiation tactics and behavior.
    
    Different agent types use different strategies:
    - Standard Agent: Straightforward, predictable
    - Power Agent: Aggressive, demands premium, uses leverage
    - Package Dealer: Pushes multi-client deals, volume discounts
    """
    
    @staticmethod
    def calculate_agent_markup(free_agent: FreeAgent) -> float:
        """
        Calculate the markup an agent adds to salary demands.
        
        Returns multiplier (1.0 = no change, 1.15 = 15% increase)
        """
        if free_agent.agent.agent_type == AgentType.NONE:
            return 1.0
        
        base_markup = 1.0 + free_agent.agent.commission_rate
        
        # Power agents push harder
        if free_agent.agent.agent_type == AgentType.POWER_AGENT:
            base_markup *= 1.10  # Additional 10% push
        
        # Package dealers are more flexible
        elif free_agent.agent.agent_type == AgentType.PACKAGE_DEALER:
            base_markup *= 0.95  # Slight reduction for volume potential
        
        return base_markup
    
    @staticmethod
    def get_negotiation_opening_statement(free_agent: FreeAgent) -> str:
        """Get agent's opening statement in negotiations"""
        agent = free_agent.agent
        
        if agent.agent_type == AgentType.NONE:
            return f"{free_agent.wrestler_name} is ready to discuss terms directly."
        
        statements = {
            AgentType.STANDARD: [
                f"I'm {agent.agent_name}, representing {free_agent.wrestler_name}. Let's talk business.",
                f"{agent.agent_name} here. My client is interested, but we have standards.",
                f"This is {agent.agent_name}. {free_agent.wrestler_name} has options, but I'm here to listen."
            ],
            AgentType.POWER_AGENT: [
                f"{agent.agent_name} speaking. My client {free_agent.wrestler_name} is a premium talent. I hope you're serious.",
                f"I represent {free_agent.wrestler_name}. We have multiple promotions at the table. Make your best offer.",
                f"{agent.agent_name}. You want {free_agent.wrestler_name}? Great. This won't be cheap.",
                f"Let me be clear: {free_agent.wrestler_name} is elite. My fee reflects that. Your offer should too."
            ],
            AgentType.PACKAGE_DEALER: [
                f"{agent.agent_name}. I represent {len(agent.other_clients) + 1} talented wrestlers, including {free_agent.wrestler_name}. Interested in a package?",
                f"This is {agent.agent_name}. {free_agent.wrestler_name} is available, but I have other clients who'd fit your roster perfectly.",
                f"{agent.agent_name} here. Sign {free_agent.wrestler_name} and I can bring you {len(agent.other_clients)} more quality talents."
            ]
        }
        
        options = statements.get(agent.agent_type, [statements[AgentType.STANDARD][0]])
        return random.choice(options)
    
    @staticmethod
    def evaluate_offer(
        free_agent: FreeAgent,
        offer_salary: int,
        offer_bonus: int = 0,
        offer_length_weeks: int = 52,
        offer_creative_control: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluate an offer from the agent's perspective.
        
        Returns:
            - accepted: Boolean
            - response: String message
            - counter_offer: Dict with suggested terms (if not accepted)
            - reasoning: List of reasons for decision
        """
        agent = free_agent.agent
        demands = free_agent.demands
        mood = free_agent.mood
        
        # Get mood modifiers
        mood_mods = MoodEffects.get_modifiers(mood)
        
        # Calculate total offer value
        total_offered = offer_salary + (offer_bonus / max(offer_length_weeks, 1))
        total_asking = demands.asking_salary + (demands.signing_bonus_expected / demands.preferred_length_weeks)
        
        # Calculate acceptance threshold
        base_threshold = mood_mods.acceptance_threshold
        
        # Agent modifiers
        if agent.agent_type == AgentType.POWER_AGENT:
            base_threshold += 0.10  # Power agents are pickier
        elif agent.agent_type == AgentType.PACKAGE_DEALER:
            base_threshold -= 0.05  # Package dealers more flexible
        
        # Check if offer meets threshold
        offer_ratio = total_offered / total_asking if total_asking > 0 else 1.0
        
        reasoning = []
        
        # Evaluate salary
        if offer_salary < demands.minimum_salary:
            reasoning.append(f"Salary ${offer_salary:,} below minimum ${demands.minimum_salary:,}")
        elif offer_salary >= demands.asking_salary:
            reasoning.append(f"Salary meets asking price")
        else:
            reasoning.append(f"Salary ${offer_salary:,} is {((offer_salary / demands.asking_salary) * 100):.0f}% of asking")
        
        # Evaluate bonus
        if demands.signing_bonus_expected > 0:
            if offer_bonus >= demands.signing_bonus_expected:
                reasoning.append(f"Signing bonus acceptable")
            else:
                reasoning.append(f"Signing bonus ${offer_bonus:,} below expected ${demands.signing_bonus_expected:,}")
        
        # Evaluate creative control
        if demands.creative_control_level > 0:
            if offer_creative_control >= demands.creative_control_level:
                reasoning.append(f"Creative control acceptable")
            else:
                reasoning.append(f"Creative control insufficient (want level {demands.creative_control_level})")
        
        # Decision logic
        accepted = False
        response = ""
        counter_offer = None
        
        if offer_ratio >= base_threshold:
            # ACCEPTED
            accepted = True
            
            if agent.agent_type == AgentType.NONE:
                response = f"{free_agent.wrestler_name}: I accept your offer. Let's do this!"
            elif agent.agent_type == AgentType.POWER_AGENT:
                response = f"{agent.agent_name}: My client accepts. Send the contract."
            elif agent.agent_type == AgentType.PACKAGE_DEALER:
                response = f"{agent.agent_name}: Deal. Now, about my other clients..."
            else:
                response = f"{agent.agent_name}: We have a deal. {free_agent.wrestler_name} is excited to join."
        
        else:
            # REJECTED - Generate counter-offer
            accepted = False
            
            # Counter-offer strategy
            if agent.agent_type == AgentType.POWER_AGENT:
                # Aggressive counter
                counter_salary = int(demands.asking_salary * 1.05)  # 5% above asking
                counter_bonus = int(demands.signing_bonus_expected * 1.1)
                response = f"{agent.agent_name}: That's insulting. {free_agent.wrestler_name} is worth more. Here's our counter."
            
            elif agent.agent_type == AgentType.PACKAGE_DEALER:
                # Flexible counter with package pitch
                counter_salary = int((demands.asking_salary + offer_salary) / 2)
                counter_bonus = int((demands.signing_bonus_expected + offer_bonus) / 2)
                response = f"{agent.agent_name}: Close, but not quite. Counter-offer attached. Also, sign my other clients and I'll give you a 10% package discount."
            
            else:
                # Standard counter - meet in middle
                counter_salary = int((demands.asking_salary + offer_salary) / 2)
                counter_bonus = int((demands.signing_bonus_expected + offer_bonus) / 2)
                response = f"{agent.agent_name}: We appreciate the offer, but it's below market value. Here's a fair counter."
            
            counter_offer = {
                'salary': max(counter_salary, demands.minimum_salary),
                'signing_bonus': counter_bonus,
                'length_weeks': demands.preferred_length_weeks,
                'creative_control': demands.creative_control_level,
                'other_demands': {
                    'merchandise_split': demands.merchandise_split,
                    'ppv_bonus': demands.ppv_bonus_expected
                }
            }
        
        return {
            'accepted': accepted,
            'response': response,
            'counter_offer': counter_offer,
            'reasoning': reasoning,
            'offer_ratio': round(offer_ratio, 2),
            'threshold_required': round(base_threshold, 2),
            'agent_type': agent.agent_type.value if agent.agent_type else 'none',
            'agent_name': agent.agent_name
        }
    
    @staticmethod
    def get_package_deal_discount(client_count: int) -> float:
        """
        Calculate discount for signing multiple clients from same agent.
        
        Returns multiplier (0.9 = 10% discount)
        """
        if client_count < 2:
            return 1.0
        elif client_count == 2:
            return 0.95  # 5% discount
        elif client_count == 3:
            return 0.90  # 10% discount
        else:  # 4+
            return 0.85  # 15% discount
    
    @staticmethod
    def generate_agent_leverage_statement(free_agent: FreeAgent) -> Optional[str]:
        """
        Generate a statement where agent uses leverage (rival offers, other clients, etc.)
        Returns None if no leverage available.
        """
        agent = free_agent.agent
        
        if agent.agent_type == AgentType.NONE:
            return None
        
        leverage = []
        
        # Rival offers leverage
        if free_agent.rival_interest:
            active_offers = [r for r in free_agent.rival_interest if r.offer_made]
            if active_offers:
                highest = max(r.offer_salary for r in active_offers)
                leverage.append(f"We have a ${highest:,} offer on the table from {active_offers[0].promotion_name}")
        
        # Package deal leverage
        if agent.agent_type == AgentType.PACKAGE_DEALER and agent.other_clients:
            leverage.append(f"Sign all {len(agent.other_clients) + 1} of my clients and save 15%")
        
        # Popularity leverage
        if free_agent.popularity >= 75:
            leverage.append(f"{free_agent.wrestler_name} is a proven draw - fans will follow")
        
        # Legend leverage
        if free_agent.is_legend:
            leverage.append(f"You're negotiating with a legend. Act accordingly")
        
        if not leverage:
            return None
        
        statement = f"{agent.agent_name}: Let me be clear - {random.choice(leverage)}."
        return statement


class NegotiationHistory:
    """Track negotiation rounds for analytics"""
    
    def __init__(self):
        self.rounds: list = []
    
    def add_round(
        self,
        round_number: int,
        offer: Dict[str, Any],
        response: Dict[str, Any]
    ):
        """Record a negotiation round"""
        self.rounds.append({
            'round': round_number,
            'offer': offer,
            'response': response,
            'timestamp': None  # Would use datetime in production
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get negotiation summary"""
        return {
            'total_rounds': len(self.rounds),
            'rounds': self.rounds,
            'final_result': self.rounds[-1]['response']['accepted'] if self.rounds else None
        }