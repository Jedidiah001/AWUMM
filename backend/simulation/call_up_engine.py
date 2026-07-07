"""
Call-Up Engine - Developmental to Main Roster Promotion System
Handles automated and manual call-up mechanics from ROC Nexus to main roster brands.
Integrates with prospect_system.py for seamless talent pipeline management.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import random
from datetime import datetime

# Use relative imports for simulation module
try:
    from models.developmental_roster import (
        DevelopmentalRosterManager,
        DevelopmentalRosterEntry,
        CallUpStatus,
        CallUpReason,
        DevelopmentalBrand,
    )
    from models.prospect_system import ProspectProfile, BreakthroughStatus
except ImportError:
    from backend.models.developmental_roster import (
        DevelopmentalRosterManager,
        DevelopmentalRosterEntry,
        CallUpStatus,
        CallUpReason,
        DevelopmentalBrand,
    )
    from backend.models.prospect_system import ProspectProfile, BreakthroughStatus


@dataclass
class CallUpRecommendation:
    """Represents a recommendation for calling up a developmental talent"""
    wrestler_id: str
    wrestler_name: str
    destination_brand: str
    reason: CallUpReason
    priority_score: float  # 0-100, higher = more urgent
    readiness_score: float
    brand_need_score: float  # How much the brand needs this type of talent
    storyline_fit: str = ""
    risk_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "wrestler_id": self.wrestler_id,
            "wrestler_name": self.wrestler_name,
            "destination_brand": self.destination_brand,
            "reason": self.reason.value,
            "reason_label": self.reason.label,
            "priority_score": round(self.priority_score, 2),
            "readiness_score": round(self.readiness_score, 2),
            "brand_need_score": round(self.brand_need_score, 2),
            "storyline_fit": self.storyline_fit,
            "risk_factors": self.risk_factors,
            "recommendation_strength": self._get_strength_label(),
        }
    
    def _get_strength_label(self) -> str:
        if self.priority_score >= 85:
            return "Strongly Recommended"
        elif self.priority_score >= 70:
            return "Recommended"
        elif self.priority_score >= 55:
            return "Consider"
        else:
            return "Low Priority"


class CallUpEngine:
    """
    Engine for managing call-ups from developmental (ROC Nexus) to main roster.
    
    Features:
    - Automated call-up recommendations based on brand needs
    - Integration with prospect breakthrough system
    - Injury replacement logic
    - Storyline-driven call-up suggestions
    - Success/failure tracking and learning
    """
    
    def __init__(self, dev_roster_manager: DevelopmentalRosterManager):
        self.dev_roster = dev_roster_manager
        
        # Brand need weights
        self.brand_needs: Dict[str, Dict[str, float]] = {
            "ROC Alpha": {"Main Event": 0.3, "Upper Midcard": 0.25, "Midcard": 0.2, "Lower Midcard": 0.15, "Jobber": 0.1},
            "ROC Velocity": {"Main Event": 0.2, "Upper Midcard": 0.3, "Midcard": 0.25, "Lower Midcard": 0.15, "Jobber": 0.1},
            "ROC Vanguard": {"Main Event": 0.15, "Upper Midcard": 0.2, "Midcard": 0.3, "Lower Midcard": 0.25, "Jobber": 0.1},
        }
        
        # Historical success rates by brand
        self.brand_success_rates: Dict[str, float] = {
            "ROC Alpha": 0.65,
            "ROC Velocity": 0.60,
            "ROC Vanguard": 0.70,
        }
        
        # Call-up cooldown (weeks between call-ups to same brand)
        self.call_up_cooldown: Dict[str, int] = {
            "ROC Alpha": 0,
            "ROC Velocity": 0,
            "ROC Vanguard": 0,
        }
    
    def generate_recommendations(
        self,
        universe_state: Any,
        current_year: int,
        current_week: int
    ) -> List[CallUpRecommendation]:
        """
        Generate call-up recommendations based on current universe state.
        
        Args:
            universe_state: The current universe state object
            current_year: Current game year
            current_week: Current game week
            
        Returns:
            List of CallUpRecommendation objects sorted by priority
        """
        recommendations = []
        
        # Get wrestlers ready for call-up
        ready_wrestlers = self.dev_roster.get_ready_for_call_up()
        
        if not ready_wrestlers:
            return recommendations
        
        # Analyze brand needs
        brand_needs_analysis = self._analyze_brand_needs(universe_state)
        
        # Check for injury replacements needed
        injury_replacements = self._find_injury_replacement_needs(universe_state)
        
        for entry in ready_wrestlers:
            # Skip if recently called up
            if (entry.last_call_up_year == current_year and 
                current_week - entry.last_call_up_week < 12):
                continue
            
            # Generate recommendations for each brand
            for brand in ["ROC Alpha", "ROC Velocity", "ROC Vanguard"]:
                rec = self._evaluate_call_up_fit(
                    entry=entry,
                    brand=brand,
                    brand_needs=brand_needs_analysis.get(brand, {}),
                    injury_replacements=injury_replacements.get(brand, []),
                    universe_state=universe_state,
                    current_year=current_year,
                    current_week=current_week
                )
                
                if rec and rec.priority_score >= 50:
                    recommendations.append(rec)
        
        # Sort by priority score (highest first)
        recommendations.sort(key=lambda x: x.priority_score, reverse=True)
        
        return recommendations
    
    def _analyze_brand_needs(self, universe_state: Any) -> Dict[str, Dict[str, Any]]:
        """Analyze what each brand needs in terms of roster composition"""
        brand_needs = {}
        
        for brand in ["ROC Alpha", "ROC Velocity", "ROC Vanguard"]:
            # Get wrestlers on this brand
            brand_wrestlers = [
                w for w in universe_state.wrestlers
                if w.primary_brand == brand and not w.is_retired
            ]
            
            # Count by role
            role_counts = {}
            for w in brand_wrestlers:
                role = w.role
                role_counts[role] = role_counts.get(role, 0) + 1
            
            # Calculate need scores (inverse of current count * weight)
            need_scores = {}
            total_weight = sum(self.brand_needs[brand].values())
            
            for role, base_weight in self.brand_needs[brand].items():
                current_count = role_counts.get(role, 0)
                ideal_count = int(base_weight * len(brand_wrestlers) / total_weight) if brand_wrestlers else 1
                
                # Need score: higher if current < ideal
                if current_count < ideal_count:
                    need_scores[role] = (ideal_count - current_count) / max(1, ideal_count)
                else:
                    need_scores[role] = 0.1  # Minimal need if over-staffed
            
            brand_needs[brand] = {
                "role_counts": role_counts,
                "need_scores": need_scores,
                "total_wrestlers": len(brand_wrestlers),
            }
        
        return brand_needs
    
    def _find_injury_replacement_needs(self, universe_state: Any) -> Dict[str, List[str]]:
        """Find brands that need injury replacements"""
        replacements_needed = {
            "ROC Alpha": [],
            "ROC Velocity": [],
            "ROC Vanguard": [],
        }
        
        for wrestler in universe_state.wrestlers:
            if wrestler.is_injured and wrestler.injury.weeks_remaining >= 4:
                brand = wrestler.primary_brand
                if brand in replacements_needed:
                    replacements_needed[brand].append(wrestler.role)
        
        return replacements_needed
    
    def _evaluate_call_up_fit(
        self,
        entry: DevelopmentalRosterEntry,
        brand: str,
        brand_needs: Dict[str, Any],
        injury_replacements: List[str],
        universe_state: Any,
        current_year: int,
        current_week: int
    ) -> Optional[CallUpRecommendation]:
        """Evaluate how well a wrestler fits a brand's needs"""
        
        # Base readiness score
        readiness = entry.get_readiness_summary()
        readiness_score = readiness["readiness_score"]
        
        if not readiness["is_eligible"]:
            return None
        
        # Calculate brand need score
        brand_need_score = 0.0
        primary_reason = CallUpReason.BRAND_NEED
        
        # Check if brand needs this wrestler's role (estimate from dev rating)
        estimated_role = self._estimate_main_roster_role(entry.developmental_rating)
        role_need = brand_needs.get("need_scores", {}).get(estimated_role, 0.1)
        brand_need_score = role_need * 100
        
        # Injury replacement boost
        if estimated_role in injury_replacements:
            brand_need_score += 30
            primary_reason = CallUpReason.INJURY_REPLACEMENT
        
        # Breakthrough performance check
        if entry.coach_evaluation >= 80:
            brand_need_score += 15
            if primary_reason == CallUpReason.BRAND_NEED:
                primary_reason = CallUpReason.BREAKTHROUGH_PERFORMANCE
        
        # Cooldown penalty
        cooldown_weeks = self.call_up_cooldown.get(brand, 0)
        if cooldown_weeks > 0:
            brand_need_score -= min(20, cooldown_weeks * 2)
        
        # Calculate final priority score
        priority_score = (
            readiness_score * 0.4 +
            brand_need_score * 0.4 +
            entry.match_quality_avg * 0.1 +
            entry.crowd_reaction_avg * 0.1
        )
        
        # Identify risk factors
        risk_factors = []
        if entry.times_called_up > 0 and entry.call_up_success_rate < 0.5:
            risk_factors.append("Previous call-up struggled")
        if entry.weeks_in_developmental < 12:
            risk_factors.append("Limited developmental time")
        if entry.match_quality_avg < 65:
            risk_factors.append("Inconsistent match quality")
        
        # Generate storyline fit description
        storyline_fit = self._generate_storyline_fit(entry, brand, universe_state)
        
        return CallUpRecommendation(
            wrestler_id=entry.wrestler_id,
            wrestler_name=entry.wrestler_name,
            destination_brand=brand,
            reason=primary_reason,
            priority_score=min(100, max(0, priority_score)),
            readiness_score=readiness_score,
            brand_need_score=min(100, max(0, brand_need_score)),
            storyline_fit=storyline_fit,
            risk_factors=risk_factors,
        )
    
    def _estimate_main_roster_role(self, developmental_rating: int) -> str:
        """Estimate what role a wrestler would have on main roster"""
        if developmental_rating >= 80:
            return "Upper Midcard"
        elif developmental_rating >= 65:
            return "Midcard"
        elif developmental_rating >= 50:
            return "Lower Midcard"
        else:
            return "Jobber"
    
    def _generate_storyline_fit(
        self,
        entry: DevelopmentalRosterEntry,
        brand: str,
        universe_state: Any
    ) -> str:
        """Generate a storyline justification for the call-up"""
        storylines = []
        
        # Based on strengths
        if entry.match_quality_avg >= 75:
            storylines.append(f"{entry.wrestler_name} has been dominating in Nexus with exceptional match quality")
        
        if entry.crowd_reaction_avg >= 75:
            storylines.append(f"The Nexus crowd has been electric for {entry.wrestler_name}")
        
        if entry.coach_evaluation >= 80:
            storylines.append("Coaching staff gives highest recommendation")
        
        # Brand-specific angles
        if brand == "ROC Alpha":
            if not storylines:
                storylines.append("Alpha looking to inject fresh energy into the roster")
            storylines.append("Perfect fit for Alpha's high-energy style")
        elif brand == "ROC Velocity":
            if not storylines:
                storylines.append("Velocity needs new contenders")
            storylines.append("Speed and agility perfect for Velocity's fast-paced action")
        elif brand == "ROC Vanguard":
            if not storylines:
                storylines.append("Vanguard building for the future")
            storylines.append("Technical skills align with Vanguard's wrestling-focused identity")
        
        return ". ".join(storylines[:2])
    
    def execute_call_up(
        self,
        wrestler_id: str,
        destination_brand: str,
        reason: CallUpReason,
        universe_state: Any,
        current_year: int,
        current_week: int,
        initiating_gm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a call-up from developmental to main roster.
        
        Returns result dict with success status and details.
        """
        # Initiate the call-up in the roster manager
        result = self.dev_roster.initiate_call_up(
            wrestler_id=wrestler_id,
            destination_brand=destination_brand,
            reason=reason,
            initiating_gm=initiating_gm,
            current_year=current_year,
            current_week=current_week
        )
        
        if not result["success"]:
            return result
        
        # Update cooldown
        self.call_up_cooldown[destination_brand] = 4  # 4-week cooldown
        
        # Get the wrestler from universe
        wrestler = universe_state.get_wrestler_by_id(wrestler_id)
        if wrestler:
            # Update wrestler's brand
            old_brand = wrestler.primary_brand
            wrestler.primary_brand = destination_brand
            
            # Log the call-up event
            if hasattr(universe_state, 'log_event'):
                universe_state.log_event({
                    "type": "call_up",
                    "year": current_year,
                    "week": current_week,
                    "wrestler_id": wrestler_id,
                    "wrestler_name": wrestler.name,
                    "from_brand": old_brand,
                    "to_brand": destination_brand,
                    "reason": reason.value,
                })
        
        return {
            **result,
            "cooldown_weeks": 4,
            "next_eligible_week": current_week + 4,
        }
    
    def simulate_call_up_outcome(
        self,
        wrestler_id: str,
        universe_state: Any,
        weeks_on_main_roster: int = 12
    ) -> Dict[str, Any]:
        """
        Simulate the outcome of a call-up after a period on main roster.
        
        Returns whether the call-up was successful or if wrestler should return.
        """
        entry = self.dev_roster.get_entry(wrestler_id)
        if not entry:
            return {"error": "Wrestler not found"}
        
        wrestler = universe_state.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return {"error": "Wrestler not found in universe"}
        
        # Calculate success probability
        base_success_rate = self.brand_success_rates.get(entry.assigned_brand, 0.65)
        
        # Modifiers
        readiness_mod = (entry.get_readiness_summary()["readiness_score"] - 50) / 100 * 0.3
        performance_mod = (entry.match_quality_avg - 50) / 100 * 0.2
        crowd_mod = (entry.crowd_reaction_avg - 50) / 100 * 0.1
        
        success_probability = base_success_rate + readiness_mod + performance_mod + crowd_mod
        success_probability = max(0.3, min(0.95, success_probability))
        
        # Determine outcome
        is_successful = random.random() < success_probability
        
        # Process outcome
        self.dev_roster.process_call_up_outcome(
            wrestler_id=wrestler_id,
            success=is_successful,
            return_to_developmental=not is_successful
        )
        
        # Update history
        if self.dev_roster.call_up_history:
            latest_history = self.dev_roster.call_up_history[-1]
            latest_history.success_outcome = is_successful
            
            if not is_successful:
                latest_history.return_date_year = getattr(universe_state, 'current_year', 0)
                latest_history.return_date_week = getattr(universe_state, 'current_week', 0)
                
                # Return wrestler to developmental
                wrestler.primary_brand = DevelopmentalBrand.ROC_NEXUS.value
        
        return {
            "success": is_successful,
            "probability": round(success_probability * 100, 1),
            "wrestler_name": entry.wrestler_name,
            "brand": entry.assigned_brand,
            "outcome_message": self._generate_outcome_message(is_successful, entry, wrestler),
        }
    
    def _generate_outcome_message(
        self,
        is_successful: bool,
        entry: DevelopmentalRosterEntry,
        wrestler: Any
    ) -> str:
        """Generate a narrative message for the call-up outcome"""
        if is_successful:
            messages = [
                f"{entry.wrestler_name} has successfully transitioned to the main roster!",
                f"The call-up proves successful - {entry.wrestler_name} is thriving on {entry.assigned_brand}!",
                f"{entry.wrestler_name} exceeds expectations and secures their main roster spot!",
            ]
        else:
            messages = [
                f"{entry.wrestler_name} struggles on the main roster and returns to developmental.",
                f"The call-up doesn't work out - {entry.wrestler_name} heads back to Nexus to regroup.",
                f"{entry.wrestler_name} isn't quite ready and returns to developmental for more seasoning.",
            ]
        
        return random.choice(messages)
    
    def get_brand_statistics(self, universe_state: Any) -> Dict[str, Dict[str, Any]]:
        """Get call-up statistics by brand"""
        stats = {}
        
        for brand in ["ROC Alpha", "ROC Velocity", "ROC Vanguard"]:
            brand_history = [
                h for h in self.dev_roster.call_up_history
                if h.destination_brand == brand
            ]
            
            successful = len([h for h in brand_history if h.success_outcome is True])
            returned = len([h for h in brand_history if h.return_date_year is not None])
            total = len(brand_history)
            
            stats[brand] = {
                "total_call_ups": total,
                "successful": successful,
                "returned": returned,
                "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
                "current_cooldown": self.call_up_cooldown.get(brand, 0),
            }
        
        return stats
    
    def update_cooldowns(self):
        """Decrease cooldown timers by 1 week"""
        for brand in self.call_up_cooldown:
            if self.call_up_cooldown[brand] > 0:
                self.call_up_cooldown[brand] -= 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize engine state"""
        return {
            "brand_needs": self.brand_needs,
            "brand_success_rates": self.brand_success_rates,
            "call_up_cooldowns": self.call_up_cooldown,
            "dev_roster": self.dev_roster.to_dict(),
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], dev_roster: DevelopmentalRosterManager) -> 'CallUpEngine':
        """Deserialize engine state"""
        engine = CallUpEngine(dev_roster)
        
        if "brand_needs" in data:
            engine.brand_needs = data["brand_needs"]
        if "brand_success_rates" in data:
            engine.brand_success_rates = data["brand_success_rates"]
        if "call_up_cooldowns" in data:
            engine.call_up_cooldown = data["call_up_cooldowns"]
        
        return engine
