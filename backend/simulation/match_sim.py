"""
Match Simulation Engine
Simulates professional wrestling matches with realistic outcomes and narratives.

STEP 14: Now supports multi-competitor matches!
FIXED: Now properly handles booked winners and title changes
UPDATED: Support for booked_runner_up in battle royals
"""

import random
from typing import List, Tuple, Optional, Dict, Any

from models.referee import referee_pool
from simulation.crowd_heat import create_crowd_tracker
from creative.special_matches import special_match_selector

from models.match import (
    MatchDraft, MatchResult, MatchParticipant, MatchHighlight,
    BookingBias, MatchImportance, FinishType
)
from models.wrestler import Wrestler
from simulation.injuries import injury_manager


class MatchSimulator:
    """
    Core match simulation engine.
    Handles all match types including multi-competitor matches.
    
    Supported match types:
    - singles: 1v1
    - tag: 2v2 (or more)
    - triple_threat: 3-way (no DQ, no tags)
    - fatal_4way: 4-way (no DQ, no tags)
    - triple_threat_tag: 3 teams (tags required)
    - fatal_4way_tag: 4 teams (tags required)
    - battle_royal: Multi-person over-the-top-rope elimination
    - rumble: Royal Rumble (timed entries)
    - casino_battle_royal: Casino Battle Royal (card-draw entries)
    """
    
    def __init__(self):
        self.random = random.Random()
    
    def simulate_match(
        self,
        match_draft: MatchDraft,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        universe_state=None  # STEP 13: For tag team chemistry
    ) -> MatchResult:
        """
        Main simulation entry point.
        Routes to appropriate simulation based on match type.
        """
        
        match_type = match_draft.match_type.lower()
        
        # STEP 14: Route multi-competitor matches
        if match_type in ['battle_royal', 'rumble', 'casino_battle_royal']:
            return self._simulate_battle_royal_match(match_draft, side_a_wrestlers, side_b_wrestlers, universe_state)
        
        elif match_type in ['triple_threat', 'fatal_4way', 'elimination_chamber']:
            return self._simulate_multi_competitor_match(match_draft, side_a_wrestlers, side_b_wrestlers, universe_state)
        
        elif match_type in ['triple_threat_tag', 'fatal_4way_tag']:
            return self._simulate_multi_team_match(match_draft, side_a_wrestlers, side_b_wrestlers, universe_state)
        
        else:
            # Standard singles/tag match
            return self._simulate_standard_match(match_draft, side_a_wrestlers, side_b_wrestlers, universe_state)
    
    
    def _simulate_standard_match(
        self,
        match_draft: MatchDraft,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        universe_state=None
    ) -> MatchResult:
        """
        Standard singles or tag team match (original logic).
        STEP 14: Now includes crowd heat tracking and referee influence.
        """
        # STEP 14: Initialize crowd heat tracker
        crowd_tracker = create_crowd_tracker()
        crowd_tracker.initialize_for_match(
            wrestlers=side_a_wrestlers + side_b_wrestlers,
            match_importance=match_draft.importance.value,
            is_title_match=match_draft.is_title_match,
            card_position=match_draft.card_position
        )
        
        # STEP 14: Get assigned referee
        referee = None
        if match_draft.referee_id:
            from models.referee import referee_pool
            for ref in referee_pool.referees:
                if ref.ref_id == match_draft.referee_id:
                    referee = ref
                    break
            
        # Calculate match quality ratings for each side
        side_a_rating = self._calculate_side_rating(side_a_wrestlers, universe_state)
        side_b_rating = self._calculate_side_rating(side_b_wrestlers, universe_state)
        
        # STEP 14: Track opening crowd reaction
        crowd_tracker.react_to_moment('opening_bell', [w.name for w in side_a_wrestlers + side_b_wrestlers])
        
        # FIX: Determine winner based on booked_winner OR booking bias
        if match_draft.booked_winner:
            if match_draft.booked_winner in ('side_a', 'side_b', 'draw', 'no_contest'):
                winner_side = match_draft.booked_winner
            elif match_draft.booked_winner in [w.id for w in side_a_wrestlers]:
                winner_side = 'side_a'
            elif match_draft.booked_winner in [w.id for w in side_b_wrestlers]:
                winner_side = 'side_b'
            else:
                print(f"      Booked winner {match_draft.booked_winner} not found, using bias")
                winner_side = self._determine_winner(
                    side_a_rating,
                    side_b_rating,
                    match_draft.booking_bias,
                    match_draft.importance
                )
            print(f"      Using booked winner side: {winner_side}")
        else:
            # Use the original logic
            winner_side = self._determine_winner(
                side_a_rating,
                side_b_rating,
                match_draft.booking_bias,
                match_draft.importance
            )
        
        # STEP 14: Determine finish type (with referee influence)
        finish_type = self._determine_finish_type_with_referee(
            side_a_wrestlers,
            side_b_wrestlers,
            winner_side,
            match_draft.importance,
            referee
        )
        
        # Calculate match duration
        duration = self._calculate_duration(
            match_draft.card_position,
            match_draft.importance,
            side_a_rating,
            side_b_rating
        )
        
        # STEP 14: Apply special match modifiers if applicable
        base_star_rating = self._calculate_star_rating(
            side_a_rating,
            side_b_rating,
            match_draft.importance,
            match_draft.card_position
        )
        
        if match_draft.special_match_type:
            from creative.special_matches import SpecialMatchType, special_match_selector
            try:
                special_type = SpecialMatchType(match_draft.special_match_type)
                base_star_rating, duration = special_match_selector.apply_special_match_modifiers(
                    special_type,
                    base_star_rating,
                    duration
                )
            except ValueError:
                pass  # Invalid special match type, use base values
            
        # STEP 14: Add crowd rating modifier
        crowd_summary = crowd_tracker.get_summary()
        star_rating = base_star_rating + crowd_summary['rating_modifier']
        star_rating = max(0.0, min(5.0, star_rating))
    
        # Generate highlights (with crowd reactions)
        highlights = self._generate_highlights_with_crowd(
            side_a_wrestlers,
            side_b_wrestlers,
            winner_side,
            finish_type,
            duration,
            crowd_tracker
        )
    
        # Detect upsets
        is_upset = self._detect_upset(
            side_a_wrestlers,
            side_b_wrestlers,
            winner_side,
            side_a_rating,
            side_b_rating
        )
    
        # Determine winner/loser names
        if winner_side == 'side_a':
            winner_names = match_draft.side_a.wrestler_names
            loser_names = match_draft.side_b.wrestler_names
        elif winner_side == 'side_b':
            winner_names = match_draft.side_b.wrestler_names
            loser_names = match_draft.side_a.wrestler_names
        else:  # draw/no_contest
            winner_names = []
            loser_names = []
    
        # FIX: Determine if title changed hands
        title_changed_hands = False
        new_champion_id = None
        new_champion_name = None
        
        if match_draft.is_title_match and match_draft.title_id:
            championship = universe_state.get_championship_by_id(match_draft.title_id) if universe_state else None
            winning_wrestlers = side_a_wrestlers if winner_side == 'side_a' else side_b_wrestlers
            winning_ids = [w.id for w in winning_wrestlers]
            current_holder_id = championship.current_holder_id if championship else None

            if winner_side in ('side_a', 'side_b') and current_holder_id not in winning_ids:
                title_changed_hands = True
                if winning_wrestlers:
                    new_champion_id = winning_wrestlers[0].id
                    new_champion_name = " & ".join([w.name for w in winning_wrestlers])
                print(f"      🏆 TITLE CHANGE: {new_champion_name} is the NEW CHAMPION!")
            else:
                retained_by = championship.current_holder_name if championship else 'champion'
                print(f"      🛡️ Title retained by {retained_by}")
    
        # Create result
        result = MatchResult(
            match_id=match_draft.match_id,
            side_a=match_draft.side_a,
            side_b=match_draft.side_b,
            match_type=match_draft.match_type,
            winner=winner_side,
            winner_names=winner_names,
            loser_names=loser_names,
            finish_type=finish_type,
            duration_minutes=duration,
            star_rating=star_rating,
            highlights=highlights,
            match_summary=self._generate_summary(match_draft, winner_names, loser_names, finish_type),
            is_upset=is_upset,
            card_position=match_draft.card_position,
            is_title_match=match_draft.is_title_match,
            title_name=match_draft.title_name,
            title_id=match_draft.title_id,  # FIX: Include title_id
            title_changed_hands=title_changed_hands,  # FIX: Set this!
            new_champion_id=new_champion_id,  # FIX: Set this!
            new_champion_name=new_champion_name,  # FIX: Set this!
            # STEP 14: New fields
            referee_name=referee.name if referee else "Unknown Referee",
            crowd_energy=crowd_summary['ending_energy'],
            crowd_pacing_grade=crowd_summary['pacing_grade'],
            special_match_type=match_draft.special_match_type
        )
    
        return result
    
    def _simulate_multi_competitor_match(
        self,
        match_draft: MatchDraft,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        universe_state=None
    ) -> MatchResult:
        """
        Simulate triple threat or fatal 4-way match.
        No DQ, no count-outs, first pinfall/submission wins.
        
        match_draft structure for multi-competitor:
        - side_a.wrestler_ids = [competitor_1_id, competitor_2_id, ...]
        - side_b.wrestler_ids = [] (empty)
        """
        
        # Combine all competitors
        all_competitors = side_a_wrestlers + side_b_wrestlers
        
        required_competitors = 6 if match_draft.match_type == 'elimination_chamber' else 3
        if len(all_competitors) < required_competitors:
            match_label = 'Elimination Chamber' if match_draft.match_type == 'elimination_chamber' else 'Multi-competitor match'
            raise ValueError(f"{match_label} needs {required_competitors}+ wrestlers, got {len(all_competitors)}")
        
        print(f"   🔀 {match_draft.match_type.upper()}: {', '.join([w.name for w in all_competitors])}")
        
        # Calculate ratings for each competitor
        competitor_ratings = {w.id: self._calculate_wrestler_rating(w) for w in all_competitors}
        
        # FIX: Handle booked winner for multi-competitor matches
        if match_draft.booked_winner:
            # Find the wrestler that should win based on booked_winner
            winner = None
            for wrestler in all_competitors:
                if wrestler.id == match_draft.booked_winner:
                    winner = wrestler
                    print(f"      📌 Using booked winner: {winner.name}")
                    break
            
            # If not found by ID, fall back to random
            if not winner:
                print(f"      ⚠️ Booked winner not found in competitors, using random")
                winner = self._determine_multi_winner(all_competitors, competitor_ratings, match_draft.booking_bias)
        else:
            # Determine winner (weighted by booking bias if applicable)
            winner = self._determine_multi_winner(all_competitors, competitor_ratings, match_draft.booking_bias)
        
        # STEP 14: Get assigned referee
        referee = None
        if match_draft.referee_id:
            from models.referee import referee_pool
            for ref in referee_pool.referees:
                if ref.ref_id == match_draft.referee_id:
                    referee = ref
                    break
        
        # Determine finish type (no DQ/countouts in multi-matches)
        finish_type = self._determine_multi_finish_type(winner, match_draft.importance)
        
        # If referee assigned and cheating finish, check for DQ call
        if referee and finish_type == FinishType.CHEATING:
            dq_probability = referee.get_dq_probability(match_draft.importance.value)
            if random.random() < dq_probability:
                # In multi-man matches, DQ is rare but can happen
                # Instead, just change to clean finish (referee caught them)
                finish_type = FinishType.CLEAN_PIN
        
        # Calculate duration (multi-matches tend to be longer)
        duration = self._calculate_duration(
            match_draft.card_position,
            match_draft.importance,
            sum(competitor_ratings.values()) / len(competitor_ratings),
            sum(competitor_ratings.values()) / len(competitor_ratings)
        ) + random.randint(2, 5)  # Bonus time for multi-person chaos
        
        # Calculate star rating
        avg_rating = sum(competitor_ratings.values()) / len(competitor_ratings)
        star_rating = self._calculate_star_rating(
            avg_rating,
            avg_rating,
            match_draft.importance,
            match_draft.card_position
        ) + 0.25  # Multi-matches often slightly higher rated
        star_rating = min(5.0, star_rating)
        
        # Generate highlights
        highlights = self._generate_multi_highlights(
            all_competitors,
            winner,
            finish_type,
            duration,
            match_draft.match_type
        )
        
        # Detect upsets
        is_upset = self._detect_multi_upset(all_competitors, winner, competitor_ratings)
        
        # Build result
        loser_names = [w.name for w in all_competitors if w.id != winner.id]
        
        # FIX: Check for title change in multi-competitor matches
        title_changed_hands = False
        new_champion_id = None
        new_champion_name = None
        
        if match_draft.is_title_match and match_draft.title_id and universe_state:
            # Get current champion
            championship = universe_state.get_championship_by_id(match_draft.title_id)
            if championship and championship.current_holder_id != winner.id:
                title_changed_hands = True
                new_champion_id = winner.id
                new_champion_name = winner.name
                print(f"      🏆 TITLE CHANGE: {new_champion_name} is the NEW CHAMPION!")
        
        result = MatchResult(
            match_id=match_draft.match_id,
            side_a=match_draft.side_a,
            side_b=match_draft.side_b,
            match_type=match_draft.match_type,
            winner='side_a',  # Winner is always in side_a for multi-matches
            winner_names=[winner.name],
            loser_names=loser_names,
            finish_type=finish_type,
            duration_minutes=duration,
            star_rating=star_rating,
            highlights=highlights,
            match_summary=f"{winner.name} won the {match_draft.match_type.replace('_', ' ')} match.",
            is_upset=is_upset,
            card_position=match_draft.card_position,
            is_title_match=match_draft.is_title_match,
            title_name=match_draft.title_name,
            title_id=match_draft.title_id,
            title_changed_hands=title_changed_hands,
            new_champion_id=new_champion_id,
            new_champion_name=new_champion_name,
            referee_name=referee.name if referee else "Unknown Referee"
        )
        return result
    
    def _simulate_multi_team_match(
        self,
        match_draft: MatchDraft,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        universe_state=None
    ) -> MatchResult:
        """
        Simulate triple threat tag or fatal 4-way tag match.
        Tags ARE required (unlike singles multi-matches).
        
        match_draft structure:
        - side_a.wrestler_ids = [team1_member1, team1_member2, team2_member1, team2_member2, ...]
        - side_b.wrestler_ids = [] (empty, or contains additional teams)
        """
        
        all_wrestlers = side_a_wrestlers + side_b_wrestlers
        
        # Group into teams (assume pairs)
        teams = []
        for i in range(0, len(all_wrestlers), 2):
            if i + 1 < len(all_wrestlers):
                teams.append([all_wrestlers[i], all_wrestlers[i+1]])
        
        if len(teams) < 3:
            raise ValueError(f"Multi-team match needs 3+ teams, got {len(teams)}")
        
        print(f"   👥 {match_draft.match_type.upper()}: {len(teams)} teams")
        
        # Calculate team ratings
        team_ratings = {}
        for idx, team in enumerate(teams):
            team_ratings[idx] = self._calculate_side_rating(team, universe_state)
        
        # Handle booked winner for multi-team matches
        winning_team_idx = None
        if match_draft.booked_winner:
            # booked_winner should be wrestler_id of someone on the winning team
            for idx, team in enumerate(teams):
                for wrestler in team:
                    if wrestler.id == match_draft.booked_winner:
                        winning_team_idx = idx
                        print(f"      📌 Using booked winner's team: Team {idx + 1}")
                        break
                if winning_team_idx is not None:
                    break
        
        if winning_team_idx is None:
            # Determine winning team randomly
            winning_team_idx = self._determine_multi_team_winner(teams, team_ratings, match_draft.booking_bias)
        
        winning_team = teams[winning_team_idx]
        
        # Determine finish
        finish_type = self._determine_finish_type(
            winning_team,
            [w for t in teams for w in t if t != winning_team],
            'side_a',
            match_draft.importance
        )
        
        # Duration
        duration = self._calculate_duration(
            match_draft.card_position,
            match_draft.importance,
            team_ratings[winning_team_idx],
            sum(team_ratings.values()) / len(team_ratings)
        ) + random.randint(3, 6)
        
        # Star rating
        avg_rating = sum(team_ratings.values()) / len(team_ratings)
        star_rating = self._calculate_star_rating(
            avg_rating,
            avg_rating,
            match_draft.importance,
            match_draft.card_position
        ) + 0.3  # Multi-tag matches are spectacles
        star_rating = min(5.0, star_rating)
        
        # Highlights
        highlights = self._generate_multi_team_highlights(
            teams,
            winning_team,
            finish_type,
            duration
        )
        
        # Upset detection
        is_upset = False
        
        # Build result
        winner_names = [w.name for w in winning_team]
        loser_names = [w.name for team in teams if team != winning_team for w in team]
        
        # FIX: Check for title change in tag team matches
        title_changed_hands = False
        new_champion_id = None
        new_champion_name = None
        
        if match_draft.is_title_match and match_draft.title_id and universe_state:
            # For tag titles, check if winning team is different from current champions
            championship = universe_state.get_championship_by_id(match_draft.title_id)
            if championship:
                # Check if any member of winning team is current champion
                winning_team_ids = [w.id for w in winning_team]
                if championship.current_holder_id not in winning_team_ids:
                    title_changed_hands = True
                    # For tag titles, typically use first member as "holder"
                    new_champion_id = winning_team[0].id
                    new_champion_name = " & ".join([w.name for w in winning_team])
                    print(f"      🏆 TITLE CHANGE: {new_champion_name} are the NEW CHAMPIONS!")
        
        result = MatchResult(
            match_id=match_draft.match_id,
            side_a=match_draft.side_a,
            side_b=match_draft.side_b,
            match_type=match_draft.match_type,
            winner='side_a',
            winner_names=winner_names,
            loser_names=loser_names,
            finish_type=finish_type,
            duration_minutes=duration,
            star_rating=star_rating,
            highlights=highlights,
            match_summary=f"{' & '.join(winner_names)} won the {match_draft.match_type.replace('_', ' ')} match.",
            is_upset=is_upset,
            card_position=match_draft.card_position,
            is_title_match=match_draft.is_title_match,
            title_name=match_draft.title_name,
            title_id=match_draft.title_id,
            title_changed_hands=title_changed_hands,
            new_champion_id=new_champion_id,
            new_champion_name=new_champion_name
        )
        
        return result
    
    def _simulate_battle_royal_match(
        self,
        match_draft: MatchDraft,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        universe_state=None
    ) -> MatchResult:
        """
        Simulate battle royal, Royal Rumble, or Casino Battle Royal.
        Uses the specialized BattleRoyalSimulator.
        
        UPDATED: Now supports booked_winner and booked_runner_up
        """
        
        from simulation.battle_royal import battle_royal_simulator
        
        # Combine all participants
        all_participants = side_a_wrestlers + side_b_wrestlers
        
        # Handle booked winner for battle royals
        booked_winner_wrestler = None
        if match_draft.booked_winner:
            for wrestler in all_participants:
                if wrestler.id == match_draft.booked_winner:
                    booked_winner_wrestler = wrestler
                    print(f"      📌 Using booked winner: {wrestler.name}")
                    break
            if not booked_winner_wrestler:
                print(f"      ⚠️ Booked winner ID {match_draft.booked_winner} not found in participants")
        
        # Handle booked runner-up for battle royals
        booked_runner_up_wrestler = None
        if hasattr(match_draft, 'booked_runner_up') and match_draft.booked_runner_up:
            for wrestler in all_participants:
                if wrestler.id == match_draft.booked_runner_up:
                    booked_runner_up_wrestler = wrestler
                    print(f"      📌 Using booked runner-up: {wrestler.name}")
                    break
            if not booked_runner_up_wrestler:
                print(f"      ⚠️ Booked runner-up ID {match_draft.booked_runner_up} not found in participants")
        
        booked_iron_man_wrestler = None
        if hasattr(match_draft, 'booked_iron_man') and match_draft.booked_iron_man:
            booked_iron_man_wrestler = next((w for w in all_participants if w.id == match_draft.booked_iron_man), None)

        booked_most_elims_wrestler = None
        if hasattr(match_draft, 'booked_most_eliminations') and match_draft.booked_most_eliminations:
            booked_most_elims_wrestler = next((w for w in all_participants if w.id == match_draft.booked_most_eliminations), None)

        # Validate winner and runner-up are different
        if booked_winner_wrestler and booked_runner_up_wrestler:
            if booked_winner_wrestler.id == booked_runner_up_wrestler.id:
                print(f"      ⚠️ Winner and runner-up cannot be the same, ignoring runner-up")
                booked_runner_up_wrestler = None
        
        # Run battle royal simulation
        br_result = battle_royal_simulator.simulate_battle_royal(
            all_participants,
            match_type=match_draft.match_type,
            universe_state=universe_state,
            booked_winner=booked_winner_wrestler,
            booked_runner_up=booked_runner_up_wrestler,
            booked_iron_man=booked_iron_man_wrestler,
            booked_most_eliminations=booked_most_elims_wrestler
        )
        
        winner = br_result['winner']
        highlights = br_result['highlights']
        duration = br_result['duration_minutes']
        
        # Calculate star rating based on participant quality
        avg_rating = sum(w.overall_rating for w in all_participants) / len(all_participants)
        star_rating = (avg_rating / 100) * 4.0  # Battle royals cap at 4 stars usually
        star_rating += random.uniform(-0.25, 0.5)
        star_rating = max(2.0, min(5.0, star_rating))
        star_rating = round(star_rating * 4) / 4
        
        # Detect upset
        is_upset = self._detect_multi_upset(all_participants, winner, {w.id: w.overall_rating for w in all_participants})
        
        # Build result
        loser_names = [w.name for w in all_participants if w.id != winner.id]
        
        # FIX: Check for title change in battle royals
        title_changed_hands = False
        new_champion_id = None
        new_champion_name = None
        
        if match_draft.is_title_match and match_draft.title_id and universe_state:
            championship = universe_state.get_championship_by_id(match_draft.title_id)
            if championship and championship.current_holder_id != winner.id:
                title_changed_hands = True
                new_champion_id = winner.id
                new_champion_name = winner.name
                print(f"      🏆 TITLE CHANGE: {new_champion_name} is the NEW CHAMPION!")
        
        # Build elimination summary
        elimination_order = br_result.get('elimination_order', [])
        elimination_summary = ', '.join([w.name for w in elimination_order[:5]]) if elimination_order else 'N/A'
        extra_notes = []
        if br_result.get('booked_iron_man'):
            extra_notes.append(f"Iron Man: {br_result['booked_iron_man'].name}")
        if br_result.get('booked_most_eliminations'):
            extra_notes.append(f"Most Eliminations: {br_result['booked_most_eliminations'].name}")
        note_text = (' ' + ' | '.join(extra_notes)) if extra_notes else ''
        
        result = MatchResult(
            match_id=match_draft.match_id,
            side_a=match_draft.side_a,
            side_b=match_draft.side_b,
            match_type=match_draft.match_type,
            winner='side_a',  # Winner stored in side_a
            winner_names=[winner.name],
            loser_names=loser_names[:5],  # Only show first 5 losers in summary
            finish_type=FinishType.CLEAN_PIN,  # Battle royals don't have traditional finishes
            duration_minutes=duration,
            star_rating=star_rating,
            highlights=highlights,
            match_summary=f"{winner.name} won the {match_draft.match_type.replace('_', ' ').upper()}! Elimination order: {elimination_summary}...{note_text}",
            is_upset=is_upset,
            card_position=match_draft.card_position,
            is_title_match=match_draft.is_title_match,
            title_name=match_draft.title_name,
            title_id=match_draft.title_id,
            title_changed_hands=title_changed_hands,
            new_champion_id=new_champion_id,
            new_champion_name=new_champion_name
        )
        
        return result
    
    # ========================================================================
    # MULTI-COMPETITOR HELPER METHODS
    # ========================================================================
    
    def _calculate_wrestler_rating(self, wrestler: Wrestler) -> float:
        """Calculate individual wrestler's match quality rating"""
        
        base_attributes = (
            wrestler.brawling * 0.20 +
            wrestler.technical * 0.20 +
            wrestler.speed * 0.15 +
            wrestler.psychology * 0.25 +
            wrestler.stamina * 0.15 +
            wrestler.mic * 0.05
        )
        
        popularity_factor = wrestler.popularity * 0.3
        momentum_factor = (wrestler.momentum + 100) / 10
        fatigue_penalty = wrestler.fatigue * 0.15
        
        role_bonus = {
            'Main Event': 5,
            'Upper Midcard': 3,
            'Midcard': 0,
            'Lower Midcard': -2,
            'Jobber': -5
        }.get(wrestler.role, 0)
        
        rating = (
            base_attributes +
            popularity_factor +
            momentum_factor +
            role_bonus -
            fatigue_penalty
        )
        
        return max(0, min(100, rating))
    
    def _determine_multi_winner(
        self,
        competitors: List[Wrestler],
        ratings: Dict[str, float],
        booking_bias: BookingBias
    ) -> Wrestler:
        """
        Determine winner in multi-competitor match.
        First competitor is Side A (gets booking bias if applicable).
        """
        
        # Apply booking bias to first competitor (side_a)
        bias_multipliers = {
            BookingBias.STRONG_A: 3.0,
            BookingBias.SLIGHT_A: 1.5,
            BookingBias.EVEN: 1.0,
            BookingBias.SLIGHT_B: 0.7,
            BookingBias.STRONG_B: 0.4
        }
        
        multiplier = bias_multipliers.get(booking_bias, 1.0)
        
        # Build weighted list
        weights = []
        for idx, competitor in enumerate(competitors):
            base_weight = ratings[competitor.id]
            
            # Apply bias to first competitor
            if idx == 0:
                base_weight *= multiplier
            
            weights.append(base_weight)
        
        return random.choices(competitors, weights=weights)[0]
    
    def _determine_multi_team_winner(
        self,
        teams: List[List[Wrestler]],
        team_ratings: Dict[int, float],
        booking_bias: BookingBias
    ) -> int:
        """Determine winning team index in multi-team match"""
        
        bias_multipliers = {
            BookingBias.STRONG_A: 3.0,
            BookingBias.SLIGHT_A: 1.5,
            BookingBias.EVEN: 1.0,
            BookingBias.SLIGHT_B: 0.7,
            BookingBias.STRONG_B: 0.4
        }
        
        multiplier = bias_multipliers.get(booking_bias, 1.0)
        
        weights = []
        for idx in range(len(teams)):
            weight = team_ratings[idx]
            
            if idx == 0:  # First team gets bias
                weight *= multiplier
            
            weights.append(weight)
        
        return random.choices(range(len(teams)), weights=weights)[0]
    
    def _determine_multi_finish_type(
        self,
        winner: Wrestler,
        importance: MatchImportance
    ) -> FinishType:
        """
        Determine finish type for multi-competitor match.
        No DQ/countouts in multi-matches.
        """
        
        if importance == MatchImportance.PROTECT_BOTH:
            # Still no DQ, but can be rollup/surprise finish
            return FinishType.ROLLUP if random.random() < 0.6 else FinishType.CLEAN_PIN
        
        # Weight by alignment
        if winner.alignment == 'Face':
            options = [
                (FinishType.CLEAN_PIN, 60),
                (FinishType.SUBMISSION, 20),
                (FinishType.ROLLUP, 20)
            ]
        elif winner.alignment == 'Heel':
            options = [
                (FinishType.CLEAN_PIN, 30),
                (FinishType.CHEATING, 40),  # Can still cheat even without DQ
                (FinishType.ROLLUP, 30)
            ]
        else:  # Tweener
            options = [
                (FinishType.CLEAN_PIN, 50),
                (FinishType.ROLLUP, 30),
                (FinishType.SUBMISSION, 20)
            ]
        
        finishes, weights = zip(*options)
        return random.choices(finishes, weights=weights)[0]
    
    def _detect_multi_upset(
        self,
        competitors: List[Wrestler],
        winner: Wrestler,
        ratings: Dict[str, float]
    ) -> bool:
        """Detect upset in multi-competitor match"""
        
        # Sort competitors by rating
        sorted_competitors = sorted(competitors, key=lambda w: ratings[w.id], reverse=True)
        
        # If winner is in bottom half AND top competitor lost
        winner_rank = sorted_competitors.index(winner) + 1
        
        if winner_rank > len(competitors) / 2:
            # Lower-ranked wrestler won
            top_competitor = sorted_competitors[0]
            rating_diff = ratings[top_competitor.id] - ratings[winner.id]
            
            if rating_diff > 20:
                return True
        
        return False
    
    def _generate_multi_highlights(
        self,
        competitors: List[Wrestler],
        winner: Wrestler,
        finish_type: FinishType,
        duration: int,
        match_type: str
    ) -> List[MatchHighlight]:
        """Generate highlights for triple threat / fatal 4-way"""
        
        highlights = []
        
        competitor_names = [w.name for w in competitors]
        
        # Opening
        highlights.append(MatchHighlight(
            timestamp="0:30",
            description=f"The bell rings! {', '.join(competitor_names)} all vie for victory!",
            highlight_type="opening"
        ))
        
        # Early chaos
        aggressor = random.choice(competitors)
        highlights.append(MatchHighlight(
            timestamp=f"{random.randint(2, 4)}:{random.randint(10, 50):02d}",
            description=f"{aggressor.name} takes early control, targeting multiple opponents!",
            highlight_type="offense"
        ))
        
        # Alliances/betrayals
        if len(competitors) >= 3:
            ally1, ally2 = random.sample(competitors, 2)
            highlights.append(MatchHighlight(
                timestamp=f"{duration // 3}:{random.randint(0, 59):02d}",
                description=f"{ally1.name} and {ally2.name} briefly team up to take down a common threat!",
                highlight_type="alliance"
            ))
            
            highlights.append(MatchHighlight(
                timestamp=f"{duration // 2}:{random.randint(0, 59):02d}",
                description=f"{ally1.name} BETRAYS {ally2.name}! Every person for themselves!",
                highlight_type="betrayal"
            ))
        
        # Near-falls
        for _ in range(random.randint(2, 4)):
            near_fall_wrestler = random.choice(competitors)
            highlights.append(MatchHighlight(
                timestamp=f"{duration - random.randint(2, 5)}:{random.randint(0, 59):02d}",
                description=f"NEAR FALL! {near_fall_wrestler.name} almost wins it!",
                highlight_type="nearfall"
            ))
        
        # Finish
        finish_desc = {
            FinishType.CLEAN_PIN: f"{winner.name} hits a devastating finisher and pins for the win!",
            FinishType.SUBMISSION: f"{winner.name} locks in a submission - someone taps!",
            FinishType.CHEATING: f"{winner.name} uses underhanded tactics to steal the victory!",
            FinishType.ROLLUP: f"{winner.name} catches an opponent with a sneaky rollup!"
        }.get(finish_type, f"{winner.name} wins!")
        
        highlights.append(MatchHighlight(
            timestamp=f"{duration}:00",
            description=finish_desc,
            highlight_type="finish"
        ))
        
        return highlights
    
    def _generate_multi_team_highlights(
        self,
        teams: List[List[Wrestler]],
        winning_team: List[Wrestler],
        finish_type: FinishType,
        duration: int
    ) -> List[MatchHighlight]:
        """Generate highlights for multi-team tag matches"""
        
        highlights = []
        
        team_names = [" & ".join([w.name for w in team]) for team in teams]
        
        highlights.append(MatchHighlight(
            timestamp="0:30",
            description=f"All teams enter the fray! {', '.join(team_names)} battle for supremacy!",
            highlight_type="opening"
        ))
        
        # Tag team chaos
        for i in range(random.randint(3, 5)):
            random_team = random.choice(teams)
            member = random.choice(random_team)
            
            highlights.append(MatchHighlight(
                timestamp=f"{random.randint(3, duration-3)}:{random.randint(0, 59):02d}",
                description=f"{member.name} makes a hot tag! Their partner clears the ring!",
                highlight_type="offense"
            ))
        
        # Near-falls
        for _ in range(random.randint(2, 3)):
            near_fall_team = random.choice(teams)
            highlights.append(MatchHighlight(
                timestamp=f"{duration - random.randint(2, 4)}:{random.randint(0, 59):02d}",
                description=f"NEAR FALL! {near_fall_team[0].name} almost wins it for their team!",
                highlight_type="nearfall"
            ))
        
        # Finish
        winner_names = " & ".join([w.name for w in winning_team])
        highlights.append(MatchHighlight(
            timestamp=f"{duration}:00",
            description=f"{winner_names} secure the victory for their team!",
            highlight_type="finish"
        ))
        
        return highlights
    
    # ========================================================================
    # ORIGINAL HELPER METHODS (for singles/tag matches)
    # ========================================================================
    
    def _calculate_side_rating(self, wrestlers: List[Wrestler], universe_state=None) -> float:
        """
        Calculate overall match quality rating for one side.
        Combines attributes, popularity, momentum, and current condition.
        
        STEP 13: Now includes tag team chemistry bonus!
        """
        if not wrestlers:
            return 50.0
        
        total_rating = 0.0
        
        for wrestler in wrestlers:
            # Base attribute score (0-100)
            base_attributes = (
                wrestler.brawling * 0.20 +
                wrestler.technical * 0.20 +
                wrestler.speed * 0.15 +
                wrestler.psychology * 0.25 +
                wrestler.stamina * 0.15 +
                wrestler.mic * 0.05
            )
            
            # Popularity factor (0-100)
            popularity_factor = wrestler.popularity * 0.3
            
            # Momentum factor (-100 to 100, normalized to 0-20)
            momentum_factor = (wrestler.momentum + 100) / 10
            
            # Fatigue penalty (0-100 fatigue = 0-15 point penalty)
            fatigue_penalty = wrestler.fatigue * 0.15
            
            # Injury penalty
            injury_penalty = 0
            if wrestler.injury.severity == 'Minor':
                injury_penalty = 5
            elif wrestler.injury.severity == 'Moderate':
                injury_penalty = 15
            elif wrestler.injury.severity == 'Major':
                injury_penalty = 30
            
            # Role modifier (main eventers perform better in big matches)
            role_bonus = 0
            if wrestler.role == 'Main Event':
                role_bonus = 5
            elif wrestler.role == 'Upper Midcard':
                role_bonus = 3
            elif wrestler.role == 'Jobber':
                role_bonus = -3
            
            wrestler_rating = (
                base_attributes +
                popularity_factor +
                momentum_factor +
                role_bonus -
                fatigue_penalty -
                injury_penalty
            )
            
            total_rating += max(0, min(100, wrestler_rating))
        
        # Average for tag teams
        base_rating = total_rating / len(wrestlers)
        
        # STEP 13: Apply tag team chemistry bonus
        if len(wrestlers) >= 2 and universe_state:
            wrestler_ids = [w.id for w in wrestlers]
            chemistry_multiplier = universe_state.tag_team_manager.calculate_chemistry_bonus(wrestler_ids)
            
            # Apply chemistry bonus (0.8x - 1.2x multiplier)
            base_rating *= chemistry_multiplier
            
            # Debug output
            if chemistry_multiplier != 1.0:
                team = universe_state.tag_team_manager.get_team_by_members(wrestler_ids)
                if team:
                    print(f"      Tag team chemistry: {team.team_name} ({team.chemistry}/100) = {chemistry_multiplier:.2f}x multiplier")

        if universe_state and hasattr(universe_state, 'relationship_network'):
            wrestler_ids = [w.id for w in wrestlers]
            manager_bonus = universe_state.relationship_network.get_manager_bonus(wrestler_ids, context="match")
            if manager_bonus:
                base_rating *= (1.0 + manager_bonus)
                print(f"      Manager bonus applied: +{manager_bonus * 100:.1f}%")

        return base_rating
    
    def _determine_winner(
        self,
        side_a_rating: float,
        side_b_rating: float,
        booking_bias: BookingBias,
        importance: MatchImportance
    ) -> str:
        """
        Determine match winner based on ratings and booking bias.
        Returns 'side_a', 'side_b', 'draw', or 'no_contest'
        """
        
        # Base probabilities from booking bias
        bias_probabilities = {
            BookingBias.STRONG_A: 0.85,
            BookingBias.SLIGHT_A: 0.65,
            BookingBias.EVEN: 0.50,
            BookingBias.SLIGHT_B: 0.35,
            BookingBias.STRONG_B: 0.15
        }
        
        side_a_win_probability = bias_probabilities[booking_bias]
        
        # Slight adjustment based on quality difference (max ±5%)
        quality_diff = (side_a_rating - side_b_rating) / 100
        side_a_win_probability += quality_diff * 0.05
        
        # Clamp to 5%-95%
        side_a_win_probability = max(0.05, min(0.95, side_a_win_probability))
        
        # Roll for winner
        roll = random.random()
        
        if roll < side_a_win_probability:
            return 'side_a'
        else:
            return 'side_b'
    
    def _determine_finish_type(
        self,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        winner_side: str,
        importance: MatchImportance
    ) -> FinishType:
        """
        Determine how the match finishes.
        Faces tend to win clean, heels cheat, upsets are often rollups.
        """
        
        # Get winner and loser alignments
        if winner_side == 'side_a':
            winners = side_a_wrestlers
            losers = side_b_wrestlers
        else:
            winners = side_b_wrestlers
            losers = side_a_wrestlers
        
        winner_alignment = winners[0].alignment if winners else 'Face'
        loser_alignment = losers[0].alignment if losers else 'Heel'
        
        # PROTECT_BOTH importance often leads to non-finishes
        if importance == MatchImportance.PROTECT_BOTH:
            if random.random() < 0.4:
                return random.choice([FinishType.DQ, FinishType.COUNTOUT, FinishType.NO_CONTEST])
        
        # Base finish type probabilities
        finish_weights = []
        
        # Clean pin/submission
        if winner_alignment == 'Face':
            finish_weights.append((FinishType.CLEAN_PIN, 60))
            finish_weights.append((FinishType.SUBMISSION, 15))
        else:
            finish_weights.append((FinishType.CLEAN_PIN, 30))
            finish_weights.append((FinishType.SUBMISSION, 10))
        
        # Cheating (heels more likely)
        if winner_alignment == 'Heel':
            finish_weights.append((FinishType.CHEATING, 35))
        else:
            finish_weights.append((FinishType.CHEATING, 5))
        
        # Rollup (upset finishes)
        finish_weights.append((FinishType.ROLLUP, 10))
        
        # DQ/Countout
        finish_weights.append((FinishType.DQ, 5))
        finish_weights.append((FinishType.COUNTOUT, 3))
        
        # Weighted random choice
        finishes, weights = zip(*finish_weights)
        return random.choices(finishes, weights=weights)[0]
    
    def _determine_finish_type_with_referee(
        self,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        winner_side: str,
        importance: MatchImportance,
        referee
    ) -> FinishType:
        """
        Determine finish type with referee personality influence.
        
        STEP 14: Referee strictness affects DQ probability.
        """
        
        # Get base finish type
        finish_type = self._determine_finish_type(
            side_a_wrestlers,
            side_b_wrestlers,
            winner_side,
            importance
        )
        
        # If referee assigned, check if they would call DQ
        if referee and finish_type == FinishType.CHEATING:
            dq_probability = referee.get_dq_probability(importance.value)
            
            if random.random() < dq_probability:
                # Referee calls DQ instead of allowing cheating finish
                finish_type = FinishType.DQ
        
        return finish_type
    
    def _calculate_duration(
        self,
        card_position: int,
        importance: MatchImportance,
        side_a_rating: float,
        side_b_rating: float
    ) -> int:
        """
        Calculate match duration in minutes.
        Main events are longer, openers are shorter.
        """
        
        # Base duration by card position
        if card_position == 1:
            base = 8  # Opener
        elif card_position <= 3:
            base = 10  # Early card
        elif card_position <= 5:
            base = 12  # Mid-card
        else:
            base = 18  # Main event area
        
        # Importance modifier
        if importance == MatchImportance.HIGH_DRAMA:
            base += 5
        elif importance == MatchImportance.PROTECT_BOTH:
            base -= 2
        
        # Quality modifier (better wrestlers = longer matches)
        avg_rating = (side_a_rating + side_b_rating) / 2
        if avg_rating > 80:
            base += 3
        elif avg_rating < 50:
            base -= 2
        
        # Random variance ±3 minutes
        duration = base + random.randint(-3, 3)
        
        return max(5, min(30, duration))
    
    def _calculate_star_rating(
        self,
        side_a_rating: float,
        side_b_rating: float,
        importance: MatchImportance,
        card_position: int
    ) -> float:
        """
        Calculate match star rating (0.0 - 5.0 stars).
        Based on wrestler quality and match importance.
        """
        
        # Average wrestler quality
        avg_rating = (side_a_rating + side_b_rating) / 2
        
        # Base stars from quality (0-100 → 0-4.5 stars)
        base_stars = (avg_rating / 100) * 4.5
        
        # Importance bonus
        if importance == MatchImportance.HIGH_DRAMA:
            base_stars += 0.3
        elif card_position >= 6:  # Main event area
            base_stars += 0.2
        
        # Random variance ±0.25
        stars = base_stars + random.uniform(-0.25, 0.25)
        
        # Clamp to 0.0 - 5.0
        stars = max(0.0, min(5.0, stars))
        
        # Round to nearest 0.25
        return round(stars * 4) / 4
    
    def _generate_highlights(
        self,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        winner_side: str,
        finish_type: FinishType,
        duration: int
    ) -> List[MatchHighlight]:
        """
        Generate narrative highlights/beats for the match.
        """
        highlights = []
        
        side_a_name = side_a_wrestlers[0].name if side_a_wrestlers else "Side A"
        side_b_name = side_b_wrestlers[0].name if side_b_wrestlers else "Side B"
        
        # Opening
        highlights.append(MatchHighlight(
            timestamp="0:30",
            description=f"{side_a_name} and {side_b_name} lock up in the center of the ring.",
            highlight_type="opening"
        ))
        
        # Early offense
        early_aggressor = random.choice([side_a_name, side_b_name])
        highlights.append(MatchHighlight(
            timestamp=f"{random.randint(2, 4)}:{random.randint(10, 50):02d}",
            description=f"{early_aggressor} takes control with a series of strikes and power moves.",
            highlight_type="offense"
        ))
        
        # Momentum shift
        other_wrestler = side_b_name if early_aggressor == side_a_name else side_a_name
        highlights.append(MatchHighlight(
            timestamp=f"{duration // 2}:{random.randint(0, 59):02d}",
            description=f"{other_wrestler} counters and shifts momentum with a big signature move!",
            highlight_type="comeback"
        ))
        
        # Near-fall (if match is good quality)
        if duration > 12:
            highlights.append(MatchHighlight(
                timestamp=f"{duration - 3}:{random.randint(0, 59):02d}",
                description=f"NEAR FALL! {random.choice([side_a_name, side_b_name])} barely kicks out at 2.9!",
                highlight_type="nearfall"
            ))
        
        # Finish
        winner_name = side_a_name if winner_side == 'side_a' else side_b_name
        finish_descriptions = {
            FinishType.CLEAN_PIN: f"{winner_name} hits their finisher and gets the 1-2-3!",
            FinishType.SUBMISSION: f"{winner_name} locks in a submission hold and gets the tap out!",
            FinishType.CHEATING: f"{winner_name} uses the ropes for leverage and steals the pin!",
            FinishType.ROLLUP: f"{winner_name} catches their opponent with a surprise rollup!",
            FinishType.DQ: f"The referee calls for the bell after blatant rule-breaking!",
            FinishType.COUNTOUT: f"{winner_name} wins as their opponent can't answer the 10-count!",
            FinishType.NO_CONTEST: f"The match breaks down into chaos - it's a no contest!"
        }
        
        highlights.append(MatchHighlight(
            timestamp=f"{duration}:00",
            description=finish_descriptions.get(finish_type, f"{winner_name} wins!"),
            highlight_type="finish"
        ))
        
        return highlights
    
    def _generate_highlights_with_crowd(
        self,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        winner_side: str,
        finish_type: FinishType,
        duration: int,
        crowd_tracker
    ) -> List[MatchHighlight]:
        """
        Generate highlights with crowd reactions tracked.
        
        STEP 14: Integrates crowd heat system.
        """
        
        highlights = []
        
        side_a_name = side_a_wrestlers[0].name if side_a_wrestlers else "Side A"
        side_b_name = side_b_wrestlers[0].name if side_b_wrestlers else "Side B"
        
        # Opening (crowd already tracked in main method)
        highlights.append(MatchHighlight(
            timestamp="0:30",
            description=f"{side_a_name} and {side_b_name} lock up in the center of the ring.",
            highlight_type="opening"
        ))
        
        # Early offense
        early_aggressor = random.choice([side_a_name, side_b_name])
        crowd_tracker.react_to_moment('big_move', [early_aggressor])
        highlights.append(MatchHighlight(
            timestamp=f"{random.randint(2, 4)}:{random.randint(10, 50):02d}",
            description=f"{early_aggressor} takes control with a series of strikes and power moves.",
            highlight_type="offense"
        ))
        
        # Momentum shift
        other_wrestler = side_b_name if early_aggressor == side_a_name else side_a_name
        crowd_tracker.react_to_moment('comeback', [other_wrestler])
        highlights.append(MatchHighlight(
            timestamp=f"{duration // 2}:{random.randint(0, 59):02d}",
            description=f"{other_wrestler} counters and shifts momentum with a big signature move!",
            highlight_type="comeback"
        ))
        
        # Near-fall (if match is good quality)
        if duration > 12:
            near_fall_wrestler = random.choice([side_a_name, side_b_name])
            crowd_tracker.react_to_moment('nearfall', [near_fall_wrestler])
            highlights.append(MatchHighlight(
                timestamp=f"{duration - 3}:{random.randint(0, 59):02d}",
                description=f"NEAR FALL! {near_fall_wrestler} barely kicks out at 2.9!",
                highlight_type="nearfall"
            ))
        
        # Finish
        winner_name = side_a_name if winner_side == 'side_a' else side_b_name
        crowd_tracker.react_to_moment('finish', [winner_name])
        
        finish_descriptions = {
            FinishType.CLEAN_PIN: f"{winner_name} hits their finisher and gets the 1-2-3!",
            FinishType.SUBMISSION: f"{winner_name} locks in a submission hold and gets the tap out!",
            FinishType.CHEATING: f"{winner_name} uses the ropes for leverage and steals the pin!",
            FinishType.ROLLUP: f"{winner_name} catches their opponent with a surprise rollup!",
            FinishType.DQ: f"The referee calls for the bell after blatant rule-breaking!",
            FinishType.COUNTOUT: f"{winner_name} wins as their opponent can't answer the 10-count!",
            FinishType.NO_CONTEST: f"The match breaks down into chaos - it's a no contest!"
        }
        
        highlights.append(MatchHighlight(
            timestamp=f"{duration}:00",
            description=finish_descriptions.get(finish_type, f"{winner_name} wins!"),
            highlight_type="finish"
        ))
        
        return highlights
    
    def _detect_upset(
        self,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        winner_side: str,
        side_a_rating: float,
        side_b_rating: float
    ) -> bool:
        """
        Detect if this was a major upset.
        Upsets occur when a significantly weaker wrestler/team wins.
        """
        
        winners = side_a_wrestlers if winner_side == 'side_a' else side_b_wrestlers
        losers = side_b_wrestlers if winner_side == 'side_a' else side_a_wrestlers
        
        if not winners or not losers:
            return False
        
        winner = winners[0]
        loser = losers[0]
        
        # Popularity difference check
        pop_diff = loser.popularity - winner.popularity
        
        # Role difference check
        role_hierarchy = {
            'Jobber': 1,
            'Lower Midcard': 2,
            'Midcard': 3,
            'Upper Midcard': 4,
            'Main Event': 5
        }
        
        winner_role_rank = role_hierarchy.get(winner.role, 3)
        loser_role_rank = role_hierarchy.get(loser.role, 3)
        role_diff = loser_role_rank - winner_role_rank
        
        # Rating difference
        rating_diff = side_b_rating - side_a_rating if winner_side == 'side_a' else side_a_rating - side_b_rating
        
        # Upset if:
        # - Popularity gap > 20 AND
        # - Role difference >= 2 (e.g., Jobber beats Main Event) AND
        # - Rating difference > 15
        if pop_diff > 20 and role_diff >= 2 and rating_diff > 15:
            return True
        
        return False
    
    def _generate_summary(
        self,
        match_draft: MatchDraft,
        winner_names: List[str],
        loser_names: List[str],
        finish_type: FinishType
    ) -> str:
        """Generate a brief match summary"""
        if not winner_names:
            return "The match ended in a no contest."
        
        winner_str = " & ".join(winner_names)
        loser_str = " & ".join(loser_names) if loser_names else "the field"
        
        finish_desc = {
            FinishType.CLEAN_PIN: "with a clean pinfall",
            FinishType.SUBMISSION: "by submission",
            FinishType.CHEATING: "with help from underhanded tactics",
            FinishType.ROLLUP: "with a surprise rollup",
            FinishType.DQ: "by disqualification",
            FinishType.COUNTOUT: "by countout"
        }
        
        desc = finish_desc.get(finish_type, "")
        
        if match_draft.is_title_match:
            return f"{winner_str} defeated {loser_str} {desc} in a {match_draft.title_name} match."
        else:
            return f"{winner_str} defeated {loser_str} {desc}."


# Global simulator instance
match_simulator = MatchSimulator()
