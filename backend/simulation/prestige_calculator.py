"""
Championship Prestige Calculator
Tracks and updates championship prestige based on match quality, defenses, and champion quality.

STEP 23: Championship prestige system with enhanced analytics and recovery recommendations
"""

from typing import Dict, Any, List, Optional
from models.championship import Championship
from models.wrestler import Wrestler
from models.match import MatchResult


class PrestigeCalculator:
    """
    Calculates and updates championship prestige based on various factors.
    
    Prestige increases with:
    - High-quality title matches (4+ star matches)
    - Strong champions (high overall rating)
    - Frequent defenses
    - Long, meaningful reigns
    
    Prestige decreases with:
    - Low-quality title matches (< 2.5 stars)
    - Weak champions (low overall rating)
    - Infrequent defenses (title appears less important)
    - Very short reigns (hot potato booking)
    """
    
    def __init__(self):
        # Base prestige values by title type
        self.base_prestige = {
            'World': 85,
            'Secondary': 65,
            'Midcard': 50,
            'Tag Team': 55,
            'Women': 70,
            'Developmental': 40
        }
        
        # Prestige change thresholds
        self.EXCELLENT_MATCH_THRESHOLD = 4.0  # 4+ stars
        self.GOOD_MATCH_THRESHOLD = 3.0       # 3+ stars
        self.POOR_MATCH_THRESHOLD = 2.5       # Below 2.5 stars
        
        # Defense frequency thresholds (in weeks)
        self.IDEAL_DEFENSE_FREQUENCY = 4  # Every 4 weeks is ideal
        self.MAX_DEFENSE_GAP = 8          # More than 8 weeks is bad
    
    def calculate_match_prestige_change(
        self,
        championship: Championship,
        match_result: MatchResult,
        champion: Wrestler
    ) -> int:
        """
        Calculate prestige change from a title match.
        
        Returns delta to add to championship prestige (-10 to +10 range).
        """
        
        delta = 0
        star_rating = match_result.star_rating
        
        # ==============================================================
        # FACTOR 1: Match Quality (biggest factor)
        # ==============================================================
        
        if star_rating >= 4.5:
            delta += 8  # Instant classic
        elif star_rating >= self.EXCELLENT_MATCH_THRESHOLD:
            delta += 5  # Excellent match
        elif star_rating >= self.GOOD_MATCH_THRESHOLD:
            delta += 2  # Good match
        elif star_rating >= self.POOR_MATCH_THRESHOLD:
            delta += 0  # Acceptable match (no change)
        else:
            delta -= 3  # Poor match hurts prestige
        
        # ==============================================================
        # FACTOR 2: Match Importance
        # ==============================================================
        
        if match_result.card_position >= 7:
            # Main event/semi-main - more prestige impact
            delta = int(delta * 1.3)
        
        if hasattr(match_result, 'special_match_type') and match_result.special_match_type:
            # Special stipulations add prestige
            delta += 1
        
        # ==============================================================
        # FACTOR 3: Champion Quality
        # ==============================================================
        
        champion_quality = champion.overall_rating
        
        if champion_quality >= 85:
            delta += 2  # Elite champion elevates the title
        elif champion_quality >= 70:
            delta += 1  # Strong champion
        elif champion_quality < 50:
            delta -= 1  # Weak champion hurts prestige
        
        # ==============================================================
        # FACTOR 4: Title Change Impact
        # ==============================================================
        
        if match_result.title_changed_hands:
            if match_result.is_upset:
                # Shocking title change - mixed impact
                delta += 3  # Memorable moment
            else:
                # Expected title change
                delta += 1
        else:
            # Successful defense
            if star_rating >= 4.0:
                delta += 1  # Great defense adds prestige
        
        # ==============================================================
        # FACTOR 5: PPV vs TV
        # ==============================================================
        
        # PPV matches have more prestige impact
        # (This is inferred from match_result.card_position and show context)
        # We'll handle this in the main update method when we have show context
        
        # Clamp delta to reasonable range
        delta = max(-10, min(10, delta))
        
        return delta
    
    def calculate_defense_frequency_modifier(
        self,
        championship: Championship,
        current_year: int,
        current_week: int
    ) -> int:
        """
        Calculate prestige change based on defense frequency.
        
        Returns delta based on how often the title is defended.
        """
        
        if not championship.last_defense_year or not championship.last_defense_week:
            return 0  # No previous defense to compare
        
        # Calculate weeks since last defense
        weeks_since_defense = (
            (current_year - championship.last_defense_year) * 52 +
            (current_week - championship.last_defense_week)
        )
        
        delta = 0
        
        if weeks_since_defense <= self.IDEAL_DEFENSE_FREQUENCY:
            # Frequent defenses = good
            delta += 1
        elif weeks_since_defense > self.MAX_DEFENSE_GAP:
            # Too long without defense = bad
            delta -= 2
        
        return delta
    
    def calculate_reign_length_impact(
        self,
        championship: Championship,
        reign_length_days: int
    ) -> int:
        """
        Calculate prestige impact when a reign ends.
        
        Very short reigns hurt prestige (hot potato booking).
        Long, meaningful reigns help prestige.
        """
        
        delta = 0
        
        if reign_length_days < 7:
            # Less than a week - terrible hot potato booking
            delta -= 5
        elif reign_length_days < 30:
            # Less than a month - short reign
            delta -= 2
        elif reign_length_days >= 180:
            # 6+ months - long, meaningful reign
            delta += 3
        elif reign_length_days >= 365:
            # 1+ year - legendary reign
            delta += 5
        
        return delta
    
    def calculate_vacancy_prestige_impact(
        self,
        weeks_vacant: int,
        vacancy_reason: str
    ) -> int:
        """
        Calculate prestige impact from title vacancy.
        
        Vacancies generally hurt prestige, especially long ones.
        """
        delta = 0
        
        # Vacancy duration penalty
        if weeks_vacant >= 8:
            delta -= 5
        elif weeks_vacant >= 4:
            delta -= 3
        elif weeks_vacant >= 2:
            delta -= 1
        
        # Reason matters
        if vacancy_reason in ['injury', 'contract_expiration']:
            delta -= 1  # Unfortunate but understandable
        elif vacancy_reason in ['stripped', 'fired', 'released']:
            delta -= 3  # Looks bad
        
        return max(-10, delta)
    
    def update_title_prestige(
        self,
        championship: Championship,
        match_result: MatchResult,
        champion: Wrestler,
        is_ppv: bool = False
    ):
        """
        Main method: Update championship prestige after a title match.
        
        This is called from show_sim.py after a title match.
        """
        
        # Calculate base change from match quality
        delta = self.calculate_match_prestige_change(championship, match_result, champion)
        
        # PPV matches have 1.5x impact
        if is_ppv:
            delta = int(delta * 1.5)
        
        # Apply the change
        old_prestige = championship.prestige
        championship.adjust_prestige(delta)
        
        print(f"      📊 Prestige: {championship.name} {old_prestige} → {championship.prestige} ({delta:+d})")
        
        # Check for prestige milestones
        if championship.prestige >= 90 and old_prestige < 90:
            print(f"      ⭐ {championship.name} has reached LEGENDARY prestige!")
        elif championship.prestige <= 30 and old_prestige > 30:
            print(f"      ⚠️ {championship.name} prestige has fallen to DAMAGED status!")
    
    def decay_prestige_for_inactivity(
        self,
        championship: Championship,
        current_year: int,
        current_week: int
    ):
        """
        Apply slow prestige decay if title hasn't been defended recently.
        Called weekly during show processing.
        """
        
        if championship.is_vacant:
            # Vacant titles lose prestige faster
            championship.adjust_prestige(-1)
            return
        
        if not championship.last_defense_year or not championship.last_defense_week:
            return
        
        weeks_since_defense = (
            (current_year - championship.last_defense_year) * 52 +
            (current_week - championship.last_defense_week)
        )
        
        # Apply decay based on inactivity
        if weeks_since_defense > 12:  # 3 months
            championship.adjust_prestige(-2)
            print(f"      ⏳ {championship.name} prestige decayed due to inactivity")
        elif weeks_since_defense > 8:  # 2 months
            championship.adjust_prestige(-1)
    
    def get_prestige_tier(self, prestige: int) -> str:
        """
        Get prestige tier label.
        
        Tiers:
        - legendary (90-100)
        - elite (75-89)
        - strong (60-74)
        - average (45-59)
        - weak (30-44)
        - damaged (0-29)
        """
        if prestige >= 90:
            return "legendary"
        elif prestige >= 75:
            return "elite"
        elif prestige >= 60:
            return "strong"
        elif prestige >= 45:
            return "average"
        elif prestige >= 30:
            return "weak"
        else:
            return "damaged"
    
    def get_prestige_description(self, prestige: int) -> str:
        """Get human-readable prestige description"""
        tier = self.get_prestige_tier(prestige)
        
        descriptions = {
            "legendary": "This championship is revered as one of the most prestigious titles in wrestling history.",
            "elite": "This championship is highly valued and carries significant weight in the industry.",
            "strong": "This championship is respected and has a solid reputation.",
            "average": "This championship has moderate prestige and recognition.",
            "weak": "This championship's prestige has been declining and needs to be rebuilt.",
            "damaged": "This championship's reputation has been severely damaged and requires major rehabilitation."
        }
        
        return descriptions.get(tier, "Unknown")
    
    def analyze_prestige_trends(
        self,
        championship: Championship
    ) -> Dict[str, Any]:
        """
        Analyze prestige trends for a championship.
        Returns analysis data for frontend display.
        """
        
        prestige = championship.prestige
        tier = self.get_prestige_tier(prestige)
        
        analysis = {
            'current_prestige': prestige,
            'tier': tier,
            'description': self.get_prestige_description(prestige),
            'total_defenses': championship.total_defenses,
            'factors': [],
            'health_score': prestige,  # Simple health score = prestige
            'trend': 'stable',
            'recommendations': []
        }
        
        # Determine trend
        if prestige >= 85:
            analysis['trend'] = 'excellent'
        elif prestige >= 70:
            analysis['trend'] = 'good'
        elif prestige < 40:
            analysis['trend'] = 'declining'
        
        # Analyze current state
        if championship.is_vacant:
            analysis['factors'].append({
                'type': 'warning',
                'message': 'Title is currently vacant - prestige will decay'
            })
            analysis['recommendations'].append('Fill vacancy immediately to prevent further prestige loss')
        
        if championship.has_interim_champion:
            analysis['factors'].append({
                'type': 'info',
                'message': 'Interim champion holding the title'
            })
        
        if prestige >= 85:
            analysis['factors'].append({
                'type': 'positive',
                'message': 'Championship has elite prestige'
            })
        elif prestige < 40:
            analysis['factors'].append({
                'type': 'negative',
                'message': 'Championship prestige is low - needs high-quality matches'
            })
            analysis['recommendations'].append('Book high-quality title matches with top stars')
            analysis['recommendations'].append('Target 4+ star matches for all defenses')
        
        if prestige < 50:
            analysis['recommendations'].append('Avoid frequent title changes (let champion build a reign)')
            analysis['recommendations'].append('Feature the title prominently on weekly shows')
        
        # Defense frequency
        if championship.total_defenses == 0:
            analysis['factors'].append({
                'type': 'info',
                'message': 'No title defenses recorded yet'
            })
        elif championship.total_defenses < 5:
            analysis['factors'].append({
                'type': 'info',
                'message': 'Limited defense history - prestige still developing'
            })
        
        return analysis
    
    def suggest_prestige_recovery_plan(self, championship: Championship) -> List[str]:
        """
        Suggest steps to recover prestige for a damaged title.
        Returns a list of actionable recommendations.
        """
        plan = []
        
        if championship.is_vacant:
            plan.append('0. URGENT: Fill vacancy immediately with tournament/match')
        
        if championship.prestige < 50:
            plan.append('1. Book the title in high-profile matches (PPV main events)')
            plan.append('2. Ensure champion is a top-tier performer (80+ overall rating)')
            plan.append('3. Target 4+ star matches for all defenses')
            plan.append('4. Avoid frequent title changes (let champion build a reign)')
            plan.append('5. Feature the title prominently on weekly shows')
        
        if championship.prestige < 35:
            plan.append('6. Consider a prestige-building storyline or tournament')
            plan.append('7. Defend the title at every major PPV')
        
        return plan
    
    def get_prestige_color(self, prestige: int) -> str:
        """Get color class for prestige display"""
        tier = self.get_prestige_tier(prestige)
        
        colors = {
            'legendary': '#FFD700',  # Gold
            'elite': '#1E90FF',      # Dodger Blue
            'strong': '#32CD32',     # Lime Green
            'average': '#FFA500',    # Orange
            'weak': '#FF6347',       # Tomato
            'damaged': '#DC143C'     # Crimson
        }
        
        return colors.get(tier, '#808080')


# Global prestige calculator instance
prestige_calculator = PrestigeCalculator()