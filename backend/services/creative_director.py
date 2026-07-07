"""
Creative Director Service - AI-powered show booking
Handles match selection, storyline integration, gender-separated booking
Works with both Wrestler objects and dict data from database
"""

import random
from typing import List, Dict, Optional, Union


class CreativeDirector:
    """
    AI Creative Director for booking shows
    """
    
    def __init__(self, show):
        self.show = show
        self.used_wrestlers = set()
    
    # ========================================================================
    # HELPER METHODS FOR ACCESSING WRESTLER DATA
    # ========================================================================
    
    def _get_wrestler_attr(self, wrestler: Union[object, dict], attr: str, default=None):
        """Get attribute from either Wrestler object or dict"""
        if isinstance(wrestler, dict):
            # overall_rating is a computed property not stored in DB - calculate it
            if attr == 'overall_rating':
                brawling = wrestler.get('brawling', 50)
                technical = wrestler.get('technical', 50)
                speed = wrestler.get('speed', 50)
                mic = wrestler.get('mic', 50)
                psychology = wrestler.get('psychology', 50)
                stamina = wrestler.get('stamina', 50)
                return int((brawling + technical + speed + mic + psychology + stamina) / 6)
            return wrestler.get(attr, default)
        else:
            return getattr(wrestler, attr, default)
    
    def _get_feud_attr(self, feud: Union[object, dict], attr: str, default=None):
        """Get attribute from either Feud object or dict"""
        if isinstance(feud, dict):
            # DB feuds store wrestlers as participant_ids list, not wrestler1_id/wrestler2_id
            if attr == 'wrestler1_id':
                ids = feud.get('participant_ids', [])
                return ids[0] if ids else default
            if attr == 'wrestler2_id':
                ids = feud.get('participant_ids', [])
                return ids[1] if len(ids) > 1 else default
            return feud.get(attr, default)
        else:
            return getattr(feud, attr, default)
    
    # ========================================================================
    # MAIN EVENT BOOKING
    # ========================================================================
    
    def book_main_event(self, male_roster: List, female_roster: List, 
                       feuds: List, production_plan: Dict) -> Optional[Dict]:
        """
        Book the main event based on production plan criteria
        Works with both Wrestler objects and dicts
        """
        try:
            main_event_criteria = production_plan.get('main_event_criteria', {})
            priority = main_event_criteria.get('priority', 'top_stars')
            
            # Determine division
            if priority == 'womens_revolution':
                roster = female_roster
                gender_division = 'female'
            else:
                roster = male_roster
                gender_division = 'male'
            
            # Filter available wrestlers
            available = [w for w in roster 
                        if self._get_wrestler_attr(w, 'id') not in self.used_wrestlers]
            
            if len(available) < 2:
                return None
            
            # Sort by rating
            available.sort(
                key=lambda w: self._get_wrestler_attr(w, 'overall_rating', 50), 
                reverse=True
            )
            
            # Check for relevant feuds
            for feud in feuds:
                intensity = self._get_feud_attr(feud, 'intensity', 0)
                
                if intensity >= 70:  # Hot feud
                    w1_id = self._get_feud_attr(feud, 'wrestler1_id')
                    w2_id = self._get_feud_attr(feud, 'wrestler2_id')
                    
                    wrestler1 = next(
                        (w for w in available 
                         if self._get_wrestler_attr(w, 'id') == w1_id), 
                        None
                    )
                    wrestler2 = next(
                        (w for w in available 
                         if self._get_wrestler_attr(w, 'id') == w2_id), 
                        None
                    )
                    
                    if wrestler1 and wrestler2:
                        self.used_wrestlers.add(self._get_wrestler_attr(wrestler1, 'id'))
                        self.used_wrestlers.add(self._get_wrestler_attr(wrestler2, 'id'))
                        
                        return {
                            'match_type': 'singles',
                            'participants': [
                                self._get_wrestler_attr(wrestler1, 'id'),
                                self._get_wrestler_attr(wrestler2, 'id')
                            ],
                            'gender_division': gender_division,
                            'is_intergender': False,
                            'importance': 'high_drama',
                            'booking_bias': 'even',
                            'feud_id': self._get_feud_attr(feud, 'id')
                        }
            
            # No feud, book top stars
            participant1 = available[0]
            participant2 = available[1]
            
            self.used_wrestlers.add(self._get_wrestler_attr(participant1, 'id'))
            self.used_wrestlers.add(self._get_wrestler_attr(participant2, 'id'))
            
            return {
                'match_type': 'singles',
                'participants': [
                    self._get_wrestler_attr(participant1, 'id'),
                    self._get_wrestler_attr(participant2, 'id')
                ],
                'gender_division': gender_division,
                'is_intergender': False,
                'importance': 'normal',
                'booking_bias': 'even'
            }
            
        except Exception as e:
            print(f"Error booking main event: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    # ========================================================================
    # OPENING MATCH BOOKING
    # ========================================================================
    
    def book_opening_match(self, male_roster: List, female_roster: List, 
                          feuds: List) -> Optional[Dict]:
        """Book a hot opening match"""
        try:
            # Alternate between male and female openers
            if random.random() > 0.7:  # 30% women's opening
                roster = female_roster
                gender_division = 'female'
            else:
                roster = male_roster
                gender_division = 'male'
            
            available = [
                w for w in roster 
                if self._get_wrestler_attr(w, 'id') not in self.used_wrestlers and 
                self._get_wrestler_attr(w, 'overall_rating', 0) >= 75
            ]
            
            if len(available) < 2:
                return None
            
            # Pick high-rated workers for fast-paced opening
            participants = random.sample(available, 2)
            
            for p in participants:
                self.used_wrestlers.add(self._get_wrestler_attr(p, 'id'))
            
            return {
                'match_type': 'singles',
                'participants': [self._get_wrestler_attr(p, 'id') for p in participants],
                'gender_division': gender_division,
                'is_intergender': False,
                'importance': 'normal',
                'booking_bias': 'even'
            }
            
        except Exception as e:
            print(f"Error booking opening match: {str(e)}")
            return None
    
    # ========================================================================
    # WOMEN'S MATCH BOOKING
    # ========================================================================
    
    def book_womens_match(self, female_roster: List, feuds: List) -> Optional[Dict]:
        """Book a women's division match"""
        try:
            available = [
                w for w in female_roster 
                if self._get_wrestler_attr(w, 'id') not in self.used_wrestlers
            ]
            
            if len(available) < 2:
                return None
            
            # Sort by rating
            available.sort(
                key=lambda w: self._get_wrestler_attr(w, 'overall_rating', 50), 
                reverse=True
            )
            
            # Check for women's feuds
            for feud in feuds:
                w1_id = self._get_feud_attr(feud, 'wrestler1_id')
                w2_id = self._get_feud_attr(feud, 'wrestler2_id')
                
                wrestler1 = next(
                    (w for w in available 
                     if self._get_wrestler_attr(w, 'id') == w1_id), 
                    None
                )
                wrestler2 = next(
                    (w for w in available 
                     if self._get_wrestler_attr(w, 'id') == w2_id), 
                    None
                )
                
                if (wrestler1 and wrestler2 and 
                    self._get_wrestler_attr(wrestler1, 'gender') == 'female' and 
                    self._get_wrestler_attr(wrestler2, 'gender') == 'female'):
                    
                    self.used_wrestlers.add(self._get_wrestler_attr(wrestler1, 'id'))
                    self.used_wrestlers.add(self._get_wrestler_attr(wrestler2, 'id'))
                    
                    return {
                        'match_type': 'singles',
                        'participants': [
                            self._get_wrestler_attr(wrestler1, 'id'),
                            self._get_wrestler_attr(wrestler2, 'id')
                        ],
                        'gender_division': 'female',
                        'is_intergender': False,
                        'importance': 'normal',
                        'booking_bias': 'even',
                        'feud_id': self._get_feud_attr(feud, 'id')
                    }
            
            # No feud, book top women
            participants = available[:2]
            
            for p in participants:
                self.used_wrestlers.add(self._get_wrestler_attr(p, 'id'))
            
            return {
                'match_type': 'singles',
                'participants': [self._get_wrestler_attr(p, 'id') for p in participants],
                'gender_division': 'female',
                'is_intergender': False,
                'importance': 'normal',
                'booking_bias': 'even'
            }
            
        except Exception as e:
            print(f"Error booking women's match: {str(e)}")
            return None
    
    # ========================================================================
    # TAG TEAM MATCH BOOKING
    # ========================================================================
    
    def book_tag_team_match(self, male_roster: List, feuds: List) -> Optional[Dict]:
        """Book a men's tag team match"""
        try:
            available = [
                w for w in male_roster 
                if self._get_wrestler_attr(w, 'id') not in self.used_wrestlers
            ]
            
            if len(available) < 4:
                return None
            
            # Randomly select 4 wrestlers for tag match
            participants = random.sample(available, 4)
            
            for p in participants:
                self.used_wrestlers.add(self._get_wrestler_attr(p, 'id'))
            
            return {
                'match_type': 'tag',
                'participants': [
                    [
                        self._get_wrestler_attr(participants[0], 'id'),
                        self._get_wrestler_attr(participants[1], 'id')
                    ],
                    [
                        self._get_wrestler_attr(participants[2], 'id'),
                        self._get_wrestler_attr(participants[3], 'id')
                    ]
                ],
                'gender_division': 'male',
                'is_intergender': False,
                'importance': 'normal',
                'booking_bias': 'even'
            }
            
        except Exception as e:
            print(f"Error booking tag team match: {str(e)}")
            return None
    
    # ========================================================================
    # INTERGENDER TAG MATCH BOOKING
    # ========================================================================
    
    def book_intergender_tag_match(self, male_roster: List, 
                                   female_roster: List) -> Optional[Dict]:
        """Book an intergender mixed tag team match (1M+1F vs 1M+1F)"""
        try:
            available_men = [
                w for w in male_roster 
                if self._get_wrestler_attr(w, 'id') not in self.used_wrestlers
            ]
            available_women = [
                w for w in female_roster 
                if self._get_wrestler_attr(w, 'id') not in self.used_wrestlers
            ]
            
            if len(available_men) < 2 or len(available_women) < 2:
                return None
            
            # Select 2 men and 2 women
            men = random.sample(available_men, 2)
            women = random.sample(available_women, 2)
            
            for w in men + women:
                self.used_wrestlers.add(self._get_wrestler_attr(w, 'id'))
            
            return {
                'match_type': 'mixed_tag',
                'participants': [
                    {
                        'male': self._get_wrestler_attr(men[0], 'id'),
                        'female': self._get_wrestler_attr(women[0], 'id')
                    },
                    {
                        'male': self._get_wrestler_attr(men[1], 'id'),
                        'female': self._get_wrestler_attr(women[1], 'id')
                    }
                ],
                'gender_division': 'intergender',
                'is_intergender': True,
                'importance': 'normal',
                'booking_bias': 'even'
            }
            
        except Exception as e:
            print(f"Error booking intergender tag match: {str(e)}")
            return None
    
    # ========================================================================
    # MIDCARD MATCH BOOKING
    # ========================================================================
    
    def book_midcard_match(self, male_roster: List, female_roster: List, 
                          feuds: List) -> Optional[Dict]:
        """Book a mid-card filler match"""
        try:
            # Alternate between divisions
            if random.random() > 0.6:
                roster = female_roster
                gender_division = 'female'
            else:
                roster = male_roster
                gender_division = 'male'
            
            available = [
                w for w in roster 
                if self._get_wrestler_attr(w, 'id') not in self.used_wrestlers
            ]
            
            if len(available) < 2:
                return None
            
            participants = random.sample(available, 2)
            
            for p in participants:
                self.used_wrestlers.add(self._get_wrestler_attr(p, 'id'))
            
            return {
                'match_type': 'singles',
                'participants': [self._get_wrestler_attr(p, 'id') for p in participants],
                'gender_division': gender_division,
                'is_intergender': False,
                'importance': 'normal',
                'booking_bias': 'even'
            }
            
        except Exception as e:
            print(f"Error booking midcard match: {str(e)}")
            return None
    
    # ========================================================================
    # FULL CARD GENERATION
    # ========================================================================
    
    def generate_full_card_dict(self, male_roster: List, female_roster: List,
                               feuds: List, production_plan: Dict) -> List[Dict]:
        """
        Generate complete card based on production plan
        Returns list of match dicts
        """
        matches = []
        target_matches = production_plan.get('target_matches', 5)
        
        # Main event
        main_event = self.book_main_event(
            male_roster, female_roster, feuds, production_plan
        )
        if main_event:
            matches.append(main_event)
        
        # Opening match (if hot opening requested)
        if production_plan.get('opening_segment_type') == 'hot_match':
            opening = self.book_opening_match(male_roster, female_roster, feuds)
            if opening:
                matches.insert(0, opening)
        
        # Women's division match
        if len(female_roster) >= 2:
            womens = self.book_womens_match(female_roster, feuds)
            if womens:
                matches.append(womens)
        
        # Tag match
        if len(male_roster) >= 4:
            tag = self.book_tag_team_match(male_roster, feuds)
            if tag:
                matches.append(tag)
        
        # Intergender (if theme requires)
        if production_plan.get('theme') == 'intergender_showcase':
            if len(male_roster) >= 2 and len(female_roster) >= 2:
                intergender = self.book_intergender_tag_match(male_roster, female_roster)
                if intergender:
                    matches.append(intergender)
        
        # Fill remaining slots with midcard
        while len(matches) < target_matches:
            midcard = self.book_midcard_match(male_roster, female_roster, feuds)
            if midcard:
                matches.append(midcard)
            else:
                break
        
        return matches
    
    def generate_default_card(self, male_roster: List, female_roster: List, 
                             feuds: List) -> List[Dict]:
        """Generate a default card without production plan"""
        matches = []
        
        # 1 main event
        main = self.book_main_event(
            male_roster, female_roster, feuds, 
            {'main_event_criteria': {'priority': 'top_stars'}}
        )
        if main:
            matches.append(main)
        
        # 1 women's match
        womens = self.book_womens_match(female_roster, feuds)
        if womens:
            matches.append(womens)
        
        # 1 tag match
        tag = self.book_tag_team_match(male_roster, feuds)
        if tag:
            matches.append(tag)
        
        # 2 midcard
        for _ in range(2):
            midcard = self.book_midcard_match(male_roster, female_roster, feuds)
            if midcard:
                matches.append(midcard)
        
        return matches
    
    def generate_default_card_dict(self, male_roster: List, female_roster: List,
                                   feuds: List) -> List[Dict]:
        """Alias for generate_default_card (returns dicts)"""
        return self.generate_default_card(male_roster, female_roster, feuds)
    
    # ========================================================================
    # SEGMENT GENERATION
    # ========================================================================
    
    def generate_segments(self, feuds: List, matches: List[Dict]) -> List[Dict]:
        """Generate segments based on feuds and booked matches"""
        segments = []
        
        # Opening promo (if no hot match)
        if not any(m.get('importance') == 'high_drama' for m in matches[:1]):
            opening_participants = []
            if matches:
                match_participants = matches[0].get('participants', [])
                for participant in match_participants:
                    if isinstance(participant, list):
                        opening_participants.extend(participant[:1])
                    elif isinstance(participant, dict):
                        opening_participants.extend([
                            participant.get('male'),
                            participant.get('female')
                        ])
                    else:
                        opening_participants.append(participant)
                opening_participants = [pid for pid in opening_participants if pid][:2]

            segments.append({
                'segment_type': 'promo',
                'participants': opening_participants,
                'duration': 5,
                'position': 0,
                'purpose': 'hype_match',
                'is_intergender': False
            })
        
        # Feud-building segments
        for idx, feud in enumerate(feuds[:2]):  # Top 2 feuds
            segments.append({
                'segment_type': 'backstage',
                'participants': [
                    self._get_feud_attr(feud, 'wrestler1_id'),
                    self._get_feud_attr(feud, 'wrestler2_id')
                ],
                'duration': 5,
                'position': (idx + 1) * 100,
                'purpose': 'build_feud',
                'is_intergender': False
            })
        
        return segments
    
    def generate_segments_dict(self, feuds: List, matches: List[Dict]) -> List[Dict]:
        """Alias for generate_segments (returns dicts)"""
        return self.generate_segments(feuds, matches)
