"""
AI Creative Director
Rules-based booking system that generates show cards.
Considers feuds, titles, brand rosters, and upcoming PPVs.

STEP 14 ENHANCEMENTS:
✅ Multi-competitor matches for major shows
✅ Referee assignments
✅ Wrestler protection logic
✅ Roster rotation management
✅ Special match type selection
✅ Crowd heat consideration

STEP 16 ENHANCEMENTS:
✅ Integrates storyline-generated segments into show cards
✅ Passes universe_state for storyline checking

STEP 25 ENHANCEMENTS:
✅ Checks for overdue title defenses
✅ Prioritizes overdue defenses in card generation
✅ Creates "ducking challenger" storylines
"""

import random
from typing import List, Optional, Tuple
from models.wrestler import Wrestler
from models.championship import Championship
from models.feud import Feud, FeudManager
from models.match import MatchDraft, MatchParticipant, BookingBias, MatchImportance
from models.show import ShowDraft
from models.calendar import ScheduledShow

# STEP 14: Import new systems
from models.referee import referee_pool
from creative.protection import protection_manager
from creative.rotation import rotation_manager
from creative.special_matches import special_match_selector
from creative.storylines import storyline_engine

from creative.reign_goal_awareness import (
    should_extend_reign,
    get_ideal_title_loss_timing,
    get_wrestlers_owed_title_shots,
    adjust_booking_bias_for_reign_goals
)


class AICreativeDirector:
    """
    Rules-based AI that generates show cards.
    
    Booking Philosophy:
    1. Push active feuds (especially hot ones)
    2. Schedule title defenses appropriately
    3. Build towards upcoming PPVs
    4. Maintain match freshness (avoid repeats)
    5. Give rising stars opportunities
    6. Protect main eventers (STEP 14)
    7. Rotate roster fairly (STEP 14)
    8. Book multi-competitor matches for variety at PPVs (STEP 14)
    9. Assign appropriate referees (STEP 14)
    10. Select special match types for feuds (STEP 14)
    11. Include storyline-generated segments (STEP 16)
    12. Prioritize overdue title defenses (STEP 25)
    """
    
    def __init__(self):
        self.recent_matches: List[Tuple[str, str]] = []  # Track recent matchups
        self.max_recent_history = 20  # Remember last 20 matches
    
    def generate_show_card(
        self,
        scheduled_show: ScheduledShow,
        brand_roster: List[Wrestler],
        all_wrestlers: List[Wrestler],
        brand_titles: List[Championship],
        all_titles: List[Championship],
        active_feuds: List[Feud],
        feud_manager: FeudManager,
        upcoming_ppvs: List[ScheduledShow],
        universe_state=None  # STEP 16: Added universe_state parameter
    ) -> ShowDraft:
        """
        Main entry point: Generate a complete show card.
        
        STEP 14: Now uses protection, rotation, and special match systems.
        STEP 16: Now integrates storyline segments.
        STEP 25: Now prioritizes overdue title defenses.
        """
        
        print(f"\n{'='*60}")
        print(f"🎬 AI DIRECTOR: Booking {scheduled_show.name}")
        print(f"   Brand: {scheduled_show.brand}")
        print(f"   Type: {scheduled_show.show_type.upper()}")
        print(f"   Year {scheduled_show.year}, Week {scheduled_show.week}")
        print(f"{'='*60}\n")
        
        # STEP 14: Update rotation manager with current time
        rotation_manager.update_time(scheduled_show.year, scheduled_show.week)
        
        show_draft = ShowDraft(
            show_id=scheduled_show.show_id,
            show_name=scheduled_show.name,
            brand=scheduled_show.brand,
            show_type=scheduled_show.show_type,
            is_ppv=scheduled_show.is_ppv,
            year=scheduled_show.year,
            week=scheduled_show.week
        )
        
        # STEP 14: Get underutilized wrestlers
        underutilized = rotation_manager.get_underutilized_wrestlers(brand_roster, weeks_threshold=2)
        print(f"📊 Roster Analysis:")
        print(f"   - Total available: {len(brand_roster)}")
        print(f"   - Underutilized: {len(underutilized)}")
        
        if underutilized:
            print(f"   - Priority bookings: {', '.join([w.name for w, _ in underutilized[:5]])}")
        
        # STEP 25: Check for overdue title defenses
        overdue_defenses = []
        for title in brand_titles:
            if title.is_vacant:
                continue
            
            status = title.get_defense_status(
                scheduled_show.year,
                scheduled_show.week
            )
            
            # Prioritize overdue or high urgency defenses
            if status['is_overdue'] or status['urgency_level'] >= 2:
                overdue_defenses.append({
                    'title': title,
                    'status': status,
                    'urgency': status['urgency_level']
                })
        
        # Sort by urgency
        overdue_defenses.sort(key=lambda x: x['urgency'], reverse=True)
        
        print(f"   📊 Defense Status:")
        print(f"      - {len(overdue_defenses)} titles need defenses")
        for defense in overdue_defenses[:3]:  # Show top 3
            print(f"      - {defense['title'].name}: {defense['status']['urgency_label']} ({defense['status']['days_since_defense']} days)")
        
        # Filter available wrestlers (not injured, not fatigued)
        available = [w for w in brand_roster if w.can_compete and w.fatigue < 80]
        
        # STEP 14: Prioritize underutilized wrestlers
        priority_wrestlers = rotation_manager.prioritize_for_booking(available, max_count=15)
        
        # Determine card size based on show type
        if scheduled_show.is_ppv:
            if scheduled_show.tier == 'major':
                target_matches = 8  # Major PPV: 8 matches
            else:
                target_matches = 6  # Minor PPV: 6 matches
        else:
            target_matches = 5  # Weekly TV: 5 matches
        
        card_position = 1
        booked_wrestlers = set()
        
        # STEP 25: Prioritize overdue title defenses
        if overdue_defenses:
            print(f"\n   🚨 OVERDUE DEFENSES - Prioritizing title matches")
            
            for defense_info in overdue_defenses[:2]:  # Max 2 overdue defenses per show
                title = defense_info['title']
                champion = None
                
                # Find champion in available wrestlers
                if universe_state:
                    champion = universe_state.get_wrestler_by_id(title.effective_champion_id)
                
                if not champion or not champion.can_compete:
                    print(f"      ⚠️  Champion for {title.name} not available")
                    continue
                
                # Find suitable challenger
                available_challengers = [
                    w for w in available
                    if w.id != champion.id
                    and w.can_compete
                    and w.role in ['Main Event', 'Upper Midcard', 'Midcard']
                    and w.id not in booked_wrestlers
                ]
                
                if not available_challengers:
                    print(f"      ⚠️  No challengers available for {title.name}")
                    continue
                
                # Pick top challenger by popularity
                challenger = max(available_challengers, key=lambda w: w.popularity)
                
                # Create title match
                match = MatchDraft(
                    match_id=f"title_defense_{title.id}_{scheduled_show.show_id}",
                    side_a=MatchParticipant(
                        wrestler_ids=[champion.id],
                        wrestler_names=[champion.name],
                        is_tag_team=False
                    ),
                    side_b=MatchParticipant(
                        wrestler_ids=[challenger.id],
                        wrestler_names=[challenger.name],
                        is_tag_team=False
                    ),
                    match_type='singles',
                    is_title_match=True,
                    title_id=title.id,
                    title_name=title.name,
                    card_position=target_matches - len(show_draft.matches),  # High card position
                    booking_bias=BookingBias.SLIGHT_A,  # Favor champion
                    importance=MatchImportance.HIGH_DRAMA
                )
                
                # STEP 14: Assign referee
                referee = referee_pool.get_referee_for_match('high_drama', is_main_event=True)
                match.referee_id = referee.ref_id
                
                show_draft.add_match(match)
                booked_wrestlers.add(champion.id)
                booked_wrestlers.add(challenger.id)
                
                print(f"      ✅ Added OVERDUE defense: {champion.name} (c) vs {challenger.name} for {title.name}")
                card_position += 1
        
        # STEP 14: Special handling for Rumble Royale
        if scheduled_show.name == 'Rumble Royale' and len(show_draft.matches) == 0:
            print("\n👑 BOOKING ROYAL RUMBLE MATCH")
            rumble_match = self._book_royal_rumble(
                scheduled_show,
                available,
                card_position=target_matches
            )
            if rumble_match:
                show_draft.add_match(rumble_match)
                for wid in rumble_match.side_a.wrestler_ids:
                    booked_wrestlers.add(wid)
                card_position += 1
        elif len(show_draft.matches) == 0:
            # STEP 1: Book the main event (if no overdue defenses took main event slot)
            print("\n🏆 BOOKING MAIN EVENT")
            main_event = self._book_main_event(
                scheduled_show,
                available,
                brand_titles,
                all_titles,
                active_feuds,
                upcoming_ppvs,
                card_position=target_matches,
                universe_state=universe_state,
            )
            
            if main_event:
                show_draft.add_match(main_event)
                for wid in main_event.side_a.wrestler_ids + main_event.side_b.wrestler_ids:
                    booked_wrestlers.add(wid)
                print(f"   ✅ Main Event: {' vs '.join(main_event.side_a.wrestler_names + main_event.side_b.wrestler_names)}")
                card_position += 1
        
        # STEP 2: Book feature matches (feuds, titles, rising stars)
        feature_count = 2 if scheduled_show.is_ppv else 1
        
        print(f"\n⭐ BOOKING {feature_count} FEATURE MATCH(ES)")
        for i in range(feature_count):
            if len(show_draft.matches) >= target_matches:
                break
                
            feature_match = self._book_feature_match(
                scheduled_show,
                available,
                brand_titles,
                all_titles,
                active_feuds,
                booked_wrestlers,
                card_position,
                priority_wrestlers  # STEP 14: Pass priority list
            )
            
            if feature_match:
                show_draft.add_match(feature_match)
                for wid in feature_match.side_a.wrestler_ids + feature_match.side_b.wrestler_ids:
                    booked_wrestlers.add(wid)
                print(f"   ✅ Feature #{i+1}: {' vs '.join(feature_match.side_a.wrestler_names + feature_match.side_b.wrestler_names)}")
                card_position += 1
        
        # STEP 14: For PPVs, occasionally book a multi-competitor match
        if scheduled_show.is_ppv and len(show_draft.matches) < target_matches:
            if random.random() < 0.4:  # 40% chance
                print(f"\n🔀 BOOKING MULTI-COMPETITOR MATCH")
                multi_match = self._book_multi_competitor_match(
                    scheduled_show,
                    available,
                    brand_titles,
                    booked_wrestlers,
                    card_position
                )
                
                if multi_match:
                    show_draft.add_match(multi_match)
                    for wid in multi_match.side_a.wrestler_ids + multi_match.side_b.wrestler_ids:
                        booked_wrestlers.add(wid)
                    print(f"   ✅ {multi_match.match_type.upper()}: {len(multi_match.side_a.wrestler_ids)} competitors")
                    card_position += 1
        
        # STEP 3: Fill rest of card with solid matches
        remaining = target_matches - len(show_draft.matches)
        if remaining > 0:
            print(f"\n📝 FILLING REMAINING {remaining} MATCH(ES)")
            
        while len(show_draft.matches) < target_matches:
            filler = self._book_filler_match(
                available,
                booked_wrestlers,
                card_position,
                priority_wrestlers  # STEP 14: Pass priority list
            )
            
            if filler:
                show_draft.add_match(filler)
                for wid in filler.side_a.wrestler_ids + filler.side_b.wrestler_ids:
                    booked_wrestlers.add(wid)
                print(f"   ✅ Match #{card_position}: {' vs '.join(filler.side_a.wrestler_names + filler.side_b.wrestler_names)}")
                card_position += 1
            else:
                print(f"   ⚠️  Unable to book more matches (ran out of available wrestlers)")
                break  # Can't book more matches
        
        print(f"\n✅ CARD COMPLETE: {len(show_draft.matches)} matches booked")
        
        # STEP 16: Add storyline segments
        if universe_state:
            self._add_storyline_segments(show_draft, universe_state)
        
        print(f"{'='*60}\n")
        
        return show_draft
    
    # ========================================================================
    # STEP 14: MULTI-COMPETITOR MATCH BOOKING
    # ========================================================================
    
    def _book_royal_rumble(
        self,
        show: ScheduledShow,
        available: List[Wrestler],
        card_position: int
    ) -> Optional[MatchDraft]:
        """
        Book a Royal Rumble match (30 participants).
        This is the main event for Rumble Royale PPV.
        """
        
        if len(available) < 30:
            print(f"   ⚠️  Not enough wrestlers for Royal Rumble (need 30, have {len(available)})")
            return None
        
        # Pick 30 wrestlers (mix of all roles for drama)
        participants = random.sample(available, 30)
        
        # STEP 14: Assign referee
        referee = referee_pool.get_referee_for_match('high_drama', is_main_event=True)
        
        match = MatchDraft(
            match_id=f"rumble_{show.show_id}",
            side_a=MatchParticipant(
                wrestler_ids=[w.id for w in participants],
                wrestler_names=[w.name for w in participants],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type='rumble',
            is_title_match=False,
            title_id=None,
            title_name=None,
            card_position=card_position,
            booking_bias=BookingBias.EVEN,
            importance=MatchImportance.HIGH_DRAMA,
            feud_id=None,
            stipulation='Royal Rumble Match',
            referee_id=referee.ref_id  # STEP 14
        )
        
        print(f"   ✅ Royal Rumble booked with 30 participants")
        print(f"   🏁 Referee: {referee.name}")
        
        return match
    
    def _book_multi_competitor_match(
        self,
        show: ScheduledShow,
        available: List[Wrestler],
        brand_titles: List[Championship],
        booked: set,
        card_position: int
    ) -> Optional[MatchDraft]:
        """
        Book a triple threat or fatal 4-way match.
        Used to add variety to PPV cards.
        """
        
        available_unbooked = [w for w in available if w.id not in booked]
        
        # Need at least 3 wrestlers
        if len(available_unbooked) < 3:
            return None
        
        # Decide match type (60% triple threat, 40% fatal 4-way)
        is_fatal_4way = random.random() < 0.4 and len(available_unbooked) >= 4
        
        match_type = 'fatal_4way' if is_fatal_4way else 'triple_threat'
        num_competitors = 4 if is_fatal_4way else 3
        
        # Pick competitors (prefer upper/midcard)
        candidates = [
            w for w in available_unbooked 
            if w.role in ['Main Event', 'Upper Midcard', 'Midcard']
        ]
        
        if len(candidates) < num_competitors:
            candidates = available_unbooked
        
        if len(candidates) < num_competitors:
            return None
        
        competitors = random.sample(candidates, num_competitors)
        
        # 30% chance this is a title match
        is_title_match = random.random() < 0.3
        title = None
        
        if is_title_match:
            # Pick a title that one of the competitors holds
            for competitor in competitors:
                for t in brand_titles:
                    if t.current_holder_id == competitor.id:
                        title = t
                        break
                if title:
                    break
        
        # STEP 14: Assign referee
        referee = referee_pool.get_referee_for_match('normal', is_main_event=False)
        
        return MatchDraft(
            match_id=f"{match_type}_{show.show_id}_{card_position}",
            side_a=MatchParticipant(
                wrestler_ids=[w.id for w in competitors],
                wrestler_names=[w.name for w in competitors],
                is_tag_team=False
            ),
            side_b=MatchParticipant(
                wrestler_ids=[],
                wrestler_names=[],
                is_tag_team=False
            ),
            match_type=match_type,
            is_title_match=is_title_match,
            title_id=title.id if title else None,
            title_name=title.name if title else None,
            card_position=card_position,
            booking_bias=BookingBias.EVEN,  # Fair fight in multi-matches
            importance=MatchImportance.NORMAL,
            feud_id=None,
            referee_id=referee.ref_id  # STEP 14
        )
    
    # ========================================================================
    # ORIGINAL BOOKING METHODS (Enhanced with STEP 14 & STEP 25 systems)
    # ========================================================================
    
    def _book_main_event(
        self,
        show: ScheduledShow,
        available: List[Wrestler],
        brand_titles: List[Championship],
        all_titles: List[Championship],
        feuds: List[Feud],
        upcoming_ppvs: List[ScheduledShow],
        card_position: int,
        universe_state=None,
    ) -> Optional[MatchDraft]:
        """Book the main event based on show type and circumstances"""
        
        # Major PPV main events
        if show.is_ppv and show.tier == 'major':
            return self._book_major_ppv_main_event(show, available, brand_titles, all_titles, feuds, card_position, universe_state)
        
        # Minor PPV main events
        elif show.is_ppv:
            return self._book_minor_ppv_main_event(show, available, brand_titles, all_titles, feuds, card_position)
        
        # Weekly TV main events
        else:
            return self._book_weekly_main_event(show, available, brand_titles, feuds, card_position)
    
    def _book_major_ppv_main_event(
        self,
        show: ScheduledShow,
        available: List[Wrestler],
        brand_titles: List[Championship],
        all_titles: List[Championship],
        feuds: List[Feud],
        card_position: int,
        universe_state=None,
    ) -> Optional[MatchDraft]:
        """Book main event for major PPVs (Victory Dome, Summer Slamfest, etc.)"""
        
        # Priority 1: Hottest feud for the top title
        world_title = self._get_world_title(brand_titles, all_titles, show.brand)
        
        if world_title and not world_title.is_vacant:
            champion = self._find_wrestler_by_id(world_title.current_holder_id, available)
            
            if champion:
                # Check for hot feud involving champion
                champion_feuds = [f for f in feuds if champion.id in f.participant_ids and f.intensity >= 70]
                
                if champion_feuds:
                    hottest = max(champion_feuds, key=lambda f: f.intensity)
                    opponent_id = [pid for pid in hottest.participant_ids if pid != champion.id][0]
                    opponent = self._find_wrestler_by_id(opponent_id, available)
                    
                    if opponent:
                        return self._create_match(
                            [champion], [opponent],
                            is_title=True,
                            title=world_title,
                            feud=hottest,
                            card_position=card_position,
                            importance=MatchImportance.HIGH_DRAMA,
                            booking_bias=BookingBias.SLIGHT_A,  # Slight bias to champion
                            show=show  # STEP 14: Pass show for special match selection
                        )
                
                
                # No hot feud, book top contender
                top_contender = self._get_top_contender(available, champion, show.brand)
                if top_contender:
                    # STEP 30: Check reign goals before setting booking bias
                    current_reign_days = world_title.get_current_reign_length(
                        show.year, show.week
                    )
                    
                    base_bias = BookingBias.SLIGHT_A
                    
                    # Adjust bias based on reign goals
                    adjusted_bias_str = adjust_booking_bias_for_reign_goals(
                        universe_state.db if hasattr(universe_state, 'db') else None,
                        champion.id,
                        world_title.id,
                        current_reign_days,
                        'Slight Champion'
                    )
                    
                    # Convert string back to BookingBias enum
                    bias_map = {
                        'Strong Champion': BookingBias.STRONG_A,
                        'Slight Champion': BookingBias.SLIGHT_A,
                        'Even': BookingBias.EVEN,
                        'Slight Challenger': BookingBias.SLIGHT_B,
                        'Strong Challenger': BookingBias.STRONG_B
                    }
                    booking_bias = bias_map.get(adjusted_bias_str, BookingBias.SLIGHT_A)
                    
                    return self._create_match(
                        [champion], [top_contender],
                        is_title=True,
                        title=world_title,
                        card_position=card_position,
                        importance=MatchImportance.HIGH_DRAMA,
                        booking_bias=booking_bias,  # STEP 30: Use adjusted bias
                        show=show
                    )
        
        # Priority 2: Hottest non-title feud
        hot_feuds = [f for f in feuds if f.intensity >= 80 and not f.title_id]
        if hot_feuds:
            hottest = max(hot_feuds, key=lambda f: f.intensity)
            return self._book_feud_match(hottest, available, card_position, MatchImportance.HIGH_DRAMA, show)
        
        # Fallback: Best available singles match
        return self._book_dream_match(available, card_position, show)
    
    def _book_minor_ppv_main_event(
        self,
        show: ScheduledShow,
        available: List[Wrestler],
        brand_titles: List[Championship],
        all_titles: List[Championship],
        feuds: List[Feud],
        card_position: int
    ) -> Optional[MatchDraft]:
        """Book main event for minor PPVs"""
        
        # Check for hot feuds first
        hot_feuds = [f for f in feuds if f.intensity >= 60]
        
        if hot_feuds:
            hottest = max(hot_feuds, key=lambda f: f.intensity)
            return self._book_feud_match(hottest, available, card_position, MatchImportance.HIGH_DRAMA, show)
        
        # Otherwise, title match
        top_title = self._get_top_title(brand_titles, show.brand)
        if top_title and not top_title.is_vacant:
            champion = self._find_wrestler_by_id(top_title.current_holder_id, available)
            if champion:
                contender = self._get_top_contender(available, champion, show.brand)
                if contender:
                    return self._create_match(
                        [champion], [contender],
                        is_title=True,
                        title=top_title,
                        card_position=card_position,
                        importance=MatchImportance.HIGH_DRAMA,
                        booking_bias=BookingBias.EVEN,
                        show=show
                    )
        
        # Fallback
        return self._book_dream_match(available, card_position, show)
    
    def _book_weekly_main_event(
        self,
        show: ScheduledShow,
        available: List[Wrestler],
        brand_titles: List[Championship],
        feuds: List[Feud],
        card_position: int
    ) -> Optional[MatchDraft]:
        """Book main event for weekly TV"""
        
        # Priority 1: Active feud
        active_feuds = [f for f in feuds if f.intensity >= 40]
        
        if active_feuds:
            # Pick a random active feud to keep variety
            feud = random.choice(active_feuds)
            return self._book_feud_match(feud, available, card_position, MatchImportance.NORMAL, show)
        
        # Priority 2: #1 contender match
        top_title = self._get_top_title(brand_titles, show.brand)
        if top_title:
            contenders = self._get_contenders(available, show.brand, exclude_champion=True)
            if len(contenders) >= 2:
                return self._create_match(
                    [contenders[0]], [contenders[1]],
                    card_position=card_position,
                    importance=MatchImportance.NORMAL,
                    booking_bias=BookingBias.EVEN,
                    show=show
                )
        
        # Fallback: Main eventers clash
        main_eventers = [w for w in available if w.role == 'Main Event']
        if len(main_eventers) >= 2:
            pair = random.sample(main_eventers, 2)
            return self._create_match(
                [pair[0]], [pair[1]],
                card_position=card_position,
                importance=MatchImportance.NORMAL,
                booking_bias=BookingBias.EVEN,
                show=show
            )
        
        return None
    
    def _book_feature_match(
        self,
        show: ScheduledShow,
        available: List[Wrestler],
        brand_titles: List[Championship],
        all_titles: List[Championship],
        feuds: List[Feud],
        booked: set,
        card_position: int,
        priority_wrestlers: List[Wrestler] = None  # STEP 14
    ) -> Optional[MatchDraft]:
        """Book a feature match (not main event, but important)"""
        
        available_unbooked = [w for w in available if w.id not in booked]
        
        # Priority 1: Secondary title defense
        secondary_titles = [t for t in brand_titles if t.title_type in ['Secondary', 'Midcard'] and not t.is_vacant]
        
        for title in secondary_titles:
            champion = self._find_wrestler_by_id(title.current_holder_id, available_unbooked)
            if champion:
                contender = self._get_top_contender(available_unbooked, champion, show.brand)
                if contender:
                    return self._create_match(
                        [champion], [contender],
                        is_title=True,
                        title=title,
                        card_position=card_position,
                        importance=MatchImportance.NORMAL,
                        booking_bias=BookingBias.SLIGHT_A,
                        show=show
                    )
        
        # Priority 2: Feud match
        unbooked_feuds = [f for f in feuds if not any(pid in booked for pid in f.participant_ids)]
        
        if unbooked_feuds:
            feud = random.choice(unbooked_feuds)
            return self._book_feud_match(feud, available_unbooked, card_position, MatchImportance.NORMAL, show)
        
        # STEP 14: Priority 3: Push underutilized rising stars
        if priority_wrestlers:
            for star in priority_wrestlers:
                if star.id not in booked and star.momentum > 10:
                    opponent = self._find_good_opponent(star, available_unbooked)
                    
                    if opponent and opponent.id not in booked:
                        return self._create_match(
                            [star], [opponent],
                            card_position=card_position,
                            importance=MatchImportance.NORMAL,
                            booking_bias=BookingBias.SLIGHT_A,  # Push the rising star
                            show=show
                        )
        
        # Priority 4: Push a rising star (original logic)
        rising_stars = [w for w in available_unbooked if w.role in ['Upper Midcard', 'Midcard'] and w.momentum > 10]
        
        if rising_stars:
            star = max(rising_stars, key=lambda w: w.momentum)
            opponent = self._find_good_opponent(star, available_unbooked)
            
            if opponent:
                return self._create_match(
                    [star], [opponent],
                    card_position=card_position,
                    importance=MatchImportance.NORMAL,
                    booking_bias=BookingBias.SLIGHT_A,
                    show=show
                )
        
        return None
    
    def _book_filler_match(
        self,
        available: List[Wrestler],
        booked: set,
        card_position: int,
        priority_wrestlers: List[Wrestler] = None  # STEP 14
    ) -> Optional[MatchDraft]:
        """Book a filler/undercard match"""
        
        available_unbooked = [w for w in available if w.id not in booked]
        
        if len(available_unbooked) < 2:
            return None
        
        # STEP 14: Prioritize underutilized wrestlers
        if priority_wrestlers:
            unbooked_priority = [w for w in priority_wrestlers if w.id not in booked]
            
            if len(unbooked_priority) >= 2:
                pair = random.sample(unbooked_priority, 2)
                return self._create_match(
                    [pair[0]], [pair[1]],
                    card_position=card_position,
                    importance=MatchImportance.NORMAL,
                    booking_bias=BookingBias.EVEN,
                    show=None
                )
        
        # Try to find a fresh matchup
        for _ in range(10):  # Try 10 times
            pair = random.sample(available_unbooked, 2)
            
            if not self._is_recent_matchup(pair[0].id, pair[1].id):
                return self._create_match(
                    [pair[0]], [pair[1]],
                    card_position=card_position,
                    importance=MatchImportance.NORMAL,
                    booking_bias=BookingBias.EVEN,
                    show=None
                )
        
        # If we can't find fresh, just book something
        pair = random.sample(available_unbooked, 2)
        return self._create_match(
            [pair[0]], [pair[1]],
            card_position=card_position,
            importance=MatchImportance.NORMAL,
            booking_bias=BookingBias.EVEN,
            show=None
        )
    
    def _book_feud_match(
        self,
        feud: Feud,
        available: List[Wrestler],
        card_position: int,
        importance: MatchImportance,
        show: ScheduledShow
    ) -> Optional[MatchDraft]:
        """Book a match for a specific feud"""
        
        if len(feud.participant_ids) != 2:
            return None  # Only singles for now
        
        w1 = self._find_wrestler_by_id(feud.participant_ids[0], available)
        w2 = self._find_wrestler_by_id(feud.participant_ids[1], available)
        
        if not w1 or not w2:
            return None
        
        # STEP 14: Check protection manager for booking bias
        should_force_w1_win, reason = protection_manager.should_wrestler_win(w1, w2, 'even')
        
        if should_force_w1_win:
            booking_bias = BookingBias.STRONG_A
            print(f"   🛡️  Protection: {w1.name} needs win ({reason})")
        else:
            # Determine booking bias based on series record
            wins1 = feud.wins_by_participant.get(w1.id, 0)
            wins2 = feud.wins_by_participant.get(w2.id, 0)
            
            if wins1 > wins2:
                booking_bias = BookingBias.SLIGHT_B  # Give underdog a chance
            elif wins2 > wins1:
                booking_bias = BookingBias.SLIGHT_A
            else:
                booking_bias = BookingBias.EVEN
        
        title = None
        if feud.title_id:
            # Find the title
            pass  # Title lookup would go here
        
        return self._create_match(
            [w1], [w2],
            is_title=False,
            title=title,
            feud=feud,
            card_position=card_position,
            importance=importance,
            booking_bias=booking_bias,
            show=show
        )
    
    def _book_dream_match(
        self,
        available: List[Wrestler],
        card_position: int,
        show: ScheduledShow
    ) -> Optional[MatchDraft]:
        """Book the best possible match from available wrestlers"""
        
        main_eventers = [w for w in available if w.role == 'Main Event']
        
        if len(main_eventers) >= 2:
            # Pick two highest-rated main eventers
            sorted_main = sorted(main_eventers, key=lambda w: w.overall_rating, reverse=True)
            return self._create_match(
                [sorted_main[0]], [sorted_main[1]],
                card_position=card_position,
                importance=MatchImportance.HIGH_DRAMA,
                booking_bias=BookingBias.EVEN,
                show=show
            )
        
        return None
    
    def _create_match(
        self,
        side_a: List[Wrestler],
        side_b: List[Wrestler],
        is_title: bool = False,
        title: Optional[Championship] = None,
        feud: Optional[Feud] = None,
        card_position: int = 1,
        importance: MatchImportance = MatchImportance.NORMAL,
        booking_bias: BookingBias = BookingBias.EVEN,
        show: Optional[ScheduledShow] = None  # STEP 14
    ) -> MatchDraft:
        """
        Helper to create a MatchDraft.
        
        STEP 14 ENHANCEMENTS:
        - Assigns referee based on match importance
        - Selects special match type if appropriate
        """
        
        side_a_ids = [w.id for w in side_a]
        side_a_names = [w.name for w in side_a]
        
        side_b_ids = [w.id for w in side_b]
        side_b_names = [w.name for w in side_b]
        
        match_id = f"match_{side_a_ids[0]}_vs_{side_b_ids[0]}"
        
        # Track this matchup
        if len(side_a_ids) == 1 and len(side_b_ids) == 1:
            self._add_recent_matchup(side_a_ids[0], side_b_ids[0])
        
        # STEP 14: Assign referee
        is_main_event = (card_position >= 7)
        referee = referee_pool.get_referee_for_match(importance.value, is_main_event=is_main_event)
        
        # STEP 14: Determine if special match type should be used
        special_match_type = None
        stipulation = None
        
        if show and show.is_ppv and feud:
            should_book_special, prob = special_match_selector.should_book_special_match(
                is_ppv=show.is_ppv,
                is_major_ppv=(show.tier == 'major'),
                feud_intensity=feud.intensity,
                is_title_match=is_title,
                card_position=card_position
            )
            
            if should_book_special:
                # Determine participant styles (simplified)
                participant_styles = []
                for w in side_a + side_b:
                    if w.speed > 75:
                        participant_styles.append('high_flyer')
                    elif w.brawling > 75:
                        participant_styles.append('brawler')
                    elif w.technical > 75:
                        participant_styles.append('technical')
                
                # Check if this is a feud blowoff
                is_blowoff = (feud.planned_payoff_show_id == show.show_id) if feud else False
                
                selected_type = special_match_selector.select_match_type(
                    feud_intensity=feud.intensity,
                    is_title_match=is_title,
                    participant_styles=participant_styles,
                    feud_type=feud.feud_type.value if feud else None,
                    is_blowoff=is_blowoff
                )
                
                special_match_type = selected_type.value
                stipulation = special_match_selector.get_match_description(selected_type)
                
                print(f"   🎭 Special Match: {special_match_type.upper().replace('_', ' ')}")
        
        return MatchDraft(
            match_id=match_id,
            side_a=MatchParticipant(side_a_ids, side_a_names, is_tag_team=len(side_a) > 1),
            side_b=MatchParticipant(side_b_ids, side_b_names, is_tag_team=len(side_b) > 1),
            match_type='singles' if len(side_a) == 1 and len(side_b) == 1 else 'tag',
            is_title_match=is_title,
            title_id=title.id if title else None,
            title_name=title.name if title else None,
            card_position=card_position,
            booking_bias=booking_bias,
            importance=importance,
            feud_id=feud.id if feud else None,
            stipulation=stipulation,  # STEP 14
            referee_id=referee.ref_id,  # STEP 14
            special_match_type=special_match_type  # STEP 14
        )
    
    # Helper methods (unchanged from original)
    
    def _get_world_title(self, brand_titles: List[Championship], all_titles: List[Championship], brand: str) -> Optional[Championship]:
        """Get the world/top title for a brand"""
        for title in brand_titles:
            if title.title_type == 'World':
                return title
        
        # Check cross-brand titles
        for title in all_titles:
            if title.assigned_brand == 'Cross-Brand' and title.title_type == 'World':
                return title
        
        return None
    
    def _get_top_title(self, brand_titles: List[Championship], brand: str) -> Optional[Championship]:
        """Get any top-tier title"""
        priority = ['World', 'Secondary', 'Midcard']
        
        for tier in priority:
            for title in brand_titles:
                if title.title_type == tier:
                    return title
        
        return brand_titles[0] if brand_titles else None
    
    def _find_wrestler_by_id(self, wrestler_id: str, wrestlers: List[Wrestler]) -> Optional[Wrestler]:
        """Find a wrestler in a list"""
        for w in wrestlers:
            if w.id == wrestler_id:
                return w
        return None
    
    def _get_top_contender(self, available: List[Wrestler], champion: Wrestler, brand: str) -> Optional[Wrestler]:
        """Find the best contender for a champion"""
        contenders = [w for w in available if w.id != champion.id and w.role in ['Main Event', 'Upper Midcard']]
        
        if not contenders:
            return None
        
        # Sort by combination of overall rating and momentum
        scored = [(w, w.overall_rating + w.momentum) for w in contenders]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored[0][0]
    
    def _get_contenders(self, available: List[Wrestler], brand: str, exclude_champion: bool = False) -> List[Wrestler]:
        """Get list of top contenders"""
        contenders = [w for w in available if w.role in ['Main Event', 'Upper Midcard']]
        
        scored = [(w, w.overall_rating + w.momentum) for w in contenders]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [w for w, score in scored]
    
    def _find_good_opponent(self, wrestler: Wrestler, available: List[Wrestler]) -> Optional[Wrestler]:
        """Find a good opponent for a wrestler"""
        # Prefer opponents in similar role tier
        role_tiers = {
            'Main Event': 5,
            'Upper Midcard': 4,
            'Midcard': 3,
            'Lower Midcard': 2,
            'Jobber': 1
        }
        
        wrestler_tier = role_tiers.get(wrestler.role, 3)
        
        candidates = [w for w in available if w.id != wrestler.id]
        
        # Score by role proximity and overall rating
        scored = []
        for w in candidates:
            tier = role_tiers.get(w.role, 3)
            tier_diff = abs(tier - wrestler_tier)
            score = w.overall_rating - (tier_diff * 10)
            scored.append((w, score))
        
        if not scored:
            return None
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]
    
    def _is_recent_matchup(self, w1_id: str, w2_id: str) -> bool:
        """Check if two wrestlers fought recently"""
        matchup = tuple(sorted([w1_id, w2_id]))
        return matchup in self.recent_matches
    
    def _add_recent_matchup(self, w1_id: str, w2_id: str):
        """Add a matchup to recent history"""
        matchup = tuple(sorted([w1_id, w2_id]))
        
        if matchup in self.recent_matches:
            self.recent_matches.remove(matchup)
        
        self.recent_matches.append(matchup)
        
        # Keep only recent history
        if len(self.recent_matches) > self.max_recent_history:
            self.recent_matches.pop(0)
    
    # ========================================================================
    # STEP 16: STORYLINE SEGMENT INTEGRATION
    # ========================================================================
    
    def _add_storyline_segments(self, show_draft: ShowDraft, universe_state):
        """Add segments from active storylines to the show"""
        try:
            # Get storyline segments for this show
            storyline_segments = storyline_engine.get_storyline_segments_for_show(
                show_draft.show_type,
                show_draft.brand,
                universe_state
            )
            
            if storyline_segments:
                print(f"\n📖 ADDING STORYLINE SEGMENTS")
                
                for segment in storyline_segments:
                    # Check if we have room for more segments
                    if show_draft.segments and len(show_draft.segments) >= 4:
                        print(f"   ⚠️ Segment limit reached, skipping remaining storyline segments")
                        break
                    
                    # Add to show draft
                    show_draft.add_segment(segment)
                    print(f"   ✅ Added storyline segment: {segment.segment_type}")
                
                print(f"   Total storyline segments added: {len(storyline_segments)}")
            
        except Exception as e:
            print(f"   ⚠️ Error adding storyline segments: {e}")
            import traceback
            traceback.print_exc()


# Global AI director instance
ai_director = AICreativeDirector()
