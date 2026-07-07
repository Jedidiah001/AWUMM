"""
Free Agent Mood Processing Engine (STEP 117)
Handles mood updates, transitions, and weekly processing.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime
import random

from models.free_agent_mood import (
    FreeAgentMood, MoodEffects, MoodTransitionRules,
    calculate_mood, get_mood_modifiers, check_mood_transition
)


class MoodProcessor:
    """
    Processes mood state changes for free agents.
    Integrates with FreeAgentPoolManager for weekly updates.
    """
    
    def __init__(self, database):
        self.database = database
        self.transition_history = []  # Track mood changes for analytics
    
    def initialize_mood(self, free_agent) -> FreeAgentMood:
        """
        Calculate initial mood for a newly created free agent.
        
        Args:
            free_agent: FreeAgent object
            
        Returns:
            Calculated FreeAgentMood
        """
        mood = calculate_mood(
            weeks_unemployed=free_agent.weeks_unemployed,
            rejection_count=free_agent.rejection_count,
            departure_reason=free_agent.source.value if hasattr(free_agent.source, 'value') else str(free_agent.source),
            rival_interest_count=len(free_agent.rival_interest),
            is_legend=free_agent.is_legend,
            is_major_superstar=free_agent.is_major_superstar,
            age=free_agent.age,
            peak_popularity=getattr(free_agent, 'peak_popularity', free_agent.popularity),
            current_popularity=free_agent.popularity,
            has_controversy=free_agent.has_controversy
        )
        
        print(f"   🎭 {free_agent.wrestler_name}: Initial mood = {mood.value}")
        
        return mood
    
    def recalculate_mood(self, free_agent, force: bool = False) -> Tuple[FreeAgentMood, bool]:
        """
        Recalculate mood based on current state.
        
        Args:
            free_agent: FreeAgent object
            force: If True, always recalculate. If False, only if significant change
            
        Returns:
            (new_mood, changed)
        """
        old_mood = free_agent.mood
        
        new_mood = calculate_mood(
            weeks_unemployed=free_agent.weeks_unemployed,
            rejection_count=free_agent.rejection_count,
            departure_reason=free_agent.source.value if hasattr(free_agent.source, 'value') else str(free_agent.source),
            rival_interest_count=len(free_agent.rival_interest),
            is_legend=free_agent.is_legend,
            is_major_superstar=free_agent.is_major_superstar,
            age=free_agent.age,
            peak_popularity=getattr(free_agent, 'peak_popularity', free_agent.popularity),
            current_popularity=free_agent.popularity,
            has_controversy=free_agent.has_controversy
        )
        
        changed = (old_mood != new_mood)
        
        if changed or force:
            return new_mood, changed
        
        return old_mood, False
    
    def check_event_trigger(
        self,
        free_agent,
        event_type: str,
        **event_data
    ) -> Tuple[bool, Optional[FreeAgentMood], str]:
        """
        Check if a specific event should trigger a mood change.
        
        Args:
            free_agent: FreeAgent object
            event_type: Type of event (rejection, rival_offer, etc.)
            event_data: Additional event information
            
        Returns:
            (should_transition, new_mood, reason)
        """
        
        current_mood = free_agent.mood
        
        # EVENT: Negotiation Rejection
        if event_type == 'rejection':
            if current_mood == FreeAgentMood.ARROGANT:
                # Arrogant wrestlers take rejections hard
                if free_agent.rejection_count >= 2:
                    return True, FreeAgentMood.BITTER, "Multiple rejections wounded pride"
            
            elif current_mood == FreeAgentMood.PATIENT:
                # Patient becomes hungry after rejections
                if free_agent.rejection_count >= 3:
                    return True, FreeAgentMood.HUNGRY, "Ready to compromise after rejections"
            
            elif current_mood == FreeAgentMood.HUNGRY:
                # Hungry becomes desperate
                if free_agent.rejection_count >= 4:
                    return True, FreeAgentMood.DESPERATE, "Running out of options"
        
        # EVENT: New Rival Offer
        elif event_type == 'rival_offer':
            offer_count = event_data.get('new_offers', 0)
            
            if current_mood == FreeAgentMood.DESPERATE:
                # Desperate gets hope
                if offer_count >= 1:
                    return True, FreeAgentMood.HUNGRY, "New interest restored confidence"
            
            elif current_mood == FreeAgentMood.PATIENT:
                # Patient becomes arrogant with multiple offers
                if offer_count >= 2:
                    return True, FreeAgentMood.ARROGANT, "Multiple suitors inflated ego"
            
            elif current_mood == FreeAgentMood.HUNGRY:
                # Hungry becomes patient with new leverage
                if offer_count >= 1:
                    return True, FreeAgentMood.PATIENT, "Can afford to be selective again"
        
        # EVENT: Rival Offer Withdrawn
        elif event_type == 'offer_withdrawn':
            if current_mood == FreeAgentMood.ARROGANT:
                # Reality check
                if len(free_agent.rival_interest) == 0:
                    return True, FreeAgentMood.BITTER, "Market rejected inflated demands"
        
        # EVENT: Popularity Increase (media buzz, interview, etc.)
        elif event_type == 'popularity_boost':
            boost = event_data.get('boost', 0)
            
            if current_mood == FreeAgentMood.DESPERATE and boost >= 10:
                return True, FreeAgentMood.HUNGRY, "Media attention restored market value"
            
            elif current_mood == FreeAgentMood.HUNGRY and boost >= 15:
                return True, FreeAgentMood.PATIENT, "Increased buzz allows selectivity"
        
        # EVENT: Popularity Decrease (controversy, bad interview, etc.)
        elif event_type == 'popularity_drop':
            drop = event_data.get('drop', 0)
            
            if current_mood == FreeAgentMood.ARROGANT and drop >= 10:
                return True, FreeAgentMood.PATIENT, "Market correction adjusted expectations"
            
            elif current_mood == FreeAgentMood.PATIENT and drop >= 15:
                return True, FreeAgentMood.HUNGRY, "Declining buzz created urgency"
        
        # EVENT: Time Passage (checked weekly)
        elif event_type == 'weekly_check':
            # Use standard transition rules
            return check_mood_transition(
                current_mood=current_mood,
                weeks_unemployed=free_agent.weeks_unemployed,
                rejection_count=free_agent.rejection_count,
                new_rival_offers=event_data.get('new_rival_offers', 0),
                popularity_change=event_data.get('popularity_change', 0)
            )
        
        return False, None, ""
    
    def process_weekly_moods(
        self,
        free_agents: List,
        year: int,
        week: int
    ) -> List[Dict]:
        """
        Process mood updates for all free agents weekly.
        
        Args:
            free_agents: List of FreeAgent objects
            year: Current year
            week: Current week
            
        Returns:
            List of mood change events
        """
        changes = []
        
        for fa in free_agents:
            # Skip if already signed
            if fa.is_signed:
                continue
            
            old_mood = fa.mood
            
            # Check for weekly transition
            should_transition, new_mood, reason = self.check_event_trigger(
                fa,
                'weekly_check',
                new_rival_offers=0,  # Would need to track this
                popularity_change=0   # Would need to track this
            )
            
            if should_transition and new_mood:
                fa.mood = new_mood
                
                # Update asking prices based on new mood
                self._update_demands_for_mood(fa)
                
                # Record change
                change_event = {
                    'free_agent_id': fa.id,
                    'wrestler_name': fa.wrestler_name,
                    'old_mood': old_mood.value,
                    'new_mood': new_mood.value,
                    'reason': reason,
                    'year': year,
                    'week': week,
                    'weeks_unemployed': fa.weeks_unemployed,
                    'new_asking_salary': fa.demands.asking_salary,
                    'new_minimum_salary': fa.demands.minimum_salary
                }
                
                changes.append(change_event)
                
                # Track in history
                self.transition_history.append(change_event)
                
                print(f"   🎭 {fa.wrestler_name}: {old_mood.value} → {new_mood.value} ({reason})")
        
        return changes
    
    def _update_demands_for_mood(self, free_agent):
        """
        Update asking price and minimum salary based on mood change.
        
        This recalculates demands using mood modifiers.
        """
        modifiers = get_mood_modifiers(free_agent.mood)
        
        # Recalculate asking price from base market value
        base_value = free_agent.market_value
        
        # Apply mood multiplier
        new_asking = int(base_value * modifiers.asking_price_multiplier)
        new_minimum = int(base_value * modifiers.minimum_price_multiplier)
        
        # Update demands
        free_agent.demands.asking_salary = new_asking
        free_agent.demands.minimum_salary = new_minimum
        
        # Update other demand attributes based on mood
        if modifiers.demands_extras:
            # Bitter/Arrogant want creative control
            if not free_agent.demands.creative_control:
                free_agent.demands.creative_control = "consultation"
        
        if modifiers.will_accept_lowball:
            # Desperate will accept almost anything
            free_agent.demands.minimum_salary = int(base_value * 0.5)
    
    def apply_mood_effects_to_negotiation(
        self,
        free_agent,
        offered_salary: int,
        offered_terms: Dict
    ) -> Dict:
        """
        Calculate how mood affects negotiation response.
        
        Args:
            free_agent: FreeAgent object
            offered_salary: Salary being offered
            offered_terms: Other contract terms
            
        Returns:
            Dict with negotiation result
        """
        modifiers = get_mood_modifiers(free_agent.mood)
        
        # Calculate offer as percentage of asking price
        offer_percent = offered_salary / max(free_agent.demands.asking_salary, 1)
        
        # Will they accept?
        will_accept = offer_percent >= modifiers.acceptance_threshold
        
        # If below threshold, check special cases
        if not will_accept and modifiers.will_accept_lowball:
            # Desperate will accept if above minimum
            if offered_salary >= free_agent.demands.minimum_salary:
                will_accept = True
        
        # Generate counter-offer if rejecting
        counter_salary = None
        if not will_accept:
            # Counter-offer is aggressive based on mood
            gap = free_agent.demands.asking_salary - offered_salary
            counter_reduction = gap * (1.0 - modifiers.counteroffer_aggression)
            counter_salary = int(offered_salary + gap - counter_reduction)
            
            # Never counter below asking price
            counter_salary = max(counter_salary, free_agent.demands.asking_salary)
        
        # Check for demanded extras
        missing_extras = []
        if modifiers.demands_extras:
            if not offered_terms.get('creative_control'):
                missing_extras.append('creative_control')
            if not offered_terms.get('merchandise_bonus') and free_agent.popularity >= 70:
                missing_extras.append('merchandise_bonus')
        
        # Generate response message
        if will_accept:
            if offer_percent >= 1.0:
                message = f"{free_agent.wrestler_name} accepts the offer enthusiastically!"
            elif offer_percent >= 0.9:
                message = f"{free_agent.wrestler_name} accepts the fair offer."
            else:
                message = f"{free_agent.wrestler_name} reluctantly accepts, feeling they deserve more."
        else:
            if free_agent.mood == FreeAgentMood.ARROGANT:
                message = f"{free_agent.wrestler_name} scoffs at the lowball offer. 'Do you know who I am?'"
            elif free_agent.mood == FreeAgentMood.BITTER:
                message = f"{free_agent.wrestler_name} rejects angrily. 'After what I've been through, you insult me with this?'"
            elif free_agent.mood == FreeAgentMood.PATIENT:
                message = f"{free_agent.wrestler_name} politely declines. 'I'm waiting for the right opportunity.'"
            else:
                message = f"{free_agent.wrestler_name} counters with ${counter_salary:,}/show."
        
        return {
            'accepted': will_accept,
            'counter_salary': counter_salary,
            'missing_extras': missing_extras,
            'message': message,
            'stubbornness_level': modifiers.negotiation_stubbornness,
            'will_negotiate_further': not modifiers.will_accept_lowball,
            'mood': free_agent.mood.value,
            'mood_label': MoodTransitionRules.get_mood_label(free_agent.mood)
        }
    
    def simulate_negotiation_rounds(
        self,
        free_agent,
        initial_offer: int,
        max_rounds: int = 5
    ) -> Dict:
        """
        Simulate multiple rounds of negotiation.
        
        Args:
            free_agent: FreeAgent object
            initial_offer: Starting salary offer
            max_rounds: Maximum negotiation rounds
            
        Returns:
            Dict with negotiation outcome
        """
        modifiers = get_mood_modifiers(free_agent.mood)
        
        current_offer = initial_offer
        asking_price = free_agent.demands.asking_salary
        
        rounds = []
        
        for round_num in range(1, max_rounds + 1):
            # Check acceptance
            result = self.apply_mood_effects_to_negotiation(
                free_agent,
                current_offer,
                {}  # Simplified - would include actual terms
            )
            
            rounds.append({
                'round': round_num,
                'offer': current_offer,
                'result': result['message'],
                'accepted': result['accepted']
            })
            
            if result['accepted']:
                return {
                    'success': True,
                    'final_salary': current_offer,
                    'rounds': rounds,
                    'total_rounds': round_num
                }
            
            # Check if negotiations break down
            if round_num >= modifiers.negotiation_stubbornness:
                return {
                    'success': False,
                    'reason': 'Negotiations broke down - wrestler too stubborn',
                    'rounds': rounds,
                    'total_rounds': round_num
                }
            
            # Counter-offer
            if result['counter_salary']:
                # Split the difference (simplified negotiation)
                gap = result['counter_salary'] - current_offer
                current_offer = int(current_offer + (gap * 0.5))
        
        return {
            'success': False,
            'reason': 'Maximum rounds reached without agreement',
            'rounds': rounds,
            'total_rounds': max_rounds
        }
    
    def get_mood_statistics(self, free_agents: List) -> Dict:
        """
        Get statistical breakdown of moods in the pool.
        
        Args:
            free_agents: List of FreeAgent objects
            
        Returns:
            Dict with mood distribution stats
        """
        stats = {
            'total': len(free_agents),
            'by_mood': {},
            'avg_weeks_unemployed': {},
            'avg_asking_price': {},
            'easiest_to_sign': [],
            'hardest_to_sign': []
        }
        
        # Count by mood
        for mood in FreeAgentMood:
            mood_agents = [fa for fa in free_agents if fa.mood == mood]
            stats['by_mood'][mood.value] = len(mood_agents)
            
            if mood_agents:
                stats['avg_weeks_unemployed'][mood.value] = sum(
                    fa.weeks_unemployed for fa in mood_agents
                ) / len(mood_agents)
                
                stats['avg_asking_price'][mood.value] = sum(
                    fa.demands.asking_salary for fa in mood_agents
                ) / len(mood_agents)
        
        # Identify easiest/hardest to sign
        sorted_agents = sorted(
            free_agents,
            key=lambda fa: get_mood_modifiers(fa.mood).acceptance_threshold
        )
        
        stats['easiest_to_sign'] = [
            {
                'id': fa.id,
                'name': fa.wrestler_name,
                'mood': fa.mood.value,
                'asking_salary': fa.demands.asking_salary,
                'acceptance_threshold': get_mood_modifiers(fa.mood).acceptance_threshold
            }
            for fa in sorted_agents[:5]
        ]
        
        stats['hardest_to_sign'] = [
            {
                'id': fa.id,
                'name': fa.wrestler_name,
                'mood': fa.mood.value,
                'asking_salary': fa.demands.asking_salary,
                'acceptance_threshold': get_mood_modifiers(fa.mood).acceptance_threshold
            }
            for fa in sorted_agents[-5:]
        ]
        
        return stats
    
    def get_transition_history(self, limit: int = 20) -> List[Dict]:
        """Get recent mood transitions"""
        return self.transition_history[-limit:]
    
    def clear_history(self):
        """Clear transition history (for memory management)"""
        self.transition_history = []


# Singleton instance (will be initialized by FreeAgentPoolManager)
_mood_processor = None

def get_mood_processor(database):
    """Get or create global mood processor instance"""
    global _mood_processor
    if _mood_processor is None:
        _mood_processor = MoodProcessor(database)
    return _mood_processor