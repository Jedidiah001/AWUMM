"""
Rival Promotion Manager
Manages in-memory state of rival promotions and provides
the interface used by BiddingWarEngine.
"""

from typing import List, Optional, Dict, Any
from models.rival_promotion import RivalPromotion, DEFAULT_RIVAL_PROMOTIONS
from persistence.rival_promotion_db import (
    save_rival_promotion,
    load_all_rival_promotions,
    get_rival_promotion,
    delete_rival_promotion,
    log_relationship_change
)
from models.rival_promotion import RivalPromotionTier, RivalBrandIdentity


class RivalPromotionManager:
    """
    Singleton-style manager for rival promotions.
    Loads from DB on init, keeps in-memory cache, saves on change.
    """

    def __init__(self, database):
        self.database = database
        self._promotions: List[RivalPromotion] = []
        self._load_or_seed()

    def _load_or_seed(self) -> None:
        """Load from DB; if empty, seed with defaults."""
        rows = load_all_rival_promotions(self.database)

        if rows:
            self._promotions = [
                RivalPromotion.from_dict(r) for r in rows
            ]
            print(f"✅ Loaded {len(self._promotions)} rival promotions from database")
        else:
            # First run — seed defaults
            self._promotions = list(DEFAULT_RIVAL_PROMOTIONS)
            for promo in self._promotions:
                save_rival_promotion(self.database, promo)
            print(f"✅ Seeded {len(self._promotions)} default rival promotions")

    def get_all_promotions(self) -> List[RivalPromotion]:
        """Get all rival promotions."""
        return list(self._promotions)

    def get_promotion_by_id(self, promotion_id: str) -> Optional[RivalPromotion]:
        """Get a promotion by its ID."""
        return next((p for p in self._promotions if p.promotion_id == promotion_id), None)

    def get_promotion_by_name(self, name: str) -> Optional[RivalPromotion]:
        """Get a promotion by name or abbreviation."""
        for p in self._promotions:
            if p.name == name or p.abbreviation == name:
                return p
        return None

    def get_promotions_by_tier(self, tier: RivalPromotionTier) -> List[RivalPromotion]:
        """Get all promotions of a specific tier."""
        return [p for p in self._promotions if p.tier == tier]

    def get_promotions_interested_in(self, fa_id: str) -> List[RivalPromotion]:
        """Get all promotions actively pursuing a free agent."""
        return [p for p in self._promotions if fa_id in p.active_pursuits]

    def save_promotion(self, promotion: RivalPromotion) -> None:
        """Update in-memory cache and persist."""
        found = False
        for i, p in enumerate(self._promotions):
            if p.promotion_id == promotion.promotion_id:
                self._promotions[i] = promotion
                found = True
                break
        
        if not found:
            self._promotions.append(promotion)
        
        save_rival_promotion(self.database, promotion)

    def add_promotion(self, promotion: RivalPromotion) -> None:
        """Add a new rival promotion."""
        self._promotions.append(promotion)
        save_rival_promotion(self.database, promotion)

    def remove_promotion(self, promotion_id: str) -> bool:
        """Remove a rival promotion."""
        for i, p in enumerate(self._promotions):
            if p.promotion_id == promotion_id:
                self._promotions.pop(i)
                delete_rival_promotion(self.database, promotion_id)
                return True
        return False

    def reset_annual_budgets(self) -> None:
        """Called at year boundary to restore rival budgets."""
        for promo in self._promotions:
            promo.remaining_budget = promo.budget_per_year
            promo.signed_this_year = 0
            save_rival_promotion(self.database, promo)
        print("✅ Rival promotion budgets reset for new year")

    def add_pursuit(self, promotion_id: str, fa_id: str) -> bool:
        """Add a free agent to a promotion's active pursuits."""
        promo = self.get_promotion_by_id(promotion_id)
        if promo and fa_id not in promo.active_pursuits:
            promo.active_pursuits.append(fa_id)
            self.save_promotion(promo)
            return True
        return False

    def remove_pursuit(self, promotion_id: str, fa_id: str) -> bool:
        """Remove a free agent from a promotion's active pursuits."""
        promo = self.get_promotion_by_id(promotion_id)
        if promo and fa_id in promo.active_pursuits:
            promo.active_pursuits.remove(fa_id)
            self.save_promotion(promo)
            return True
        return False

    def record_signing(self, promotion_id: str, salary: int) -> None:
        """Record that a promotion signed someone."""
        promo = self.get_promotion_by_id(promotion_id)
        if promo:
            promo.signed_this_year += 1
            promo.remaining_budget -= salary
            promo.roster_size += 1
            self.save_promotion(promo)

    def record_bidding_war_win(self, promotion_id: str) -> None:
        """Record that a promotion won a bidding war."""
        promo = self.get_promotion_by_id(promotion_id)
        if promo:
            promo.won_bidding_wars += 1
            self.save_promotion(promo)

    def record_bidding_war_loss(self, promotion_id: str) -> None:
        """Record that a promotion lost a bidding war."""
        promo = self.get_promotion_by_id(promotion_id)
        if promo:
            promo.lost_bidding_wars += 1
            self.save_promotion(promo)

    def adjust_relationship(self, promotion_id: str, change: int, reason: str, year: int, week: int) -> None:
        """Adjust relationship with a promotion and log it."""
        promo = self.get_promotion_by_id(promotion_id)
        if promo:
            old_value = promo.relationship_with_player
            promo.relationship_with_player = max(0, min(100, old_value + change))
            self.save_promotion(promo)
            log_relationship_change(self.database, promotion_id, change, reason, year, week)

    def get_relationship(self, promotion_id: str) -> int:
        """Get current relationship score with a promotion."""
        promo = self.get_promotion_by_id(promotion_id)
        return promo.relationship_with_player if promo else 50

    def get_promotions_with_budget(self, min_budget: int = 0) -> List[RivalPromotion]:
        """Get promotions that have remaining budget."""
        return [p for p in self._promotions if p.remaining_budget >= min_budget]

    def get_promotions_needing_role(self, role: str) -> List[RivalPromotion]:
        """Get promotions that need a specific role."""
        return [p for p in self._promotions if role in p.roster_needs]

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert all promotions to dictionary list."""
        return [p.to_dict() for p in self._promotions]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all rival promotions."""
        total_budget = sum(p.remaining_budget for p in self._promotions)
        total_signed = sum(p.signed_this_year for p in self._promotions)
        
        by_tier = {}
        for p in self._promotions:
            tier_name = p.tier.value if hasattr(p.tier, 'value') else str(p.tier)
            by_tier[tier_name] = by_tier.get(tier_name, 0) + 1
        
        return {
            'total_promotions': len(self._promotions),
            'total_remaining_budget': total_budget,
            'total_signed_this_year': total_signed,
            'by_tier': by_tier,
            'active_pursuits': sum(len(p.active_pursuits) for p in self._promotions)
        }


# Module-level singleton (initialized by app.py)
rival_promotion_manager: Optional[RivalPromotionManager] = None


def initialize_rival_promotion_manager(database) -> RivalPromotionManager:
    """
    Initialize the global rival promotion manager.
    Called once at app startup.
    """
    global rival_promotion_manager
    rival_promotion_manager = RivalPromotionManager(database)
    return rival_promotion_manager


def get_rival_promotion_manager() -> Optional[RivalPromotionManager]:
    """
    Get the global rival promotion manager instance.
    Returns None if not initialized.
    """
    return rival_promotion_manager