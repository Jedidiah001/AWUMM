"""
Special Match Types
Selection logic for stipulation matches (cage, ladder, no DQ, etc.)

Used for:
- PPV variety
- Feud blowoffs
- Title matches
- Special occasions
"""

from typing import List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass  # ← ADD THIS LINE
import random


class SpecialMatchType(Enum):
    """Special stipulation matches"""
    
    # Containment
    STEEL_CAGE = "steel_cage"              # Cage match, escape or pinfall
    HELL_IN_A_CELL = "hell_in_a_cell"      # Massive cage, brutal
    
    # High-flying
    LADDER_MATCH = "ladder_match"          # Climb ladder to win
    TLC = "tlc"                            # Tables, Ladders, Chairs
    
    # Brawling
    NO_DQ = "no_dq"                        # No disqualifications
    STREET_FIGHT = "street_fight"          # No DQ, falls count anywhere
    LAST_MAN_STANDING = "last_man_standing"  # Must answer 10 count
    
    # Specialty
    IRON_MAN = "iron_man"                  # Timed match, most falls wins
    SUBMISSION = "submission"              # Only submissions allowed
    I_QUIT = "i_quit"                      # Must say "I Quit"
    
    # Multi-person
    ELIMINATION = "elimination"            # Eliminate all opponents
    GAUNTLET = "gauntlet"                  # Face multiple opponents in succession
    
    # Career-ending
    LOSER_LEAVES_TOWN = "loser_leaves_town"  # Loser is fired


@dataclass
class SpecialMatchRecommendation:
    """Recommendation for a special match type"""
    match_type: SpecialMatchType
    reason: str
    confidence: float  # 0.0 - 1.0


class SpecialMatchSelector:
    """Determines when and what special matches to book"""
    
    def __init__(self):
        pass
    
    def should_book_special_match(
        self,
        is_ppv: bool,
        is_major_ppv: bool,
        feud_intensity: Optional[int] = None,
        is_title_match: bool = False,
        card_position: int = 5
    ) -> Tuple[bool, float]:
        """
        Determine if a special match is warranted.
        
        Returns:
            (should_book, probability)
        """
        
        probability = 0.0
        
        # PPVs have higher chance
        if is_major_ppv:
            probability += 0.4
        elif is_ppv:
            probability += 0.25
        else:
            probability += 0.05  # Rare on TV
        
        # Hot feuds benefit from stipulations
        if feud_intensity:
            if feud_intensity >= 80:
                probability += 0.3
            elif feud_intensity >= 60:
                probability += 0.2
        
        # Title matches can have stips
        if is_title_match:
            probability += 0.1
        
        # Main events more likely
        if card_position >= 7:
            probability += 0.15
        
        # Clamp
        probability = min(0.8, probability)  # Max 80% chance
        
        should_book = random.random() < probability
        
        return (should_book, probability)
    
    def select_match_type(
        self,
        feud_intensity: Optional[int] = None,
        is_title_match: bool = False,
        participant_styles: List[str] = None,
        feud_type: Optional[str] = None,
        is_blowoff: bool = False
    ) -> SpecialMatchType:
        """
        Select appropriate special match type.
        
        Args:
            feud_intensity: Intensity of feud (0-100)
            is_title_match: Championship on the line
            participant_styles: List of wrestler styles ('brawler', 'high_flyer', etc.)
            feud_type: Type of feud ('personal', 'title', etc.)
            is_blowoff: Is this the feud-ending match
        
        Returns:
            Selected SpecialMatchType
        """
        
        recommendations = []
        
        # CAGE MATCHES - for containment, preventing interference
        if feud_intensity and feud_intensity >= 70:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.STEEL_CAGE,
                reason="High feud intensity - need containment",
                confidence=0.7
            ))
        
        if is_blowoff and feud_intensity and feud_intensity >= 80:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.HELL_IN_A_CELL,
                reason="Major feud blowoff - ultimate brutality",
                confidence=0.8
            ))
        
        # LADDER MATCHES - for high-flyers, title matches
        if participant_styles and 'high_flyer' in participant_styles:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.LADDER_MATCH,
                reason="High-flying wrestlers excel in ladder matches",
                confidence=0.6
            ))
        
        if is_title_match:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.LADDER_MATCH,
                reason="Title suspended above ring creates drama",
                confidence=0.5
            ))
        
        # NO DQ / STREET FIGHT - for brawlers, intense feuds
        if participant_styles and 'brawler' in participant_styles:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.STREET_FIGHT,
                reason="Brawlers thrive in no-rules environment",
                confidence=0.7
            ))
        
        if feud_intensity and feud_intensity >= 60:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.NO_DQ,
                reason="Intense feud - let them fight without restrictions",
                confidence=0.6
            ))
        
        # LAST MAN STANDING - for brutal feuds
        if is_blowoff and feud_intensity and feud_intensity >= 75:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.LAST_MAN_STANDING,
                reason="Feud blowoff - must prove superiority",
                confidence=0.7
            ))
        
        # SUBMISSION - for technical wrestlers
        if participant_styles and 'technical' in participant_styles:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.SUBMISSION,
                reason="Technical wrestlers shine in submission matches",
                confidence=0.5
            ))
        
        # I QUIT - for the most heated feuds
        if is_blowoff and feud_intensity and feud_intensity >= 90:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.I_QUIT,
                reason="Ultimate feud ender - public humiliation",
                confidence=0.8
            ))
        
        # IRON MAN - for title matches, technical wrestlers
        if is_title_match and participant_styles and 'technical' in participant_styles:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.IRON_MAN,
                reason="Prestigious title match with technical wrestlers",
                confidence=0.6
            ))
        
        # LOSER LEAVES TOWN - for retirement/firing angles
        if is_blowoff and feud_type == 'personal' and feud_intensity and feud_intensity >= 85:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.LOSER_LEAVES_TOWN,
                reason="Ultimate stakes - career on the line",
                confidence=0.5
            ))
        
        # If no specific recommendations, default to NO DQ
        if not recommendations:
            recommendations.append(SpecialMatchRecommendation(
                match_type=SpecialMatchType.NO_DQ,
                reason="Default special stipulation",
                confidence=0.3
            ))
        
        # Select based on confidence
        best_match = max(recommendations, key=lambda r: r.confidence)
        
        return best_match.match_type
    
    def get_match_description(self, match_type: SpecialMatchType) -> str:
        """Get description of match type rules"""
        
        descriptions = {
            SpecialMatchType.STEEL_CAGE: "Enclosed in a steel cage. Win by pinfall, submission, or escape.",
            SpecialMatchType.HELL_IN_A_CELL: "Massive cage structure surrounds the ring. Escape is nearly impossible.",
            SpecialMatchType.LADDER_MATCH: "Object suspended above ring. Climb ladder to retrieve it.",
            SpecialMatchType.TLC: "Tables, Ladders, and Chairs are legal. Chaos guaranteed.",
            SpecialMatchType.NO_DQ: "No disqualifications. Anything goes.",
            SpecialMatchType.STREET_FIGHT: "No DQ, falls count anywhere. Weapons encouraged.",
            SpecialMatchType.LAST_MAN_STANDING: "Win by keeping opponent down for 10 count.",
            SpecialMatchType.IRON_MAN: "Timed match (30 or 60 minutes). Most falls wins.",
            SpecialMatchType.SUBMISSION: "Victory only by submission. No pinfalls.",
            SpecialMatchType.I_QUIT: "Win by making opponent say 'I Quit' into microphone.",
            SpecialMatchType.ELIMINATION: "Eliminate all opponents to win.",
            SpecialMatchType.GAUNTLET: "Face multiple opponents in succession.",
            SpecialMatchType.LOSER_LEAVES_TOWN: "Loser must leave the promotion."
        }
        
        return descriptions.get(match_type, "Special match with unique rules.")
    
    def apply_special_match_modifiers(
        self,
        match_type: SpecialMatchType,
        base_star_rating: float,
        base_duration: int
    ) -> Tuple[float, int]:
        """
        Apply modifiers to star rating and duration based on match type.
        
        Returns:
            (modified_star_rating, modified_duration)
        """
        
        star_modifier = 0.0
        duration_modifier = 0
        
        if match_type == SpecialMatchType.STEEL_CAGE:
            star_modifier = 0.25
            duration_modifier = 3
        
        elif match_type == SpecialMatchType.HELL_IN_A_CELL:
            star_modifier = 0.5
            duration_modifier = 5
        
        elif match_type == SpecialMatchType.LADDER_MATCH:
            star_modifier = 0.4
            duration_modifier = 4
        
        elif match_type == SpecialMatchType.TLC:
            star_modifier = 0.5
            duration_modifier = 6
        
        elif match_type == SpecialMatchType.NO_DQ:
            star_modifier = 0.15
            duration_modifier = 2
        
        elif match_type == SpecialMatchType.STREET_FIGHT:
            star_modifier = 0.3
            duration_modifier = 4
        
        elif match_type == SpecialMatchType.LAST_MAN_STANDING:
            star_modifier = 0.4
            duration_modifier = 5
        
        elif match_type == SpecialMatchType.IRON_MAN:
            star_modifier = 0.6
            duration_modifier = 20  # 30-60 minute matches
        
        elif match_type == SpecialMatchType.SUBMISSION:
            star_modifier = 0.2
            duration_modifier = 2
        
        elif match_type == SpecialMatchType.I_QUIT:
            star_modifier = 0.35
            duration_modifier = 6
        
        new_rating = min(5.0, base_star_rating + star_modifier)
        new_duration = base_duration + duration_modifier
        
        return (new_rating, new_duration)


# Global special match selector
special_match_selector = SpecialMatchSelector()