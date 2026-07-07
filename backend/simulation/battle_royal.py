"""
Battle Royal Simulation Engine
Handles multi-person over-the-top-rope elimination matches.

Match Types:
- Battle Royal: All start in ring, eliminate over top rope
- Royal Rumble: Timed entries (90 seconds), 30 participants
- Casino Battle Royal: Card-draw entries (suits determine entry order)

UPDATED: Now supports booked_winner and booked_runner_up
"""

import random
from typing import List, Dict, Any, Tuple, Optional
from models.wrestler import Wrestler
from models.match import MatchHighlight


class BattleRoyalSimulator:
    """Simulates battle royal style matches"""
    
    def __init__(self):
        self.random = random.Random()
    
    def simulate_battle_royal(
        self,
        participants: List[Wrestler],
        match_type: str = 'battle_royal',
        universe_state=None,
        booked_winner: Optional[Wrestler] = None,
        booked_runner_up: Optional[Wrestler] = None,
        booked_iron_man: Optional[Wrestler] = None,
        booked_most_eliminations: Optional[Wrestler] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for battle royal simulation.
        
        Args:
            participants: List of all wrestlers in the match
            match_type: 'battle_royal', 'rumble', or 'casino_battle_royal'
            universe_state: Universe state for additional context
            booked_winner: If specified, this wrestler will win the match
            booked_runner_up: If specified, this wrestler will be the last eliminated (runner-up)
        
        Returns:
            Dictionary with winner, elimination_order, highlights, duration
        """
        
        if match_type == 'rumble':
            return self._simulate_royal_rumble(participants, universe_state, booked_winner, booked_runner_up, booked_iron_man, booked_most_eliminations)
        elif match_type == 'casino_battle_royal':
            return self._simulate_casino_battle_royal(participants, universe_state, booked_winner, booked_runner_up, booked_iron_man, booked_most_eliminations)
        else:
            return self._simulate_standard_battle_royal(participants, universe_state, booked_winner, booked_runner_up, booked_iron_man, booked_most_eliminations)
    
    def _validate_booked_participants(
        self,
        participants: List[Wrestler],
        booked_winner: Optional[Wrestler],
        booked_runner_up: Optional[Wrestler]
    ) -> Tuple[Optional[Wrestler], Optional[Wrestler]]:
        """
        Validate and return corrected booked_winner and booked_runner_up.
        
        Returns:
            Tuple of (validated_winner, validated_runner_up)
        """
        validated_winner = booked_winner
        validated_runner_up = booked_runner_up
        
        # Validate booked winner is in the match
        if validated_winner and validated_winner not in participants:
            print(f"   ⚠️  Booked winner {validated_winner.name} not in participants, ignoring")
            validated_winner = None
        
        # Validate booked runner-up is in the match
        if validated_runner_up and validated_runner_up not in participants:
            print(f"   ⚠️  Booked runner-up {validated_runner_up.name} not in participants, ignoring")
            validated_runner_up = None
        
        # Validate winner and runner-up are different
        if validated_winner and validated_runner_up:
            if validated_winner.id == validated_runner_up.id:
                print(f"   ⚠️  Winner and runner-up cannot be the same person, ignoring runner-up")
                validated_runner_up = None
        
        # Print booking info
        if validated_winner:
            print(f"   📋 Booked Winner: {validated_winner.name}")
        if validated_runner_up:
            print(f"   📋 Booked Runner-Up: {validated_runner_up.name}")
        
        return validated_winner, validated_runner_up
    
    def _apply_booked_results(
        self,
        sorted_wrestlers: List[Wrestler],
        booked_winner: Optional[Wrestler],
        booked_runner_up: Optional[Wrestler]
    ) -> Tuple[List[Wrestler], Wrestler]:
        """
        Apply booked winner and runner-up to the sorted wrestler list.
        
        Args:
            sorted_wrestlers: List of wrestlers sorted by elimination (first = first out)
            booked_winner: The wrestler who should win (if any)
            booked_runner_up: The wrestler who should be runner-up (if any)
        
        Returns:
            Tuple of (modified_sorted_list, winner)
        """
        if not booked_winner and not booked_runner_up:
            # No booking, return as-is
            return sorted_wrestlers, sorted_wrestlers[-1]
        
        # Remove booked winner and runner-up from the list
        modified_list = [w for w in sorted_wrestlers 
                        if (not booked_winner or w.id != booked_winner.id) 
                        and (not booked_runner_up or w.id != booked_runner_up.id)]
        
        # Add runner-up second to last (last eliminated before winner)
        if booked_runner_up:
            modified_list.append(booked_runner_up)
        
        # Add winner at the end (they survive)
        if booked_winner:
            modified_list.append(booked_winner)
            winner = booked_winner
        else:
            winner = modified_list[-1]
        
        return modified_list, winner
    
    def _simulate_standard_battle_royal(
        self,
        participants: List[Wrestler],
        universe_state,
        booked_winner: Optional[Wrestler] = None,
        booked_runner_up: Optional[Wrestler] = None,
        booked_iron_man: Optional[Wrestler] = None,
        booked_most_eliminations: Optional[Wrestler] = None
    ) -> Dict[str, Any]:
        """
        Standard battle royal: All start in ring, last one standing wins.
        """
        
        print(f"\n🏟️  BATTLE ROYAL: {len(participants)} competitors!")
        
        # Validate booked participants
        booked_winner, booked_runner_up = self._validate_booked_participants(
            participants, booked_winner, booked_runner_up
        )
        
        # Calculate survival scores for each wrestler
        survival_scores = {}
        for wrestler in participants:
            score = self._calculate_survival_score(wrestler)
            survival_scores[wrestler.id] = score
        
        # Determine elimination order (lowest score eliminated first)
        sorted_wrestlers = sorted(
            participants,
            key=lambda w: survival_scores[w.id] + random.uniform(-10, 10)  # Add randomness
        )
        
        # Apply booked winner and runner-up
        sorted_wrestlers, winner = self._apply_booked_results(
            sorted_wrestlers, booked_winner, booked_runner_up
        )
        
        elimination_order = sorted_wrestlers[:-1]  # All except winner
        
        # Generate narrative highlights
        highlights = self._generate_battle_royal_highlights(
            participants,
            elimination_order,
            winner,
            match_type='battle_royal'
        )
        
        # Duration based on participant count (1 minute per wrestler roughly)
        duration = len(participants) + random.randint(-3, 5)
        duration = max(10, min(35, duration))
        
        print(f"   🏆 WINNER: {winner.name}")
        if elimination_order:
            print(f"   🥈 Runner-Up: {elimination_order[-1].name}")
            print(f"   📊 First 5 Eliminated: {', '.join([w.name for w in elimination_order[:5]])}...")
        
        return {
            'winner': winner,
            'elimination_order': elimination_order,
            'highlights': highlights,
            'duration_minutes': duration,
            'match_type': 'battle_royal',
            'booked_iron_man': booked_iron_man,
            'booked_most_eliminations': booked_most_eliminations
        }
    
    def _simulate_royal_rumble(
        self,
        participants: List[Wrestler],
        universe_state,
        booked_winner: Optional[Wrestler] = None,
        booked_runner_up: Optional[Wrestler] = None,
        booked_iron_man: Optional[Wrestler] = None,
        booked_most_eliminations: Optional[Wrestler] = None
    ) -> Dict[str, Any]:
        """
        Royal Rumble: Timed entries every 90 seconds, 30 participants.
        """
        
        print(f"\n👑 ROYAL RUMBLE: {len(participants)} entrants!")
        
        if len(participants) != 30:
            print(f"   ⚠️  Warning: Royal Rumble should have 30 entrants, got {len(participants)}")
        
        # Validate booked participants
        booked_winner, booked_runner_up = self._validate_booked_participants(
            participants, booked_winner, booked_runner_up
        )
        
        # Randomize entry order (or use existing order if specified)
        entry_order = participants.copy()
        random.shuffle(entry_order)
        
        # Calculate survival scores
        survival_scores = {}
        for idx, wrestler in enumerate(entry_order):
            base_score = self._calculate_survival_score(wrestler)
            
            # Early entrants get bonus points (iron man bonuses)
            if idx < 2:
                base_score += 15  # Entry #1 or #2
            elif idx < 5:
                base_score += 10  # Entry #3-5
            
            # Late entrants have slight disadvantage (less time to rest)
            if idx > 25:
                base_score -= 5
            
            survival_scores[wrestler.id] = base_score
        
        # Determine elimination order
        sorted_wrestlers = sorted(
            entry_order,
            key=lambda w: survival_scores[w.id] + random.uniform(-15, 15)
        )
        
        # Apply booked winner and runner-up
        sorted_wrestlers, winner = self._apply_booked_results(
            sorted_wrestlers, booked_winner, booked_runner_up
        )
        
        elimination_order = sorted_wrestlers[:-1]
        
        # Generate Rumble-specific highlights
        highlights = self._generate_rumble_highlights(
            entry_order,
            elimination_order,
            winner
        )
        
        # Rumbles are longer (30-50 minutes for 30 entrants)
        duration = 35 + random.randint(-5, 10)
        
        print(f"   🏆 WINNER: {winner.name} (Entry #{entry_order.index(winner) + 1})")
        if elimination_order:
            print(f"   🥈 Runner-Up: {elimination_order[-1].name}")
        print(f"   🥇 Final Four: {', '.join([w.name for w in sorted_wrestlers[-4:]])}")
        
        return {
            'winner': winner,
            'elimination_order': elimination_order,
            'entry_order': entry_order,
            'highlights': highlights,
            'duration_minutes': duration,
            'match_type': 'rumble',
            'booked_iron_man': booked_iron_man,
            'booked_most_eliminations': booked_most_eliminations
        }
    
    def _simulate_casino_battle_royal(
        self,
        participants: List[Wrestler],
        universe_state,
        booked_winner: Optional[Wrestler] = None,
        booked_runner_up: Optional[Wrestler] = None,
        booked_iron_man: Optional[Wrestler] = None,
        booked_most_eliminations: Optional[Wrestler] = None
    ) -> Dict[str, Any]:
        """
        Casino Battle Royal: Card-draw entry system (AEW style).
        """
        
        print(f"\n🎰 CASINO BATTLE ROYAL: {len(participants)} entrants!")
        
        # Validate booked participants
        booked_winner, booked_runner_up = self._validate_booked_participants(
            participants, booked_winner, booked_runner_up
        )
        
        # Assign card suits (determines entry order)
        suits = ['Spades', 'Hearts', 'Diamonds', 'Clubs']
        
        # Group participants by suit
        suit_groups = {suit: [] for suit in suits}
        
        for idx, wrestler in enumerate(participants):
            suit = suits[idx % 4]
            suit_groups[suit].append(wrestler)
        
        # Entry order: Clubs first, Diamonds second, Hearts third, Spades last
        entry_order = (
            suit_groups['Clubs'] +
            suit_groups['Diamonds'] +
            suit_groups['Hearts'] +
            suit_groups['Spades']
        )
        
        # Simulate similar to rumble
        survival_scores = {}
        for idx, wrestler in enumerate(entry_order):
            base_score = self._calculate_survival_score(wrestler)
            
            # Spades (last entries) have advantage
            if idx >= len(entry_order) * 0.75:
                base_score += 10
            
            survival_scores[wrestler.id] = base_score
        
        sorted_wrestlers = sorted(
            entry_order,
            key=lambda w: survival_scores[w.id] + random.uniform(-12, 12)
        )
        
        # Apply booked winner and runner-up
        sorted_wrestlers, winner = self._apply_booked_results(
            sorted_wrestlers, booked_winner, booked_runner_up
        )
        
        elimination_order = sorted_wrestlers[:-1]
        
        highlights = self._generate_casino_highlights(
            entry_order,
            suit_groups,
            elimination_order,
            winner
        )
        
        duration = 25 + random.randint(-3, 8)
        
        print(f"   🏆 WINNER: {winner.name}")
        if elimination_order:
            print(f"   🥈 Runner-Up: {elimination_order[-1].name}")
        
        return {
            'winner': winner,
            'elimination_order': elimination_order,
            'entry_order': entry_order,
            'suit_groups': {suit: [w.name for w in wrestlers] for suit, wrestlers in suit_groups.items()},
            'highlights': highlights,
            'duration_minutes': duration,
            'match_type': 'casino_battle_royal',
            'booked_iron_man': booked_iron_man,
            'booked_most_eliminations': booked_most_eliminations
        }
    
    def _calculate_survival_score(self, wrestler: Wrestler) -> float:
        """
        Calculate how likely a wrestler is to survive/win a battle royal.
        
        Factors:
        - Overall rating (50%)
        - Stamina (20%) - critical for long matches
        - Popularity (15%) - stars tend to last longer
        - Size/Brawling (15%) - harder to eliminate
        """
        
        base_score = wrestler.overall_rating * 0.5
        stamina_score = wrestler.stamina * 0.2
        popularity_score = wrestler.popularity * 0.15
        power_score = wrestler.brawling * 0.15
        
        # Role bonus (main eventers protected)
        role_bonus = {
            'Main Event': 10,
            'Upper Midcard': 5,
            'Midcard': 0,
            'Lower Midcard': -3,
            'Jobber': -8
        }.get(wrestler.role, 0)
        
        # Momentum factor
        momentum_factor = wrestler.momentum / 10
        
        # Fatigue penalty
        fatigue_penalty = wrestler.fatigue * 0.1
        
        total = (
            base_score +
            stamina_score +
            popularity_score +
            power_score +
            role_bonus +
            momentum_factor -
            fatigue_penalty
        )
        
        return max(0, total)
    
    def _generate_battle_royal_highlights(
        self,
        participants: List[Wrestler],
        elimination_order: List[Wrestler],
        winner: Wrestler,
        match_type: str
    ) -> List[MatchHighlight]:
        """Generate narrative highlights for standard battle royal"""
        
        highlights = []
        
        # Opening
        highlights.append(MatchHighlight(
            timestamp="0:30",
            description=f"The bell rings! {len(participants)} competitors battle in the ring!",
            highlight_type="opening"
        ))
        
        # Early eliminations (first 3)
        for i in range(min(3, len(elimination_order))):
            eliminated = elimination_order[i]
            highlights.append(MatchHighlight(
                timestamp=f"{2 + i}:{random.randint(0, 59):02d}",
                description=f"{eliminated.name} is eliminated early!",
                highlight_type="elimination"
            ))
        
        # Mid-match chaos
        mid_point = len(elimination_order) // 2
        if mid_point > 0 and mid_point < len(elimination_order):
            mid_eliminated = elimination_order[mid_point]
            highlights.append(MatchHighlight(
                timestamp=f"{len(participants) // 2}:{random.randint(0, 59):02d}",
                description=f"Mass brawl erupts! {mid_eliminated.name} goes over the top rope!",
                highlight_type="chaos"
            ))
        
        # Final four announcement
        if len(elimination_order) >= 3:
            final_four = elimination_order[-3:] + [winner]
            highlights.append(MatchHighlight(
                timestamp=f"{len(participants) - 4}:{random.randint(0, 59):02d}",
                description=f"Final Four: {', '.join([w.name for w in final_four])}!",
                highlight_type="final_four"
            ))
        
        # Near elimination for winner (dramatic moment)
        if len(elimination_order) >= 2:
            near_eliminator = random.choice(elimination_order[-3:]) if len(elimination_order) >= 3 else elimination_order[-1]
            highlights.append(MatchHighlight(
                timestamp=f"{len(participants) - 2}:{random.randint(0, 59):02d}",
                description=f"{winner.name} is on the apron! {near_eliminator.name} tries to eliminate them but {winner.name} hangs on!",
                highlight_type="nearfall"
            ))
        
        # Last elimination (the finish)
        if elimination_order:
            runner_up = elimination_order[-1]
            highlights.append(MatchHighlight(
                timestamp=f"{len(participants)}:{random.randint(0, 59):02d}",
                description=f"It's down to {winner.name} and {runner_up.name}! {winner.name} sends {runner_up.name} over the top rope to WIN THE BATTLE ROYAL!",
                highlight_type="finish"
            ))
        
        return highlights
    
    def _generate_rumble_highlights(
        self,
        entry_order: List[Wrestler],
        elimination_order: List[Wrestler],
        winner: Wrestler
    ) -> List[MatchHighlight]:
        """Generate Royal Rumble specific highlights"""
        
        highlights = []
        
        # Entrant #1 and #2
        if len(entry_order) >= 2:
            highlights.append(MatchHighlight(
                timestamp="0:00",
                description=f"Entrant #1: {entry_order[0].name}! Entrant #2: {entry_order[1].name}! The Rumble begins!",
                highlight_type="opening"
            ))
        
        # Notable early entry
        if len(entry_order) >= 10:
            early_idx = random.randint(4, 9)
            highlights.append(MatchHighlight(
                timestamp="3:30",
                description=f"Entrant #{early_idx + 1}: {entry_order[early_idx].name} hits the ring!",
                highlight_type="entry"
            ))
        
        # First elimination
        if elimination_order:
            first_out = elimination_order[0]
            highlights.append(MatchHighlight(
                timestamp="5:15",
                description=f"First elimination! {first_out.name} is out!",
                highlight_type="elimination"
            ))
        
        # Iron man moment (early entrants still in)
        iron_men = [w for w in entry_order[:5] if w not in elimination_order[:len(elimination_order)//2]]
        if iron_men:
            highlights.append(MatchHighlight(
                timestamp="15:00",
                description=f"Iron Man moment! {iron_men[0].name} entered early and is still going strong!",
                highlight_type="offense"
            ))
        
        # Midpoint entry
        if len(entry_order) >= 15:
            highlights.append(MatchHighlight(
                timestamp="18:00",
                description=f"Entrant #15: {entry_order[14].name}! The ring is filling up!",
                highlight_type="entry"
            ))
        
        # Notable late entry
        if len(entry_order) >= 26:
            late_entry_idx = random.randint(25, min(29, len(entry_order) - 1))
            highlights.append(MatchHighlight(
                timestamp="28:00",
                description=f"Entrant #{late_entry_idx + 1}: {entry_order[late_entry_idx].name} with a late entry!",
                highlight_type="entry"
            ))
        
        # Final four
        if len(elimination_order) >= 3:
            final_four = elimination_order[-3:] + [winner]
            highlights.append(MatchHighlight(
                timestamp="32:00",
                description=f"We're down to the Final Four: {', '.join([w.name for w in final_four])}!",
                highlight_type="final_four"
            ))
        
        # Final two
        if elimination_order:
            runner_up = elimination_order[-1]
            highlights.append(MatchHighlight(
                timestamp="34:30",
                description=f"Down to the final two! {winner.name} vs {runner_up.name}!",
                highlight_type="final_two"
            ))
            
            # Winner entry number for dramatic effect
            winner_entry = entry_order.index(winner) + 1
            entry_note = ""
            if winner_entry <= 5:
                entry_note = f" as an early entrant (#{ winner_entry})!"
            elif winner_entry >= 25:
                entry_note = f" after entering at #{ winner_entry}!"
            
            highlights.append(MatchHighlight(
                timestamp="35:45",
                description=f"{winner.name} eliminates {runner_up.name} to WIN THE ROYAL RUMBLE{entry_note}",
                highlight_type="finish"
            ))
        
        return highlights
    
    def _generate_casino_highlights(
        self,
        entry_order: List[Wrestler],
        suit_groups: Dict[str, List[Wrestler]],
        elimination_order: List[Wrestler],
        winner: Wrestler
    ) -> List[MatchHighlight]:
        """Generate Casino Battle Royal highlights"""
        
        highlights = []
        
        # Clubs enter
        clubs_names = [w.name for w in suit_groups['Clubs'][:3]]
        highlights.append(MatchHighlight(
            timestamp="0:00",
            description=f"♣️ CLUBS enter first! {', '.join(clubs_names)} and {len(suit_groups['Clubs']) - 3} more hit the ring!" if len(suit_groups['Clubs']) > 3 else f"♣️ CLUBS enter first! {', '.join([w.name for w in suit_groups['Clubs']])} hit the ring!",
            highlight_type="opening"
        ))
        
        # Early eliminations during Clubs phase
        if elimination_order:
            early_eliminated = [w for w in elimination_order[:3] if w in suit_groups['Clubs']]
            if early_eliminated:
                highlights.append(MatchHighlight(
                    timestamp="1:30",
                    description=f"{early_eliminated[0].name} is eliminated early in the Clubs phase!",
                    highlight_type="elimination"
                ))
        
        # Diamonds enter
        diamonds_star = max(suit_groups['Diamonds'], key=lambda w: w.popularity) if suit_groups['Diamonds'] else None
        highlights.append(MatchHighlight(
            timestamp="2:30",
            description=f"♦️ DIAMONDS join the fight!" + (f" {diamonds_star.name} leads the charge!" if diamonds_star else ""),
            highlight_type="entry"
        ))
        
        # Hearts enter
        hearts_star = max(suit_groups['Hearts'], key=lambda w: w.popularity) if suit_groups['Hearts'] else None
        highlights.append(MatchHighlight(
            timestamp="5:00",
            description=f"♥️ HEARTS enter the chaos!" + (f" {hearts_star.name} clears house!" if hearts_star else ""),
            highlight_type="entry"
        ))
        
        # Spades enter (final group - often has favorites)
        spades_star = max(suit_groups['Spades'], key=lambda w: w.popularity) if suit_groups['Spades'] else None
        highlights.append(MatchHighlight(
            timestamp="7:30",
            description=f"♠️ SPADES - the final suit!" + (f" {spades_star.name} enters with fresh legs!" if spades_star else " All competitors are now in!"),
            highlight_type="entry"
        ))
        
        # Mass elimination chaos
        if len(elimination_order) >= 5:
            mid_eliminated = elimination_order[len(elimination_order)//2]
            highlights.append(MatchHighlight(
                timestamp="12:00",
                description=f"Chaos in the ring! Multiple eliminations including {mid_eliminated.name}!",
                highlight_type="elimination"
            ))
        
        # Final four
        if len(elimination_order) >= 3:
            final_four = elimination_order[-3:] + [winner]
            highlights.append(MatchHighlight(
                timestamp="18:00",
                description=f"Final Four in the Casino Battle Royal: {', '.join([w.name for w in final_four])}!",
                highlight_type="final_four"
            ))
        
        # Dramatic near elimination
        if elimination_order:
            highlights.append(MatchHighlight(
                timestamp="21:00",
                description=f"{winner.name} skins the cat to save themselves! The crowd goes wild!",
                highlight_type="nearfall"
            ))
        
        # Final moment
        if elimination_order:
            runner_up = elimination_order[-1]
            
            # Find which suit the winner was in
            winner_suit = None
            for suit, wrestlers in suit_groups.items():
                if winner in wrestlers:
                    winner_suit = suit
                    break
            
            suit_emoji = {'Clubs': '♣️', 'Diamonds': '♦️', 'Hearts': '♥️', 'Spades': '♠️'}.get(winner_suit, '')
            
            highlights.append(MatchHighlight(
                timestamp="24:00",
                description=f"{winner.name} {suit_emoji} eliminates {runner_up.name} to win the CASINO BATTLE ROYAL!",
                highlight_type="finish"
            ))
        
        return highlights


# Global simulator instance
battle_royal_simulator = BattleRoyalSimulator()