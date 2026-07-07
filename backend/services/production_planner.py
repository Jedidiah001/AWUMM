"""
Production Planner Service - Show Planning & Theme Management
Handles show structure, pacing, themes, and production quality
"""

import random
from datetime import datetime
from typing import Dict, List, Optional

class ProductionPlanner:
    """
    Production planning and show structure management
    """
    
    # Show themes with bonuses
    SHOW_THEMES = {
        'standard': {
            'name': 'Standard Show',
            'description': 'Regular weekly programming',
            'match_quality_bonus': 0.0,
            'attendance_bonus_pct': 0.0,
            'min_matches': 4,
            'max_matches': 6
        },
        'championship_night': {
            'name': 'Championship Night',
            'description': 'Multiple title matches',
            'match_quality_bonus': 0.3,
            'attendance_bonus_pct': 0.15,
            'min_matches': 5,
            'max_matches': 6,
            'required_title_matches': 3
        },
        'rivalry_resolution': {
            'name': 'Rivalry Resolution',
            'description': 'Major feuds culminate',
            'match_quality_bonus': 0.4,
            'attendance_bonus_pct': 0.20,
            'min_matches': 4,
            'max_matches': 5,
            'special_stipulations': ['steel_cage', 'ladder_match', 'last_man_standing']
        },
        'womens_revolution': {
            'name': 'Women\'s Revolution',
            'description': 'Women\'s wrestling showcase',
            'match_quality_bonus': 0.2,
            'attendance_bonus_pct': 0.10,
            'min_matches': 5,
            'max_matches': 6,
            'min_womens_matches': 3
        },
        'intergender_showcase': {
            'name': 'Intergender Showcase',
            'description': 'Mixed gender competition',
            'match_quality_bonus': 0.25,
            'attendance_bonus_pct': 0.12,
            'min_matches': 5,
            'max_matches': 6,
            'required_intergender': 1
        },
        'battle_night': {
            'name': 'Battle Night',
            'description': 'Multi-person matches',
            'match_quality_bonus': 0.15,
            'attendance_bonus_pct': 0.08,
            'min_matches': 4,
            'max_matches': 5,
            'multi_person_focus': True
        },
        'supercard': {
            'name': 'Special Supercard',
            'description': 'Stacked premium show',
            'match_quality_bonus': 0.5,
            'attendance_bonus_pct': 0.30,
            'min_matches': 6,
            'max_matches': 8
        }
    }
    
    # Opening segment types
    OPENING_TYPES = [
        'hot_match',          # Start with exciting match
        'authority_promo',    # GM/Commissioner announcement
        'champion_celebration', # Title holder celebrates
        'surprise_return',    # Unexpected return
        'confrontation'       # Face-off between rivals
    ]
    
    # Main event criteria
    MAIN_EVENT_PRIORITIES = {
        'top_stars': 'Highest-rated wrestlers',
        'hottest_feud': 'Most intense active rivalry',
        'title_match': 'Championship on the line',
        'womens_revolution': 'Women\'s main event',
        'stipulation_match': 'Special match type',
        'dream_match': 'Fantasy matchup'
    }
    
    def __init__(self, show):
        self.show = show
        self.theme = None
        self.target_matches = 5
        self.total_runtime_minutes = 120  # 2 hours default
    
    def generate_production_plan(self) -> Dict:
        """
        Generate a complete production plan for the show
        """
        # Determine show type
        show_type = self.show.show_type
        
        # Select theme
        theme = self._select_theme(show_type)
        theme_config = self.SHOW_THEMES.get(theme, self.SHOW_THEMES['standard'])
        
        # Calculate target matches
        if show_type == 'ppv':
            self.target_matches = random.randint(7, 9)
            self.total_runtime_minutes = 180  # 3 hours
        elif show_type == 'supercard':
            self.target_matches = random.randint(6, 8)
            self.total_runtime_minutes = 150  # 2.5 hours
        else:
            self.target_matches = random.randint(
                theme_config['min_matches'],
                theme_config['max_matches']
            )
            self.total_runtime_minutes = 120
        
        # Opening segment
        opening_type = self._select_opening_type(theme)
        
        # Main event criteria
        main_event_criteria = self._determine_main_event(theme)
        
        # Commercial breaks (TV only)
        commercial_breaks = []
        if show_type == 'weekly_tv':
            commercial_breaks = self._plan_commercial_breaks()
        
        # Pacing strategy
        pacing = self._create_pacing_strategy()
        
        # Build complete plan
        production_plan = {
            'theme': theme,
            'theme_display_name': theme_config['name'],
            'theme_description': theme_config['description'],
            'theme_bonus_match_quality': theme_config['match_quality_bonus'],
            'theme_bonus_attendance_pct': theme_config['attendance_bonus_pct'],
            
            'target_matches': self.target_matches,
            'total_runtime_minutes': self.total_runtime_minutes,
            
            'opening_segment_type': opening_type,
            'main_event_criteria': main_event_criteria,
            
            'commercial_breaks': commercial_breaks,
            'pacing_strategy': pacing,
            
            'special_requirements': self._get_theme_requirements(theme_config),
            
            'created_at': datetime.now().isoformat()
        }
        
        return production_plan
    
    def _select_theme(self, show_type: str) -> str:
        """Select appropriate theme based on show type and randomness"""
        if show_type == 'ppv':
            # PPVs get special themes
            return random.choice(['championship_night', 'rivalry_resolution', 'supercard'])
        elif show_type == 'supercard':
            return 'supercard'
        else:
            # Weekly TV - mostly standard, occasionally special
            weights = {
                'standard': 60,
                'championship_night': 10,
                'rivalry_resolution': 5,
                'womens_revolution': 10,
                'intergender_showcase': 5,
                'battle_night': 10
            }
            
            themes = list(weights.keys())
            theme_weights = list(weights.values())
            
            return random.choices(themes, weights=theme_weights, k=1)[0]
    
    def _select_opening_type(self, theme: str) -> str:
        """Select opening segment type based on theme"""
        if theme == 'rivalry_resolution':
            return 'confrontation'
        elif theme == 'championship_night':
            return random.choice(['champion_celebration', 'hot_match'])
        elif theme == 'womens_revolution':
            return 'hot_match'  # Women's opening match
        else:
            return random.choice(self.OPENING_TYPES)
    
    def _determine_main_event(self, theme: str) -> Dict:
        """Determine main event criteria based on theme"""
        if theme == 'championship_night':
            priority = 'title_match'
        elif theme == 'rivalry_resolution':
            priority = 'hottest_feud'
        elif theme == 'womens_revolution':
            priority = 'womens_revolution'
        elif theme == 'battle_night':
            priority = 'stipulation_match'
        else:
            priority = random.choice(list(self.MAIN_EVENT_PRIORITIES.keys()))
        
        return {
            'priority': priority,
            'reason': self.MAIN_EVENT_PRIORITIES[priority]
        }
    
    def _plan_commercial_breaks(self) -> List[Dict]:
        """Plan commercial break positions for TV shows"""
        # Standard TV format: ~6 commercial breaks over 2 hours
        breaks = []
        
        # Break after opening segment (8 min)
        breaks.append({
            'position': 8,
            'duration': 3,
            'type': 'standard'
        })
        
        # Break after first match (~25 min)
        breaks.append({
            'position': 25,
            'duration': 3,
            'type': 'standard'
        })
        
        # Mid-show break (~45 min)
        breaks.append({
            'position': 45,
            'duration': 4,
            'type': 'mid_show'
        })
        
        # Break after mid-card (~65 min)
        breaks.append({
            'position': 65,
            'duration': 3,
            'type': 'standard'
        })
        
        # Pre-main event break (~85 min)
        breaks.append({
            'position': 85,
            'duration': 3,
            'type': 'standard'
        })
        
        # Final break during main event (~105 min)
        breaks.append({
            'position': 105,
            'duration': 3,
            'type': 'cliffhanger'
        })
        
        return breaks
    
    def _create_pacing_strategy(self) -> Dict:
        """Create pacing strategy for the show"""
        return {
            'opening_intensity': 'high',      # Start hot
            'first_hour': 'build_momentum',   # Build excitement
            'second_hour': 'peak_and_deliver', # Deliver payoffs
            
            'match_time_distribution': {
                'opener': '10-12 min',
                'midcard': '8-10 min',
                'womens': '10-12 min',
                'semi_main': '15-18 min',
                'main_event': '20-25 min'
            },
            
            'segment_placement': {
                'backstage': 'between_matches',
                'promos': 'after_commercial',
                'video_packages': 'before_main_event'
            }
        }
    
    def _get_theme_requirements(self, theme_config: Dict) -> Dict:
        """Extract special requirements from theme"""
        requirements = {}
        
        if 'required_title_matches' in theme_config:
            requirements['min_title_matches'] = theme_config['required_title_matches']
        
        if 'min_womens_matches' in theme_config:
            requirements['min_womens_matches'] = theme_config['min_womens_matches']
        
        if 'required_intergender' in theme_config:
            requirements['min_intergender_matches'] = theme_config['required_intergender']
        
        if 'special_stipulations' in theme_config:
            requirements['suggested_stipulations'] = theme_config['special_stipulations']
        
        if 'multi_person_focus' in theme_config:
            requirements['multi_person_focus'] = True
        
        return requirements
    
    def calculate_show_bonuses(self, match_results: List[Dict]) -> Dict:
        """
        Calculate bonuses applied to the show based on production plan
        """
        theme_config = self.SHOW_THEMES.get(self.theme, self.SHOW_THEMES['standard'])
        
        bonuses = {
            'match_quality_bonus': theme_config['match_quality_bonus'],
            'attendance_multiplier': 1.0 + theme_config['attendance_bonus_pct'],
            'revenue_multiplier': 1.0 + theme_config['attendance_bonus_pct'],
            
            # Additional bonuses for meeting requirements
            'theme_bonus_applied': False
        }
        
        # Check if theme requirements were met
        requirements_met = self._check_requirements_met(match_results)
        
        if requirements_met:
            bonuses['theme_bonus_applied'] = True
            bonuses['match_quality_bonus'] += 0.1  # Extra bonus
        
        return bonuses
    
    def _check_requirements_met(self, match_results: List[Dict]) -> bool:
        """Check if theme requirements were met"""
        # Placeholder - would check actual match results
        return True


# ============================================================================
# MATCH SIMULATOR SERVICE
# ============================================================================

class MatchSimulator:
    """
    Match simulation engine with gender-aware logic
    """
    
    FINISH_TYPES = {
        'clean': {'weight': 60, 'rating_impact': 0.0},
        'submission': {'weight': 15, 'rating_impact': 0.1},
        'knockout': {'weight': 10, 'rating_impact': 0.15},
        'dirty': {'weight': 8, 'rating_impact': -0.2},
        'dq': {'weight': 5, 'rating_impact': -0.3},
        'countout': {'weight': 2, 'rating_impact': -0.4}
    }
    
    def __init__(self):
        self.match_history = []
    
    def simulate_match(self, match, production_plan: Optional[Dict] = None) -> Dict:
        """
        Simulate a match and generate result
        """
        from models.wrestler import Wrestler
        
        # Get participants
        participants = self._get_match_participants(match)
        
        if not participants:
            return self._create_error_result("No valid participants")
        
        # Calculate base match quality
        base_quality = self._calculate_base_quality(participants, match)
        
        # Apply production bonuses
        if production_plan:
            theme_bonus = production_plan.get('theme_bonus_match_quality', 0.0)
            base_quality += theme_bonus
        
        # Apply match importance modifier
        importance = match.importance if hasattr(match, 'importance') else 'normal'
        if importance == 'high_drama':
            base_quality += 0.3
        elif importance == 'protect_both':
            base_quality += 0.1
        
        # Apply special stipulation bonus
        if hasattr(match, 'special_stipulation') and match.special_stipulation:
            base_quality += self._get_stipulation_bonus(match.special_stipulation)
        
        # Determine winner
        winner = self._determine_winner(participants, match)
        
        # Determine finish type
        finish_type = self._determine_finish_type(match, base_quality)
        finish_impact = self.FINISH_TYPES[finish_type]['rating_impact']
        
        # Final rating (0.0 - 5.0 stars)
        final_rating = max(0.0, min(5.0, base_quality + finish_impact + random.uniform(-0.3, 0.3)))
        
        # Check for title change
        title_change = False
        if hasattr(match, 'is_title_match') and match.is_title_match:
            title_change = self._check_title_change(match, winner)
        
        # Check for upset
        was_upset = self._check_if_upset(participants, winner)
        
        # Generate result
        result = {
            'match_id': match.id if hasattr(match, 'id') else None,
            'match_type': match.match_type if hasattr(match, 'match_type') else 'singles',
            'winner_id': winner.id if winner else None,
            'rating': round(final_rating, 2),
            'finish_type': finish_type,
            'duration_minutes': self._calculate_match_duration(match, final_rating),
            'title_change': title_change,
            'was_upset': was_upset,
            'is_intergender': match.is_intergender if hasattr(match, 'is_intergender') else False,
            'highlights': self._generate_match_highlights(participants, winner, final_rating)
        }
        
        self.match_history.append(result)
        return result
    
    def _get_match_participants(self, match):
        """Extract participant wrestler objects from match"""
        from models.wrestler import Wrestler
        
        participants = []
        
        if hasattr(match, 'participants_json'):
            participant_data = match.participants_json
        else:
            return []
        
        # Handle different match types
        if isinstance(participant_data, list):
            for item in participant_data:
                if isinstance(item, dict):
                    # Intergender team
                    if 'male' in item and 'female' in item:
                        male = Wrestler.query.get(item['male'])
                        female = Wrestler.query.get(item['female'])
                        if male:
                            participants.append(male)
                        if female:
                            participants.append(female)
                elif isinstance(item, list):
                    # Tag team
                    for wrestler_id in item:
                        wrestler = Wrestler.query.get(wrestler_id)
                        if wrestler:
                            participants.append(wrestler)
                else:
                    # Singles
                    wrestler = Wrestler.query.get(item)
                    if wrestler:
                        participants.append(wrestler)
        
        return participants
    
    def _calculate_base_quality(self, participants: List, match) -> float:
        """Calculate base match quality from participant ratings"""
        if not participants:
            return 2.0
        
        # Average rating of participants
        avg_rating = sum(w.overall_rating for w in participants) / len(participants)
        
        # Convert to 0-5 scale
        base_quality = (avg_rating / 100.0) * 5.0
        
        # Gender diversity bonus for intergender
        if hasattr(match, 'is_intergender') and match.is_intergender:
            base_quality += 0.15  # Novelty bonus
        
        # Match type modifier
        match_type = match.match_type if hasattr(match, 'match_type') else 'singles'
        
        if match_type in ['triple_threat', 'fatal_4way']:
            base_quality += 0.2  # Multi-person excitement
        elif match_type == 'ladder_match':
            base_quality += 0.3  # Spectacular spots
        elif match_type == 'battle_royal':
            base_quality -= 0.3  # Often messy
        
        return base_quality
    
    def _get_stipulation_bonus(self, stipulation: str) -> float:
        """Get quality bonus for special stipulations"""
        bonuses = {
            'steel_cage': 0.3,
            'hell_in_a_cell': 0.4,
            'ladder_match': 0.35,
            'tlc': 0.4,
            'iron_man': 0.3,
            'last_man_standing': 0.25,
            'i_quit': 0.3,
            'no_dq': 0.1,
            'street_fight': 0.15,
            'submission': 0.1
        }
        
        return bonuses.get(stipulation, 0.0)
    
    def _determine_winner(self, participants: List, match):
        """Determine match winner based on booking bias and ratings"""
        if not participants:
            return None
        
        # Check for booked winner
        if hasattr(match, 'booked_winner_id') and match.booked_winner_id:
            booked = next((p for p in participants if p.id == match.booked_winner_id), None)
            if booked:
                return booked
        
        # Get booking bias
        bias = match.booking_bias if hasattr(match, 'booking_bias') else 'even'
        
        # For intergender, need special logic
        if hasattr(match, 'is_intergender') and match.is_intergender:
            return self._determine_intergender_winner(participants, bias)
        
        # Standard booking logic
        if bias == 'even':
            # Weight by rating
            weights = [w.overall_rating for w in participants]
            return random.choices(participants, weights=weights, k=1)[0]
        
        elif bias.startswith('strong_'):
            # 85% chance for side A or B
            if bias == 'strong_a':
                return participants[0] if random.random() < 0.85 else participants[-1]
            else:
                return participants[-1] if random.random() < 0.85 else participants[0]
        
        elif bias.startswith('slight_'):
            # 65% chance for side A or B
            if bias == 'slight_a':
                return participants[0] if random.random() < 0.65 else participants[-1]
            else:
                return participants[-1] if random.random() < 0.65 else participants[0]
        
        # Default: highest rated
        return max(participants, key=lambda w: w.overall_rating)
    
    def _determine_intergender_winner(self, participants: List, bias: str):
        """Special logic for intergender matches"""
        # In mixed tag, either gender can win
        # Weight equally between male/female participants
        
        male_participants = [p for p in participants if p.gender == 'male']
        female_participants = [p for p in participants if p.gender == 'female']
        
        # 50/50 gender split first
        if random.random() < 0.5 and female_participants:
            pool = female_participants
        elif male_participants:
            pool = male_participants
        else:
            pool = participants
        
        # Then weight by rating within gender
        weights = [w.overall_rating for w in pool]
        return random.choices(pool, weights=weights, k=1)[0]
    
    def _determine_finish_type(self, match, quality: float) -> str:
        """Determine how the match ends"""
        # Higher quality matches more likely to have clean finish
        if quality >= 4.0:
            # Great match - 80% clean
            if random.random() < 0.8:
                return 'clean'
        
        # Select finish based on weights
        finish_types = list(self.FINISH_TYPES.keys())
        weights = [self.FINISH_TYPES[ft]['weight'] for ft in finish_types]
        
        return random.choices(finish_types, weights=weights, k=1)[0]
    
    def _check_title_change(self, match, winner) -> bool:
        """Check if title changes hands"""
        from models.championship import Championship
        
        if not hasattr(match, 'title_id') or not match.title_id:
            return False
        
        title = Championship.query.get(match.title_id)
        if not title:
            return False
        
        # If winner is not current champion, title changes
        if title.current_champion_id != winner.id:
            title.current_champion_id = winner.id
            title.reign_start_date = datetime.now()
            return True
        
        return False
    
    def _check_if_upset(self, participants: List, winner) -> bool:
        """Check if result is considered an upset"""
        if not participants or not winner:
            return False
        
        # Upset if winner is significantly lower rated
        avg_rating = sum(p.overall_rating for p in participants) / len(participants)
        
        return winner.overall_rating < (avg_rating - 10)
    
    def _calculate_match_duration(self, match, rating: float) -> int:
        """Calculate match duration in minutes"""
        base_duration = 12
        
        match_type = match.match_type if hasattr(match, 'match_type') else 'singles'
        
        # Match type modifiers
        if match_type == 'rumble':
            return 60
        elif match_type == 'battle_royal':
            return 20
        elif match_type == 'iron_man':
            return 30
        elif match_type in ['triple_threat', 'fatal_4way']:
            base_duration = 15
        
        # Importance modifier
        importance = match.importance if hasattr(match, 'importance') else 'normal'
        if importance == 'high_drama':
            base_duration += 8
        
        # Title match modifier
        if hasattr(match, 'is_title_match') and match.is_title_match:
            base_duration += 5
        
        # Quality modifier
        base_duration += int((rating - 2.5) * 2)
        
        return max(5, min(30, base_duration))
    
    def _generate_match_highlights(self, participants: List, winner, rating: float) -> List[str]:
        """Generate narrative highlights for the match"""
        highlights = []
        
        if rating >= 4.5:
            highlights.append("⭐ Match of the Night candidate!")
        elif rating >= 4.0:
            highlights.append("🔥 Excellent match quality")
        
        if winner:
            highlights.append(f"🏆 {winner.ring_name} picks up the victory")
        
        if len(participants) > 2:
            highlights.append(f"💥 {len(participants)}-person chaos!")
        
        return highlights
    
    def _create_error_result(self, error_msg: str) -> Dict:
        """Create error result for failed simulation"""
        return {
            'error': error_msg,
            'rating': 0.0,
            'winner_id': None,
            'finish_type': 'error'
        }