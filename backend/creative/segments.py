"""
Segment Generator
AI system that creates segments for shows based on feuds, storylines, and roster.

Generates:
- Opening segments to start shows
- Filler segments between matches
- Main event build segments
- Post-match segments
"""

import random
from typing import List, Optional, Dict, Any

from models.segment import SegmentTemplate, SegmentType, SegmentTone, SegmentLocation
from models.wrestler import Wrestler
from models.championship import Championship
from models.feud import Feud
from models.calendar import ScheduledShow


class SegmentGenerator:
    """Generates appropriate segments for shows"""
    
    def __init__(self):
        # Interviewer names
        self.interviewers = [
            "Rachel Stone",
            "Michael Cole",
            "Kevin Patrick",
            "Sarah Mitchell",
            "Byron Saxton"
        ]
        
        # Authority figure names
        self.authority_figures = [
            "General Manager",
            "Commissioner",
            "President",
            "Director of Operations"
        ]
    
    def generate_segments_for_show(
        self,
        show_type: str,  # 'weekly_tv' or 'ppv'
        is_ppv: bool,
        brand_roster: List[Wrestler],
        active_feuds: List[Feud],
        titles: List[Championship],
        max_segments: int = 3
    ) -> List[SegmentTemplate]:
        """
        Generate appropriate segments for a show.
        
        Args:
            show_type: Type of show
            is_ppv: True if PPV/PLE
            brand_roster: Available wrestlers
            active_feuds: Current feuds
            titles: Championships
            max_segments: Maximum segments to generate
        
        Returns:
            List of SegmentTemplates
        """
        
        segments = []
        
        # Filter available wrestlers (not injured, can appear)
        available = [w for w in brand_roster if w.can_compete]
        
        if not available:
            return segments
        
        # PPVs get more segments
        if is_ppv:
            target_segments = min(max_segments, 4)
        else:
            target_segments = min(max_segments, 2)
        
        # 1. Hot feud segments (priority)
        hot_feuds = [f for f in active_feuds if f.intensity >= 60]
        
        for feud in hot_feuds[:1]:  # Max 1 feud segment per show
            segment = self._generate_feud_segment(feud, available)
            if segment:
                segments.append(segment)
        
        # 2. Championship segment (if champion is available)
        if len(segments) < target_segments:
            for title in titles:
                if not title.is_vacant:
                    champion = self._find_wrestler(title.current_holder_id, available)
                    if champion:
                        segment = self._generate_championship_segment(champion, title)
                        if segment:
                            segments.append(segment)
                            break
        
        # 3. Rising star promo (momentum > 20)
        if len(segments) < target_segments:
            rising_stars = [w for w in available if w.momentum > 20]
            if rising_stars:
                star = random.choice(rising_stars)
                segment = self._generate_promo_segment(star)
                if segment:
                    segments.append(segment)
        
        # 4. Random interview or confrontation
        if len(segments) < target_segments:
            segment_type = random.choice(['interview', 'confrontation'])
            
            if segment_type == 'interview' and len(available) >= 1:
                subject = random.choice(available)
                segment = SegmentTemplate.create_interview(
                    interviewer_name=random.choice(self.interviewers),
                    subject_id=subject.id,
                    subject_name=subject.name,
                    mic_skill=subject.mic  # FIXED: was mic
                )
                segments.append(segment)
            
            elif segment_type == 'confrontation' and len(available) >= 2:
                w1, w2 = random.sample(available, 2)
                segment = SegmentTemplate.create_confrontation(
                    wrestler1_id=w1.id,
                    wrestler1_name=w1.name,
                    wrestler2_id=w2.id,
                    wrestler2_name=w2.name,
                    ends_in_brawl=random.random() < 0.3
                )
                segments.append(segment)
        
        # Assign card positions
        for i, segment in enumerate(segments):
            if i == 0:
                segment.is_opening = True
                segment.card_position = 0
            else:
                segment.card_position = i * 2  # Space between matches
        
        return segments[:target_segments]
    
    def _generate_feud_segment(
        self,
        feud: Feud,
        available: List[Wrestler]
    ) -> Optional[SegmentTemplate]:
        """Generate a segment for a feud"""
        
        # Get feud participants who are available
        participants = []
        for pid in feud.participant_ids[:2]:  # Max 2 for segment
            wrestler = self._find_wrestler(pid, available)
            if wrestler:
                participants.append(wrestler)
        
        if len(participants) < 2:
            return None
        
        # High intensity = more confrontational
        if feud.intensity >= 80:
            segment_types = ['confrontation', 'promo_battle', 'attack']
            weights = [40, 30, 30]
        elif feud.intensity >= 60:
            segment_types = ['promo_battle', 'confrontation', 'interview']
            weights = [40, 35, 25]
        else:
            segment_types = ['promo', 'interview', 'confrontation']
            weights = [40, 35, 25]
        
        segment_type = random.choices(segment_types, weights=weights)[0]
        
        if segment_type == 'promo':
            speaker = max(participants, key=lambda w: w.mic)  # FIXED: was mic
            return SegmentTemplate.create_promo(
                speaker_id=speaker.id,
                speaker_name=speaker.name,
                mic_skill=speaker.mic,  # FIXED: was mic
                feud_id=feud.id,
                tone=SegmentTone.INTENSE
            )
        
        elif segment_type == 'promo_battle':
            return SegmentTemplate.create_promo_battle(
                participants=[(w.id, w.name, w.mic) for w in participants],  # FIXED: was mic
                feud_id=feud.id
            )
        
        elif segment_type == 'confrontation':
            return SegmentTemplate.create_confrontation(
                wrestler1_id=participants[0].id,
                wrestler1_name=participants[0].name,
                wrestler2_id=participants[1].id,
                wrestler2_name=participants[1].name,
                feud_id=feud.id,
                ends_in_brawl=feud.intensity >= 70
            )
        
        elif segment_type == 'attack':
            attacker = random.choice(participants)
            victim = [p for p in participants if p.id != attacker.id][0]
            
            return SegmentTemplate.create_attack(
                attacker_id=attacker.id,
                attacker_name=attacker.name,
                victim_id=victim.id,
                victim_name=victim.name,
                location='backstage' if random.random() < 0.6 else 'in_ring'
            )
        
        elif segment_type == 'interview':
            subject = max(participants, key=lambda w: w.mic)  # FIXED: was mic
            return SegmentTemplate.create_interview(
                interviewer_name=random.choice(self.interviewers),
                subject_id=subject.id,
                subject_name=subject.name,
                mic_skill=subject.mic,  # FIXED: was mic
                feud_id=feud.id
            )
        
        return None
    
    def _generate_championship_segment(
        self,
        champion: Wrestler,
        title: Championship
    ) -> Optional[SegmentTemplate]:
        """Generate a championship-related segment"""
        
        segment_types = ['celebration', 'promo', 'interview']
        weights = [20, 50, 30]
        
        segment_type = random.choices(segment_types, weights=weights)[0]
        
        if segment_type == 'celebration':
            return SegmentTemplate.create_celebration(
                champion_id=champion.id,
                champion_name=champion.name,
                title_name=title.name,
                title_id=title.id
            )
        
        elif segment_type == 'promo':
            tone = SegmentTone.CELEBRATORY if champion.alignment == 'Face' else SegmentTone.THREATENING
            
            return SegmentTemplate.create_promo(
                speaker_id=champion.id,
                speaker_name=champion.name,
                mic_skill=champion.mic,  # FIXED: was mic
                tone=tone
            )
        
        elif segment_type == 'interview':
            return SegmentTemplate.create_interview(
                interviewer_name=random.choice(self.interviewers),
                subject_id=champion.id,
                subject_name=champion.name,
                mic_skill=champion.mic  # FIXED: was mic
            )
        
        return None
    
    def _generate_promo_segment(
        self,
        wrestler: Wrestler
    ) -> Optional[SegmentTemplate]:
        """Generate a basic promo segment"""
        
        # Choose tone based on alignment and momentum
        if wrestler.alignment == 'Face':
            if wrestler.momentum > 30:
                tone = SegmentTone.CELEBRATORY
            else:
                tone = SegmentTone.EMOTIONAL
        elif wrestler.alignment == 'Heel':
            tone = SegmentTone.THREATENING
        else:  # Tweener
            tone = SegmentTone.INTENSE
        
        return SegmentTemplate.create_promo(
            speaker_id=wrestler.id,
            speaker_name=wrestler.name,
            mic_skill=wrestler.mic,  # FIXED: was mic
            tone=tone
        )
    
    def generate_post_match_segment(
        self,
        winner_id: str,
        winner_name: str,
        loser_id: str,
        loser_name: str,
        is_title_match: bool = False,
        is_upset: bool = False
    ) -> Optional[SegmentTemplate]:
        """
        Generate a post-match segment if warranted.
        
        Called after important matches for additional story development.
        """
        
        # Upsets often lead to attacks
        if is_upset and random.random() < 0.4:
            return SegmentTemplate.create_attack(
                attacker_id=loser_id,
                attacker_name=loser_name,
                victim_id=winner_id,
                victim_name=winner_name,
                location='in_ring'
            )
        
        # Title wins might get celebrations
        if is_title_match and random.random() < 0.3:
            return SegmentTemplate.create_celebration(
                champion_id=winner_id,
                champion_name=winner_name,
                title_name="Championship",  # Would need actual title
                title_id="title"
            )
        
        return None
    
    def generate_contract_signing(
        self,
        wrestler1: Wrestler,
        wrestler2: Wrestler,
        match_stipulation: str = "Championship Match"
    ) -> SegmentTemplate:
        """Generate a contract signing segment (usually for PPV build)"""
        
        authority = random.choice(self.authority_figures)
        
        return SegmentTemplate.create_contract_signing(
            wrestler1_id=wrestler1.id,
            wrestler1_name=wrestler1.name,
            wrestler2_id=wrestler2.id,
            wrestler2_name=wrestler2.name,
            match_stipulation=match_stipulation,
            authority_name=authority
        )
    
    def generate_surprise_return(
        self,
        returning_wrestler: Wrestler
    ) -> SegmentTemplate:
        """Generate a surprise return segment"""
        
        return SegmentTemplate.create_return(
            returning_id=returning_wrestler.id,
            returning_name=returning_wrestler.name
        )
    
    
    def generate_ducking_challenger_segment(
        self,
        championship,
        champion,
        challenger,
        days_overdue: int
    ):
        """
        Generate a segment where a challenger calls out the champion for avoiding defenses.
    
        Args:
            championship: The championship in question
            champion: The current champion
            challenger: The wrestler calling them out
            days_overdue: How many days the defense is overdue
        """
        from models.segment import SegmentTemplate, SegmentTone
    
        promo_lines = [
            f"{champion.name}, you've held that {championship.name} for {days_overdue} days without defending it!",
            f"You call yourself a champion? More like a coward!",
            f"I'm challenging you RIGHT NOW - defend that title or VACATE IT!",
            f"The people deserve a fighting champion, not someone who runs and hides!"
        ]
    
        segment = SegmentTemplate.create_promo(
            speaker_id=challenger.id,
            speaker_name=challenger.name,
            mic_skill=challenger.mic,
            tone=SegmentTone.AGGRESSIVE
        )
    
        segment.description = f"{challenger.name} calls out {champion.name} for avoiding title defenses"
        segment.promo_content = promo_lines
        segment.target_wrestler_id = champion.id
        segment.target_wrestler_name = champion.name
        segment.involves_title = championship.id

        return segment

    
    def _find_wrestler(
        self,
        wrestler_id: str,
        roster: List[Wrestler]
    ) -> Optional[Wrestler]:
        """Find wrestler in roster by ID"""
        for wrestler in roster:
            if wrestler.id == wrestler_id:
                return wrestler
        return None


# Global segment generator instance
segment_generator = SegmentGenerator()