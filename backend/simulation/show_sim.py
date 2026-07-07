"""
Show Simulation Orchestrator
Simulates entire wrestling shows from start to finish.
Coordinates match simulation, segment simulation, stat updates, financial calculations, and history tracking.

STEP 14 ENHANCEMENTS:
✅ Records match results in protection manager
✅ Records match appearances in rotation manager
✅ Tracks wrestler booking records

STEP 15 ENHANCEMENTS:
✅ Simulates segments alongside matches
✅ Integrates promo battles and backstage segments
✅ Combined match + segment rating system
✅ Segment-driven feud creation and intensity changes
✅ Handles both AI-generated and frontend-created segments

STEP 16 ENHANCEMENTS:
✅ Checks for storyline triggers before each show
✅ Processes story beats during show week
✅ Saves storyline state after shows

STEP 25 ENHANCEMENTS:
✅ Records successful title defenses using match_draft.title_id
✅ Tracks defense count for championship prestige

STEP 30 ENHANCEMENTS:
✅ Evaluates reign satisfaction when champion loses title
✅ Creates reign goals when wrestler wins title

STEP 120 ENHANCEMENTS:
✅ Generates contract alerts after updating contract weeks
"""

import random
from typing import List, Dict, Any
from models.show import ShowDraft, ShowResult, SegmentResult
from models.match import MatchResult, FinishType
from models.wrestler import Wrestler
from models.championship import Championship
from simulation.match_sim import match_simulator
from economy.finance import finance_calculator
from creative.storylines import storyline_engine
from persistence.injury_db import save_return_angle


class ShowSimulator:
    """
    Orchestrates the simulation of an entire wrestling show.
    
    Process:
    1. Pre-show setup (calculate attendance, financials)
    2. STEP 16: Check for storyline triggers
    3. STEP 16: Process story beats for current week
    4. Simulate each match AND segment in card order
    5. Apply post-match effects (stats, injuries, title changes)
    6. Apply post-segment effects (feuds, momentum, popularity)
    7. STEP 14: Record results in protection/rotation managers
    8. STEP 25: Record title defenses
    9. Post-show processing (contracts, age checks, special events)
    10. STEP 120: Generate contract alerts
    11. STEP 16: Save storyline state
    12. Save results to database
    """
    
    def __init__(self):
        pass

    def _prepare_elimination_chamber_competitors(
        self,
        match_draft,
        side_a_wrestlers,
        side_b_wrestlers,
        universe_state,
        show_draft,
    ):
        if (match_draft.match_type or '').lower() != 'elimination_chamber':
            return side_a_wrestlers, side_b_wrestlers

        selected = []
        selected_ids = set()
        for wrestler in side_a_wrestlers + side_b_wrestlers:
            if wrestler and wrestler.id not in selected_ids:
                selected.append(wrestler)
                selected_ids.add(wrestler.id)

        if len(selected) < 6:
            gender = (match_draft.gender_division or '').lower()
            show_brand = getattr(show_draft, 'brand', '')
            cross_brand = show_brand == 'Cross-Brand'
            candidates = []

            for wrestler in universe_state.get_active_wrestlers():
                if wrestler.id in selected_ids:
                    continue
                if gender in ('male', 'female') and wrestler.gender.lower() != gender:
                    continue
                if not cross_brand and show_brand and wrestler.primary_brand != show_brand:
                    continue
                candidates.append(wrestler)

            candidates.sort(
                key=lambda wrestler: (
                    getattr(wrestler, 'overall_rating', 0),
                    getattr(wrestler, 'popularity', 0),
                ),
                reverse=True,
            )

            for wrestler in candidates:
                selected.append(wrestler)
                selected_ids.add(wrestler.id)
                if len(selected) == 6:
                    break

        if len(selected) < 6:
            raise ValueError(
                f"Elimination Chamber requires 6 wrestlers, got {len(selected)}"
            )

        selected = selected[:6]
        match_draft.side_a.wrestler_ids = [wrestler.id for wrestler in selected]
        match_draft.side_a.wrestler_names = [wrestler.name for wrestler in selected]
        match_draft.side_a.is_tag_team = False
        match_draft.side_b.wrestler_ids = []
        match_draft.side_b.wrestler_names = []
        match_draft.side_b.is_tag_team = False
        return selected, []
    
    def simulate_show(
        self,
        show_draft: ShowDraft,
        universe_state  # DatabaseUniverseState object
    ) -> ShowResult:
        """
        Main entry point: Simulate an entire show.
        
        Args:
            show_draft: The booked show card (matches + segments)
            universe_state: Current universe state with all wrestlers/titles/etc
        
        Returns:
            ShowResult with all match/segment results and show-level stats
        """
        
        print(f"\n{'='*60}")
        print(f"🎬 SIMULATING: {show_draft.show_name}")
        print(f"   Brand: {show_draft.brand} | Type: {show_draft.show_type}")
        print(f"   Year {show_draft.year}, Week {show_draft.week}")
        print(f"   Matches: {len(show_draft.matches)} | Segments: {len(show_draft.segments) if show_draft.segments else 0}")
        print(f"{'='*60}\n")
        
        # Create show result container
        show_result = ShowResult(
            show_id=show_draft.show_id,
            show_name=show_draft.show_name,
            brand=show_draft.brand,
            show_type=show_draft.show_type,
            year=show_draft.year,
            week=show_draft.week,
            is_ppv=show_draft.is_ppv
        )
        
        # ================================================================
        # STEP 16: CHECK FOR STORYLINE TRIGGERS
        # ================================================================
        
        print("🎭 Checking for storyline triggers...")
        
        try:
            triggered_storylines = storyline_engine.check_and_trigger_storylines(
                universe_state,
                show_draft.year,
                show_draft.week
            )
            
            if triggered_storylines:
                print(f"   ✅ {len(triggered_storylines)} storyline(s) triggered!")
                for storyline in triggered_storylines:
                    show_result.add_event(
                        'storyline_triggered',
                        f"🎭 STORYLINE BEGINS: {storyline.name}"
                    )
            else:
                print(f"   No storylines triggered this week")
        except Exception as e:
            print(f"   ⚠️ Error checking storyline triggers: {e}")
        
        # ================================================================
        # STEP 16: PROCESS STORY BEATS
        # ================================================================
        
        print("📖 Processing storyline beats...")
        
        try:
            story_beat_results = storyline_engine.process_current_week(
                universe_state,
                show_draft.year,
                show_draft.week
            )
            
            if story_beat_results:
                print(f"   ✅ {len(story_beat_results)} story beat(s) executed!")
                for beat_result in story_beat_results:
                    # Add story beat events to show
                    for effect in beat_result.get('effects', []):
                        show_result.add_event('storyline_beat', effect)
                    
                    # Check if storyline completed
                    if beat_result.get('storyline_completed'):
                        show_result.add_event(
                            'storyline_completed',
                            f"🎭 STORYLINE CONCLUDED: {beat_result['storyline_name']}"
                        )
            else:
                print(f"   No story beats this week")
        except Exception as e:
            print(f"   ⚠️ Error processing story beats: {e}")
        
        print()
        
        # ================================================================
        # PRE-SHOW: Financial Calculations
        # ================================================================
        
        print("💰 Calculating attendance and revenue...")
        
        # Get all wrestlers on the card
        wrestlers_on_card = self._get_wrestlers_on_card(show_draft, universe_state)
        
        brand_prestige = self._calculate_brand_prestige(show_draft.brand, universe_state)
        finance_projection = finance_calculator.project_show_finances(
            show_draft,
            wrestlers_on_card,
            brand_prestige=brand_prestige,
            current_balance=universe_state.balance,
            randomize=True,
        )

        show_result.total_attendance = finance_projection['projected_attendance']
        show_result.total_revenue = finance_projection['projected_total_revenue']
        show_result.total_payroll = finance_projection['expense_breakdown']['payroll']
        show_result.net_profit = finance_projection['projected_net_profit']
        show_result.revenue_breakdown = finance_projection['revenue_breakdown']
        show_result.expense_breakdown = finance_projection['expense_breakdown']
        show_result.profit_projection = finance_projection
        show_result.profit_warnings = finance_projection['warnings']
        show_result.profit_recommendations = finance_projection['recommendations']

        print(f"   Attendance: {show_result.total_attendance:,}")
        print(f"   Revenue: ${show_result.total_revenue:,}")
        print(f"   Payroll: ${show_result.total_payroll:,}")
        print(f"   Production: ${finance_projection['expense_breakdown']['production']:,}")
        print(f"   Venue: ${finance_projection['expense_breakdown']['venue']:,}")
        print(f"   Guaranteed Media: ${finance_projection['revenue_breakdown']['guaranteed_media_revenue']:,}")
        print(f"   Net: ${show_result.net_profit:,} {'📈' if show_result.net_profit >= 0 else '📉'}")
        print()
        
        # ================================================================
        # COMBINED CARD SIMULATION (MATCHES + SEGMENTS IN ORDER)
        # ================================================================
        
        print("🎪 Simulating show card in order...\n")
        
        # Get combined card order
        card_order = show_draft.get_card_order()
        
        total_star_rating = 0.0
        total_items = 0

        # ================================================================
        # STEP 63/64/72: PACING MANAGER + THEME SETUP
        # ================================================================

        pacing_manager = None
        theme_bonus_quality = 0.0
        theme_event_prefix = ""

        try:
            from models.show_config import ShowPacingManager, ShowTheme, SHOW_THEME_CONFIGS
            from simulation.show_production import show_theme_manager

            pacing_manager = ShowPacingManager(
                show_type=show_draft.show_type,
                brand=show_draft.brand,
            )

            # Determine theme and apply bonuses
            theme = show_theme_manager.determine_show_theme(
                week=show_draft.week,
                year=show_draft.year,
                show_name=show_draft.show_name,
                is_ppv=show_draft.is_ppv,
                brand=show_draft.brand,
            )
            theme_cfg = SHOW_THEME_CONFIGS.get(theme)
            if theme_cfg:
                theme_bonus_quality = theme_cfg.bonus_match_quality
                theme_event_prefix = theme_cfg.extra_event_log_prefix

                # Apply revenue and attendance bonuses
                if theme_cfg.bonus_attendance_pct > 0:
                    bonus_attendance = int(show_result.total_attendance * theme_cfg.bonus_attendance_pct)
                    show_result.total_attendance += bonus_attendance

                if theme_cfg.bonus_revenue_pct > 0:
                    bonus_revenue = int(show_result.total_revenue * theme_cfg.bonus_revenue_pct)
                    show_result.total_revenue += bonus_revenue
                    show_result.net_profit += bonus_revenue
                    universe_state.balance += bonus_revenue

                print(f"🎨 Show Theme: {theme_cfg.display_name}")
                if theme_bonus_quality > 0:
                    print(f"   Match Quality Bonus: +{theme_bonus_quality:.1f} stars")
                if theme_cfg.bonus_attendance_pct > 0:
                    print(f"   Attendance Bonus: +{theme_cfg.bonus_attendance_pct*100:.0f}%")
                if theme_event_prefix:
                    show_result.add_event('show_theme', f"{theme_event_prefix}: {show_draft.show_name}")
                print()
        except Exception as e:
            print(f"   ⚠️ Pacing/theme setup error (non-critical): {e}")
        
        for item_num, card_item in enumerate(card_order, 1):
            item_type = card_item['type']
            
            if item_type == 'match':
                # ========================================================
                # SIMULATE MATCH
                # ========================================================
                match_draft = card_item['item']
                
                # Build display name
                side_a_names = ' & '.join(match_draft.side_a.wrestler_names) if match_draft.side_a.wrestler_names else 'Side A'
                side_b_names = ' & '.join(match_draft.side_b.wrestler_names) if match_draft.side_b.wrestler_names else ''
                
                if side_b_names:
                    print(f"🥊 Match {item_num}: {side_a_names} vs {side_b_names}")
                else:
                    print(f"🥊 Match {item_num}: {match_draft.match_type.upper()} - {len(match_draft.side_a.wrestler_ids)} competitors")
                
                # Get wrestler objects
                side_a_wrestlers = [universe_state.get_wrestler_by_id(wid) for wid in match_draft.side_a.wrestler_ids]
                side_b_wrestlers = [universe_state.get_wrestler_by_id(wid) for wid in match_draft.side_b.wrestler_ids]
                
                # Filter out None (in case of missing wrestlers)
                side_a_wrestlers = [w for w in side_a_wrestlers if w]
                side_b_wrestlers = [w for w in side_b_wrestlers if w]

                side_a_wrestlers, side_b_wrestlers = self._prepare_elimination_chamber_competitors(
                    match_draft,
                    side_a_wrestlers,
                    side_b_wrestlers,
                    universe_state,
                    show_draft,
                )
                
                # Handle multi-man matches (all in side_a)
                if not side_b_wrestlers and side_a_wrestlers:
                    # This is a multi-man match (battle royal, etc)
                    side_b_wrestlers = []
                
                if not side_a_wrestlers:
                    print("   ⚠️  Skipping match - missing wrestlers")
                    continue
                
                # SIMULATE THE MATCH
                match_result = match_simulator.simulate_match(
                    match_draft,
                    side_a_wrestlers,
                    side_b_wrestlers,
                    universe_state=universe_state
                )
                
                print(f"   Winner: {' & '.join(match_result.winner_names)}")
                print(f"   Finish: {match_result.finish_type.value}")
                print(f"   Rating: {'⭐' * int(match_result.star_rating)} ({match_result.star_rating:.2f} stars)")
                
                # Show additional match info
                if hasattr(match_result, 'referee_name') and match_result.referee_name:
                    print(f"   Referee: {match_result.referee_name}")
                if hasattr(match_result, 'crowd_pacing_grade') and match_result.crowd_pacing_grade:
                    print(f"   Crowd: {match_result.crowd_pacing_grade} (Energy: {match_result.crowd_energy}/100)")
                if hasattr(match_result, 'special_match_type') and match_result.special_match_type:
                    print(f"   Special Match: {match_result.special_match_type.replace('_', ' ').upper()}")
                
                if match_result.is_upset:
                    print(f"   🚨 MAJOR UPSET!")
                
                if match_result.is_title_match:
                    print(f"   🏆 {match_result.title_name} Match")
                
                # Add to show result
                show_result.add_match_result(match_result)
                total_star_rating += match_result.star_rating
                total_items += 1

                # Step 63/64: Track pacing
                if pacing_manager:
                    try:
                        pacing_manager.record_item(
                            position=item_num,
                            item_type="match",
                            item_name=" vs ".join(match_result.winner_names + match_result.loser_names),
                            duration_minutes=getattr(match_result, 'duration_minutes', 10),
                            star_rating=match_result.star_rating,
                        )
                    except Exception:
                        pass

                # Step 72: Apply theme match quality bonus
                if theme_bonus_quality > 0:
                    match_result.star_rating = min(5.0, match_result.star_rating + theme_bonus_quality)
                
                # ========================================================
                # STEP 25: Record title defense
                # ========================================================
                if match_draft.is_title_match and not match_result.title_changed_hands:
                    championship = universe_state.get_championship_by_id(match_draft.title_id)
                    if championship:
                        championship.record_successful_defense(
                            year=show_draft.year,
                            week=show_draft.week,
                            show_id=show_draft.show_id
                        )
                        print(f"      📊 Recorded successful defense: {championship.name}")

                        # CRITICAL: Save and commit championship after defense
                        universe_state.save_championship(championship)
                        try:
                            universe_state.db.conn.commit()
                            print(f"      💾 Title defense committed to database")
                        except Exception as e:
                            print(f"      ⚠️ Error committing defense: {e}")
                
                # Apply post-match effects
                self._apply_match_effects(
                    match_result,
                    match_draft,
                    side_a_wrestlers,
                    side_b_wrestlers,
                    universe_state,
                    show_result
                )
                
                # Record in protection/rotation managers
                try:
                    from creative.protection import protection_manager
                    from creative.rotation import rotation_manager
                    
                    all_participants = match_result.side_a.wrestler_ids + match_result.side_b.wrestler_ids
                    
                    for wrestler_id in all_participants:
                        rotation_manager.record_match_appearance(
                            wrestler_id=wrestler_id,
                            card_position=match_result.card_position,
                            year=show_draft.year,
                            week=show_draft.week
                        )
                    
                    if match_result.winner == 'side_a':
                        for wrestler_id in match_result.side_a.wrestler_ids:
                            protection_manager.record_match_result(wrestler_id, won=True)
                        for wrestler_id in match_result.side_b.wrestler_ids:
                            protection_manager.record_match_result(wrestler_id, won=False)
                    elif match_result.winner == 'side_b':
                        for wrestler_id in match_result.side_b.wrestler_ids:
                            protection_manager.record_match_result(wrestler_id, won=True)
                        for wrestler_id in match_result.side_a.wrestler_ids:
                            protection_manager.record_match_result(wrestler_id, won=False)
                    else:
                        for wrestler_id in all_participants:
                            protection_manager.record_match_result(wrestler_id, won=False, was_draw=True)
                except ImportError:
                    pass
                
            elif item_type == 'segment':
                # ========================================================
                # SIMULATE SEGMENT (STEP 15)
                # ========================================================
                segment_draft = card_item['item']
                
                # Handle segment simulation with proper error handling
                segment_result = self._simulate_segment(
                    segment_draft, 
                    universe_state, 
                    show_result,
                    item_num
                )
                
                if segment_result:
                    # Add to show result
                    show_result.add_segment_result(segment_result)
                    total_star_rating += segment_result.segment_rating
                    total_items += 1

                    # Step 63: Track pacing for segments
                    if pacing_manager:
                        try:
                            seg_type = self._get_segment_type(segment_draft)
                            pacing_manager.record_item(
                                position=item_num,
                                item_type="segment",
                                item_name=seg_type,
                                duration_minutes=getattr(segment_draft, 'duration_minutes', 5),
                                star_rating=segment_result.segment_rating,
                                segment_type=seg_type,
                            )
                        except Exception:
                            pass
                    
                    # Apply post-segment effects
                    self._apply_segment_effects(
                        segment_result,
                        segment_draft,
                        universe_state,
                        show_result
                    )
            
            print()
        
        # ================================================================
        # POST-SHOW PROCESSING
        # ================================================================
        
        # Calculate overall show rating (combined matches + segments)
        if total_items > 0:
            show_result.overall_rating = total_star_rating / total_items
        
        # Calculate individual ratings
        show_result.calculate_ratings()

        # Step 63: Attach pacing report to show result
        if pacing_manager:
            try:
                pacing_report = pacing_manager.to_dict()
                show_result.add_event(
                    'pacing_report',
                    f"📊 Pacing Grade: {pacing_report['pacing_grade']} | "
                    f"Final Energy: {pacing_report['final_crowd_energy']} | "
                    f"Runtime: {pacing_report['elapsed_minutes']} min"
                )
                # Store on show result for API access
                show_result.pacing_report = pacing_report
                print(f"   Pacing Grade: {pacing_report['pacing_grade']}")
                print(f"   Final Crowd Energy: {pacing_report['final_crowd_energy']}/100")
                if pacing_report.get('is_overrunning'):
                    print(f"   ⚠️ SHOW OVERRAN by {pacing_report['elapsed_minutes'] - pacing_report['total_available_minutes']} minutes!")
                print()
            except Exception as e:
                print(f"   ⚠️ Pacing report error: {e}")
        
        print(f"📊 SHOW RATINGS:")
        print(f"   Overall: {'⭐' * int(show_result.overall_rating)} ({show_result.overall_rating:.2f} stars)")
        print(f"   Matches: {'⭐' * int(show_result.match_rating)} ({show_result.match_rating:.2f} stars)")
        if show_result.segment_results:
            print(f"   Segments: {'⭐' * int(show_result.segment_rating)} ({show_result.segment_rating:.2f} stars)")
        print()
        
        # STEP 11: Update wrestler stats after show
        print("📊 Updating wrestler statistics...")
        wrestlers_in_show = set()
        
        for match_result in show_result.match_results:
            wrestlers_in_show.update(match_result.side_a.wrestler_ids)
            wrestlers_in_show.update(match_result.side_b.wrestler_ids)
        
        for segment_result in show_result.segment_results:
            for participant in segment_result.participants:
                wrestler_id = self._get_participant_id(participant)
                if wrestler_id and wrestler_id not in ['interviewer', 'authority']:
                    wrestlers_in_show.add(wrestler_id)
        
        # Update stats if available
        if hasattr(universe_state, 'db') and hasattr(universe_state.db, 'update_wrestler_stats_cache'):
            for wrestler_id in wrestlers_in_show:
                universe_state.db.update_wrestler_stats_cache(wrestler_id)
        
        # Check milestones if module exists
        try:
            from simulation.milestones import check_milestones_for_show
            check_milestones_for_show(show_result, universe_state, universe_state.db)
        except ImportError:
            pass
        
        print(f"✅ Updated stats for {len(wrestlers_in_show)} wrestlers")
        
        # Update universe balance
        universe_state.balance += show_result.net_profit
        
        # Increment show count
        universe_state.show_count += 1
        
        # ================================================================
        # STEP 23: PROCESS CHAMPIONSHIP PRESTIGE DECAY
        # ================================================================
        
        print("📊 Checking championship prestige...")
        from simulation.prestige_calculator import prestige_calculator
        
        for championship in universe_state.championships:
            # Check for inactivity-based decay
            prestige_calculator.decay_prestige_for_inactivity(
                championship,
                show_draft.year,
                show_draft.week
            )
            
            # Save if prestige changed
            universe_state.save_championship(championship)
        
        print()
        
        # Process contracts
        self._process_contracts(wrestlers_on_card, universe_state, show_result)
        
        # ================================================================
        # STEP 120: Generate contract alerts after updating contract weeks
        # ================================================================
        
        print("📋 Generating contract alerts...")
        
        try:
            from economy.contracts import contract_manager
            
            # Get game state for current week/year
            game_state = {
                'current_week': show_draft.week,
                'current_year': show_draft.year
            }
            
            # Generate alerts for all active wrestlers
            alerts_generated = contract_manager.generate_alerts_for_contracts(
                wrestlers=universe_state.get_active_wrestlers(),
                current_week=game_state['current_week'],
                current_year=game_state['current_year']
            )
            
            if alerts_generated:
                print(f"   ✅ Generated {alerts_generated} contract alert(s)")
            else:
                print(f"   No new contract alerts")
                
        except ImportError as e:
            print(f"   ⚠️ Contract manager not available: {e}")
        except Exception as e:
            print(f"   ⚠️ Error generating contract alerts: {e}")
        
        print()
        
        # Fatigue recovery
        self._process_fatigue_recovery(wrestlers_on_card, universe_state)
        
        # Injury healing
        self._process_injury_healing(universe_state, show_result)
        
        # Year-end aging
        if show_draft.week == 52:
            self._process_year_end_aging(universe_state, show_result)
            
            # STEP 17: Calculate year-end awards
            print("\n🏆 CALCULATING YEAR-END AWARDS...")
            try:
                from simulation.awards_engine import awards_engine
                from persistence.awards_db import save_awards_ceremony
                
                ceremony = awards_engine.calculate_year_end_awards(
                    show_draft.year,
                    universe_state.db,
                    universe_state
                )
                
                save_awards_ceremony(universe_state.db, ceremony)
                
                show_result.add_event(
                    'awards_ceremony',
                    f"🏆 Year {show_draft.year} Awards Ceremony Complete - {len(ceremony.awards)} awards presented!"
                )
                
                print(f"✅ Year {show_draft.year} awards calculated and saved")
                
            except Exception as e:
                print(f"⚠️ Failed to calculate awards: {e}")
                import traceback
                traceback.print_exc()
        
        # Special events
        if show_draft.is_ppv:
            self._process_surprise_returns(universe_state, show_result)
        
        # ================================================================
        # STEP 16: SAVE STORYLINE STATE
        # ================================================================
        
        print("💾 Saving storyline state...")
        
        try:
            if hasattr(universe_state, 'db'):
                storyline_state = storyline_engine.save_state()
                universe_state.db.save_storyline_state(storyline_state)
                print("   ✅ Storyline state saved")
        except Exception as e:
            print(f"   ⚠️ Error saving storyline state: {e}")
        

        # Keep all active champions aligned to their title brand after each show.
        self._align_champions_to_title_brands(universe_state)

        # ================================================================
        # STEP 12: AUTO-SAVE AFTER SHOW
        # ================================================================
        
        if show_result.is_ppv or universe_state.show_count % 4 == 0:
            print("💾 Creating autosave...")
            try:
                from persistence.save_manager import SaveManager
                import os
                
                saves_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'data',
                    'saves'
                )
                save_manager = SaveManager(saves_dir)
                
                save_manager.save_universe(
                    database=universe_state.db,
                    slot=0,
                    save_name=f"Autosave - {show_result.show_name}",
                    include_history=False
                )
                
                print("✅ Autosave complete!")
            except Exception as e:
                print(f"⚠️ Autosave failed: {e}")
        
        print(f"✅ Show simulation complete!")
        print(f"   New Balance: ${universe_state.balance:,}")
        print(f"{'='*60}\n")
        
        return show_result
    
    def _align_champions_to_title_brands(self, universe_state) -> None:
        """Ensure title holders are on the same brand as their non-cross-brand championships."""
        try:
            championships = getattr(universe_state, 'championships', []) or []
            for title in championships:
                title_brand = getattr(title, 'assigned_brand', None)
                holder_id = getattr(title, 'current_holder_id', None)
                if not title_brand or title_brand == 'Cross-Brand' or not holder_id:
                    continue
                wrestler = universe_state.get_wrestler_by_id(holder_id)
                if not wrestler:
                    continue
                current_brand = getattr(wrestler, 'primary_brand', None)
                if current_brand != title_brand:
                    wrestler.primary_brand = title_brand
                    if hasattr(wrestler, 'current_brand'):
                        wrestler.current_brand = title_brand
                    universe_state.save_wrestler(wrestler)
                    print(f"      🔄 Brand alignment: {wrestler.name} moved to {title_brand} (champion of {title.name})")
        except Exception as e:
            print(f"   ⚠️ Champion-brand alignment step failed: {e}")

    # ====================================================================
    # SEGMENT SIMULATION (STEP 15)
    # ====================================================================
    
    def _simulate_segment(
        self,
        segment_draft,
        universe_state,
        show_result: ShowResult,
        item_num: int
    ) -> SegmentResult:
        """
        Simulate a segment, handling both AI-generated and frontend-created segments.
        
        Returns a SegmentResult that can be added to the show.
        """
        # Get segment type - could be string or enum
        segment_type = self._get_segment_type(segment_draft)
        
        # Get participant info
        participants = self._get_segment_participants(segment_draft)
        participant_names = ', '.join([self._get_participant_name(p) for p in participants]) if participants else 'TBD'
        
        print(f"🎤 Segment {item_num}: {segment_type.upper()} ({participant_names})")
        
        # Get wrestler objects
        wrestler_dict = {}
        for participant in participants:
            wrestler_id = self._get_participant_id(participant)
            if wrestler_id and wrestler_id not in ['interviewer', 'authority']:
                wrestler = universe_state.get_wrestler_by_id(wrestler_id)
                if wrestler:
                    wrestler_dict[wrestler_id] = wrestler
        
        # Try to use the full segment simulator
        try:
            from simulation.segment_sim import segment_simulator
            from models.segment import SegmentDraft as FullSegmentDraft, SegmentType, SegmentTone, SegmentParticipant
            
            # Convert to proper SegmentDraft if needed
            full_participants = []
            for p in participants:
                wrestler_id = self._get_participant_id(p)
                wrestler_name = self._get_participant_name(p)
                wrestler = wrestler_dict.get(wrestler_id)
                
                full_participants.append(SegmentParticipant(
                    wrestler_id=wrestler_id or '',
                    wrestler_name=wrestler_name or 'Unknown',
                    role=self._get_participant_role(p),
                    mic_skill=wrestler.mic if wrestler else 50
                ))
            
            # Parse segment type enum
            try:
                seg_type_enum = SegmentType(segment_type)
            except (ValueError, KeyError):
                seg_type_enum = SegmentType.PROMO
            
            # Parse tone
            tone_str = getattr(segment_draft, 'tone', 'intense')
            if isinstance(tone_str, str):
                try:
                    tone_enum = SegmentTone(tone_str)
                except (ValueError, KeyError):
                    tone_enum = SegmentTone.INTENSE
            else:
                tone_enum = tone_str if hasattr(tone_str, 'value') else SegmentTone.INTENSE
            
            full_segment_draft = FullSegmentDraft(
                segment_id=getattr(segment_draft, 'segment_id', f'seg_{item_num}'),
                segment_type=seg_type_enum,
                participants=full_participants,
                feud_id=getattr(segment_draft, 'feud_id', None),
                title_id=getattr(segment_draft, 'title_id', None),
                tone=tone_enum,
                duration_minutes=getattr(segment_draft, 'duration_minutes', 5),
                card_position=getattr(segment_draft, 'card_position', item_num)
            )
            
            # Simulate using the full simulator
            full_result = segment_simulator.simulate_segment(full_segment_draft, wrestler_dict)
            
            # Convert to the simplified SegmentResult for ShowResult
            segment_result = SegmentResult(
                segment_id=full_result.segment_id,
                segment_type=segment_type,
                participants=participants,
                duration_minutes=full_result.duration_minutes,
                segment_rating=full_result.segment_rating,
                crowd_heat=full_result.crowd_heat,
                key_moments=[e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in full_result.exchanges] if hasattr(full_result, 'exchanges') else full_result.key_moments,
                winner_id=full_result.winner_id,
                winner_name=full_result.winner_name,
                feud_intensity_change=full_result.feud_intensity_change,
                momentum_changes=full_result.momentum_changes,
                popularity_changes=full_result.popularity_changes,
                is_memorable=full_result.is_memorable,
                created_feud=full_result.created_feud
            )

            if hasattr(universe_state, 'relationship_network'):
                participant_ids = [
                    self._get_participant_id(participant)
                    for participant in participants
                    if self._get_participant_id(participant) not in [None, 'interviewer', 'authority']
                ]
                manager_bonus = universe_state.relationship_network.get_manager_bonus(participant_ids, context="promo")
                if manager_bonus:
                    segment_result.segment_rating = min(5.0, round(segment_result.segment_rating + (manager_bonus * 5), 2))
                    segment_result.crowd_heat = min(100, int(segment_result.crowd_heat + (manager_bonus * 100)))
                    print(f"   Manager promo bonus applied: +{manager_bonus * 5:.2f} stars")
            
            print(f"   Rating: {'⭐' * int(segment_result.segment_rating)} ({segment_result.segment_rating:.2f} stars)")
            print(f"   Crowd Heat: {segment_result.crowd_heat}")
            
            if segment_result.winner_id:
                print(f"   Winner: {segment_result.winner_name}")
            
            if segment_result.key_moments:
                first_moment = segment_result.key_moments[0]
                if isinstance(first_moment, dict):
                    print(f"   Key Moment: {first_moment.get('content_type', 'moment')}")
                else:
                    print(f"   Key Moment: {first_moment}")
            
            if segment_result.is_memorable:
                print(f"   ⭐ MEMORABLE SEGMENT!")
            
            return segment_result
            
        except Exception as e:
            print(f"      ⚠️ Segment simulation error: {e}, using fallback")
            import traceback
            traceback.print_exc()
            
            # Fallback: create a simple result
            return self._create_fallback_segment_result(
                segment_draft, 
                segment_type, 
                participants, 
                wrestler_dict,
                item_num
            )
    
    def _create_fallback_segment_result(
        self,
        segment_draft,
        segment_type: str,
        participants: List,
        wrestler_dict: Dict,
        item_num: int
    ) -> SegmentResult:
        """Create a simple segment result when full simulation fails."""
        
        # Calculate a basic rating based on participant mic skills
        avg_mic = 50
        if wrestler_dict:
            mic_skills = [w.mic for w in wrestler_dict.values() if hasattr(w, 'mic')]
            if mic_skills:
                avg_mic = sum(mic_skills) / len(mic_skills)
        
        # Base rating on mic skill (0-100 -> 1-5 stars)
        base_rating = (avg_mic / 100) * 4 + 1  # 1-5 range
        # Add some variance
        rating = max(1.0, min(5.0, base_rating + random.uniform(-0.5, 0.5)))
        
        # Calculate crowd heat
        crowd_heat = int(rating * 15 + random.randint(-10, 10))
        
        # Determine if memorable (4+ stars)
        is_memorable = rating >= 4.0
        
        # Generate key moments
        key_moments = [f"A {segment_type.replace('_', ' ')} segment took place"]
        
        # Momentum/popularity changes based on rating
        momentum_changes = {}
        popularity_changes = {}
        
        for wrestler_id, wrestler in wrestler_dict.items():
            if rating >= 3.5:
                momentum_changes[wrestler_id] = int(rating * 2)
                popularity_changes[wrestler_id] = int(rating)
            elif rating >= 2.5:
                momentum_changes[wrestler_id] = 0
                popularity_changes[wrestler_id] = 0
            else:
                momentum_changes[wrestler_id] = -3
                popularity_changes[wrestler_id] = -1
        
        segment_result = SegmentResult(
            segment_id=getattr(segment_draft, 'segment_id', f'seg_{item_num}'),
            segment_type=segment_type,
            participants=participants,
            duration_minutes=getattr(segment_draft, 'duration_minutes', 5),
            segment_rating=rating,
            crowd_heat=crowd_heat,
            key_moments=key_moments,
            winner_id=None,
            winner_name=None,
            feud_intensity_change=5 if rating >= 3.0 else 0,
            momentum_changes=momentum_changes,
            popularity_changes=popularity_changes,
            is_memorable=is_memorable,
            created_feud=False
        )
        
        print(f"   Rating: {'⭐' * int(rating)} ({rating:.2f} stars)")
        print(f"   Crowd Heat: {crowd_heat}")
        
        if is_memorable:
            print(f"   ⭐ MEMORABLE SEGMENT!")
        
        return segment_result
    
    # ====================================================================
    # SEGMENT HELPER METHODS
    # ====================================================================
    
    def _get_segment_type(self, segment_draft) -> str:
        """Extract segment type as string from segment draft."""
        segment_type = getattr(segment_draft, 'segment_type', 'promo')
        if hasattr(segment_type, 'value'):
            return segment_type.value
        return str(segment_type)
    
    def _get_segment_participants(self, segment_draft) -> List:
        """Extract participants list from segment draft."""
        return getattr(segment_draft, 'participants', [])
    
    def _get_participant_id(self, participant) -> str:
        """Extract wrestler_id from participant (dict or object)."""
        if isinstance(participant, str):
            return participant
        if isinstance(participant, dict):
            return participant.get('wrestler_id') or participant.get('id') or ''
        return getattr(participant, 'wrestler_id', '')
    
    def _get_participant_name(self, participant) -> str:
        """Extract wrestler_name from participant (dict or object)."""
        if isinstance(participant, str):
            return participant
        if isinstance(participant, dict):
            return participant.get('wrestler_name') or participant.get('name') or 'Unknown'
        return getattr(participant, 'wrestler_name', 'Unknown')
    
    def _get_participant_role(self, participant) -> str:
        """Extract role from participant (dict or object)."""
        if isinstance(participant, dict):
            return participant.get('role', 'speaker')
        return getattr(participant, 'role', 'speaker')
    
    # ====================================================================
    # POST-MATCH EFFECTS
    # ====================================================================
    
    def _apply_match_effects(
        self,
        match_result: MatchResult,
        match_draft,
        side_a_wrestlers: List[Wrestler],
        side_b_wrestlers: List[Wrestler],
        universe_state,
        show_result: ShowResult
    ):
        """Apply all post-match effects to wrestlers"""
        
        # For multi-man matches, all winners are in side_a
        if not side_b_wrestlers:
            # Multi-man match - find the actual winner
            winner_id = match_result.winner_names[0] if match_result.winner_names else None
            winners = []
            losers = []
            
            for wrestler in side_a_wrestlers:
                if wrestler.name == winner_id or wrestler.name in match_result.winner_names:
                    winners.append(wrestler)
                else:
                    losers.append(wrestler)
        else:
            # Standard match
            winners = side_a_wrestlers if match_result.winner == 'side_a' else side_b_wrestlers
            losers = side_b_wrestlers if match_result.winner == 'side_a' else side_a_wrestlers
        
        # Winner effects
        for winner in winners:
            momentum_gain = 5
            popularity_gain = 2
            
            if match_result.star_rating >= 4.0:
                momentum_gain += 3
                popularity_gain += 2
            elif match_result.star_rating >= 3.0:
                momentum_gain += 1
                popularity_gain += 1
            
            if losers:
                avg_loser_popularity = sum(l.popularity for l in losers) / len(losers)
                if avg_loser_popularity > winner.popularity:
                    quality_diff = int((avg_loser_popularity - winner.popularity) / 10)
                    momentum_gain += quality_diff
                    popularity_gain += quality_diff // 2
            
            if match_result.is_upset:
                momentum_gain += 10
                popularity_gain += 5
                print(f"      {winner.name}: UPSET VICTORY BOOST!")
            
            if match_result.is_title_match and match_result.title_changed_hands:
                momentum_gain += 15
                popularity_gain += 8
                print(f"      {winner.name}: NEW CHAMPION BOOST!")
            
            winner.adjust_momentum(momentum_gain)
            winner.adjust_popularity(popularity_gain)
            winner.adjust_fatigue(15)
            
            print(f"      {winner.name}: Momentum +{momentum_gain}, Popularity +{popularity_gain}, Fatigue +15")
        
        # Loser effects
        for loser in losers:
            momentum_loss = -3
            popularity_loss = -1
            
            if match_result.finish_type in [FinishType.ROLLUP, FinishType.DQ, FinishType.COUNTOUT]:
                momentum_loss = -1
                popularity_loss = 0
            
            if match_result.is_upset:
                momentum_loss -= 8
                popularity_loss -= 3
                print(f"      {loser.name}: UPSET LOSS PENALTY!")
            
            if match_result.is_title_match and match_result.title_changed_hands:
                momentum_loss -= 10
                popularity_loss -= 5
                print(f"      {loser.name}: LOST CHAMPIONSHIP!")
            
            loser.adjust_momentum(momentum_loss)
            loser.adjust_popularity(popularity_loss)
            loser.adjust_fatigue(20)
            
            print(f"      {loser.name}: Momentum {momentum_loss}, Popularity {popularity_loss}, Fatigue +20")
        
        # ================================================================
        # INJURY CHECK WITH FULL INTEGRATION (STEP 21)
        # ================================================================
        
        all_participants = side_a_wrestlers + side_b_wrestlers
        
        # Get injury manager if available
        from simulation.injuries import injury_manager
        
        if injury_manager and hasattr(match_result, 'match_type'):
            # Process injuries through injury manager
            injuries = injury_manager.process_match_injuries(
                match_result=match_result,
                wrestlers=all_participants,
                match_type=getattr(match_result, 'match_type', 'singles'),
                year=show_result.year,
                week=show_result.week,
                show_id=show_result.show_id,
                show_name=show_result.show_name,
                is_ppv=show_result.is_ppv
            )
            
            # Process each injury
            for injury_data in injuries:
                wrestler = next((w for w in all_participants if w.id == injury_data['wrestler_id']), None)
                if wrestler:
                    # Add to match result if supported
                    if not hasattr(match_result, 'injuries'):
                        match_result.injuries = []
                    match_result.injuries.append(injury_data)
                    
                    # Add to show events
                    severity_emoji = {
                        'Minor': '🤕',
                        'Moderate': '🚑',
                        'Severe': '🏥',
                        'Career Threatening': '💀'
                    }.get(injury_data['severity'], '⚠️')
                    
                    show_result.add_event(
                        'injury',
                        f"{severity_emoji} {injury_data['wrestler_name']} suffered a {injury_data['severity'].lower()} {injury_data['description']} ({injury_data['weeks_out']} weeks)"
                    )
                    
                    print(f"      {severity_emoji} INJURY: {injury_data['wrestler_name']} - {injury_data['description']} ({injury_data['weeks_out']} weeks)")
                    
                    # If severe injury, potentially create injury angle next week
                    if injury_data['severity'] in ['Severe', 'Career Threatening']:
                        # Flag for injury angle creation
                        if not hasattr(show_result, 'injury_angles_needed'):
                            show_result.injury_angles_needed = []
                        show_result.injury_angles_needed.append({
                            'wrestler_id': injury_data['wrestler_id'],
                            'wrestler_name': injury_data['wrestler_name'],
                            'severity': injury_data['severity']
                        })
        else:
            # Fallback to original simple injury system if injury manager not available
            for wrestler in all_participants:
                injury_chance = 0.03
                
                if match_result.duration_minutes > 20:
                    injury_chance += 0.02
                
                if wrestler.brawling > 80 or wrestler.speed > 80:
                    injury_chance += 0.01
                
                if random.random() < injury_chance:
                    severity = random.choices(
                        ['Minor', 'Moderate', 'Major'],
                        weights=[70, 25, 5]
                    )[0]
                    weeks_out = {
                        'Minor': random.randint(1, 2),
                        'Moderate': random.randint(3, 6),
                        'Major': random.randint(8, 16)
                    }[severity]
                    
                    descriptions = {
                        'Minor': ['bruised ribs', 'twisted ankle', 'minor concussion'],
                        'Moderate': ['knee injury', 'shoulder strain', 'back injury'],
                        'Major': ['torn ACL', 'broken arm', 'severe concussion']
                    }
                    
                    description = random.choice(descriptions[severity])
                    
                    wrestler.apply_injury(severity, description, weeks_out)
                    
                    if hasattr(match_result, 'injuries'):
                        match_result.injuries.append({
                            'wrestler_id': wrestler.id,
                            'wrestler_name': wrestler.name,
                            'severity': severity,
                            'description': description,
                            'weeks_out': weeks_out
                        })
                    
                    show_result.add_event(
                        'injury',
                        f"{wrestler.name} suffered a {severity.lower()} {description} ({weeks_out} weeks)"
                    )
                    
                    print(f"      ⚠️  {wrestler.name}: {severity} injury - {description} ({weeks_out} weeks)")
        
        # ================================================================
        # TITLE CHANGE HANDLING + STEP 23: PRESTIGE TRACKING
        # ================================================================
        
        # DEBUG: Print what we're checking
        print(f"\n      {'='*50}")
        print(f"      🔍 TITLE MATCH CHECK:")
        print(f"      is_title_match: {match_result.is_title_match}")
        print(f"      winner: {match_result.winner}")
        print(f"      title_changed_hands: {getattr(match_result, 'title_changed_hands', 'ATTRIBUTE MISSING')}")
        print(f"      winners: {[w.name for w in winners] if winners else 'None'}")
        print(f"      {'='*50}\n")
        
        if match_result.is_title_match and match_result.winner in ['side_a', 'side_b'] and winners:
            title = None
            
            # Try to get championship by ID first (more reliable), then by name
            if match_draft and hasattr(match_draft, 'title_id') and match_draft.title_id:
                title = universe_state.get_championship_by_id(match_draft.title_id)
                print(f"      🔍 DEBUG: Found title by ID: {title.name if title else 'NOT FOUND'}")
            
            if not title:
                print(f"      🔍 DEBUG: Trying to find by name: {match_result.title_name}")
                for championship in universe_state.championships:
                    if match_result.title_name and championship.name == match_result.title_name:
                        title = championship
                        print(f"      🔍 DEBUG: Found title by name: {title.name}")
                        break
            
            if title:
                print(f"      ✅ Processing title: {title.name}")
                
                # STEP 23: Update prestige based on match quality
                from simulation.prestige_calculator import prestige_calculator
                
                # Get the champion (before potential title change)
                current_champion = None
                if not title.is_vacant:
                    current_champion = universe_state.get_wrestler_by_id(title.current_holder_id)
                
                # If title changed hands, use the NEW champion for prestige calculation
                if match_result.title_changed_hands:
                    new_champion_id = getattr(match_result, 'new_champion_id', None)
                    new_champion_name = getattr(match_result, 'new_champion_name', None)
                    new_champion = (
                        universe_state.get_wrestler_by_id(new_champion_id)
                        if new_champion_id else
                        (winners[0] if winners else None)
                    )
                    
                    if not new_champion:
                        print(f"      ⚠️ Cannot process title change - no winner found")
                    else:
                        current_champion = new_champion
                        old_champion_id = title.current_holder_id
                        
                        # STEP 30: Evaluate former champion's reign satisfaction BEFORE title change
                        if old_champion_id:
                            former_champion = universe_state.get_wrestler_by_id(old_champion_id)
                            
                            if former_champion:
                                # Get current reign data
                                current_reign = title.history[-1] if title.history else None
                                
                                if current_reign and current_reign.wrestler_id == old_champion_id:
                                    # Calculate defenses and avg rating
                                    try:
                                        cursor = universe_state.db.conn.cursor()
                                        cursor.execute('''
                                            SELECT COUNT(*) as defenses, AVG(star_rating) as avg_rating
                                            FROM title_defenses
                                            WHERE title_id = ? AND champion_id = ?
                                            AND year >= ? AND week >= ?
                                        ''', (
                                            title.id,
                                            old_champion_id,
                                            current_reign.won_date_year,
                                            current_reign.won_date_week
                                        ))
                                        
                                        defense_data = cursor.fetchone()
                                        
                                        # Build reign data for satisfaction calculation
                                        reign_data = {
                                            'reign_start_year': current_reign.won_date_year,
                                            'reign_start_week': current_reign.won_date_week,
                                            'reign_end_year': show_result.year,
                                            'reign_end_week': show_result.week,
                                            'days_held': current_reign.days_held if current_reign.days_held else 0,
                                            'successful_defenses': defense_data['defenses'] if defense_data else 0,
                                            'avg_star_rating': defense_data['avg_rating'] if defense_data else 0,
                                            'loss_type': match_result.finish_type.value,
                                            'end_show_name': show_result.show_name
                                        }
                                        
                                        # Evaluate satisfaction
                                        try:
                                            from simulation.reign_satisfaction import evaluate_reign_satisfaction_on_title_loss
                                            
                                            satisfaction = evaluate_reign_satisfaction_on_title_loss(
                                                universe_state.db,
                                                former_champion,
                                                title,
                                                reign_data
                                            )
                                            
                                            # Save updated wrestler with morale change
                                            universe_state.save_wrestler(former_champion)
                                            
                                            print(f"      📊 Reign satisfaction: {satisfaction['morale_change']:+d} morale")
                                            
                                        except ImportError:
                                            print(f"      ⚠️ Reign satisfaction module not available")
                                        except Exception as e:
                                            print(f"      ⚠️ Error calculating reign satisfaction: {e}")
                                    
                                    except Exception as e:
                                        print(f"      ⚠️ Error querying title defenses: {e}")
                        
                        # Award title to new champion
                        title.award_title(
                            wrestler_id=new_champion.id,
                            wrestler_name=new_champion_name or new_champion.name,
                            show_id=show_result.show_id,
                            show_name=show_result.show_name,
                            year=show_result.year,
                            week=show_result.week
                        )

                        # Keep champions aligned to the brand their title belongs to.
                        title_brand = getattr(title, 'assigned_brand', None)
                        if title_brand and title_brand != 'Cross-Brand':
                            try:
                                for champ_member in winners:
                                    champ_member.primary_brand = title_brand
                                    if hasattr(champ_member, 'current_brand'):
                                        champ_member.current_brand = title_brand
                                    universe_state.save_wrestler(champ_member)
                                print(f"      🔄 Brand alignment: {new_champion.name} moved to {title_brand} as champion")
                            except Exception as e:
                                print(f"      ⚠️ Failed to align champion brand for {new_champion.name}: {e}")
                        
                        # STEP 30: Create reign goals for new champion
                        try:
                            from simulation.reign_satisfaction import create_reign_goals_on_title_win
                            
                            goals = create_reign_goals_on_title_win(
                                universe_state.db,
                                new_champion,
                                title,
                                show_result.year,
                                show_result.week
                            )
                            
                            print(f"      🎯 Created {len(goals)} reign goals for {new_champion.name}")
                            
                        except ImportError:
                            print(f"      ⚠️ Reign goals module not available")
                        except Exception as e:
                            print(f"      ⚠️ Error creating reign goals: {e}")
                        
                        show_result.add_event(
                            'title_change',
                            f"🏆 NEW CHAMPION: {new_champion_name or new_champion.name} won the {title.name}!"
                        )
                        
                        print(f"      🏆 TITLE CHANGE: {new_champion_name or new_champion.name} wins {title.name}")
                
                # Update prestige if we have a champion
                if current_champion:
                    prestige_calculator.update_title_prestige(
                        championship=title,
                        match_result=match_result,
                        champion=current_champion,
                        is_ppv=show_result.is_ppv
                    )
                
                # NOTE: Defense recording handled by STEP 25 in main loop above
                if not match_result.title_changed_hands:
                    print(f"      🛡️ TITLE DEFENSE: {title.current_holder_name} retained {title.name}")
                
                # CRITICAL: Save championship and COMMIT
                universe_state.save_championship(title)
                try:
                    universe_state.db.conn.commit()
                    print(f"      💾 Championship changes committed to database")
                except Exception as e:
                    print(f"      ⚠️ Error committing championship: {e}")
            else:
                print(f"      ❌ TITLE NOT FOUND! Cannot process title change")
        
        # Tag team stats update
        if len(side_a_wrestlers) >= 2 and len(side_b_wrestlers) >= 2:
            side_a_ids = [w.id for w in side_a_wrestlers]
            side_b_ids = [w.id for w in side_b_wrestlers]
            
            if hasattr(universe_state, 'tag_team_manager'):
                team_a = universe_state.tag_team_manager.get_team_by_members(side_a_ids)
                team_b = universe_state.tag_team_manager.get_team_by_members(side_b_ids)
                
                if match_result.winner == 'side_a':
                    if team_a:
                        team_a.record_match_outcome('win', match_result.star_rating)
                        universe_state.save_tag_team(team_a)
                        print(f"      🏷️ {team_a.team_name}: Team record now {team_a.team_wins}-{team_a.team_losses} (Chemistry: {team_a.chemistry})")
                    
                    if team_b:
                        team_b.record_match_outcome('loss', match_result.star_rating)
                        universe_state.save_tag_team(team_b)
                
                elif match_result.winner == 'side_b':
                    if team_b:
                        team_b.record_match_outcome('win', match_result.star_rating)
                        universe_state.save_tag_team(team_b)
                        print(f"      🏷️ {team_b.team_name}: Team record now {team_b.team_wins}-{team_b.team_losses} (Chemistry: {team_b.chemistry})")
                    
                    if team_a:
                        team_a.record_match_outcome('loss', match_result.star_rating)
                        universe_state.save_tag_team(team_a)
                
                elif match_result.winner == 'draw':
                    if team_a:
                        team_a.record_match_outcome('draw', match_result.star_rating)
                        universe_state.save_tag_team(team_a)
                    if team_b:
                        team_b.record_match_outcome('draw', match_result.star_rating)
                        universe_state.save_tag_team(team_b)
        
        # Feud update
        if match_result.side_a.wrestler_ids and match_result.side_b.wrestler_ids:
            existing_feud = universe_state.feud_manager.get_feud_between(
                match_result.side_a.wrestler_ids[0],
                match_result.side_b.wrestler_ids[0]
            )
            
            if existing_feud:
                existing_feud.add_segment(
                    show_id=show_result.show_id,
                    show_name=show_result.show_name,
                    year=show_result.year,
                    week=show_result.week,
                    segment_type='match',
                    description=f"{' & '.join(match_result.winner_names)} defeated {' & '.join(match_result.loser_names)}",
                    intensity_change=5 if match_result.star_rating >= 3.5 else 2
                )
                
                winner_id = winners[0].id if winners else None
                if winner_id:
                    existing_feud.record_match_result(winner_id)
                
                universe_state.save_feud(existing_feud)
                
                print(f"      🔥 Feud intensity now: {existing_feud.intensity}")
            
            elif match_result.is_upset and winners and losers:
                feud = universe_state.feud_manager.auto_create_from_upset(
                    winner_id=winners[0].id,
                    winner_name=winners[0].name,
                    loser_id=losers[0].id,
                    loser_name=losers[0].name,
                    year=show_result.year,
                    week=show_result.week,
                    show_id=show_result.show_id
                )
                
                universe_state.save_feud(feud)
                
                show_result.add_event(
                    'feud_started',
                    f"🔥 NEW FEUD! {winners[0].name} vs {losers[0].name} has begun!"
                )
                
                print(f"      🔥 NEW FEUD CREATED: {winners[0].name} vs {losers[0].name}")
        
        if hasattr(universe_state, 'relationship_network'):
            relationship_network = universe_state.relationship_network

            for team in [side_a_wrestlers, side_b_wrestlers]:
                if len(team) >= 2:
                    anchor = team[0]
                    for partner in team[1:]:
                        friendship = relationship_network.create_or_update_relationship(
                            anchor.id,
                            anchor.name,
                            partner.id,
                            partner.name,
                            'friendship',
                            strength_delta=2,
                            note=f"Teamed together on {show_result.show_name}."
                        )
                        universe_state.save_relationship(friendship)

                        veteran = anchor if anchor.years_experience >= partner.years_experience else partner
                        younger = partner if veteran is anchor else anchor
                        if veteran.years_experience - younger.years_experience >= 7 and younger.age <= 30:
                            mentorship = relationship_network.create_or_update_relationship(
                                veteran.id,
                                veteran.name,
                                younger.id,
                                younger.name,
                                'mentorship',
                                strength_delta=2,
                                metadata={'mentor_id': veteran.id, 'protege_id': younger.id},
                                note=f"Shared ring time on {show_result.show_name} strengthened the mentor/protege pairing."
                            )
                            universe_state.save_relationship(mentorship)

            if winners and losers:
                rivalry_intensity = 6 if match_result.is_upset or match_result.title_changed_hands else 3
                heat = relationship_network.create_or_update_relationship(
                    winners[0].id,
                    winners[0].name,
                    losers[0].id,
                    losers[0].name,
                    'heat',
                    strength_delta=rivalry_intensity,
                    note=f"Match result on {show_result.show_name} escalated backstage tension."
                )
                universe_state.save_relationship(heat)

        if hasattr(universe_state, 'faction_manager'):
            processed_factions = set()
            for team, success in ((side_a_wrestlers, match_result.winner == 'side_a'), (side_b_wrestlers, match_result.winner == 'side_b')):
                for wrestler in team:
                    faction = universe_state.faction_manager.get_faction_by_member(wrestler.id)
                    if faction and faction.faction_id not in processed_factions:
                        faction.record_member_spotlight(wrestler.id, success=success)
                        universe_state.save_faction(faction)
                        processed_factions.add(faction.faction_id)

        # Save all affected wrestlers
        for wrestler in side_a_wrestlers + side_b_wrestlers:
            universe_state.save_wrestler(wrestler)
    
    # ====================================================================
    # POST-SEGMENT EFFECTS (STEP 15)
    # ====================================================================
    
    def _apply_segment_effects(
        self,
        segment_result: SegmentResult,
        segment_draft,
        universe_state,
        show_result: ShowResult
    ):
        """Apply post-segment effects to wrestlers and feuds"""
        
        # Apply momentum changes
        momentum_changes = segment_result.momentum_changes or {}
        for wrestler_id, change in momentum_changes.items():
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            if wrestler:
                wrestler.momentum = max(-100, min(100, wrestler.momentum + change))
                universe_state.save_wrestler(wrestler)
                print(f"      {wrestler.name}: Momentum {'+' if change >= 0 else ''}{change}")
        
        # Apply popularity changes
        popularity_changes = segment_result.popularity_changes or {}
        for wrestler_id, change in popularity_changes.items():
            wrestler = universe_state.get_wrestler_by_id(wrestler_id)
            if wrestler:
                wrestler.popularity = max(0, min(100, wrestler.popularity + change))
                universe_state.save_wrestler(wrestler)
                print(f"      {wrestler.name}: Popularity {'+' if change >= 0 else ''}{change}")
        
        # Update feud intensity
        feud_id = getattr(segment_draft, 'feud_id', None)
        feud_intensity_change = segment_result.feud_intensity_change or 0
        
        if feud_id and feud_intensity_change != 0:
            feud = universe_state.feud_manager.get_feud_by_id(feud_id)
            if feud:
                old_intensity = feud.intensity
                feud.intensity = max(0, min(100, feud.intensity + feud_intensity_change))
                
                segment_type = self._get_segment_type(segment_draft)
                key_moments = segment_result.key_moments or []
                description = key_moments[0] if key_moments else 'Segment occurred'
                if isinstance(description, dict):
                    description = description.get('content_type', 'Segment occurred')
                
                feud.add_segment(
                    show_id=segment_result.segment_id,
                    show_name=show_result.show_name,
                    year=show_result.year,
                    week=show_result.week,
                    segment_type=segment_type,
                    description=str(description),
                    intensity_change=feud_intensity_change
                )
                
                universe_state.save_feud(feud)
                
                print(f"      🔥 Feud intensity: {old_intensity} → {feud.intensity} ({'+' if feud_intensity_change >= 0 else ''}{feud_intensity_change})")
        
        # Create new feud from attacks or betrayals
        segment_type = self._get_segment_type(segment_draft)
        participants = self._get_segment_participants(segment_draft)
        purpose = getattr(segment_draft, 'purpose', 'general')

        if purpose in ['build_feud', 'start_feud'] and len(participants) >= 2:
            self._apply_segment_purpose_to_feud(
                segment_result,
                segment_draft,
                universe_state,
                show_result,
                purpose
            )
        
        if segment_type in ['backstage_attack', 'in_ring_attack', 'betrayal'] and len(participants) >= 2:
            p1_id = self._get_participant_id(participants[0])
            p1_name = self._get_participant_name(participants[0])
            p2_id = self._get_participant_id(participants[1])
            p2_name = self._get_participant_name(participants[1])
            
            existing_feud = universe_state.feud_manager.get_feud_between(p1_id, p2_id)
            
            if not existing_feud and p1_id and p2_id:
                from models.feud import FeudType
                
                new_feud = universe_state.feud_manager.create_feud(
                    feud_type=FeudType.PERSONAL,
                    participant_ids=[p1_id, p2_id],
                    participant_names=[p1_name, p2_name],
                    year=show_result.year,
                    week=show_result.week,
                    initial_intensity=30 if segment_type == 'betrayal' else 20
                )
                
                universe_state.save_feud(new_feud)
                
                show_result.add_event(
                    'feud_started',
                    f"🔥 NEW FEUD! {p1_name} vs {p2_name} has begun!"
                )
                
                print(f"      🔥 NEW FEUD CREATED: {p1_name} vs {p2_name}")
        
        # Add memorable segment event (4+ stars)
        if segment_result.is_memorable:
            key_moments = segment_result.key_moments or []
            if key_moments:
                first_moment = key_moments[0]
                if isinstance(first_moment, dict):
                    highlight_desc = first_moment.get('content_type', segment_type)
                else:
                    highlight_desc = str(first_moment)
            else:
                highlight_desc = segment_type
            
            show_result.add_event(
                'memorable_segment',
                f"⭐ MEMORABLE {segment_type.upper()}: {highlight_desc}"
            )
    
    def _apply_segment_purpose_to_feud(
        self,
        segment_result: SegmentResult,
        segment_draft,
        universe_state,
        show_result: ShowResult,
        purpose: str
    ):
        """Make manual segment purpose choices affect the feud system."""
        participants = [
            p for p in self._get_segment_participants(segment_draft)
            if self._get_participant_id(p) not in ['', 'interviewer', 'authority']
        ]
        if len(participants) < 2:
            return

        p1_id = self._get_participant_id(participants[0])
        p2_id = self._get_participant_id(participants[1])
        if not p1_id or not p2_id or p1_id == p2_id:
            return

        p1_name = self._get_participant_name(participants[0])
        p2_name = self._get_participant_name(participants[1])
        p1 = universe_state.get_wrestler_by_id(p1_id)
        p2 = universe_state.get_wrestler_by_id(p2_id)
        if p1:
            p1_name = p1.name
        if p2:
            p2_name = p2.name

        feud_manager = getattr(universe_state, 'feud_manager', None)
        if not feud_manager:
            return

        segment_type = self._get_segment_type(segment_draft)
        existing_feud = feud_manager.get_feud_between(p1_id, p2_id)
        change = 15 if purpose == 'start_feud' else 10
        description = f"{p1_name} and {p2_name} escalated their rivalry in a {segment_type.replace('_', ' ')} segment."

        if existing_feud:
            existing_feud.add_segment(
                show_id=segment_result.segment_id,
                show_name=show_result.show_name,
                year=show_result.year,
                week=show_result.week,
                segment_type=segment_type,
                description=description,
                intensity_change=change
            )
            universe_state.save_feud(existing_feud)
            segment_result.feud_intensity_change = max(segment_result.feud_intensity_change or 0, change)
            show_result.add_event(
                'feud_heated_up',
                f"{p1_name} vs {p2_name} heated up after a {segment_type.replace('_', ' ')} segment."
            )
            print(f"      FEUD HEATED UP: {p1_name} vs {p2_name} (+{change})")
        else:
            from models.feud import FeudType

            initial_intensity = 45 if purpose == 'start_feud' else 35
            new_feud = feud_manager.create_feud(
                feud_type=FeudType.PERSONAL,
                participant_ids=[p1_id, p2_id],
                participant_names=[p1_name, p2_name],
                year=show_result.year,
                week=show_result.week,
                show_id=show_result.show_id,
                initial_intensity=initial_intensity
            )
            new_feud.add_segment(
                show_id=segment_result.segment_id,
                show_name=show_result.show_name,
                year=show_result.year,
                week=show_result.week,
                segment_type=segment_type,
                description=description,
                intensity_change=0
            )
            universe_state.save_feud(new_feud)
            segment_result.created_feud = True
            segment_result.feud_intensity_change = max(segment_result.feud_intensity_change or 0, initial_intensity)
            show_result.add_event(
                'feud_started',
                f"NEW FEUD! {p1_name} vs {p2_name} started after a {segment_type.replace('_', ' ')} segment."
            )
            print(f"      NEW FEUD CREATED: {p1_name} vs {p2_name}")

        try:
            universe_state.db.conn.commit()
        except Exception as e:
            print(f"      Could not commit feud segment changes immediately: {e}")

    # ====================================================================
    # CONTRACT MANAGEMENT
    # ====================================================================
    
    def _process_contracts(
        self,
        wrestlers_on_card: List[Wrestler],
        universe_state,
        show_result: ShowResult
    ):
        """Decrement contracts for wrestlers who appeared on the show"""
        
        for wrestler in wrestlers_on_card:
            wrestler.contract.weeks_remaining -= 1
            
            if wrestler.contract.weeks_remaining <= 0:
                show_result.add_event(
                    'contract_expired',
                    f"📋 {wrestler.name}'s contract has EXPIRED!"
                )
                print(f"   📋 CONTRACT EXPIRED: {wrestler.name}")
            
            elif wrestler.contract.weeks_remaining <= 4:
                show_result.add_event(
                    'contract_expiring',
                    f"⚠️  {wrestler.name}'s contract expires in {wrestler.contract.weeks_remaining} weeks"
                )
            
            universe_state.save_wrestler(wrestler)
    
    def _process_fatigue_recovery(
        self,
        wrestlers_on_card: List[Wrestler],
        universe_state
    ):
        """Recover fatigue for wrestlers who didn't appear"""
        
        on_card_ids = {w.id for w in wrestlers_on_card}
        
        for wrestler in universe_state.get_active_wrestlers():
            if wrestler.id not in on_card_ids:
                wrestler.recover_fatigue(20)
                universe_state.save_wrestler(wrestler)
    
    def _process_injury_healing(
        self,
        universe_state,
        show_result: ShowResult
    ):
        """Progress injury healing for all injured wrestlers"""
        
        for wrestler in universe_state.wrestlers:
            if wrestler.is_injured:
                old_weeks = wrestler.injury.weeks_remaining
                wrestler.heal_injury(weeks_passed=1)
                
                if not wrestler.is_injured and old_weeks > 0:
                    show_result.add_event(
                        'injury_healed',
                        f"✅ {wrestler.name} has recovered from their {wrestler.injury.description}!"
                    )
                    print(f"   ✅ {wrestler.name} recovered from injury")
                
                universe_state.save_wrestler(wrestler)
    
    # ====================================================================
    # YEAR-END PROCESSING
    # ====================================================================
    
    def _process_year_end_aging(
        self,
        universe_state,
        show_result: ShowResult
    ):
        """Process aging and retirements at year-end (Week 52)"""
        
        print("\n🎂 YEAR-END AGING PROCESS...\n")
        
        try:
            from simulation.aging import aging_system
            
            aging_report = aging_system.process_year_end_aging(
                universe_state.get_active_wrestlers()
            )
            
            print(f"   Aged {aging_report['aged_count']} wrestlers")
            
            if aging_report.get('degradation_report'):
                print(f"\n   📉 Attribute Degradation:")
                for report in aging_report['degradation_report'][:10]:
                    changes_str = ', '.join([f"{attr}: {val}" for attr, val in report['changes'].items()])
                    print(f"      {report['wrestler_name']} (Age {report['age']}): {changes_str}")
            
            if aging_report.get('retirements'):
                print(f"\n   👴 RETIREMENTS ({len(aging_report['retirements'])}):")
                
                for wrestler in aging_report['retirements']:
                    show_result.add_event(
                        'retirement',
                        f"👴 {wrestler.name} has announced their RETIREMENT after {wrestler.years_experience} years! (Age {wrestler.age})"
                    )
                    
                    print(f"      {wrestler.name} (Age {wrestler.age}, {wrestler.years_experience} years)")
            
            for wrestler in universe_state.get_active_wrestlers():
                universe_state.save_wrestler(wrestler)
            
            for retired in aging_report.get('retirements', []):
                universe_state.save_wrestler(retired)
        
        except ImportError:
            print("   ⚠️  Aging system not available")
        
        print()
    
    def _process_surprise_returns(
        self,
        universe_state,
        show_result: ShowResult
    ):
        """Handle surprise returns at PPVs"""
        
        # Only at major PPVs
        if not show_result.is_ppv:
            return
            
        from simulation.injuries import injury_manager
        
        # Define return chances by PPV
        ppv_return_chances = {
            'Rumble Royale': 0.25,  # 25% chance
            'Victory Dome': 0.20,    # 20% chance
            'Summer Slamfest': 0.15, # 15% chance
            'Night of Glory': 0.15,  # 15% chance
            'Overdrive': 0.10,       # 10% chance
            'Other': 0.05            # 5% for other PPVs
        }
        
        return_chance = ppv_return_chances.get(
            show_result.show_name,
            ppv_return_chances['Other']
        )
        
        if random.random() > return_chance:
            return
            
        # Get wrestlers who could return
        potential_returns = []
        
        # Check injury history for wrestlers out 3+ months
        injury_history = injury_manager.database.execute_raw('''
            SELECT DISTINCT wrestler_id, wrestler_name, weeks_missed
            FROM injury_history
            WHERE return_year IS NULL OR return_week IS NULL
            ORDER BY weeks_missed DESC
        ''')
        
        for record in injury_history:
            if record['weeks_missed'] >= 12:  # Out 3+ months
                wrestler = universe_state.get_wrestler_by_id(record['wrestler_id'])
                if wrestler and not wrestler.is_injured and not wrestler.is_retired:
                    potential_returns.append(wrestler)
        
        # Also check retired major stars
        for wrestler in universe_state.retired_wrestlers:
            if wrestler.is_major_superstar and wrestler.age < 50:
                if random.random() < 0.10:  # 10% chance for retired stars
                    potential_returns.append(wrestler)
        
        if not potential_returns:
            return
            
        # Pick someone to return
        returning_wrestler = random.choice(potential_returns)
        
        # Unretire if needed
        if returning_wrestler.is_retired:
            returning_wrestler.is_retired = False
            show_result.add_event(
                'surprise_return',
                f"🎉 SHOCK RETURN FROM RETIREMENT! {returning_wrestler.name} is BACK!"
            )
            print(f"   🎉 RETIREMENT RETURN: {returning_wrestler.name}!")
        else:
            show_result.add_event(
                'surprise_return',
                f"🎉 SURPRISE RETURN! {returning_wrestler.name} is BACK!"
            )
            print(f"   🎉 SURPRISE RETURN: {returning_wrestler.name}!")
        
        # Generate return angle
        if injury_manager:
            # Find a target (current champion or top heel)
            target = None
            for championship in universe_state.championships:
                if championship.current_holder_id and championship.title_type == 'World':
                    target = universe_state.get_wrestler_by_id(championship.current_holder_id)
                    break
            
            if not target:
                # Pick top heel
                heels = [w for w in universe_state.get_active_wrestlers() 
                        if w.alignment == 'Heel' and w.role == 'Main Event']
                if heels:
                    target = max(heels, key=lambda w: w.popularity)
            
            angle = injury_manager.angle_generator.generate_return_angle(
                returning_wrestler=returning_wrestler,
                is_surprise=True,
                target=target,
                weeks_out=record.get('weeks_missed', 0) if 'record' in locals() else 0
            )
            
            # Apply boosts
            returning_wrestler.adjust_momentum(angle['momentum_boost'])
            returning_wrestler.adjust_popularity(angle['popularity_boost'])
            returning_wrestler.adjust_fatigue(-50)  # Fresh and ready
            
            # Save return angle to database
            angle['show_id'] = show_result.show_id
            angle['show_name'] = show_result.show_name
            angle['year'] = show_result.year
            angle['week'] = show_result.week
            
            save_return_angle(injury_manager.database, angle)
            
            # Save wrestler
            universe_state.save_wrestler(returning_wrestler)
            
            print(f"      Momentum: +{angle['momentum_boost']}")
            print(f"      Popularity: +{angle['popularity_boost']}")
            
            if target:
                # Create feud with target
                from models.feud import FeudType
                
                feud = universe_state.feud_manager.create_feud(
                    feud_type=FeudType.PERSONAL,
                    participant_ids=[returning_wrestler.id, target.id],
                    participant_names=[returning_wrestler.name, target.name],
                    year=show_result.year,
                    week=show_result.week,
                    initial_intensity=60
                )
                
                universe_state.save_feud(feud)
                
                show_result.add_event(
                    'feud_started',
                    f"🔥 {returning_wrestler.name} confronts {target.name}!"
                )
                
                print(f"      New feud with {target.name}")
    
    # ====================================================================
    # HELPER METHODS
    # ====================================================================
    
    def _get_wrestlers_on_card(
        self,
        show_draft: ShowDraft,
        universe_state
    ) -> List[Wrestler]:
        """Get all unique wrestlers appearing on the card (matches + segments)"""
        
        wrestler_ids = set()
        
        # Wrestlers in matches
        for match in show_draft.matches:
            wrestler_ids.update(match.side_a.wrestler_ids)
            wrestler_ids.update(match.side_b.wrestler_ids)
        
        # Wrestlers in segments (STEP 15)
        if show_draft.segments:
            for segment in show_draft.segments:
                participants = self._get_segment_participants(segment)
                for participant in participants:
                    wrestler_id = self._get_participant_id(participant)
                    if wrestler_id and wrestler_id not in ['interviewer', 'authority']:
                        wrestler_ids.add(wrestler_id)
        
        wrestlers = []
        for wid in wrestler_ids:
            wrestler = universe_state.get_wrestler_by_id(wid)
            if wrestler:
                wrestlers.append(wrestler)
        
        return wrestlers
    
    def _record_title_defense(self, match_result, show_result, universe_state):
        """Record title defense in lineage system"""
        if not match_result.is_title_match or not match_result.title_id:
            return
    
        # Get title
        title = universe_state.get_championship_by_id(match_result.title_id)
        if not title:
            return
    
        # Determine champion and challenger
        if match_result.winner == 'side_a':
            if title.current_holder_id in match_result.side_a.wrestler_ids:
                champion_id = title.current_holder_id
                champion_name = title.current_holder_name
                challenger_ids = match_result.side_b.wrestler_ids
                challenger_names = match_result.side_b.wrestler_names
                result = 'retained'
            else:
                # Title changed hands
                return  # Will be handled by title change logic
        else:
            if title.current_holder_id in match_result.side_b.wrestler_ids:
                champion_id = title.current_holder_id
                champion_name = title.current_holder_name
                challenger_ids = match_result.side_a.wrestler_ids
                challenger_names = match_result.side_a.wrestler_names
                result = 'retained'
            else:
                # Title changed hands
                return  # Will be handled by title change logic
    
        # For now, just take first challenger in multi-person matches
        challenger_id = challenger_ids[0] if challenger_ids else None
        challenger_name = challenger_names[0] if challenger_names else "Unknown"
    
        if not challenger_id:
            return
    
        # Create defense record
        from models.title_lineage import TitleDefense
    
        defense = TitleDefense(
            defense_id=f"def_{match_result.match_id}",
            title_id=match_result.title_id,
            champion_id=champion_id,
            champion_name=champion_name,
            challenger_id=challenger_id,
            challenger_name=challenger_name,
            show_id=show_result.show_id,
            show_name=show_result.show_name,
            year=show_result.year,
            week=show_result.week,
            result=result,
            finish_type=match_result.finish_type.value,
            star_rating=match_result.star_rating,
            match_duration=match_result.duration_minutes
        )
    
        # Record in database
        if hasattr(universe_state, 'lineage_tracker'):
            universe_state.lineage_tracker.record_title_defense(defense)

    
    def _calculate_brand_prestige(
        self,
        brand: str,
        universe_state
    ) -> int:
        """Calculate brand prestige (0-100) based on titles and roster quality"""
        
        brand_wrestlers = universe_state.get_wrestlers_by_brand(brand) if brand != 'Cross-Brand' else universe_state.get_active_wrestlers()
        
        if not brand_wrestlers:
            return 50
        
        avg_popularity = sum(w.popularity for w in brand_wrestlers) / len(brand_wrestlers)
        
        return int(avg_popularity)


# Global show simulator instance
show_simulator = ShowSimulator()
