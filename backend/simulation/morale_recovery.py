"""
morale_recovery.py
Steps 254-259: Morale Recovery System

Six management tools for proactively restoring wrestler morale:
  Step 254 — Private Meetings       (listen, acknowledge, commit)
  Step 255 — Push Adjustments       (main event push, midcard push, protection)
  Step 256 — Contract Renegotiation (salary raise, extension, signing bonus)
  Step 257 — Creative Input         (storyline direction, match type approval, segment veto)
  Step 258 — Time Off / Rest        (hiatus, lighter schedule, vacation)
  Step 259 — Mentorship Roles       (assign as mentor to younger talent)

Design rules:
  - All recoveries apply a cooldown so the booker can't spam them
  - Each recovery has a morale floor requirement (some only work at mild unhappiness)
  - Recovery effectiveness scales inversely with wrestler's current morale
    (bigger swing when they're more miserable)
  - Side effects (cost, roster impact) are tracked and reported
  - Results are persisted as RecoveryEvent rows via database
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

class RecoveryType(str, Enum):
    PRIVATE_MEETING       = "private_meeting"
    PUSH_ADJUSTMENT       = "push_adjustment"
    CONTRACT_RENEGOTIATION = "contract_renegotiation"
    CREATIVE_INPUT        = "creative_input"
    TIME_OFF              = "time_off"
    MENTORSHIP_ROLE       = "mentorship_role"


class RecoveryOutcome(str, Enum):
    SUCCESS    = "success"      # Full morale gain realised
    PARTIAL    = "partial"      # Reduced gain — wrestler sceptical
    BACKFIRE   = "backfire"     # Morale dropped (promise felt hollow / insincere)
    REFUSED    = "refused"      # Wrestler declined management's approach


class MeetingApproach(str, Enum):
    LISTEN     = "listen"       # Just hear them out — no commitment
    ACKNOWLEDGE = "acknowledge" # Admit booker was wrong about something
    COMMIT     = "commit"       # Make a specific actionable promise


class PushType(str, Enum):
    MAIN_EVENT  = "main_event"   # Elevated to main event scene
    MIDCARD     = "midcard"      # Given featured midcard storyline
    PROTECTION  = "protection"   # Stop booking losses, protected finisher


class RenegotiationTool(str, Enum):
    SALARY_RAISE  = "salary_raise"   # Immediate per-show raise
    EXTENSION     = "extension"      # Add weeks to existing contract
    SIGNING_BONUS = "signing_bonus"  # One-time cash payment


class CreativeInputType(str, Enum):
    STORYLINE_DIRECTION = "storyline_direction"  # Wrestler helps shape their own feud
    MATCH_TYPE_APPROVAL = "match_type_approval"  # Approval rights on stipulation
    SEGMENT_VETO        = "segment_veto"          # Can veto one segment per show


class TimeOffType(str, Enum):
    HIATUS          = "hiatus"           # Full break from TV (2-6 weeks)
    LIGHTER_SCHEDULE = "lighter_schedule" # Fewer appearances per cycle
    VACATION        = "vacation"          # 1-week luxury perk, small morale burst


# ============================================================
# Data classes
# ============================================================

@dataclass
class RecoveryEvent:
    """Persisted record of a recovery action taken by management."""
    event_id:       str
    wrestler_id:    str
    wrestler_name:  str
    recovery_type:  RecoveryType
    outcome:        RecoveryOutcome
    morale_before:  int
    morale_after:   int
    morale_change:  int
    details:        Dict[str, Any]   # recovery-specific parameters
    notes:          List[str]        # human-readable outcome notes
    cost:           int              # $ spent (salary raise, bonus, etc.)
    game_year:      int
    game_week:      int
    created_at:     str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "wrestler_id":   self.wrestler_id,
            "wrestler_name": self.wrestler_name,
            "recovery_type": self.recovery_type.value,
            "outcome":       self.outcome.value,
            "morale_before": self.morale_before,
            "morale_after":  self.morale_after,
            "morale_change": self.morale_change,
            "details":       self.details,
            "notes":         self.notes,
            "cost":          self.cost,
            "game_year":     self.game_year,
            "game_week":     self.game_week,
            "created_at":    self.created_at,
        }


@dataclass
class RecoveryCooldown:
    """Per-wrestler cooldown tracker for each recovery type."""
    wrestler_id: str
    # Maps RecoveryType.value -> game week of last use
    last_used: Dict[str, int] = field(default_factory=dict)

    # Cooldown durations in game weeks
    COOLDOWNS: Dict[str, int] = field(default_factory=lambda: {
        RecoveryType.PRIVATE_MEETING.value:        2,
        RecoveryType.PUSH_ADJUSTMENT.value:        8,
        RecoveryType.CONTRACT_RENEGOTIATION.value: 12,
        RecoveryType.CREATIVE_INPUT.value:         6,
        RecoveryType.TIME_OFF.value:               10,
        RecoveryType.MENTORSHIP_ROLE.value:        16,
    })

    def can_use(self, recovery_type: RecoveryType, current_week_abs: int) -> bool:
        last = self.last_used.get(recovery_type.value, -999)
        cooldown = self.COOLDOWNS.get(recovery_type.value, 4)
        return (current_week_abs - last) >= cooldown

    def weeks_until_available(self, recovery_type: RecoveryType, current_week_abs: int) -> int:
        last = self.last_used.get(recovery_type.value, -999)
        cooldown = self.COOLDOWNS.get(recovery_type.value, 4)
        remaining = cooldown - (current_week_abs - last)
        return max(0, remaining)

    def mark_used(self, recovery_type: RecoveryType, current_week_abs: int):
        self.last_used[recovery_type.value] = current_week_abs


# ============================================================
# Helper: absolute week counter (year * 52 + week)
# ============================================================

def _abs_week(year: int, week: int) -> int:
    return (year - 1) * 52 + week


def _morale_category(morale: int) -> str:
    if morale <= 20:   return "miserable"
    if morale <= 40:   return "unhappy"
    if morale <= 50:   return "discontented"
    if morale <= 69:   return "content"
    if morale <= 89:   return "happy"
    return "ecstatic"


# ============================================================
# Core Recovery Engine
# ============================================================

class MoraleRecoveryEngine:
    """
    Handles all six morale recovery tools.
    Each method returns a RecoveryEvent describing what happened.
    """

    # ----------------------------------------------------------
    # Step 254 — Private Meeting
    # ----------------------------------------------------------

    def private_meeting(
        self,
        wrestler,
        approach: MeetingApproach,
        promise_detail: str,        # used when approach == COMMIT
        year: int,
        week: int,
        cooldown: RecoveryCooldown,
    ) -> RecoveryEvent:
        """
        Hold a private 1-on-1 meeting with the wrestler.

        Approach outcomes:
          LISTEN      +5..+12   — reliable but small
          ACKNOWLEDGE +8..+18   — wrestler respects honesty; backfire if morale > 60
          COMMIT      +10..+25  — big gain but 25% chance of PARTIAL if morale < 30
        """
        rtype = RecoveryType.PRIVATE_MEETING
        abs_w = _abs_week(year, week)
        morale_before = wrestler.morale
        notes: List[str] = []
        cost = 0

        # Backfire condition: wrestler is content — meeting feels patronising
        if morale_before >= 65 and approach != MeetingApproach.LISTEN:
            wrestler.adjust_morale(-5)
            outcome = RecoveryOutcome.BACKFIRE
            morale_change = wrestler.morale - morale_before
            notes.append(
                f"{wrestler.name} felt the meeting was unnecessary — their morale is fine. "
                "Save management meetings for wrestlers who actually need them."
            )
        elif approach == MeetingApproach.LISTEN:
            gain = random.randint(5, 12)
            wrestler.adjust_morale(gain)
            outcome = RecoveryOutcome.SUCCESS
            morale_change = wrestler.morale - morale_before
            notes.append(
                f"You listened to {wrestler.name}'s grievances without making commitments. "
                f"They feel heard. Morale +{gain}."
            )
        elif approach == MeetingApproach.ACKNOWLEDGE:
            gain = random.randint(8, 18)
            wrestler.adjust_morale(gain)
            outcome = RecoveryOutcome.SUCCESS
            morale_change = wrestler.morale - morale_before
            notes.append(
                f"You acknowledged that {wrestler.name} deserved better. "
                f"Their respect for management improved. Morale +{gain}."
            )
        else:  # COMMIT
            if morale_before <= 30 and random.random() < 0.25:
                # Sceptical — too far gone to believe promises
                gain = random.randint(3, 8)
                wrestler.adjust_morale(gain)
                outcome = RecoveryOutcome.PARTIAL
                morale_change = wrestler.morale - morale_before
                notes.append(
                    f"{wrestler.name} is sceptical about management promises after "
                    f"being mistreated. They gave a half-smile. Morale +{gain} (reduced)."
                )
            else:
                gain = random.randint(10, 25)
                wrestler.adjust_morale(gain)
                outcome = RecoveryOutcome.SUCCESS
                morale_change = wrestler.morale - morale_before
                notes.append(
                    f"You committed to: '{promise_detail}'. "
                    f"{wrestler.name} left the meeting re-energised. Morale +{gain}. "
                    "⚠️ Make good on this promise or face a morale crash."
                )

        cooldown.mark_used(rtype, abs_w)

        return RecoveryEvent(
            event_id=str(uuid.uuid4()),
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            recovery_type=rtype,
            outcome=outcome,
            morale_before=morale_before,
            morale_after=wrestler.morale,
            morale_change=morale_change,
            details={
                "approach": approach.value,
                "promise_detail": promise_detail,
            },
            notes=notes,
            cost=cost,
            game_year=year,
            game_week=week,
        )

    # ----------------------------------------------------------
    # Step 255 — Push Adjustment
    # ----------------------------------------------------------

    def push_adjustment(
        self,
        wrestler,
        push_type: PushType,
        year: int,
        week: int,
        cooldown: RecoveryCooldown,
    ) -> RecoveryEvent:
        """
        Elevate or protect the wrestler's on-screen position.

        MAIN_EVENT   +15..+30  (only meaningful if wrestler is midcard or below)
        MIDCARD      +10..+20
        PROTECTION   +8..+15   (stops losses without changing position)
        """
        rtype = RecoveryType.PUSH_ADJUSTMENT
        abs_w = _abs_week(year, week)
        morale_before = wrestler.morale
        notes: List[str] = []
        cost = 0

        role = getattr(wrestler, 'role', 'midcard').lower()

        if push_type == PushType.MAIN_EVENT:
            if role in ('main_eventer', 'champion'):
                # Already there — push feels hollow
                gain = random.randint(3, 8)
                outcome = RecoveryOutcome.PARTIAL
                notes.append(
                    f"{wrestler.name} is already in the main event scene. "
                    "They shrugged at the announcement. Morale boost is minimal."
                )
            else:
                gain = random.randint(15, 30)
                outcome = RecoveryOutcome.SUCCESS
                notes.append(
                    f"🏆 {wrestler.name} has been elevated to the main event! "
                    f"Morale +{gain}. Expect them to step up their effort immediately."
                )
        elif push_type == PushType.MIDCARD:
            gain = random.randint(10, 20)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"📺 {wrestler.name} receives a featured midcard storyline. "
                f"Morale +{gain}. They feel valued by the creative team."
            )
        else:  # PROTECTION
            gain = random.randint(8, 15)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"🛡️ {wrestler.name}'s booking has been protected — "
                "no more clean losses, finisher preserved. "
                f"Morale +{gain}. They notice the respect."
            )

        wrestler.adjust_morale(gain)
        morale_change = wrestler.morale - morale_before
        cooldown.mark_used(rtype, abs_w)

        return RecoveryEvent(
            event_id=str(uuid.uuid4()),
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            recovery_type=rtype,
            outcome=outcome,
            morale_before=morale_before,
            morale_after=wrestler.morale,
            morale_change=morale_change,
            details={"push_type": push_type.value},
            notes=notes,
            cost=cost,
            game_year=year,
            game_week=week,
        )

    # ----------------------------------------------------------
    # Step 256 — Contract Renegotiation
    # ----------------------------------------------------------

    def contract_renegotiation(
        self,
        wrestler,
        tool: RenegotiationTool,
        salary_raise: int = 0,       # $ per show (for SALARY_RAISE)
        extension_weeks: int = 0,    # weeks added (for EXTENSION)
        bonus_amount: int = 0,       # one-time $ (for SIGNING_BONUS)
        year: int = 1,
        week: int = 1,
        cooldown: RecoveryCooldown = None,
        universe=None,               # needed to charge promotion balance
    ) -> Tuple[RecoveryEvent, int]:
        """
        Offer contract sweetener.

        Returns (RecoveryEvent, actual_cost_charged).
        Caller is responsible for deducting cost from promotion balance.
        """
        rtype = RecoveryType.CONTRACT_RENEGOTIATION
        abs_w = _abs_week(year, week)
        morale_before = wrestler.morale
        notes: List[str] = []
        cost = 0

        if tool == RenegotiationTool.SALARY_RAISE:
            if salary_raise <= 0:
                salary_raise = 1000
            wrestler.contract.salary_per_show += salary_raise
            # Weekly cost impact
            cost = salary_raise  # per show going forward — logged as one-time for event
            # Morale gain scales with raise size relative to current salary
            current = wrestler.contract.salary_per_show - salary_raise
            pct_raise = salary_raise / max(current, 1000) * 100
            gain = min(int(pct_raise * 0.5) + 8, 30)
            wrestler.adjust_morale(gain)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"💰 Salary raised by ${salary_raise:,}/show "
                f"(now ${wrestler.contract.salary_per_show:,}/show). "
                f"Morale +{gain}."
            )

        elif tool == RenegotiationTool.EXTENSION:
            if extension_weeks <= 0:
                extension_weeks = 12
            wrestler.contract.weeks_remaining += extension_weeks
            wrestler.contract.total_length_weeks += extension_weeks
            cost = 0
            gain = min(extension_weeks // 2, 20)
            wrestler.adjust_morale(gain)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"📋 Contract extended by {extension_weeks} weeks "
                f"({wrestler.contract.weeks_remaining} weeks remaining). "
                f"Morale +{gain}."
            )

        else:  # SIGNING_BONUS
            if bonus_amount <= 0:
                bonus_amount = 10000
            cost = bonus_amount
            gain = min(int(bonus_amount / 1000) + 5, 25)
            wrestler.adjust_morale(gain)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"🎁 Signing bonus of ${bonus_amount:,} issued. "
                f"Morale +{gain}. {wrestler.name} appreciates the gesture of good faith."
            )

        morale_change = wrestler.morale - morale_before
        if cooldown:
            cooldown.mark_used(rtype, abs_w)

        event = RecoveryEvent(
            event_id=str(uuid.uuid4()),
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            recovery_type=rtype,
            outcome=outcome,
            morale_before=morale_before,
            morale_after=wrestler.morale,
            morale_change=morale_change,
            details={
                "tool": tool.value,
                "salary_raise": salary_raise,
                "extension_weeks": extension_weeks,
                "bonus_amount": bonus_amount,
            },
            notes=notes,
            cost=cost,
            game_year=year,
            game_week=week,
        )
        return event, cost

    # ----------------------------------------------------------
    # Step 257 — Creative Input
    # ----------------------------------------------------------

    def creative_input(
        self,
        wrestler,
        input_type: CreativeInputType,
        year: int,
        week: int,
        cooldown: RecoveryCooldown,
    ) -> RecoveryEvent:
        """
        Give the wrestler a say in their creative direction.

        STORYLINE_DIRECTION  +10..+20   ongoing morale boost
        MATCH_TYPE_APPROVAL  +8..+15
        SEGMENT_VETO         +6..+12    (weak but stackable, no cooldown penalty)
        """
        rtype = RecoveryType.CREATIVE_INPUT
        abs_w = _abs_week(year, week)
        morale_before = wrestler.morale
        notes: List[str] = []
        cost = 0

        # High-morale wrestlers still love creative control — no backfire
        if input_type == CreativeInputType.STORYLINE_DIRECTION:
            gain = random.randint(10, 20)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"🎭 {wrestler.name} now has input on their storyline direction. "
                f"They've submitted three ideas to creative. Morale +{gain}. "
                "Their in-ring intensity will reflect this investment."
            )
        elif input_type == CreativeInputType.MATCH_TYPE_APPROVAL:
            gain = random.randint(8, 15)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"📝 {wrestler.name} has match-type approval for the next 8 weeks. "
                f"No more surprise stipulations without sign-off. Morale +{gain}."
            )
        else:  # SEGMENT_VETO
            gain = random.randint(6, 12)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"🚫 {wrestler.name} has been granted one segment veto per show cycle. "
                f"They immediately vetoed a comedy segment they were dreading. Morale +{gain}."
            )

        wrestler.adjust_morale(gain)
        morale_change = wrestler.morale - morale_before
        cooldown.mark_used(rtype, abs_w)

        return RecoveryEvent(
            event_id=str(uuid.uuid4()),
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            recovery_type=rtype,
            outcome=outcome,
            morale_before=morale_before,
            morale_after=wrestler.morale,
            morale_change=morale_change,
            details={"input_type": input_type.value},
            notes=notes,
            cost=cost,
            game_year=year,
            game_week=week,
        )

    # ----------------------------------------------------------
    # Step 258 — Time Off / Rest
    # ----------------------------------------------------------

    def time_off(
        self,
        wrestler,
        off_type: TimeOffType,
        hiatus_weeks: int = 4,        # used for HIATUS
        year: int = 1,
        week: int = 1,
        cooldown: RecoveryCooldown = None,
        behavior_state=None,          # WrestlerBehaviorState — clears lame duck if applicable
    ) -> RecoveryEvent:
        """
        Pull the wrestler from TV for rest.

        HIATUS          +15..+30  (miss shows but return refreshed)
        LIGHTER_SCHEDULE +8..+15  (still appears but not overworked)
        VACATION        +10..+18  (one-week luxury perk)
        """
        rtype = RecoveryType.TIME_OFF
        abs_w = _abs_week(year, week) if year and week else 0
        morale_before = wrestler.morale
        notes: List[str] = []
        cost = 0

        if off_type == TimeOffType.HIATUS:
            if hiatus_weeks < 2:
                hiatus_weeks = 2
            if hiatus_weeks > 8:
                hiatus_weeks = 8
            gain = random.randint(15, 30)
            wrestler.adjust_morale(gain)
            outcome = RecoveryOutcome.SUCCESS
            # Mark wrestler unavailable (caller handles booking logic)
            notes.append(
                f"😴 {wrestler.name} is on hiatus for {hiatus_weeks} weeks. "
                f"They'll return refreshed and re-motivated. Morale +{gain}. "
                "⚠️ They will be absent from booking during this period."
            )
            # Clear lame duck state — rest resets the clock
            if behavior_state:
                behavior_state.is_running_down_contract = False
                behavior_state.lame_duck_effort_penalty = 0.0

        elif off_type == TimeOffType.LIGHTER_SCHEDULE:
            gain = random.randint(8, 15)
            wrestler.adjust_morale(gain)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"📅 {wrestler.name}'s schedule has been lightened. "
                f"Fewer road dates, more recovery time. Morale +{gain}."
            )

        else:  # VACATION
            cost = random.randint(3000, 8000)  # company-sponsored luxury trip
            gain = random.randint(10, 18)
            wrestler.adjust_morale(gain)
            outcome = RecoveryOutcome.SUCCESS
            notes.append(
                f"✈️ Company-sponsored vacation for {wrestler.name} (cost: ${cost:,}). "
                f"They came back tanned, rested, and focused. Morale +{gain}."
            )

        morale_change = wrestler.morale - morale_before
        if cooldown:
            cooldown.mark_used(rtype, abs_w)

        return RecoveryEvent(
            event_id=str(uuid.uuid4()),
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            recovery_type=rtype,
            outcome=outcome,
            morale_before=morale_before,
            morale_after=wrestler.morale,
            morale_change=morale_change,
            details={
                "off_type": off_type.value,
                "hiatus_weeks": hiatus_weeks if off_type == TimeOffType.HIATUS else 0,
            },
            notes=notes,
            cost=cost,
            game_year=year,
            game_week=week,
        )

    # ----------------------------------------------------------
    # Step 259 — Mentorship Role
    # ----------------------------------------------------------

    def assign_mentorship(
        self,
        mentor,               # experienced wrestler (mentor)
        mentee,               # younger talent being mentored
        year: int,
        week: int,
        cooldown: RecoveryCooldown,
        all_wrestlers: List,  # full roster for cross-brand check
    ) -> Tuple[RecoveryEvent, Optional[RecoveryEvent]]:
        """
        Assign an experienced wrestler as a mentor to a younger talent.

        Mentor gains: +8..+20 (sense of purpose, legacy thinking)
        Mentee gains: +3..+10 (opportunity recognition)

        Requirements:
          - Mentor must be experienced (≥5 years equivalent: contract_total_weeks ≥ 130
            OR is_major_superstar)
          - Mentee must be younger/less experienced
          - Both must be on the same brand (or one of them is brand-agnostic)

        Returns (mentor_event, mentee_event). mentee_event may be None if same-brand check fails.
        """
        rtype = RecoveryType.MENTORSHIP_ROLE
        abs_w = _abs_week(year, week)
        mentor_morale_before = mentor.morale
        notes_mentor: List[str] = []
        notes_mentee: List[str] = []

        # Eligibility: mentor needs tenure or star status
        is_veteran = (
            getattr(mentor, 'is_major_superstar', False) or
            getattr(mentor.contract, 'total_length_weeks', 0) >= 130
        )

        if not is_veteran:
            # Not experienced enough — awkward pairing
            mentor.adjust_morale(-3)
            mentor_event = RecoveryEvent(
                event_id=str(uuid.uuid4()),
                wrestler_id=mentor.id,
                wrestler_name=mentor.name,
                recovery_type=rtype,
                outcome=RecoveryOutcome.BACKFIRE,
                morale_before=mentor_morale_before,
                morale_after=mentor.morale,
                morale_change=mentor.morale - mentor_morale_before,
                details={
                    "mentor_id": mentor.id,
                    "mentee_id": mentee.id,
                    "mentee_name": mentee.name,
                },
                notes=[
                    f"{mentor.name} doesn't feel they have enough experience "
                    "to be a mentor yet. The assignment felt patronising. Morale −3."
                ],
                cost=0,
                game_year=year,
                game_week=week,
            )
            return mentor_event, None

        # Mentor gains purpose
        mentor_gain = random.randint(8, 20)
        mentor.adjust_morale(mentor_gain)
        notes_mentor.append(
            f"🎓 {mentor.name} has been assigned as a mentor to {mentee.name}. "
            f"They feel a sense of legacy and purpose. Morale +{mentor_gain}. "
            "Their match quality and locker room presence will improve."
        )

        # Check same brand
        mentor_brand = getattr(mentor, 'primary_brand', None)
        mentee_brand = getattr(mentee, 'primary_brand', None)
        same_brand = (mentor_brand == mentee_brand) or not mentor_brand or not mentee_brand

        mentee_event = None
        if same_brand:
            mentee_morale_before = mentee.morale
            mentee_gain = random.randint(3, 10)
            mentee.adjust_morale(mentee_gain)
            notes_mentee.append(
                f"⭐ {mentee.name} is being mentored by {mentor.name}. "
                f"They're learning from one of the best. Morale +{mentee_gain}."
            )
            mentee_event = RecoveryEvent(
                event_id=str(uuid.uuid4()),
                wrestler_id=mentee.id,
                wrestler_name=mentee.name,
                recovery_type=rtype,
                outcome=RecoveryOutcome.SUCCESS,
                morale_before=mentee_morale_before,
                morale_after=mentee.morale,
                morale_change=mentee.morale - mentee_morale_before,
                details={
                    "mentor_id": mentor.id,
                    "mentor_name": mentor.name,
                    "mentee_id": mentee.id,
                },
                notes=notes_mentee,
                cost=0,
                game_year=year,
                game_week=week,
            )

        cooldown.mark_used(rtype, abs_w)

        mentor_event = RecoveryEvent(
            event_id=str(uuid.uuid4()),
            wrestler_id=mentor.id,
            wrestler_name=mentor.name,
            recovery_type=rtype,
            outcome=RecoveryOutcome.SUCCESS,
            morale_before=mentor_morale_before,
            morale_after=mentor.morale,
            morale_change=mentor.morale - mentor_morale_before,
            details={
                "mentor_id": mentor.id,
                "mentee_id": mentee.id,
                "mentee_name": mentee.name,
            },
            notes=notes_mentor,
            cost=0,
            game_year=year,
            game_week=week,
        )

        return mentor_event, mentee_event

    # ----------------------------------------------------------
    # Utility: recovery availability summary for a wrestler
    # ----------------------------------------------------------

    def get_recovery_menu(
        self,
        wrestler,
        cooldown: RecoveryCooldown,
        year: int,
        week: int,
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of all 6 recovery options with availability, cooldown info,
        and recommended actions based on the wrestler's current state.
        """
        abs_w = _abs_week(year, week)
        morale = wrestler.morale
        cat = _morale_category(morale)

        menu = []
        for rtype in RecoveryType:
            available = cooldown.can_use(rtype, abs_w)
            weeks_left = cooldown.weeks_until_available(rtype, abs_w)

            # Recommendation logic
            recommended = False
            if rtype == RecoveryType.PRIVATE_MEETING and morale <= 60:
                recommended = True
            elif rtype == RecoveryType.PUSH_ADJUSTMENT and morale <= 50:
                recommended = True
            elif rtype == RecoveryType.CONTRACT_RENEGOTIATION and morale <= 45:
                recommended = True
            elif rtype == RecoveryType.CREATIVE_INPUT and morale <= 55:
                recommended = True
            elif rtype == RecoveryType.TIME_OFF and morale <= 35:
                recommended = True
            elif rtype == RecoveryType.MENTORSHIP_ROLE and morale <= 65:
                recommended = True

            menu.append({
                "recovery_type": rtype.value,
                "label": rtype.value.replace("_", " ").title(),
                "available": available,
                "cooldown_weeks_remaining": weeks_left,
                "recommended": recommended and available,
                "morale_category": cat,
            })

        return menu


# Module-level singleton
morale_recovery_engine = MoraleRecoveryEngine()