"""
morale_events.py
Steps 260-265: Morale Events & Storyline Consequences

Step 260 — Show Recap Integration     : inject morale events into post-show recap feed
Step 261 — Morale-Driven Storylines   : generate feuds/storylines from morale state
Step 262 — Locker Room Crisis         : escalation tier system (tension → crisis → meltdown)
Step 263 — Office Screen Broadcast    : real-time alert feed for the GM office view
Step 264 — Weekly Morale Digest       : end-of-week narrative summary
Step 265 — Consequence Propagation    : morale events ripple to related wrestlers
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Enums
# ============================================================

class MoraleEventCategory(str, Enum):
    BEHAVIOR_FIRED      = "behavior_fired"       # Step 260 — a behavior triggered this show
    RECOVERY_TAKEN      = "recovery_taken"       # Step 260 — management acted
    STORYLINE_SPAWNED   = "storyline_spawned"    # Step 261 — new morale-driven storyline
    CRISIS_ESCALATED    = "crisis_escalated"     # Step 262 — crisis tier moved up
    CRISIS_RESOLVED     = "crisis_resolved"      # Step 262 — crisis de-escalated
    OFFICE_ALERT        = "office_alert"         # Step 263 — GM notification
    DIGEST_ENTRY        = "digest_entry"         # Step 264 — weekly narrative line
    PROPAGATION         = "propagation"          # Step 265 — morale ripple effect


class CrisisTier(str, Enum):
    NONE      = "none"       # No crisis
    TENSION   = "tension"    # ≥1 unhappy wrestler, behaviors active
    CRISIS    = "crisis"     # ≥3 unhappy + at least one public demand or sandbagging
    MELTDOWN  = "meltdown"   # ≥5 miserable + backstage poison spreading


class AlertPriority(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    URGENT   = "urgent"
    CRITICAL = "critical"


class MoraleStorylineType(str, Enum):
    UNHAPPY_HEEL_TURN        = "unhappy_heel_turn"
    VETERAN_MENTORS_ROOKIE   = "veteran_mentors_rookie"
    LOCKER_ROOM_REVOLT       = "locker_room_revolt"
    REDEMPTION_ARC           = "redemption_arc"
    DEPARTURE_ANGLE          = "departure_angle"
    BRAND_CIVIL_WAR          = "brand_civil_war"


# ============================================================
# Data Classes
# ============================================================

@dataclass
class ShowMoraleEvent:
    """A morale-driven event that appears in the show recap feed."""
    event_id:    str
    category:    MoraleEventCategory
    priority:    AlertPriority
    headline:    str          # short title for recap card
    description: str          # full narrative paragraph
    wrestler_ids: List[str]
    wrestler_names: List[str]
    show_id:     Optional[str]
    year:        int
    week:        int
    metadata:    Dict[str, Any] = field(default_factory=dict)
    created_at:  str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "category":      self.category.value,
            "priority":      self.priority.value,
            "headline":      self.headline,
            "description":   self.description,
            "wrestler_ids":  self.wrestler_ids,
            "wrestler_names": self.wrestler_names,
            "show_id":       self.show_id,
            "year":          self.year,
            "week":          self.week,
            "metadata":      self.metadata,
            "created_at":    self.created_at,
        }


@dataclass
class MoraleStorylineSeed:
    """A morale-driven storyline suggestion for the creative team."""
    seed_id:         str
    storyline_type:  MoraleStorylineType
    title:           str
    logline:         str           # one-sentence pitch
    full_outline:    str           # 3-beat narrative outline
    primary_wrestler_id:   str
    primary_wrestler_name: str
    supporting_cast:       List[Dict[str, str]]   # [{id, name, role}]
    morale_trigger:        int     # morale level that spawned this
    urgency:               str     # low | medium | high | critical
    suggested_duration_weeks: int
    year:            int
    week:            int
    accepted:        bool = False
    rejected:        bool = False
    created_at:      str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed_id":               self.seed_id,
            "storyline_type":        self.storyline_type.value,
            "title":                 self.title,
            "logline":               self.logline,
            "full_outline":          self.full_outline,
            "primary_wrestler_id":   self.primary_wrestler_id,
            "primary_wrestler_name": self.primary_wrestler_name,
            "supporting_cast":       self.supporting_cast,
            "morale_trigger":        self.morale_trigger,
            "urgency":               self.urgency,
            "suggested_duration_weeks": self.suggested_duration_weeks,
            "year":                  self.year,
            "week":                  self.week,
            "accepted":              self.accepted,
            "rejected":              self.rejected,
            "created_at":            self.created_at,
        }


@dataclass
class LockerRoomCrisis:
    """Tracks escalating locker room instability."""
    crisis_id:    str
    tier:         CrisisTier
    brand:        Optional[str]        # None = promotion-wide
    wrestler_ids: List[str]            # wrestlers at the centre
    wrestler_names: List[str]
    description:  str
    weekly_morale_drain: float         # passive morale drain to bystanders per week
    weeks_active: int = 0
    resolved:     bool = False
    resolution_description: str = ""
    year:         int = 1
    week:         int = 1
    created_at:   str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crisis_id":             self.crisis_id,
            "tier":                  self.tier.value,
            "brand":                 self.brand,
            "wrestler_ids":          self.wrestler_ids,
            "wrestler_names":        self.wrestler_names,
            "description":           self.description,
            "weekly_morale_drain":   self.weekly_morale_drain,
            "weeks_active":          self.weeks_active,
            "resolved":              self.resolved,
            "resolution_description": self.resolution_description,
            "year":                  self.year,
            "week":                  self.week,
            "created_at":            self.created_at,
        }


@dataclass
class OfficeAlert:
    """A GM alert that appears on the office screen."""
    alert_id:    str
    priority:    AlertPriority
    title:       str
    body:        str
    action_url:  Optional[str]    # e.g. /api/recovery/wrestler/<id>/menu
    action_label: Optional[str]   # "View Recovery Options"
    wrestler_id: Optional[str]
    wrestler_name: Optional[str]
    dismissed:   bool = False
    year:        int = 1
    week:        int = 1
    created_at:  str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id":     self.alert_id,
            "priority":     self.priority.value,
            "title":        self.title,
            "body":         self.body,
            "action_url":   self.action_url,
            "action_label": self.action_label,
            "wrestler_id":  self.wrestler_id,
            "wrestler_name": self.wrestler_name,
            "dismissed":    self.dismissed,
            "year":         self.year,
            "week":         self.week,
            "created_at":   self.created_at,
        }


# ============================================================
# Helper
# ============================================================

def _morale_category(morale: int) -> str:
    if morale <= 20:  return "miserable"
    if morale <= 40:  return "unhappy"
    if morale <= 50:  return "discontented"
    if morale <= 69:  return "content"
    if morale <= 89:  return "happy"
    return "ecstatic"


# ============================================================
# Step 260 — Show Recap Integration
# ============================================================

class ShowRecapInjector:
    """
    After a show is simulated, scan behavior events and recovery actions
    from that week and generate morale recap cards.
    """

    def generate_recap_events(
        self,
        show_id: str,
        year: int,
        week: int,
        behavior_events: List[Dict],    # from DB: behavior_events for this week
        recovery_events: List[Dict],    # from DB: recovery_events for this week
        wrestlers_by_id: Dict[str, Any],
    ) -> List[ShowMoraleEvent]:
        """Return a list of ShowMoraleEvent cards for the post-show recap."""
        cards: List[ShowMoraleEvent] = []

        # --- Behavior events ---
        BEHAVIOR_HEADLINES = {
            "release_demand":     ("🚨 Release Demand Filed",         AlertPriority.URGENT),
            "public_release_demand": ("📢 Public Release Demand",     AlertPriority.CRITICAL),
            "match_quality_decline": ("⭐ Match Quality Suffering",   AlertPriority.WARNING),
            "sandbagging":        ("🐌 Sandbagging Reported",          AlertPriority.WARNING),
            "cooperation_refusal": ("❌ Booking Refused",              AlertPriority.URGENT),
            "dirt_sheet_leak":    ("📰 Dirt Sheet Leak",              AlertPriority.WARNING),
            "social_media_vent":  ("📱 Social Media Incident",        AlertPriority.WARNING),
            "backstage_poison":   ("☠️ Backstage Toxicity",            AlertPriority.URGENT),
            "contract_running_down": ("📋 Lame Duck Mode",            AlertPriority.WARNING),
        }

        seen_wrestlers_behaviors: set = set()
        for be in behavior_events:
            btype = be.get("behavior_type", "")
            wid = be.get("wrestler_id", "")
            wname = be.get("wrestler_name", "")
            key = (wid, btype)
            if key in seen_wrestlers_behaviors:
                continue
            seen_wrestlers_behaviors.add(key)

            headline, priority = BEHAVIOR_HEADLINES.get(
                btype, (f"⚠️ Morale Incident", AlertPriority.WARNING)
            )

            description = be.get("description", "")
            if not description:
                description = (
                    f"{wname} is experiencing morale issues "
                    f"(current morale: {be.get('morale_at_time', '?')}). "
                    f"Management attention required."
                )

            cards.append(ShowMoraleEvent(
                event_id=str(uuid.uuid4()),
                category=MoraleEventCategory.BEHAVIOR_FIRED,
                priority=priority,
                headline=headline,
                description=description,
                wrestler_ids=[wid],
                wrestler_names=[wname],
                show_id=show_id,
                year=year,
                week=week,
                metadata={"behavior_type": btype, "morale_at_time": be.get("morale_at_time")},
            ))

        # --- Recovery events ---
        RECOVERY_HEADLINES = {
            "private_meeting":        "🤝 Private Meeting Held",
            "push_adjustment":        "📈 Push Adjusted",
            "contract_renegotiation": "💰 Contract Sweetened",
            "creative_input":         "🎭 Creative Control Granted",
            "time_off":               "😴 Time Off Approved",
            "mentorship_role":        "🎓 Mentorship Assigned",
        }

        for re in recovery_events:
            rtype = re.get("recovery_type", "")
            wname = re.get("wrestler_name", "")
            headline = RECOVERY_HEADLINES.get(rtype, "✅ Recovery Action Taken")
            outcome = re.get("outcome", "success")
            change = re.get("morale_change", 0)

            sign = "+" if change >= 0 else ""
            outcome_label = {"success": "✅", "partial": "⚠️", "backfire": "❌", "refused": "🚫"}.get(outcome, "✅")

            notes = re.get("notes", [])
            description = notes[0] if notes else f"{wname}: morale {sign}{change}."

            priority = (
                AlertPriority.WARNING if outcome == "backfire"
                else AlertPriority.INFO
            )

            cards.append(ShowMoraleEvent(
                event_id=str(uuid.uuid4()),
                category=MoraleEventCategory.RECOVERY_TAKEN,
                priority=priority,
                headline=f"{outcome_label} {headline}",
                description=description,
                wrestler_ids=[re.get("wrestler_id", "")],
                wrestler_names=[wname],
                show_id=show_id,
                year=year,
                week=week,
                metadata={"recovery_type": rtype, "outcome": outcome, "morale_change": change},
            ))

        # Sort: critical/urgent first
        priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.URGENT: 1,
            AlertPriority.WARNING: 2,
            AlertPriority.INFO: 3,
        }
        cards.sort(key=lambda c: priority_order.get(c.priority, 9))
        return cards


# ============================================================
# Step 261 — Morale-Driven Storyline Generator
# ============================================================

class MoraleStorylineGenerator:
    """
    Scans the roster for morale states that are ripe for storyline seeds.
    Each seed is a creative pitch the booker can accept or reject.
    """

    def scan_roster(
        self,
        wrestlers: List,
        behavior_states: Dict[str, Any],   # wrestler_id -> behavior state dict
        year: int,
        week: int,
    ) -> List[MoraleStorylineSeed]:
        seeds: List[MoraleStorylineSeed] = []

        for w in wrestlers:
            morale = w.morale
            state = behavior_states.get(w.id, {})

            # 1. Unhappy heel turn (discontented face → turns heel due to management frustration)
            if (morale <= 45 and getattr(w, 'alignment', '').lower() == 'face'
                    and state.get('has_requested_release')):
                seeds.append(self._heel_turn_seed(w, year, week))

            # 2. Departure angle (has public demand → work the real story into an angle)
            if state.get('has_gone_public') and morale <= 35:
                seeds.append(self._departure_angle_seed(w, year, week))

            # 3. Redemption arc (wrestler recovering from miserable to content)
            if 35 <= morale <= 50 and not state.get('has_requested_release'):
                seeds.append(self._redemption_arc_seed(w, year, week))

        # 4. Locker room revolt (3+ wrestlers on same brand are miserable)
        brands: Dict[str, List] = {}
        for w in wrestlers:
            b = getattr(w, 'primary_brand', 'Unknown')
            brands.setdefault(b, []).append(w)

        for brand, brand_wrestlers in brands.items():
            miserable = [w for w in brand_wrestlers if w.morale <= 30]
            if len(miserable) >= 3:
                seeds.append(self._locker_room_revolt_seed(miserable, brand, year, week))

        # 5. Veteran mentors rookie (ecstatic veteran + unhappy young talent on same brand)
        for brand, brand_wrestlers in brands.items():
            veterans = [w for w in brand_wrestlers
                        if w.morale >= 70 and getattr(w, 'is_major_superstar', False)]
            unhappy_young = [w for w in brand_wrestlers
                             if w.morale <= 50 and not getattr(w, 'is_major_superstar', False)]
            if veterans and unhappy_young:
                veteran = veterans[0]
                rookie = unhappy_young[0]
                seeds.append(self._mentorship_seed(veteran, rookie, year, week))

        # Deduplicate by primary wrestler + type
        seen = set()
        unique_seeds = []
        for s in seeds:
            key = (s.primary_wrestler_id, s.storyline_type.value)
            if key not in seen:
                seen.add(key)
                unique_seeds.append(s)

        return unique_seeds[:8]  # cap at 8 suggestions per scan

    # ------ seed builders ------

    def _heel_turn_seed(self, wrestler, year: int, week: int) -> MoraleStorylineSeed:
        return MoraleStorylineSeed(
            seed_id=str(uuid.uuid4()),
            storyline_type=MoraleStorylineType.UNHAPPY_HEEL_TURN,
            title=f"The Disillusionment of {wrestler.name}",
            logline=(
                f"{wrestler.name} — once beloved — turns on the fans after feeling "
                "management never valued their loyalty."
            ),
            full_outline=(
                f"Beat 1: {wrestler.name} loses a big match they feel they deserved to win. "
                "Cuts a subtle promo hinting at frustration. Fans are confused.\n"
                f"Beat 2: {wrestler.name} snaps on a beloved colleague, "
                "blaming the system. Heel turn complete. Crowd heat begins.\n"
                f"Beat 3: Full-blown heel persona. {wrestler.name} demands respect "
                "and the title shot they were 'owed'. Pay-off feud begins."
            ),
            primary_wrestler_id=wrestler.id,
            primary_wrestler_name=wrestler.name,
            supporting_cast=[],
            morale_trigger=wrestler.morale,
            urgency="high" if wrestler.morale <= 30 else "medium",
            suggested_duration_weeks=8,
            year=year,
            week=week,
        )

    def _departure_angle_seed(self, wrestler, year: int, week: int) -> MoraleStorylineSeed:
        return MoraleStorylineSeed(
            seed_id=str(uuid.uuid4()),
            storyline_type=MoraleStorylineType.DEPARTURE_ANGLE,
            title=f"{wrestler.name}'s Farewell Tour",
            logline=(
                f"{wrestler.name} publicly announces they are leaving ROC — "
                "turning their real frustration into a compelling on-screen exit story."
            ),
            full_outline=(
                f"Beat 1: {wrestler.name} cuts a shoot-style promo addressing 'contract talks'. "
                "Blurs kayfabe intentionally. Generates massive media coverage.\n"
                f"Beat 2: Rivals and allies react. One villain tries to accelerate "
                f"the departure; one friend tries to convince {wrestler.name} to stay.\n"
                f"Beat 3: Emotional final match. Outcome determines whether "
                f"{wrestler.name} exits as a hero or burns the place down on the way out."
            ),
            primary_wrestler_id=wrestler.id,
            primary_wrestler_name=wrestler.name,
            supporting_cast=[],
            morale_trigger=wrestler.morale,
            urgency="critical",
            suggested_duration_weeks=6,
            year=year,
            week=week,
        )

    def _redemption_arc_seed(self, wrestler, year: int, week: int) -> MoraleStorylineSeed:
        return MoraleStorylineSeed(
            seed_id=str(uuid.uuid4()),
            storyline_type=MoraleStorylineType.REDEMPTION_ARC,
            title=f"{wrestler.name}: Reborn",
            logline=(
                f"After hitting rock bottom, {wrestler.name} goes on a quiet, "
                "authentic comeback arc that earns genuine crowd sympathy."
            ),
            full_outline=(
                f"Beat 1: {wrestler.name} loses their third straight match. "
                "Locker room turns away. Vulnerable post-match promo goes viral.\n"
                f"Beat 2: A veteran or mentor reaches out. "
                f"{wrestler.name} quietly improves while the crowd starts to notice.\n"
                f"Beat 3: {wrestler.name} wins a big match in an upset. "
                "The crowd pops huge. Their morale story becomes a crowd-pleaser."
            ),
            primary_wrestler_id=wrestler.id,
            primary_wrestler_name=wrestler.name,
            supporting_cast=[],
            morale_trigger=wrestler.morale,
            urgency="low",
            suggested_duration_weeks=10,
            year=year,
            week=week,
        )

    def _locker_room_revolt_seed(
        self, miserable_wrestlers: List, brand: str, year: int, week: int
    ) -> MoraleStorylineSeed:
        primary = miserable_wrestlers[0]
        supporting = [
            {"id": w.id, "name": w.name, "role": "co-conspirator"}
            for w in miserable_wrestlers[1:4]
        ]
        return MoraleStorylineSeed(
            seed_id=str(uuid.uuid4()),
            storyline_type=MoraleStorylineType.LOCKER_ROOM_REVOLT,
            title=f"{brand} Civil War",
            logline=(
                f"A wave of discontent backstage on {brand} spills on-screen "
                "as multiple wrestlers form a united front against management."
            ),
            full_outline=(
                f"Beat 1: {primary.name} leads an alliance of unhappy talent. "
                "They refuse to follow 'official' booking decisions on air.\n"
                "Beat 2: Management (kayfabe GM character) responds by stacking the odds "
                "against the faction. Tension explodes into a brand takeover angle.\n"
                "Beat 3: Faction vs. management loyalists in a series of matches. "
                "Outcome reshuffles the brand's entire card — and calms the real locker room."
            ),
            primary_wrestler_id=primary.id,
            primary_wrestler_name=primary.name,
            supporting_cast=supporting,
            morale_trigger=primary.morale,
            urgency="critical" if len(miserable_wrestlers) >= 5 else "high",
            suggested_duration_weeks=12,
            year=year,
            week=week,
        )

    def _mentorship_seed(
        self, veteran, rookie, year: int, week: int
    ) -> MoraleStorylineSeed:
        return MoraleStorylineSeed(
            seed_id=str(uuid.uuid4()),
            storyline_type=MoraleStorylineType.VETERAN_MENTORS_ROOKIE,
            title=f"{veteran.name} Takes {rookie.name} Under Their Wing",
            logline=(
                f"ROC's elder statesman {veteran.name} reaches out to the struggling "
                f"{rookie.name}, creating an unlikely partnership both on and off screen."
            ),
            full_outline=(
                f"Beat 1: {veteran.name} defends {rookie.name} from a public attack "
                "backstage. Crowd is surprised — unlikely alliance forms.\n"
                f"Beat 2: {veteran.name} tags alongside {rookie.name}, "
                "using their star power to elevate the younger talent.\n"
                f"Beat 3: {rookie.name} wins a singles match while "
                f"{veteran.name} watches proudly from ringside. "
                "Legacy moment. Both morale scores tick up narratively."
            ),
            primary_wrestler_id=veteran.id,
            primary_wrestler_name=veteran.name,
            supporting_cast=[{"id": rookie.id, "name": rookie.name, "role": "mentee"}],
            morale_trigger=rookie.morale,
            urgency="medium",
            suggested_duration_weeks=8,
            year=year,
            week=week,
        )


# ============================================================
# Step 262 — Locker Room Crisis Escalation
# ============================================================

class CrisisEscalationEngine:
    """
    Evaluates the entire roster each week and determines crisis tier.
    Escalates or de-escalates. Applies passive morale drain to bystanders.
    """

    def evaluate(
        self,
        wrestlers: List,
        behavior_states: Dict[str, Any],   # wrestler_id -> dict
        year: int,
        week: int,
    ) -> Tuple[CrisisTier, List[OfficeAlert]]:
        """
        Returns (current_tier, alerts_generated).
        Caller must persist the result and apply morale drain.
        """
        alerts: List[OfficeAlert] = []

        # Count crisis indicators per brand
        brands: Dict[str, Dict] = {}
        for w in wrestlers:
            brand = getattr(w, 'primary_brand', 'Unknown')
            if brand not in brands:
                brands[brand] = {
                    "miserable": [], "unhappy": [], "public_demands": [],
                    "sandbagging": [], "poisoning": []
                }
            cat = _morale_category(w.morale)
            state = behavior_states.get(w.id, {})

            if cat == "miserable":
                brands[brand]["miserable"].append(w)
            elif cat == "unhappy":
                brands[brand]["unhappy"].append(w)

            if state.get("has_gone_public"):
                brands[brand]["public_demands"].append(w)
            if state.get("is_sandbagging"):
                brands[brand]["sandbagging"].append(w)
            if state.get("is_poisoning_locker_room"):
                brands[brand]["poisoning"].append(w)

        # Determine highest tier across all brands
        worst_tier = CrisisTier.NONE

        for brand, data in brands.items():
            total_unhappy = len(data["miserable"]) + len(data["unhappy"])
            has_public = len(data["public_demands"]) > 0
            has_sandbagging = len(data["sandbagging"]) > 0
            has_poison = len(data["poisoning"]) > 0

            if len(data["miserable"]) >= 5 and has_poison:
                tier = CrisisTier.MELTDOWN
            elif total_unhappy >= 3 and (has_public or has_sandbagging):
                tier = CrisisTier.CRISIS
            elif total_unhappy >= 1:
                tier = CrisisTier.TENSION
            else:
                tier = CrisisTier.NONE

            # Generate brand-level alerts
            if tier == CrisisTier.MELTDOWN:
                worst_tier = CrisisTier.MELTDOWN
                poison_names = ", ".join(w.name for w in data["poisoning"])
                alerts.append(OfficeAlert(
                    alert_id=str(uuid.uuid4()),
                    priority=AlertPriority.CRITICAL,
                    title=f"🔥 MELTDOWN: {brand}",
                    body=(
                        f"{brand} is in full meltdown. {len(data['miserable'])} wrestlers "
                        f"are miserable. Toxic influence spreading from: {poison_names}. "
                        "Immediate action required or the brand's ratings will crater."
                    ),
                    action_url="/api/recovery/summary",
                    action_label="Recovery Dashboard",
                    wrestler_id=data["poisoning"][0].id if data["poisoning"] else None,
                    wrestler_name=data["poisoning"][0].name if data["poisoning"] else None,
                    year=year,
                    week=week,
                ))
            elif tier == CrisisTier.CRISIS:
                if worst_tier not in (CrisisTier.MELTDOWN,):
                    worst_tier = CrisisTier.CRISIS
                public_names = ", ".join(w.name for w in data["public_demands"])
                alerts.append(OfficeAlert(
                    alert_id=str(uuid.uuid4()),
                    priority=AlertPriority.URGENT,
                    title=f"⚠️ Crisis: {brand}",
                    body=(
                        f"{brand} has a locker room crisis. {total_unhappy} wrestlers "
                        f"are unhappy or miserable. Public demands from: {public_names or 'none'}. "
                        "Performance is being affected."
                    ),
                    action_url="/api/morale/dashboard",
                    action_label="Morale Dashboard",
                    wrestler_id=None,
                    wrestler_name=None,
                    year=year,
                    week=week,
                ))
            elif tier == CrisisTier.TENSION:
                if worst_tier == CrisisTier.NONE:
                    worst_tier = CrisisTier.TENSION
                # Tension gets a lower-priority office alert
                alerts.append(OfficeAlert(
                    alert_id=str(uuid.uuid4()),
                    priority=AlertPriority.WARNING,
                    title=f"📉 Tension: {brand}",
                    body=(
                        f"{total_unhappy} wrestler(s) on {brand} are unhappy. "
                        "Address morale concerns before they escalate."
                    ),
                    action_url="/api/morale/behaviors",
                    action_label="View Behaviors",
                    wrestler_id=None,
                    wrestler_name=None,
                    year=year,
                    week=week,
                ))

        return worst_tier, alerts

    def apply_crisis_drain(
        self,
        tier: CrisisTier,
        wrestlers: List,
        behavior_states: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Apply passive weekly morale drain to bystander wrestlers during a crisis.
        Returns dict of {wrestler_id: morale_delta}.
        """
        deltas: Dict[str, int] = {}

        drain_map = {
            CrisisTier.NONE:     0,
            CrisisTier.TENSION:  -1,
            CrisisTier.CRISIS:   -3,
            CrisisTier.MELTDOWN: -6,
        }
        drain = drain_map.get(tier, 0)

        if drain == 0:
            return deltas

        for w in wrestlers:
            state = behavior_states.get(w.id, {})
            # Don't drain wrestlers already miserable — they're the source
            cat = _morale_category(w.morale)
            if cat == "miserable":
                continue
            # Don't drain wrestlers who are the ones causing the crisis
            if state.get("is_poisoning_locker_room") or state.get("has_gone_public"):
                continue

            actual_drain = drain + random.randint(-1, 1)
            w.adjust_morale(actual_drain)
            deltas[w.id] = actual_drain

        return deltas


# ============================================================
# Step 263 — Office Screen Broadcast
# ============================================================

class OfficeAlertBroadcaster:
    """
    Generates the alert feed shown on the GM office screen.
    Combines behavior events, crisis alerts, contract warnings,
    and recovery suggestions into a unified priority-sorted feed.
    """

    def generate_weekly_feed(
        self,
        wrestlers: List,
        behavior_states: Dict[str, Any],
        crisis_tier: CrisisTier,
        crisis_alerts: List[OfficeAlert],
        year: int,
        week: int,
    ) -> List[OfficeAlert]:
        """Generate the full alert feed for this week's office screen."""
        feed = list(crisis_alerts)

        for w in wrestlers:
            state = behavior_states.get(w.id, {})
            morale = w.morale

            # Release demand alert
            if state.get("has_requested_release") and not state.get("has_gone_public"):
                feed.append(OfficeAlert(
                    alert_id=str(uuid.uuid4()),
                    priority=AlertPriority.URGENT,
                    title=f"📩 Release Demand: {w.name}",
                    body=(
                        f"{w.name} (Morale: {morale}) has privately requested a release. "
                        f"Demand #{state.get('release_demand_count', 1)}. "
                        "Respond before this goes public."
                    ),
                    action_url=f"/api/morale/wrestler/{w.id}",
                    action_label="View Wrestler",
                    wrestler_id=w.id,
                    wrestler_name=w.name,
                    year=year,
                    week=week,
                ))

            # Public demand alert
            if state.get("has_gone_public"):
                feed.append(OfficeAlert(
                    alert_id=str(uuid.uuid4()),
                    priority=AlertPriority.CRITICAL,
                    title=f"📢 Public Demand: {w.name}",
                    body=(
                        f"{w.name} has gone public with their release demand. "
                        f"Statement: \"{state.get('public_statement', 'No comment.')}\" "
                        "Media is watching. Act now."
                    ),
                    action_url=f"/api/morale/wrestler/{w.id}/dismiss-public",
                    action_label="Respond Publicly",
                    wrestler_id=w.id,
                    wrestler_name=w.name,
                    year=year,
                    week=week,
                ))

            # Backstage poison warning
            if state.get("is_poisoning_locker_room"):
                targets = state.get("poisoning_targets", [])
                feed.append(OfficeAlert(
                    alert_id=str(uuid.uuid4()),
                    priority=AlertPriority.URGENT,
                    title=f"☠️ Toxic Influence: {w.name}",
                    body=(
                        f"{w.name} is poisoning the locker room, dragging down "
                        f"{len(targets)} colleague(s) on {getattr(w, 'primary_brand', 'their brand')}. "
                        "Isolate or release before the damage spreads further."
                    ),
                    action_url=f"/api/recovery/wrestler/{w.id}/menu",
                    action_label="Recovery Options",
                    wrestler_id=w.id,
                    wrestler_name=w.name,
                    year=year,
                    week=week,
                ))

            # Low morale general warning
            elif morale <= 35 and not state.get("has_requested_release"):
                feed.append(OfficeAlert(
                    alert_id=str(uuid.uuid4()),
                    priority=AlertPriority.WARNING,
                    title=f"📉 Low Morale: {w.name}",
                    body=(
                        f"{w.name}'s morale has dropped to {morale}. "
                        "No release demand yet, but this is a warning sign. "
                        "Consider a recovery action."
                    ),
                    action_url=f"/api/recovery/wrestler/{w.id}/menu",
                    action_label="Recovery Options",
                    wrestler_id=w.id,
                    wrestler_name=w.name,
                    year=year,
                    week=week,
                ))

        # Sort: CRITICAL → URGENT → WARNING → INFO
        priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.URGENT: 1,
            AlertPriority.WARNING: 2,
            AlertPriority.INFO: 3,
        }
        feed.sort(key=lambda a: priority_order.get(a.priority, 9))
        return feed


# ============================================================
# Step 264 — Weekly Morale Digest
# ============================================================

class WeeklyMoraleDigest:
    """
    Generates a narrative end-of-week morale summary shown in the recap.
    Written in GM internal-report style.
    """

    def generate(
        self,
        wrestlers: List,
        behavior_states: Dict[str, Any],
        recovery_events_this_week: List[Dict],
        crisis_tier: CrisisTier,
        year: int,
        week: int,
    ) -> Dict[str, Any]:
        total = len(wrestlers)
        morale_sum = sum(w.morale for w in wrestlers)
        avg_morale = round(morale_sum / max(total, 1), 1)

        miserable_list = [w for w in wrestlers if w.morale <= 20]
        unhappy_list   = [w for w in wrestlers if 21 <= w.morale <= 40]
        happy_list     = [w for w in wrestlers if w.morale >= 70]

        most_improved = None
        most_declined = None

        # Find best/worst from recovery events
        if recovery_events_this_week:
            best = max(recovery_events_this_week, key=lambda e: e.get("morale_change", 0))
            worst = min(recovery_events_this_week, key=lambda e: e.get("morale_change", 0))
            if best.get("morale_change", 0) > 0:
                most_improved = best
            if worst.get("morale_change", 0) < 0:
                most_declined = worst

        # Build narrative lines
        lines = []

        if crisis_tier == CrisisTier.MELTDOWN:
            lines.append(
                "🔥 MELTDOWN ALERT — The promotion is in full crisis. "
                f"{len(miserable_list)} wrestlers are at rock bottom. "
                "Immediate executive intervention is required."
            )
        elif crisis_tier == CrisisTier.CRISIS:
            lines.append(
                f"⚠️ Week {week}, Year {year}: The locker room is under strain. "
                f"{len(unhappy_list) + len(miserable_list)} wrestlers are unhappy or miserable. "
                "Public relations damage is possible if not addressed."
            )
        elif crisis_tier == CrisisTier.TENSION:
            lines.append(
                f"📉 Week {week}, Year {year}: Early warning signs of locker room tension. "
                f"{len(unhappy_list)} wrestlers are unhappy. "
                "Monitor closely and use proactive recovery tools."
            )
        else:
            lines.append(
                f"✅ Week {week}, Year {year}: Roster morale is generally healthy. "
                f"Average morale: {avg_morale}/100. {len(happy_list)} wrestlers are happy or ecstatic."
            )

        if miserable_list:
            names = ", ".join(w.name for w in miserable_list[:3])
            extra = f" (+{len(miserable_list) - 3} more)" if len(miserable_list) > 3 else ""
            lines.append(f"⛔ Miserable wrestlers requiring urgent attention: {names}{extra}.")

        if most_improved:
            lines.append(
                f"📈 Biggest morale gain this week: {most_improved['wrestler_name']} "
                f"({most_improved.get('morale_before', '?')} → {most_improved.get('morale_after', '?')}) "
                f"via {most_improved.get('recovery_type', 'management action').replace('_', ' ')}."
            )

        if most_declined:
            lines.append(
                f"📉 Biggest morale drop this week: {most_declined['wrestler_name']} "
                f"({most_declined.get('morale_before', '?')} → {most_declined.get('morale_after', '?')})."
            )

        return {
            "year": year,
            "week": week,
            "avg_morale": avg_morale,
            "crisis_tier": crisis_tier.value,
            "total_wrestlers": total,
            "miserable_count": len(miserable_list),
            "unhappy_count": len(unhappy_list),
            "happy_count": len(happy_list),
            "narrative_lines": lines,
            "most_improved": most_improved,
            "most_declined": most_declined,
        }


# ============================================================
# Step 265 — Consequence Propagation
# ============================================================

class ConsequencePropagator:
    """
    When a major morale event happens (public demand, meltdown, crisis resolved),
    the consequences ripple to related wrestlers:
      - Tag partners lose morale when their partner goes public
      - Brand-mates gain morale when a toxic wrestler is released
      - Allies of a wrestler who got a big push feel inspired
    """

    def propagate(
        self,
        trigger_wrestler,
        trigger_event_type: str,   # "public_demand" | "release" | "push" | "crisis_resolved"
        all_wrestlers: List,
        year: int,
        week: int,
    ) -> List[Dict[str, Any]]:
        """
        Returns list of {wrestler_id, wrestler_name, morale_delta, reason} dicts.
        Caller must call wrestler.adjust_morale() and save.
        """
        effects = []
        trigger_brand = getattr(trigger_wrestler, 'primary_brand', None)

        brand_mates = [
            w for w in all_wrestlers
            if w.id != trigger_wrestler.id
            and getattr(w, 'primary_brand', None) == trigger_brand
        ]

        if trigger_event_type == "public_demand":
            # Tag partners and close allies get nervous (-3 to -8)
            for w in brand_mates[:6]:
                delta = random.randint(-8, -3)
                w.adjust_morale(delta)
                effects.append({
                    "wrestler_id": w.id,
                    "wrestler_name": w.name,
                    "morale_delta": delta,
                    "reason": (
                        f"{trigger_wrestler.name}'s public release demand has unsettled "
                        f"the {trigger_brand} locker room."
                    ),
                })

        elif trigger_event_type == "release":
            # Toxic wrestler released → brand-mates relieved (+2 to +8)
            for w in brand_mates:
                delta = random.randint(2, 8)
                w.adjust_morale(delta)
                effects.append({
                    "wrestler_id": w.id,
                    "wrestler_name": w.name,
                    "morale_delta": delta,
                    "reason": (
                        f"{trigger_wrestler.name}'s departure has cleared the air "
                        f"on {trigger_brand}."
                    ),
                })

        elif trigger_event_type == "push":
            # A colleague got a big push → nearby wrestlers feel inspired (+1 to +5)
            for w in brand_mates[:5]:
                if w.morale < 80:
                    delta = random.randint(1, 5)
                    w.adjust_morale(delta)
                    effects.append({
                        "wrestler_id": w.id,
                        "wrestler_name": w.name,
                        "morale_delta": delta,
                        "reason": (
                            f"{trigger_wrestler.name}'s push has raised spirits "
                            f"on {trigger_brand}."
                        ),
                    })

        elif trigger_event_type == "crisis_resolved":
            # Crisis resolved → whole brand gets a moderate boost (+3 to +10)
            for w in brand_mates:
                delta = random.randint(3, 10)
                w.adjust_morale(delta)
                effects.append({
                    "wrestler_id": w.id,
                    "wrestler_name": w.name,
                    "morale_delta": delta,
                    "reason": (
                        f"The {trigger_brand} locker room crisis has been resolved. "
                        "The air is clear."
                    ),
                })

        return effects


# ============================================================
# Module-level singletons
# ============================================================

show_recap_injector       = ShowRecapInjector()
morale_storyline_generator = MoraleStorylineGenerator()
crisis_escalation_engine  = CrisisEscalationEngine()
office_alert_broadcaster  = OfficeAlertBroadcaster()
weekly_morale_digest      = WeeklyMoraleDigest()
consequence_propagator    = ConsequencePropagator()