"""
Morale Behaviors Engine
Steps 245-253: Unhappy Wrestler Behaviors

245. Release Demands
246. Public Release Requests
247. Match Quality Decline
248. Sandbagging
249. Cooperation Refusal
250. Dirt Sheet Leaking
251. Social Media Venting
252. Backstage Influence Poisoning
253. Contract Running Down
"""

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class BehaviorType(Enum):
    RELEASE_DEMAND = "release_demand"
    PUBLIC_RELEASE_DEMAND = "public_release_demand"
    MATCH_QUALITY_DECLINE = "match_quality_decline"
    SANDBAGGING = "sandbagging"
    COOPERATION_REFUSAL = "cooperation_refusal"
    DIRT_SHEET_LEAK = "dirt_sheet_leak"
    SOCIAL_MEDIA_VENT = "social_media_vent"
    BACKSTAGE_POISON = "backstage_poison"
    CONTRACT_RUNNING_DOWN = "contract_running_down"


class BehaviorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BehaviorEvent:
    """A recorded instance of a wrestler's unhappy behavior"""
    event_id: str
    wrestler_id: str
    wrestler_name: str
    behavior_type: BehaviorType
    severity: BehaviorSeverity
    description: str
    game_year: int
    game_week: int
    morale_at_time: int
    resolved: bool = False
    resolution: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    # Effects
    match_quality_penalty: float = 0.0   # 0.0–1.0 subtracted from star rating
    affects_opponent: bool = False         # sandbagging hurts opponents too
    leaked_info: Optional[str] = None      # for dirt sheet leaks
    social_post: Optional[str] = None      # for social media vents
    influenced_wrestlers: List[str] = field(default_factory=list)  # backstage poison targets

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'behavior_type': self.behavior_type.value,
            'severity': self.severity.value,
            'description': self.description,
            'game_year': self.game_year,
            'game_week': self.game_week,
            'morale_at_time': self.morale_at_time,
            'resolved': self.resolved,
            'resolution': self.resolution,
            'created_at': self.created_at,
            'match_quality_penalty': self.match_quality_penalty,
            'affects_opponent': self.affects_opponent,
            'leaked_info': self.leaked_info,
            'social_post': self.social_post,
            'influenced_wrestlers': self.influenced_wrestlers,
        }


@dataclass
class WrestlerBehaviorState:
    """
    Persistent behavior state for a single wrestler.
    Attached to wrestler objects and stored in DB.
    """
    wrestler_id: str

    # Step 245 — Release Demand
    has_requested_release: bool = False
    release_demand_year: Optional[int] = None
    release_demand_week: Optional[int] = None
    release_demand_count: int = 0

    # Step 246 — Public Release Demand
    has_gone_public: bool = False
    public_demand_year: Optional[int] = None
    public_demand_week: Optional[int] = None
    public_statement: Optional[str] = None

    # Step 247 — Match Quality Decline
    is_phoning_it_in: bool = False
    phone_in_penalty: float = 0.0   # subtracted from star rating (0.0–0.75)

    # Step 248 — Sandbagging
    is_sandbagging: bool = False
    sandbagging_penalty: float = 0.0  # 0.0–1.0

    # Step 249 — Cooperation Refusal
    refused_bookings: List[str] = field(default_factory=list)  # wrestler IDs they refuse to work
    refused_match_types: List[str] = field(default_factory=list)
    cooperation_refusal_active: bool = False

    # Step 250 — Dirt Sheet Leaking
    is_leaking_info: bool = False
    leaks_this_year: int = 0
    last_leak_week: Optional[int] = None

    # Step 251 — Social Media Venting
    is_venting_online: bool = False
    social_media_incidents: int = 0
    last_vent_week: Optional[int] = None

    # Step 252 — Backstage Influence Poisoning
    is_poisoning_locker_room: bool = False
    poisoning_targets: List[str] = field(default_factory=list)  # IDs of affected wrestlers
    influence_radius: int = 0  # 0–5, how many wrestlers affected

    # Step 253 — Contract Running Down
    is_running_down_contract: bool = False
    lame_duck_start_week: Optional[int] = None
    lame_duck_effort_penalty: float = 0.0  # 0.0–0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            'wrestler_id': self.wrestler_id,
            'has_requested_release': self.has_requested_release,
            'release_demand_year': self.release_demand_year,
            'release_demand_week': self.release_demand_week,
            'release_demand_count': self.release_demand_count,
            'has_gone_public': self.has_gone_public,
            'public_demand_year': self.public_demand_year,
            'public_demand_week': self.public_demand_week,
            'public_statement': self.public_statement,
            'is_phoning_it_in': self.is_phoning_it_in,
            'phone_in_penalty': self.phone_in_penalty,
            'is_sandbagging': self.is_sandbagging,
            'sandbagging_penalty': self.sandbagging_penalty,
            'refused_bookings': self.refused_bookings,
            'refused_match_types': self.refused_match_types,
            'cooperation_refusal_active': self.cooperation_refusal_active,
            'is_leaking_info': self.is_leaking_info,
            'leaks_this_year': self.leaks_this_year,
            'last_leak_week': self.last_leak_week,
            'is_venting_online': self.is_venting_online,
            'social_media_incidents': self.social_media_incidents,
            'last_vent_week': self.last_vent_week,
            'is_poisoning_locker_room': self.is_poisoning_locker_room,
            'poisoning_targets': self.poisoning_targets,
            'influence_radius': self.influence_radius,
            'is_running_down_contract': self.is_running_down_contract,
            'lame_duck_start_week': self.lame_duck_start_week,
            'lame_duck_effort_penalty': self.lame_duck_effort_penalty,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WrestlerBehaviorState':
        state = WrestlerBehaviorState(wrestler_id=data['wrestler_id'])
        state.has_requested_release = data.get('has_requested_release', False)
        state.release_demand_year = data.get('release_demand_year')
        state.release_demand_week = data.get('release_demand_week')
        state.release_demand_count = data.get('release_demand_count', 0)
        state.has_gone_public = data.get('has_gone_public', False)
        state.public_demand_year = data.get('public_demand_year')
        state.public_demand_week = data.get('public_demand_week')
        state.public_statement = data.get('public_statement')
        state.is_phoning_it_in = data.get('is_phoning_it_in', False)
        state.phone_in_penalty = data.get('phone_in_penalty', 0.0)
        state.is_sandbagging = data.get('is_sandbagging', False)
        state.sandbagging_penalty = data.get('sandbagging_penalty', 0.0)
        state.refused_bookings = data.get('refused_bookings', [])
        state.refused_match_types = data.get('refused_match_types', [])
        state.cooperation_refusal_active = data.get('cooperation_refusal_active', False)
        state.is_leaking_info = data.get('is_leaking_info', False)
        state.leaks_this_year = data.get('leaks_this_year', 0)
        state.last_leak_week = data.get('last_leak_week')
        state.is_venting_online = data.get('is_venting_online', False)
        state.social_media_incidents = data.get('social_media_incidents', 0)
        state.last_vent_week = data.get('last_vent_week')
        state.is_poisoning_locker_room = data.get('is_poisoning_locker_room', False)
        state.poisoning_targets = data.get('poisoning_targets', [])
        state.influence_radius = data.get('influence_radius', 0)
        state.is_running_down_contract = data.get('is_running_down_contract', False)
        state.lame_duck_start_week = data.get('lame_duck_start_week')
        state.lame_duck_effort_penalty = data.get('lame_duck_effort_penalty', 0.0)
        return state


# ============================================================
# Morale Thresholds
# ============================================================

MORALE_MISERABLE   = 20   # 0–20:  miserable zone, all behaviors possible
MORALE_UNHAPPY     = 40   # 21–40: unhappy, soft behaviors kick in
MORALE_DISCONTENTED = 50  # 41–50: discontented, latent tensions


def _morale_category(morale: int) -> str:
    if morale <= MORALE_MISERABLE:
        return 'miserable'
    if morale <= MORALE_UNHAPPY:
        return 'unhappy'
    if morale <= MORALE_DISCONTENTED:
        return 'discontented'
    if morale <= 69:
        return 'content'
    if morale <= 89:
        return 'happy'
    return 'ecstatic'


# ============================================================
# Behavior Trigger Templates
# ============================================================

RELEASE_DEMAND_MESSAGES = [
    "{name} has formally requested their release, citing creative differences.",
    "{name} has submitted a release request through their representative.",
    "{name} is no longer happy here and is requesting to be let go.",
    "{name}'s management has sent a formal letter requesting mutual termination.",
    "Sources confirm {name} has asked for their release from their contract.",
]

PUBLIC_DEMAND_MESSAGES = [
    "{name} tweets: 'Time for a change. I've asked for my release and I mean it.'",
    "{name} on their podcast: 'I don't feel valued here. I've asked to leave.'",
    "{name} posts: 'My heart isn't in it anymore. I've requested my release publicly because nothing was being done.'",
    "{name} in an interview: 'I gave them the chance to fix this privately. Now everyone knows the truth.'",
    "Breaking: {name} makes public statement demanding release from Ring of Champions.",
]

DIRT_SHEET_LEAKS = [
    "💧 INSIDER REPORT: Sources say {name} has been feeding information to wrestling media. Next week's main event has reportedly been spoiled.",
    "💧 LEAK: {name} told reporters about the planned title change at the next PPV.",
    "💧 DIRT SHEET: A disgruntled source (believed to be {name}) has revealed backstage plans including upcoming signings.",
    "💧 SPOILER ALERT: Insider information has leaked — reportedly traced back to {name}'s camp.",
    "💧 REPORT: {name} is believed to be the source behind leaked creative plans circulating online.",
]

SOCIAL_MEDIA_VENTS = [
    "👀 {name} posts cryptic tweet: 'Some promotions just don't appreciate greatness until it's gone.'",
    "👀 {name} likes several fan tweets criticizing Ring of Champions' booking decisions.",
    "👀 {name} posts: 'Hard work means nothing if the people in charge don't see it.'",
    "👀 {name} retweets a dirt sheet article about unhappy locker room conditions.",
    "👀 {name} goes live on social media: 'I'm going to be vague but... y'all know what's going on.'",
    "👀 {name} deletes their Ring of Champions profile picture and bio.",
]

SANDBAGGING_DESCRIPTIONS = [
    "{name} appeared to deliberately no-sell their opponent's offense tonight.",
    "{name} reportedly made the match difficult, refusing to cooperate on planned spots.",
    "{name} was stiff with their opponent and seemed to be actively making the match worse.",
    "Sources say {name} dropped their opponent incorrectly on a planned spot — intentionally.",
    "{name}'s effort level tonight was noticeably poor; their opponent had to carry everything.",
]

BACKSTAGE_POISON_MESSAGES = [
    "{name} has been telling younger talent that management doesn't care about them.",
    "{name} is rallying veterans in the locker room against recent booking decisions.",
    "{name} reportedly encouraged others to refuse certain creative directions.",
    "Sources say {name} has been poisoning the well — multiple wrestlers have grown discontent.",
    "{name} held an unauthorized locker room meeting questioning management's decisions.",
]

CONTRACT_RUNNING_DOWN_MESSAGES = [
    "{name} is doing the bare minimum — they're clearly counting down the days on their contract.",
    "Sources confirm {name} has no intention of re-signing and is working out their notice.",
    "{name} is in lame duck mode: showing up, doing what's required, nothing more.",
    "Backstage word is {name} is already in talks with other promotions while still under contract.",
    "{name}'s in-ring effort has notably dropped — a clear sign they've mentally moved on.",
]


# ============================================================
# Core Behavior Engine
# ============================================================

class MoraleBehaviorEngine:
    """
    Evaluates wrestler morale each week and triggers/clears behaviors.
    Called by show simulation after each show.
    """

    def evaluate_wrestler(
        self,
        wrestler,
        behavior_state: WrestlerBehaviorState,
        current_year: int,
        current_week: int,
        all_wrestlers: List = None
    ) -> List[BehaviorEvent]:
        """
        Main entry point. Returns list of new BehaviorEvent objects triggered this week.
        Also mutates behavior_state in place.
        """
        events = []
        morale = wrestler.morale
        cat = _morale_category(morale)

        # ---- Step 253: Contract Running Down ----
        # Check first — can apply even at moderate unhappiness
        events += self._evaluate_contract_running_down(
            wrestler, behavior_state, current_year, current_week
        )

        if cat in ('happy', 'ecstatic', 'content'):
            # Clear negative behaviors if morale recovered
            self._clear_behaviors_on_recovery(wrestler, behavior_state)
            return events

        # ---- Step 247: Match Quality Decline ----
        events += self._evaluate_match_quality_decline(
            wrestler, behavior_state, current_year, current_week
        )

        if cat == 'discontented':
            return events  # Only mild behaviors for discontented

        # ---- Step 251: Social Media Venting ----
        events += self._evaluate_social_media(
            wrestler, behavior_state, current_year, current_week
        )

        # ---- Step 250: Dirt Sheet Leaking ----
        events += self._evaluate_dirt_sheet(
            wrestler, behavior_state, current_year, current_week
        )

        if cat not in ('miserable', 'unhappy'):
            return events

        # ---- Step 248: Sandbagging ----
        events += self._evaluate_sandbagging(
            wrestler, behavior_state, current_year, current_week
        )

        # ---- Step 249: Cooperation Refusal ----
        events += self._evaluate_cooperation_refusal(
            wrestler, behavior_state, current_year, current_week
        )

        # ---- Step 252: Backstage Influence Poisoning ----
        if all_wrestlers:
            events += self._evaluate_backstage_poison(
                wrestler, behavior_state, current_year, current_week, all_wrestlers
            )

        # ---- Step 245: Release Demand ----
        events += self._evaluate_release_demand(
            wrestler, behavior_state, current_year, current_week
        )

        # ---- Step 246: Public Release Demand ----
        events += self._evaluate_public_release_demand(
            wrestler, behavior_state, current_year, current_week
        )

        return events

    # ----------------------------------------------------------
    # Step 245 — Release Demands
    # ----------------------------------------------------------
    def _evaluate_release_demand(self, wrestler, state, year, week) -> List[BehaviorEvent]:
        events = []
        if state.has_requested_release:
            return events  # Already demanded

        morale = wrestler.morale
        # Threshold: miserable wrestlers have high chance, unhappy moderate
        base_chance = 0.0
        if morale <= MORALE_MISERABLE:
            base_chance = 0.25
        elif morale <= MORALE_UNHAPPY:
            base_chance = 0.08

        # Major superstars more likely to demand release (they have options)
        if wrestler.is_major_superstar:
            base_chance *= 1.5

        # Repeated promises broken increases chance
        repeat_factor = min(state.release_demand_count * 0.05, 0.2)
        final_chance = base_chance + repeat_factor

        if random.random() < final_chance:
            state.has_requested_release = True
            state.release_demand_year = year
            state.release_demand_week = week
            state.release_demand_count += 1

            severity = BehaviorSeverity.CRITICAL if wrestler.is_major_superstar else BehaviorSeverity.HIGH
            msg = random.choice(RELEASE_DEMAND_MESSAGES).format(name=wrestler.name)

            events.append(BehaviorEvent(
                event_id=f"rel_{wrestler.id}_{year}_{week}",
                wrestler_id=wrestler.id,
                wrestler_name=wrestler.name,
                behavior_type=BehaviorType.RELEASE_DEMAND,
                severity=severity,
                description=msg,
                game_year=year,
                game_week=week,
                morale_at_time=morale,
            ))
        return events

    # ----------------------------------------------------------
    # Step 246 — Public Release Demands
    # ----------------------------------------------------------
    def _evaluate_public_release_demand(self, wrestler, state, year, week) -> List[BehaviorEvent]:
        events = []
        if state.has_gone_public:
            return events
        # Only goes public if they've already privately demanded and been ignored for 2+ weeks
        if not state.has_requested_release:
            return events
        weeks_ignored = 0
        if state.release_demand_year is not None:
            weeks_ignored = (year - state.release_demand_year) * 52 + (week - state.release_demand_week)
        if weeks_ignored < 2:
            return events

        # Major superstars go public more readily
        chance = 0.30 if wrestler.is_major_superstar else 0.15
        if wrestler.morale <= MORALE_MISERABLE:
            chance *= 1.5

        if random.random() < chance:
            state.has_gone_public = True
            state.public_demand_year = year
            state.public_demand_week = week

            post = random.choice(PUBLIC_DEMAND_MESSAGES).format(name=wrestler.name)
            state.public_statement = post

            # Going public costs morale for both sides and creates fan controversy
            wrestler.adjust_morale(-5)

            events.append(BehaviorEvent(
                event_id=f"pub_{wrestler.id}_{year}_{week}",
                wrestler_id=wrestler.id,
                wrestler_name=wrestler.name,
                behavior_type=BehaviorType.PUBLIC_RELEASE_DEMAND,
                severity=BehaviorSeverity.CRITICAL,
                description=post,
                game_year=year,
                game_week=week,
                morale_at_time=wrestler.morale,
                social_post=post,
            ))
        return events

    # ----------------------------------------------------------
    # Step 247 — Match Quality Decline
    # ----------------------------------------------------------
    def _evaluate_match_quality_decline(self, wrestler, state, year, week) -> List[BehaviorEvent]:
        events = []
        morale = wrestler.morale
        cat = _morale_category(morale)

        # Calculate penalty level
        if cat == 'miserable':
            penalty = round(random.uniform(0.40, 0.75), 2)
        elif cat == 'unhappy':
            penalty = round(random.uniform(0.20, 0.45), 2)
        elif cat == 'discontented':
            penalty = round(random.uniform(0.05, 0.20), 2)
        else:
            penalty = 0.0

        was_phoning_it_in = state.is_phoning_it_in
        state.is_phoning_it_in = penalty > 0
        state.phone_in_penalty = penalty

        # Only fire event when newly triggered or worsening significantly
        if penalty > 0 and not was_phoning_it_in:
            events.append(BehaviorEvent(
                event_id=f"mqd_{wrestler.id}_{year}_{week}",
                wrestler_id=wrestler.id,
                wrestler_name=wrestler.name,
                behavior_type=BehaviorType.MATCH_QUALITY_DECLINE,
                severity=BehaviorSeverity.MEDIUM if cat == 'discontented' else BehaviorSeverity.HIGH,
                description=f"{wrestler.name} is going through the motions. Match quality will suffer (−{penalty:.2f}★).",
                game_year=year,
                game_week=week,
                morale_at_time=morale,
                match_quality_penalty=penalty,
            ))
        return events

    # ----------------------------------------------------------
    # Step 248 — Sandbagging
    # ----------------------------------------------------------
    def _evaluate_sandbagging(self, wrestler, state, year, week) -> List[BehaviorEvent]:
        events = []
        morale = wrestler.morale

        # Sandbagging escalates from phoning it in — requires miserable + already declining
        if morale > MORALE_MISERABLE:
            if state.is_sandbagging:
                state.is_sandbagging = False
                state.sandbagging_penalty = 0.0
            return events

        # 20% chance per week of sandbagging when miserable
        if random.random() < 0.20:
            penalty = round(random.uniform(0.5, 1.0), 2)
            was_sandbagging = state.is_sandbagging
            state.is_sandbagging = True
            state.sandbagging_penalty = penalty

            if not was_sandbagging:
                desc = random.choice(SANDBAGGING_DESCRIPTIONS).format(name=wrestler.name)
                events.append(BehaviorEvent(
                    event_id=f"sbg_{wrestler.id}_{year}_{week}",
                    wrestler_id=wrestler.id,
                    wrestler_name=wrestler.name,
                    behavior_type=BehaviorType.SANDBAGGING,
                    severity=BehaviorSeverity.HIGH,
                    description=desc,
                    game_year=year,
                    game_week=week,
                    morale_at_time=morale,
                    match_quality_penalty=penalty,
                    affects_opponent=True,
                ))
        else:
            state.is_sandbagging = False
            state.sandbagging_penalty = 0.0

        return events

    # ----------------------------------------------------------
    # Step 249 — Cooperation Refusal
    # ----------------------------------------------------------
    def _evaluate_cooperation_refusal(self, wrestler, state, year, week) -> List[BehaviorEvent]:
        events = []
        morale = wrestler.morale

        if morale > MORALE_UNHAPPY:
            state.cooperation_refusal_active = False
            return events

        if state.cooperation_refusal_active:
            return events  # Already flagged, don't spam events

        # 15% chance when unhappy, 30% when miserable
        chance = 0.30 if morale <= MORALE_MISERABLE else 0.15

        if random.random() < chance:
            state.cooperation_refusal_active = True

            # Determine what they're refusing
            refusals = []
            if random.random() < 0.5:
                refusals.append("clean losses to lower-card wrestlers")
            if random.random() < 0.4:
                refusals.append("certain match types (stretcher matches, cage matches)")
            if random.random() < 0.3:
                refusals.append("traveling to specific events")

            if not refusals:
                refusals.append("certain creative directions")

            state.refused_match_types = refusals

            events.append(BehaviorEvent(
                event_id=f"coop_{wrestler.id}_{year}_{week}",
                wrestler_id=wrestler.id,
                wrestler_name=wrestler.name,
                behavior_type=BehaviorType.COOPERATION_REFUSAL,
                severity=BehaviorSeverity.HIGH,
                description=f"{wrestler.name} is refusing to cooperate with: {', '.join(refusals)}.",
                game_year=year,
                game_week=week,
                morale_at_time=morale,
            ))
        return events

    # ----------------------------------------------------------
    # Step 250 — Dirt Sheet Leaking
    # ----------------------------------------------------------
    def _evaluate_dirt_sheet(self, wrestler, state, year, week) -> List[BehaviorEvent]:
        events = []
        morale = wrestler.morale

        if morale > MORALE_UNHAPPY:
            state.is_leaking_info = False
            return events

        # Don't leak too often — max 1 per 3 weeks
        if state.last_leak_week and (week - state.last_leak_week) < 3:
            return events

        # 15% chance when unhappy, 25% when miserable
        chance = 0.25 if morale <= MORALE_MISERABLE else 0.15

        if random.random() < chance:
            state.is_leaking_info = True
            state.leaks_this_year += 1
            state.last_leak_week = week

            leak_msg = random.choice(DIRT_SHEET_LEAKS).format(name=wrestler.name)

            events.append(BehaviorEvent(
                event_id=f"leak_{wrestler.id}_{year}_{week}",
                wrestler_id=wrestler.id,
                wrestler_name=wrestler.name,
                behavior_type=BehaviorType.DIRT_SHEET_LEAK,
                severity=BehaviorSeverity.MEDIUM,
                description=leak_msg,
                game_year=year,
                game_week=week,
                morale_at_time=morale,
                leaked_info=leak_msg,
            ))
        return events

    # ----------------------------------------------------------
    # Step 251 — Social Media Venting
    # ----------------------------------------------------------
    def _evaluate_social_media(self, wrestler, state, year, week) -> List[BehaviorEvent]:
        events = []
        morale = wrestler.morale

        if morale > MORALE_DISCONTENTED:
            state.is_venting_online = False
            return events

        # Don't vent too often — max 1 per 2 weeks
        if state.last_vent_week and (week - state.last_vent_week) < 2:
            return events

        # Chance scales with unhappiness
        if morale <= MORALE_MISERABLE:
            chance = 0.35
        elif morale <= MORALE_UNHAPPY:
            chance = 0.20
        else:
            chance = 0.08  # discontented

        if random.random() < chance:
            state.is_venting_online = True
            state.social_media_incidents += 1
            state.last_vent_week = week

            post = random.choice(SOCIAL_MEDIA_VENTS).format(name=wrestler.name)

            events.append(BehaviorEvent(
                event_id=f"soc_{wrestler.id}_{year}_{week}",
                wrestler_id=wrestler.id,
                wrestler_name=wrestler.name,
                behavior_type=BehaviorType.SOCIAL_MEDIA_VENT,
                severity=BehaviorSeverity.MEDIUM,
                description=post,
                game_year=year,
                game_week=week,
                morale_at_time=morale,
                social_post=post,
            ))
        return events

    # ----------------------------------------------------------
    # Step 252 — Backstage Influence Poisoning
    # ----------------------------------------------------------
    def _evaluate_backstage_poison(self, wrestler, state, year, week, all_wrestlers) -> List[BehaviorEvent]:
        events = []
        morale = wrestler.morale

        # Only veterans with influence can poison the locker room
        if morale > MORALE_UNHAPPY:
            if state.is_poisoning_locker_room:
                # Stop poisoning when morale recovers
                self._lift_poison_effects(wrestler, state, all_wrestlers)
            return events

        # Need experience to have locker room influence
        if wrestler.years_experience < 5:
            return events

        # 15% chance to start poisoning when miserable/unhappy
        if not state.is_poisoning_locker_room and random.random() < 0.15:
            state.is_poisoning_locker_room = True

            # Determine influence radius based on years experience
            state.influence_radius = min(int(wrestler.years_experience / 5), 5)

            # Select targets: wrestlers near them on roster (same brand, similar role)
            candidates = [
                w for w in all_wrestlers
                if w.id != wrestler.id
                and w.primary_brand == wrestler.primary_brand
                and w.morale < 70
            ]
            random.shuffle(candidates)
            targets = candidates[:state.influence_radius]
            state.poisoning_targets = [w.id for w in targets]

            # Apply morale drain to targets
            for target in targets:
                target.adjust_morale(-random.randint(3, 8))

            desc = random.choice(BACKSTAGE_POISON_MESSAGES).format(name=wrestler.name)

            events.append(BehaviorEvent(
                event_id=f"poi_{wrestler.id}_{year}_{week}",
                wrestler_id=wrestler.id,
                wrestler_name=wrestler.name,
                behavior_type=BehaviorType.BACKSTAGE_POISON,
                severity=BehaviorSeverity.HIGH,
                description=desc,
                game_year=year,
                game_week=week,
                morale_at_time=morale,
                influenced_wrestlers=state.poisoning_targets,
            ))

        elif state.is_poisoning_locker_room:
            # Ongoing — continue draining target morale weekly (less aggressively)
            for w in all_wrestlers:
                if w.id in state.poisoning_targets:
                    w.adjust_morale(-random.randint(1, 3))

        return events

    def _lift_poison_effects(self, wrestler, state, all_wrestlers):
        """Called when wrestler recovers — stop influence poisoning"""
        state.is_poisoning_locker_room = False
        state.poisoning_targets = []
        state.influence_radius = 0

    # ----------------------------------------------------------
    # Step 253 — Contract Running Down
    # ----------------------------------------------------------
    def _evaluate_contract_running_down(self, wrestler, state, year, week) -> List[BehaviorEvent]:
        events = []
        morale = wrestler.morale
        weeks_remaining = wrestler.contract.weeks_remaining

        # Lame duck mode: contract <= 8 weeks AND unhappy/miserable
        if weeks_remaining > 8 or morale > MORALE_UNHAPPY:
            if state.is_running_down_contract:
                state.is_running_down_contract = False
                state.lame_duck_effort_penalty = 0.0
                state.lame_duck_start_week = None
            return events

        was_running_down = state.is_running_down_contract

        state.is_running_down_contract = True
        state.lame_duck_start_week = state.lame_duck_start_week or week

        # Effort penalty scales with how unhappy and how close to end
        if morale <= MORALE_MISERABLE:
            base_penalty = 0.5
        elif morale <= MORALE_UNHAPPY:
            base_penalty = 0.3
        else:
            base_penalty = 0.15

        # Increases as contract runs out
        urgency_bonus = max(0.0, (8 - weeks_remaining) * 0.03)
        state.lame_duck_effort_penalty = min(base_penalty + urgency_bonus, 0.65)

        if not was_running_down:
            desc = random.choice(CONTRACT_RUNNING_DOWN_MESSAGES).format(name=wrestler.name)
            events.append(BehaviorEvent(
                event_id=f"lame_{wrestler.id}_{year}_{week}",
                wrestler_id=wrestler.id,
                wrestler_name=wrestler.name,
                behavior_type=BehaviorType.CONTRACT_RUNNING_DOWN,
                severity=BehaviorSeverity.MEDIUM,
                description=desc,
                game_year=year,
                game_week=week,
                morale_at_time=morale,
                match_quality_penalty=state.lame_duck_effort_penalty,
            ))
        return events

    # ----------------------------------------------------------
    # Recovery: clear behaviors when morale improves
    # ----------------------------------------------------------
    def _clear_behaviors_on_recovery(self, wrestler, state: WrestlerBehaviorState):
        """When morale improves to content/happy, clear active negative behaviors"""
        state.is_phoning_it_in = False
        state.phone_in_penalty = 0.0
        state.is_sandbagging = False
        state.sandbagging_penalty = 0.0
        state.cooperation_refusal_active = False
        state.refused_match_types = []
        state.is_leaking_info = False
        state.is_venting_online = False
        state.is_poisoning_locker_room = False
        state.poisoning_targets = []
        state.influence_radius = 0
        # Note: release demand state persists — they still want out
        # Note: contract running down persists — decision is made

    # ----------------------------------------------------------
    # Utility: compute total match quality penalty for a wrestler
    # ----------------------------------------------------------
    def get_match_quality_penalty(self, state: WrestlerBehaviorState) -> float:
        """
        Returns total star rating penalty to apply during match simulation.
        Called by match_sim.py.
        """
        penalty = 0.0
        if state.is_sandbagging:
            penalty += state.sandbagging_penalty
        elif state.is_phoning_it_in:
            penalty += state.phone_in_penalty
        if state.is_running_down_contract:
            penalty += state.lame_duck_effort_penalty
        return min(penalty, 1.5)  # Never more than 1.5 stars total penalty

    # ----------------------------------------------------------
    # Dashboard summary for a wrestler
    # ----------------------------------------------------------
    def get_wrestler_behavior_summary(self, wrestler, state: WrestlerBehaviorState) -> Dict[str, Any]:
        active_behaviors = []
        warnings = []

        if state.has_requested_release:
            active_behaviors.append({
                'type': 'release_demand',
                'label': '🚨 Demanding Release',
                'description': 'Has formally requested to be released.',
                'severity': 'critical'
            })
        if state.has_gone_public:
            active_behaviors.append({
                'type': 'public_release_demand',
                'label': '📢 Gone Public',
                'description': state.public_statement or 'Made public release demand.',
                'severity': 'critical'
            })
        if state.is_phoning_it_in and not state.is_sandbagging:
            active_behaviors.append({
                'type': 'match_quality_decline',
                'label': '😴 Phoning It In',
                'description': f'Match quality penalty: −{state.phone_in_penalty:.2f}★',
                'severity': 'medium'
            })
        if state.is_sandbagging:
            active_behaviors.append({
                'type': 'sandbagging',
                'label': '💀 Sandbagging',
                'description': f'Actively making matches worse. Penalty: −{state.sandbagging_penalty:.2f}★',
                'severity': 'high'
            })
        if state.cooperation_refusal_active:
            active_behaviors.append({
                'type': 'cooperation_refusal',
                'label': '🚫 Refusing Cooperation',
                'description': f"Refuses: {', '.join(state.refused_match_types)}",
                'severity': 'high'
            })
        if state.is_leaking_info:
            active_behaviors.append({
                'type': 'dirt_sheet_leak',
                'label': '💧 Leaking to Dirt Sheets',
                'description': f'Has leaked info {state.leaks_this_year}x this year.',
                'severity': 'medium'
            })
        if state.is_venting_online:
            active_behaviors.append({
                'type': 'social_media_vent',
                'label': '📱 Venting on Social Media',
                'description': f'{state.social_media_incidents} incident(s) this year.',
                'severity': 'medium'
            })
        if state.is_poisoning_locker_room:
            active_behaviors.append({
                'type': 'backstage_poison',
                'label': '☠️ Poisoning Locker Room',
                'description': f'Influencing {len(state.poisoning_targets)} wrestler(s) negatively.',
                'severity': 'high'
            })
        if state.is_running_down_contract:
            active_behaviors.append({
                'type': 'contract_running_down',
                'label': '⏳ Running Down Contract',
                'description': f'Lame duck mode. Effort penalty: −{state.lame_duck_effort_penalty:.2f}★',
                'severity': 'medium'
            })

        total_penalty = self.get_match_quality_penalty(state)
        morale_category = _morale_category(wrestler.morale)

        return {
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'morale': wrestler.morale,
            'morale_category': morale_category,
            'active_behaviors': active_behaviors,
            'total_match_penalty': round(total_penalty, 2),
            'warning_count': len([b for b in active_behaviors if b['severity'] in ('high', 'critical')]),
            'warnings': warnings,
            'behavior_state': state.to_dict(),
        }


# Singleton instance
morale_behavior_engine = MoraleBehaviorEngine()