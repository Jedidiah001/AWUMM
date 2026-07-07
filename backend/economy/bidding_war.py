"""
Bidding War Engine
STEPS 126-133: Complete bidding war mechanics

STEP 126 - Rival Promotion Interest Generation
STEP 127 - Bidding Round Structure
STEP 128 - Blind vs. Open Bidding
STEP 129 - Bidding Escalation Events
STEP 130 - Outbid Notifications
STEP 131 - Strategic Bidding Decisions
STEP 132 - Post-Bidding Relationship Effects
STEP 133 - Anti-Bidding War Tactics
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import random
import uuid


# ======================================================================== #
# Enums                                                                     #
# ======================================================================== #

class BiddingWarStatus(Enum):
    OPEN   = "open"       # Round 1 in progress
    ROUND_2 = "round_2"  # Round 2 counter-offers
    FINAL  = "final"      # Final offers, wrestler deciding
    DECIDED = "decided"   # Done - winner chosen
    CANCELLED = "cancelled"  # No deal reached / all withdrew


class BiddingEventType(Enum):
    """STEP 129: Mid-negotiation escalation events."""
    RIVAL_DRAMATIC_INCREASE  = "rival_dramatic_increase"   # Rival jumps offer massively
    WRESTLER_DEMANDS_UP      = "wrestler_demands_up"        # FA raises their asking price
    PROMOTION_DROPS_OUT      = "promotion_drops_out"        # Rival withdraws entirely
    INJURY_REVELATION        = "injury_revelation"          # Old injury surfaces, drops value
    CONTROVERSY_EMERGES      = "controversy_emerges"        # Backstage issue surfaces
    LEAKED_TO_MEDIA          = "leaked_to_media"            # Negotiations become public
    DEADLINE_IMPOSED         = "deadline_imposed"           # Hard deadline added
    PACKAGE_DEAL_OFFERED     = "package_deal_offered"       # Rival bundles multiple FAs
    LOYALTY_DECLARATION      = "loyalty_declaration"        # FA says they prefer you


class PlayerBidAction(Enum):
    """STEP 131: Strategic options during a bidding war."""
    MATCH_OFFER         = "match_offer"          # Match current highest rival offer
    EXCEED_OFFER        = "exceed_offer"          # Outbid by a set amount
    SWEETEN_PERKS       = "sweeten_perks"         # Add non-monetary perks
    HOLD_FIRM           = "hold_firm"             # Stick with current offer
    WITHDRAW            = "withdraw"              # Drop out of bidding
    REQUEST_MEETING     = "request_meeting"       # Personal pitch (-5% cost, +relationship)
    EXCLUSIVE_WINDOW    = "exclusive_window"      # Buy exclusive negotiation time


# ======================================================================== #
# Data Classes                                                               #
# ======================================================================== #

@dataclass
class RivalBid:
    """A single bid from a rival promotion in a given round."""
    promotion_id: str
    promotion_name: str
    round_number: int
    salary_offer: int
    contract_weeks: int = 52
    signing_bonus: int = 0
    creative_perks: Dict[str, Any] = field(default_factory=dict)
    interest_level: int = 50
    is_final_offer: bool = False
    withdrew: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'promotion_id':   self.promotion_id,
            'promotion_name': self.promotion_name,
            'round_number':   self.round_number,
            'salary_offer':   self.salary_offer,
            'contract_weeks': self.contract_weeks,
            'signing_bonus':  self.signing_bonus,
            'creative_perks': self.creative_perks,
            'interest_level': self.interest_level,
            'is_final_offer': self.is_final_offer,
            'withdrew':       self.withdrew
        }


@dataclass
class BiddingEvent:
    """An escalation event that occurs mid-bidding-war."""
    event_type: BiddingEventType
    description: str
    triggered_round: int
    effect_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type':      self.event_type.value,
            'description':     self.description,
            'triggered_round': self.triggered_round,
            'effect_data':     self.effect_data
        }


@dataclass
class BiddingWar:
    """
    Full state of a bidding war over a free agent.

    Lifecycle:
        open  →  round_2  →  final  →  decided
                                    →  cancelled
    """
    bidding_war_id: str
    fa_id: str
    fa_name: str

    status: BiddingWarStatus = BiddingWarStatus.OPEN
    is_open_bidding: bool = False   # STEP 128

    current_round: int = 1
    max_rounds: int = 3

    # Player's current standing offer (None = not yet bid)
    player_offer_salary: Optional[int] = None
    player_offer_weeks: int = 52
    player_offer_bonus: int = 0
    player_creative_control: str = 'none'
    player_title_guarantee: bool = False
    player_withdrew: bool = False

    # Competing bids from all rounds
    rival_bids: List[RivalBid] = field(default_factory=list)
    events: List[BiddingEvent] = field(default_factory=list)

    # Participating rival promotions for this war
    participating_rivals: List[str] = field(default_factory=list)

    # Outcome
    winner: Optional[str] = None         # 'player' | promotion_id | 'no_deal'
    winning_salary: Optional[int] = None
    decided_year: Optional[int] = None
    decided_week: Optional[int] = None
    outcome_reason: Optional[str] = None

    # Timing
    started_year: int = 1
    started_week: int = 1
    deadline_year: Optional[int] = None
    deadline_week: Optional[int] = None

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def get_highest_rival_offer(self) -> Optional[RivalBid]:
        """Return the current highest rival salary offer (non-withdrawn)."""
        active = [b for b in self.rival_bids if not b.withdrew]
        if not active:
            return None
        return max(active, key=lambda b: b.salary_offer)

    def get_rival_bids_this_round(self) -> List[RivalBid]:
        """Get all rival bids for the current round."""
        return [b for b in self.rival_bids if b.round_number == self.current_round]

    def get_active_rival_count(self) -> int:
        """How many rivals are still in this bidding war."""
        withdrawn = {b.promotion_id for b in self.rival_bids if b.withdrew}
        return len([p for p in self.participating_rivals if p not in withdrawn])

    def player_is_leading(self) -> bool:
        """Is the player currently the highest bidder?"""
        if self.player_withdrew or self.player_offer_salary is None:
            return False
        top_rival = self.get_highest_rival_offer()
        if top_rival is None:
            return True
        return self.player_offer_salary >= top_rival.salary_offer

    def to_dict(self) -> Dict[str, Any]:
        return {
            'bidding_war_id':          self.bidding_war_id,
            'fa_id':                   self.fa_id,
            'fa_name':                 self.fa_name,
            'status':                  self.status.value,
            'is_open_bidding':         self.is_open_bidding,
            'current_round':           self.current_round,
            'max_rounds':              self.max_rounds,
            'player_offer_salary':     self.player_offer_salary,
            'player_offer_weeks':      self.player_offer_weeks,
            'player_offer_bonus':      self.player_offer_bonus,
            'player_creative_control': self.player_creative_control,
            'player_title_guarantee':  self.player_title_guarantee,
            'player_withdrew':         self.player_withdrew,
            'rival_bids':              [b.to_dict() for b in self.rival_bids],
            'events':                  [e.to_dict() for e in self.events],
            'participating_rivals':    self.participating_rivals,
            'winner':                  self.winner,
            'winning_salary':          self.winning_salary,
            'decided_year':            self.decided_year,
            'decided_week':            self.decided_week,
            'outcome_reason':          self.outcome_reason,
            'started_year':            self.started_year,
            'started_week':            self.started_week,
            'deadline_year':           self.deadline_year,
            'deadline_week':           self.deadline_week,
            # Convenience fields for UI
            'player_is_leading':       self.player_is_leading(),
            'active_rival_count':      self.get_active_rival_count(),
            'highest_rival_salary':    self.get_highest_rival_offer().salary_offer if self.get_highest_rival_offer() else None,
            'highest_rival_name':      self.get_highest_rival_offer().promotion_name if self.get_highest_rival_offer() else None,
        }


# ======================================================================== #
# Main Engine                                                                #
# ======================================================================== #

class BiddingWarEngine:
    """
    Orchestrates bidding wars between the player and rival promotions.

    Usage:
        engine = BiddingWarEngine(database, rival_manager)
        war = engine.start_bidding_war(free_agent, year, week)
        notifications = engine.get_outbid_notifications(war)
    """

    def __init__(self, database, rival_manager):
        self.database = database
        self.rival_manager = rival_manager

    # ------------------------------------------------------------------ #
    # STEP 126: Interest Generation                                        #
    # ------------------------------------------------------------------ #

    def generate_rival_interest(
        self,
        free_agent,
        year: int,
        week: int
    ) -> List[Dict[str, Any]]:
        """
        For a given free agent, determine which rival promotions are interested
        and at what level (0-100).

        Returns list of {promotion, interest_level, initial_offer} sorted by interest.
        """
        interested = []

        for promotion in self.rival_manager.get_all_promotions():
            interest = promotion.calculate_interest_level(free_agent)

            if interest < 20:
                continue  # Not interested enough to engage

            initial_offer = promotion.generate_offer_salary(free_agent, interest)

            interested.append({
                'promotion':     promotion,
                'interest_level': interest,
                'initial_offer':  initial_offer,
                'will_bid':       interest >= 40  # Only seriously interested ones bid
            })

        return sorted(interested, key=lambda x: x['interest_level'], reverse=True)

    # ------------------------------------------------------------------ #
    # STEP 127: Start & Structure Bidding War                             #
    # ------------------------------------------------------------------ #

    def start_bidding_war(
        self,
        free_agent,
        year: int,
        week: int,
        force_open_bidding: bool = False
    ) -> BiddingWar:
        """
        Initialise a bidding war for a free agent.

        - Determines which rivals join
        - Sets blind vs. open bidding (STEP 128)
        - Submits Round 1 rival bids
        """
        interested = self.generate_rival_interest(free_agent, year, week)
        bidders = [i for i in interested if i['will_bid']]

        if not bidders:
            # No rivals interested - no bidding war needed
            return None

        # STEP 128: Decide blind vs open bidding
        # Open bidding when: major star, agent with publicity_seeking, or random (15%)
        is_open = force_open_bidding
        if not is_open:
            if free_agent.popularity >= 75 or free_agent.is_major_superstar:
                is_open = random.random() < 0.5
            elif hasattr(free_agent, 'agent') and free_agent.agent:
                agent = free_agent.agent
                if hasattr(agent, 'publicity_seeking') and agent.publicity_seeking:
                    is_open = True
            else:
                is_open = random.random() < 0.15

        war_id = f"bw_{free_agent.free_agent_id}_{year}_{week}"

        war = BiddingWar(
            bidding_war_id=war_id,
            fa_id=free_agent.free_agent_id,
            fa_name=free_agent.wrestler_name,
            status=BiddingWarStatus.OPEN,
            is_open_bidding=is_open,
            current_round=1,
            max_rounds=3,
            started_year=year,
            started_week=week,
            participating_rivals=[b['promotion'].promotion_id for b in bidders]
        )

        # Submit round 1 rival bids
        for bidder in bidders:
            promotion = bidder['promotion']
            bid = RivalBid(
                promotion_id=promotion.promotion_id,
                promotion_name=promotion.name,
                round_number=1,
                salary_offer=bidder['initial_offer'],
                contract_weeks=52,
                signing_bonus=random.randint(0, bidder['initial_offer'] * 2) if bidder['interest_level'] >= 70 else 0,
                interest_level=bidder['interest_level']
            )
            war.rival_bids.append(bid)

            # Track this promotion as actively pursuing
            promotion.active_pursuits.append(free_agent.free_agent_id)
            self.rival_manager.save_promotion(promotion)

        # Persist
        self._save_war(war)
        print(f"⚔️  Bidding war started for {free_agent.wrestler_name} | {len(bidders)} rivals | {'Open' if is_open else 'Blind'} bidding")

        return war

    # ------------------------------------------------------------------ #
    # STEP 129: Escalation Events                                         #
    # ------------------------------------------------------------------ #

    def roll_escalation_events(
        self,
        war: BiddingWar,
        free_agent
    ) -> List[BiddingEvent]:
        """
        Roll for random escalation events between rounds.
        Called after the player submits their bid and before rivals counter.
        """
        new_events = []

        # Only roll between rounds 1→2 and 2→3
        if war.current_round >= war.max_rounds:
            return []

        # Each event has independent probability
        event_rolls = [
            (0.12, self._event_rival_dramatic_increase),
            (0.10, self._event_wrestler_demands_up),
            (0.08, self._event_promotion_drops_out),
            (0.06, self._event_injury_revelation),
            (0.05, self._event_controversy_emerges),
            (0.18, self._event_leaked_to_media),
            (0.07, self._event_loyalty_declaration),
        ]

        for probability, event_fn in event_rolls:
            if random.random() < probability:
                event = event_fn(war, free_agent)
                if event:
                    new_events.append(event)
                    war.events.append(event)

        return new_events

    def _event_rival_dramatic_increase(self, war, fa) -> Optional[BiddingEvent]:
        """A rival promotion makes a large jump in their offer."""
        active_rivals = [
            b for b in war.rival_bids
            if b.round_number == war.current_round and not b.withdrew
        ]
        if not active_rivals:
            return None

        target = random.choice(active_rivals)
        jump_pct = random.uniform(0.20, 0.45)
        new_salary = int(target.salary_offer * (1 + jump_pct))
        new_salary = round(new_salary / 500) * 500

        # Create an updated bid for the next round at the new amount
        upgraded_bid = RivalBid(
            promotion_id=target.promotion_id,
            promotion_name=target.promotion_name,
            round_number=war.current_round + 1,
            salary_offer=new_salary,
            interest_level=min(100, target.interest_level + 15)
        )
        war.rival_bids.append(upgraded_bid)

        return BiddingEvent(
            event_type=BiddingEventType.RIVAL_DRAMATIC_INCREASE,
            description=f"🚨 {target.promotion_name} dramatically increased their offer to ${new_salary:,}/show!",
            triggered_round=war.current_round,
            effect_data={
                'promotion_id': target.promotion_id,
                'old_salary':   target.salary_offer,
                'new_salary':   new_salary
            }
        )

    def _event_wrestler_demands_up(self, war, fa) -> Optional[BiddingEvent]:
        """Free agent raises their minimum requirements mid-negotiation."""
        increase = random.randint(1000, 3000)
        increase = round(increase / 500) * 500

        if hasattr(fa, 'demands') and fa.demands:
            fa.demands.asking_salary += increase
            fa.demands.minimum_salary += int(increase * 0.5)

        return BiddingEvent(
            event_type=BiddingEventType.WRESTLER_DEMANDS_UP,
            description=f"📈 {fa.wrestler_name}'s demands increased by ${increase:,}/show due to heightened interest.",
            triggered_round=war.current_round,
            effect_data={'salary_increase': increase}
        )

    def _event_promotion_drops_out(self, war, fa) -> Optional[BiddingEvent]:
        """A rival promotion withdraws from bidding."""
        active_rivals = {
            b.promotion_id for b in war.rival_bids
            if b.round_number == war.current_round and not b.withdrew
        }
        if len(active_rivals) <= 1:
            return None  # Don't drop the only competitor

        drop_id = random.choice(list(active_rivals))
        drop_name = next(
            b.promotion_name for b in war.rival_bids
            if b.promotion_id == drop_id
        )

        # Mark all bids from this promotion as withdrawn
        for bid in war.rival_bids:
            if bid.promotion_id == drop_id:
                bid.withdrew = True

        if drop_id in war.participating_rivals:
            war.participating_rivals.remove(drop_id)

        return BiddingEvent(
            event_type=BiddingEventType.PROMOTION_DROPS_OUT,
            description=f"🚪 {drop_name} has withdrawn from negotiations.",
            triggered_round=war.current_round,
            effect_data={'promotion_id': drop_id, 'promotion_name': drop_name}
        )

    def _event_injury_revelation(self, war, fa) -> Optional[BiddingEvent]:
        """Old injury information surfaces, reducing everyone's offers."""
        if not fa.has_chronic_issues and fa.injury_history_count < 2:
            return None  # Only fires if there's actual history

        reduction_pct = random.uniform(0.08, 0.18)

        # Reduce all future rival bids
        for bid in war.rival_bids:
            if not bid.withdrew:
                bid.salary_offer = int(bid.salary_offer * (1 - reduction_pct))
                bid.salary_offer = round(bid.salary_offer / 500) * 500

        if hasattr(fa, 'market_value'):
            fa.market_value = int(fa.market_value * (1 - reduction_pct * 0.5))

        return BiddingEvent(
            event_type=BiddingEventType.INJURY_REVELATION,
            description=f"🏥 Injury history information has surfaced, reducing interest from all parties.",
            triggered_round=war.current_round,
            effect_data={'reduction_percentage': round(reduction_pct * 100, 1)}
        )

    def _event_controversy_emerges(self, war, fa) -> Optional[BiddingEvent]:
        """A backstage issue or controversy surfaces."""
        if fa.backstage_reputation >= 60:
            return None  # No controversy for respected talent

        severity = "minor" if fa.backstage_reputation >= 40 else "significant"
        reduction_pct = 0.05 if severity == "minor" else 0.12

        for bid in war.rival_bids:
            if not bid.withdrew and bid.interest_level < 80:
                bid.salary_offer = int(bid.salary_offer * (1 - reduction_pct))
                bid.salary_offer = round(bid.salary_offer / 500) * 500
                bid.interest_level = max(0, bid.interest_level - 15)

        return BiddingEvent(
            event_type=BiddingEventType.CONTROVERSY_EMERGES,
            description=f"📰 A {severity} backstage concern about {fa.wrestler_name} has emerged, cooling interest.",
            triggered_round=war.current_round,
            effect_data={'severity': severity, 'reduction_pct': reduction_pct}
        )

    def _event_leaked_to_media(self, war, fa) -> Optional[BiddingEvent]:
        """Negotiations leak to wrestling media / dirt sheets."""
        if war.is_open_bidding:
            return None  # Already public

        war.is_open_bidding = True

        return BiddingEvent(
            event_type=BiddingEventType.LEAKED_TO_MEDIA,
            description=f"📡 Negotiations for {fa.wrestler_name} have leaked to wrestling media. All offers now public!",
            triggered_round=war.current_round,
            effect_data={'previously_blind': True}
        )

    def _event_loyalty_declaration(self, war, fa) -> Optional[BiddingEvent]:
        """Free agent publicly states they prefer signing with the player's promotion."""
        return BiddingEvent(
            event_type=BiddingEventType.LOYALTY_DECLARATION,
            description=f"💚 {fa.wrestler_name} has expressed a strong preference for joining your promotion.",
            triggered_round=war.current_round,
            effect_data={'player_advantage': 10}  # +10 to player's effective offer weight
        )

    # ------------------------------------------------------------------ #
    # STEP 130: Outbid Notifications                                      #
    # ------------------------------------------------------------------ #

    def get_outbid_notifications(
        self,
        war: BiddingWar,
        year: int,
        week: int
    ) -> List[Dict[str, Any]]:
        """
        Generate alert messages when player has been outbid.
        Returns list of notification dicts ready for the UI.
        """
        notifications = []

        if war.status in (BiddingWarStatus.DECIDED, BiddingWarStatus.CANCELLED):
            return notifications

        highest_rival = war.get_highest_rival_offer()
        if not highest_rival:
            return notifications

        if war.player_offer_salary is None:
            # Player hasn't bid yet
            notifications.append({
                'type':    'not_yet_bid',
                'urgency': 'medium',
                'message': (
                    f"⚠️  {war.fa_name} has offers from {war.get_active_rival_count()} promotions. "
                    f"Highest offer: ${highest_rival.salary_offer:,}/show from {highest_rival.promotion_name}. "
                    f"You haven't made an offer yet."
                ),
                'highest_rival_salary': highest_rival.salary_offer,
                'highest_rival_name':   highest_rival.promotion_name,
                'rounds_remaining':     war.max_rounds - war.current_round
            })
        elif not war.player_is_leading():
            gap = highest_rival.salary_offer - war.player_offer_salary
            rounds_left = war.max_rounds - war.current_round
            urgency = 'high' if rounds_left <= 1 else 'medium'

            deadline_msg = ""
            if war.deadline_week:
                deadline_msg = f" You have until Week {war.deadline_week} to respond."

            notifications.append({
                'type':                 'outbid',
                'urgency':              urgency,
                'message': (
                    f"🚨 ALERT: {highest_rival.promotion_name} has offered ${highest_rival.salary_offer:,}/show — "
                    f"${gap:,} more than your current offer of ${war.player_offer_salary:,}. "
                    f"{fa_name_placeholder(war)} is giving you {rounds_left} round(s) to respond.{deadline_msg}"
                ),
                'gap':                      gap,
                'your_offer':               war.player_offer_salary,
                'highest_rival_salary':     highest_rival.salary_offer,
                'highest_rival_name':       highest_rival.promotion_name,
                'rounds_remaining':         rounds_left,
                'minimum_to_lead':          highest_rival.salary_offer + 500
            })

        return notifications

    # ------------------------------------------------------------------ #
    # STEP 131: Strategic Bidding Decisions                               #
    # ------------------------------------------------------------------ #

    def apply_player_action(
        self,
        war: BiddingWar,
        action: PlayerBidAction,
        params: Dict[str, Any],
        year: int,
        week: int
    ) -> Dict[str, Any]:
        """
        Process the player's chosen bidding action.

        Returns result dict with: success, new_salary, message, side_effects
        """
        if war.status in (BiddingWarStatus.DECIDED, BiddingWarStatus.CANCELLED):
            return {'success': False, 'message': 'Bidding war is already resolved.'}

        if war.player_withdrew:
            return {'success': False, 'message': 'You have already withdrawn from this bidding war.'}

        result = {'success': True, 'side_effects': []}

        if action == PlayerBidAction.MATCH_OFFER:
            top = war.get_highest_rival_offer()
            if top:
                war.player_offer_salary = top.salary_offer
                result['new_salary'] = war.player_offer_salary
                result['message'] = f"✅ You matched {top.promotion_name}'s offer of ${top.salary_offer:,}/show."
            else:
                result['success'] = False
                result['message'] = "No rival offer to match."

        elif action == PlayerBidAction.EXCEED_OFFER:
            top = war.get_highest_rival_offer()
            exceed_by = params.get('exceed_by', 1000)
            base = top.salary_offer if top else (war.player_offer_salary or 5000)
            war.player_offer_salary = round((base + exceed_by) / 500) * 500
            result['new_salary'] = war.player_offer_salary
            result['message'] = f"✅ You outbid the competition at ${war.player_offer_salary:,}/show."

        elif action == PlayerBidAction.SWEETEN_PERKS:
            # Non-monetary perks — don't raise salary but boost attractiveness
            perks = params.get('perks', {})
            if 'creative_control' in perks:
                war.player_creative_control = perks['creative_control']
            if 'title_guarantee' in perks:
                war.player_title_guarantee = perks['title_guarantee']
            if 'signing_bonus' in perks:
                war.player_offer_bonus = params['perks']['signing_bonus']
            result['message'] = "✅ You sweetened the offer with additional perks."
            result['perks_added'] = perks

        elif action == PlayerBidAction.HOLD_FIRM:
            if war.player_offer_salary is None:
                result['success'] = False
                result['message'] = "You must make an initial offer before holding firm."
            else:
                result['message'] = f"⏸️  You held firm at ${war.player_offer_salary:,}/show."
                result['side_effects'].append({
                    'type':    'patience_test',
                    'message': "Holding firm puts pressure on the wrestler to decide with current offers."
                })

        elif action == PlayerBidAction.WITHDRAW:
            war.player_withdrew = True
            result['message'] = f"🚪 You withdrew from the bidding war for {war.fa_name}."
            result['side_effects'].append({'type': 'withdrew', 'fa_id': war.fa_id})

        elif action == PlayerBidAction.REQUEST_MEETING:
            # Costs nothing monetarily, but slightly boosts wrestler's lean toward player
            # Reflected as a phantom +5% on player's effective offer value
            discount = params.get('salary', war.player_offer_salary or 5000)
            war.player_offer_salary = round(discount / 500) * 500
            result['message'] = (
                f"🤝 You requested a personal meeting. {war.fa_name} appreciates the direct approach. "
                f"Your offer carries extra weight this round."
            )
            result['meeting_bonus'] = 8   # % bonus applied during decision

        elif action == PlayerBidAction.EXCLUSIVE_WINDOW:
            cost = params.get('cost', 15000)
            result['message'] = (
                f"🔒 You purchased an exclusive negotiation window. "
                f"Rivals are locked out for the next 2 weeks. Cost: ${cost:,}"
            )
            result['exclusive_cost'] = cost
            war.status = BiddingWarStatus.FINAL  # Jump to final round, no rivals
            result['side_effects'].append({'type': 'exclusive_window', 'cost': cost})

        # Advance round if appropriate
        if action not in (PlayerBidAction.WITHDRAW, PlayerBidAction.EXCLUSIVE_WINDOW):
            self._maybe_advance_round(war)

        self._save_war(war)
        return result

    def _maybe_advance_round(self, war: BiddingWar) -> None:
        """Advance to the next round if all parties have bid this round."""
        if war.current_round < war.max_rounds:
            war.current_round += 1
            if war.current_round == war.max_rounds:
                war.status = BiddingWarStatus.FINAL
            elif war.current_round == 2:
                war.status = BiddingWarStatus.ROUND_2

    # ------------------------------------------------------------------ #
    # Rivals' Counter-Bids (AI round progression)                        #
    # ------------------------------------------------------------------ #

    def generate_rival_counter_bids(
        self,
        war: BiddingWar,
        free_agent,
        year: int,
        week: int
    ) -> List[RivalBid]:
        """
        After the player acts, generate rival promotions' counter-bids for the
        new round.  Called automatically when advancing rounds.
        """
        new_bids = []
        promotions_map = {
            p.promotion_id: p for p in self.rival_manager.get_all_promotions()
        }

        # Which rivals are still active?
        withdrawn = {b.promotion_id for b in war.rival_bids if b.withdrew}
        active_rival_ids = [
            pid for pid in war.participating_rivals
            if pid not in withdrawn
        ]

        for rival_id in active_rival_ids:
            promotion = promotions_map.get(rival_id)
            if not promotion:
                continue

            interest = promotion.calculate_interest_level(free_agent)

            # Find their previous bid
            prev_bids = [
                b for b in war.rival_bids
                if b.promotion_id == rival_id and not b.withdrew
            ]
            prev_salary = max((b.salary_offer for b in prev_bids), default=0)

            # Decide whether to continue or drop
            drop_probability = max(0.05, (100 - interest) / 200)
            if random.random() < drop_probability:
                # Rival drops out
                for b in prev_bids:
                    b.withdrew = True
                if rival_id in war.participating_rivals:
                    war.participating_rivals.remove(rival_id)
                print(f"  {promotion.name} dropped out of bidding war for {war.fa_name}")
                continue

            # Calculate counter-offer (increase by 5-20%)
            increase_pct = random.uniform(0.05, 0.20)
            new_salary = round(int(prev_salary * (1 + increase_pct)) / 500) * 500
            new_salary = max(new_salary, prev_salary + 500)

            # Cap at what they can afford
            max_affordable = promotion.remaining_budget // (52 * 3)
            new_salary = min(new_salary, max_affordable)

            is_final = war.current_round >= war.max_rounds

            bid = RivalBid(
                promotion_id=rival_id,
                promotion_name=promotion.name,
                round_number=war.current_round,
                salary_offer=new_salary,
                contract_weeks=52,
                signing_bonus=random.randint(0, new_salary) if interest >= 75 else 0,
                interest_level=interest,
                is_final_offer=is_final
            )
            war.rival_bids.append(bid)
            new_bids.append(bid)

        self._save_war(war)
        return new_bids

    # ------------------------------------------------------------------ #
    # STEP 132: Resolution & Post-Bidding Relationship Effects            #
    # ------------------------------------------------------------------ #

    def resolve_bidding_war(
        self,
        war: BiddingWar,
        free_agent,
        year: int,
        week: int,
        player_meeting_bonus: int = 0
    ) -> Dict[str, Any]:
        """
        Decide who wins the bidding war.

        Free agent evaluates all offers using:
        - Total compensation (salary + bonus)
        - Mood adjustments (patient = values prestige, hungry = values money)
        - Creative control preferences
        - Title guarantee weight
        - Meeting bonus if player requested meeting

        Returns result dict and applies relationship effects.
        """
        if war.player_withdrew and not war.participating_rivals:
            return self._resolve_no_deal(war, year, week, "All parties withdrew")

        # Build offer scores
        scores = {}

        # Score player's offer
        if not war.player_withdrew and war.player_offer_salary:
            scores['player'] = self._score_offer(
                salary=war.player_offer_salary,
                weeks=war.player_offer_weeks,
                bonus=war.player_offer_bonus,
                creative_control=war.player_creative_control,
                title_guarantee=war.player_title_guarantee,
                free_agent=free_agent,
                extra_score=player_meeting_bonus
            )

        # Score rival offers
        for rival_id in war.participating_rivals:
            rival_bids = [
                b for b in war.rival_bids
                if b.promotion_id == rival_id and not b.withdrew
            ]
            if not rival_bids:
                continue
            best_bid = max(rival_bids, key=lambda b: b.salary_offer)
            promo = self.rival_manager.get_promotion_by_id(rival_id)
            prestige_bonus = (promo.prestige - 50) // 5 if promo else 0

            scores[rival_id] = self._score_offer(
                salary=best_bid.salary_offer,
                weeks=best_bid.contract_weeks,
                bonus=best_bid.signing_bonus,
                creative_control='none',
                title_guarantee=False,
                free_agent=free_agent,
                extra_score=prestige_bonus
            )

        if not scores:
            return self._resolve_no_deal(war, year, week, "No valid offers submitted")

        # Check loyalty declaration event
        loyalty_event = next(
            (e for e in war.events if e.event_type == BiddingEventType.LOYALTY_DECLARATION),
            None
        )
        if loyalty_event and 'player' in scores:
            scores['player'] += loyalty_event.effect_data.get('player_advantage', 0)

        winner_id = max(scores, key=scores.get)
        winning_salary = (
            war.player_offer_salary if winner_id == 'player'
            else next(
                b.salary_offer for b in reversed(war.rival_bids)
                if b.promotion_id == winner_id and not b.withdrew
            )
        )

        war.winner = winner_id
        war.winning_salary = winning_salary
        war.decided_year = year
        war.decided_week = week
        war.status = BiddingWarStatus.DECIDED

        if winner_id == 'player':
            war.outcome_reason = "Your promotion offered the best overall package."
        else:
            rival_name = next(
                (b.promotion_name for b in war.rival_bids if b.promotion_id == winner_id),
                winner_id
            )
            war.outcome_reason = f"{rival_name} offered the best overall package."

        # STEP 132: Apply relationship effects
        relationship_effects = self._apply_post_bidding_relationships(
            war, winner_id, year, week
        )

        self._save_war(war)

        return {
            'winner':               winner_id,
            'winner_is_player':     winner_id == 'player',
            'winning_salary':       winning_salary,
            'outcome_reason':       war.outcome_reason,
            'scores':               scores,
            'relationship_effects': relationship_effects
        }

    def _score_offer(
        self,
        salary: int,
        weeks: int,
        bonus: int,
        creative_control: str,
        title_guarantee: bool,
        free_agent,
        extra_score: int = 0
    ) -> float:
        """
        Compute a float "attractiveness score" for an offer.
        Higher = more attractive to the free agent.
        """
        score = 0.0

        # Base: total compensation
        total_comp = (salary * 3 * weeks) + bonus  # 3 shows/week
        score += total_comp / 10000

        # Creative control premium
        cc_values = {'none': 0, 'consultation': 5, 'approval': 12, 'partnership': 20, 'full_control': 30}
        score += cc_values.get(creative_control, 0)

        # Title guarantee
        if title_guarantee:
            score += 15

        # Mood modifier
        mood = getattr(free_agent, 'mood', None)
        if mood:
            mood_val = mood.value if hasattr(mood, 'value') else str(mood)
            if mood_val == 'hungry':
                score *= 1.15   # Money matters more
            elif mood_val == 'patient':
                score *= 0.95   # Less money-focused
            elif mood_val == 'arrogant':
                score *= 0.90   # Hard to impress
            elif mood_val == 'desperate':
                score *= 1.25   # Will take nearly anything

        score += extra_score
        return round(score, 2)

    def _apply_post_bidding_relationships(
        self,
        war: BiddingWar,
        winner_id: str,
        year: int,
        week: int
    ) -> List[Dict[str, Any]]:
        """
        STEP 132: Apply relationship effects after bidding war resolves.

        - Player wins → rivals lose, negative relationship with beaten rivals
        - Rivals win → small positive (they respect your participation)
        - Overpaying  → note for budget warning
        """
        from persistence.rival_promotion_db import log_relationship_change

        effects = []

        for rival_id in war.participating_rivals:
            promotion = self.rival_manager.get_promotion_by_id(rival_id)
            if not promotion:
                continue

            if winner_id == 'player':
                # We beat them — relationship worsens slightly
                change = -5
                reason = f"Lost bidding war for {war.fa_name} to player promotion"
                promotion.lost_bidding_wars += 1
            elif winner_id == rival_id:
                # They beat us — relationship is neutral (they got what they wanted)
                change = 0
                reason = f"Won bidding war for {war.fa_name}"
                promotion.won_bidding_wars += 1
            else:
                # Third party won / or this rival lost to another rival
                change = +2
                reason = f"Mutual loss in bidding war for {war.fa_name} — shared experience"
                promotion.lost_bidding_wars += 1

            log_relationship_change(self.database, rival_id, change, reason, year, week)

            # Remove from active pursuits
            if war.fa_id in promotion.active_pursuits:
                promotion.active_pursuits.remove(war.fa_id)

            self.rival_manager.save_promotion(promotion)

            effects.append({
                'promotion_id':   rival_id,
                'promotion_name': promotion.name,
                'relationship_change': change,
                'reason': reason
            })

        return effects

    def _resolve_no_deal(
        self,
        war: BiddingWar,
        year: int,
        week: int,
        reason: str
    ) -> Dict[str, Any]:
        war.winner = 'no_deal'
        war.status = BiddingWarStatus.CANCELLED
        war.decided_year = year
        war.decided_week = week
        war.outcome_reason = reason
        self._save_war(war)
        return {
            'winner': 'no_deal',
            'winner_is_player': False,
            'winning_salary': None,
            'outcome_reason': reason,
            'relationship_effects': []
        }

    # ------------------------------------------------------------------ #
    # STEP 133: Anti-Bidding War Tactics                                  #
    # ------------------------------------------------------------------ #

    def check_pre_emptive_signing_window(
        self,
        free_agent,
        year: int,
        week: int
    ) -> Dict[str, Any]:
        """
        STEP 133: Can the player sign this FA before a bidding war starts?

        Returns whether pre-emptive signing is possible and at what premium.
        """
        interested = self.generate_rival_interest(free_agent, year, week)
        rival_count = len([i for i in interested if i['will_bid']])

        # Pre-emptive window open if:
        # - FA is not yet widely known (visibility tier 3 or 4)
        # - OR FA just became available (weeks_unemployed <= 2)
        visibility = getattr(free_agent, 'visibility', None)
        vis_value = visibility.value if hasattr(visibility, 'value') else 4

        can_preempt = vis_value >= 3 or getattr(free_agent, 'weeks_unemployed', 10) <= 2

        if not can_preempt:
            return {
                'available': False,
                'reason': 'Too high-profile — rivals are already aware and will compete.'
            }

        # Pre-emptive signing costs 10-20% premium over asking
        premium_pct = 0.10 if vis_value >= 3 else 0.15
        asking = free_agent.demands.asking_salary if hasattr(free_agent, 'demands') and free_agent.demands else 5000
        preemptive_cost = round(int(asking * (1 + premium_pct)) / 500) * 500

        return {
            'available':          True,
            'preemptive_salary':  preemptive_cost,
            'asking_salary':      asking,
            'premium_percentage': round(premium_pct * 100, 1),
            'rival_count_avoided': rival_count,
            'reason': (
                f"Pre-emptive signing available. Pay ${preemptive_cost:,}/show ({premium_pct*100:.0f}% premium) "
                f"to avoid competing with {rival_count} rival(s)."
            )
        }

    def calculate_loyalty_bonus_value(
        self,
        wrestler,
        extension_weeks: int = 52
    ) -> Dict[str, Any]:
        """
        STEP 133: Estimate the savings from a loyalty bonus (re-signing current
        talent before they test free agency).

        A happy wrestler re-signs at a discount vs. what a bidding war
        would cost.
        """
        from economy.contracts import contract_manager

        market_value = contract_manager.calculate_market_value(wrestler)
        current_salary = wrestler.contract.salary_per_show

        # Happy wrestlers (morale 70+) accept 5-10% discount
        # Unhappy wrestlers demand 10-20% premium even on extension
        morale = getattr(wrestler, 'morale', 50)

        if morale >= 80:
            multiplier = 0.92   # 8% discount
            mood_label = "ecstatic"
        elif morale >= 60:
            multiplier = 0.97   # 3% discount
            mood_label = "content"
        elif morale >= 40:
            multiplier = 1.05   # 5% premium (unhappy)
            mood_label = "unhappy"
        else:
            multiplier = 1.15   # 15% premium (miserable — almost won't sign)
            mood_label = "miserable"

        extension_salary = round(int(market_value * multiplier) / 500) * 500
        savings_vs_bidding_war = max(0, market_value - extension_salary)
        annual_savings = savings_vs_bidding_war * 3 * 52  # 3 shows/week

        return {
            'wrestler_id':          wrestler.id,
            'wrestler_name':        wrestler.name,
            'current_salary':       current_salary,
            'market_value':         market_value,
            'extension_salary':     extension_salary,
            'mood_label':           mood_label,
            'morale':               morale,
            'savings_vs_bidding':   savings_vs_bidding_war,
            'annual_savings':       annual_savings,
            'recommendation': (
                f"Extending now saves ~${annual_savings:,}/year vs. a bidding war."
                if savings_vs_bidding_war > 0
                else f"Morale is low — extension will cost ${abs(savings_vs_bidding_war)}/show MORE than market rate."
            )
        }

    # ------------------------------------------------------------------ #
    # Persistence Helpers                                                  #
    # ------------------------------------------------------------------ #

    def _save_war(self, war: BiddingWar) -> None:
        from persistence.rival_promotion_db import save_bidding_war, save_rival_bid, save_bidding_event

        # Save the war record
        save_bidding_war(self.database, {
            'bidding_war_id':          war.bidding_war_id,
            'fa_id':                   war.fa_id,
            'fa_name':                 war.fa_name,
            'status':                  war.status.value,
            'is_open_bidding':         war.is_open_bidding,
            'current_round':           war.current_round,
            'max_rounds':              war.max_rounds,
            'player_offer_salary':     war.player_offer_salary,
            'player_offer_weeks':      war.player_offer_weeks,
            'player_offer_bonus':      war.player_offer_bonus,
            'player_creative_control': war.player_creative_control,
            'player_title_guarantee':  war.player_title_guarantee,
            'player_withdrew':         war.player_withdrew,
            'winner':                  war.winner,
            'winning_salary':          war.winning_salary,
            'decided_year':            war.decided_year,
            'decided_week':            war.decided_week,
            'outcome_reason':          war.outcome_reason,
            'started_year':            war.started_year,
            'started_week':            war.started_week,
            'deadline_year':           war.deadline_year,
            'deadline_week':           war.deadline_week,
        })

    def load_war(self, bidding_war_id: str) -> Optional[BiddingWar]:
        """Load a BiddingWar from the database."""
        from persistence.rival_promotion_db import (
            get_bidding_war, get_rival_bids_for_war, get_events_for_war
        )

        war_data = get_bidding_war(self.database, bidding_war_id)
        if not war_data:
            return None

        bids = get_rival_bids_for_war(self.database, bidding_war_id)
        events = get_events_for_war(self.database, bidding_war_id)

        rival_bids = [
            RivalBid(
                promotion_id=b['promotion_id'],
                promotion_name=b['promotion_name'],
                round_number=b['round_number'],
                salary_offer=b['salary_offer'],
                contract_weeks=b['contract_weeks'],
                signing_bonus=b['signing_bonus'],
                creative_perks=b['creative_perks'],
                interest_level=b['interest_level'],
                is_final_offer=bool(b['is_final_offer']),
                withdrew=bool(b['withdrew'])
            )
            for b in bids
        ]

        bidding_events = [
            BiddingEvent(
                event_type=BiddingEventType(e['event_type']),
                description=e['description'],
                triggered_round=e['triggered_round'],
                effect_data=e['effect_data']
            )
            for e in events
        ]

        return BiddingWar(
            bidding_war_id=war_data['bidding_war_id'],
            fa_id=war_data['fa_id'],
            fa_name=war_data['fa_name'],
            status=BiddingWarStatus(war_data['status']),
            is_open_bidding=bool(war_data['is_open_bidding']),
            current_round=war_data['current_round'],
            max_rounds=war_data['max_rounds'],
            player_offer_salary=war_data['player_offer_salary'],
            player_offer_weeks=war_data['player_offer_weeks'] or 52,
            player_offer_bonus=war_data['player_offer_bonus'] or 0,
            player_creative_control=war_data['player_creative_control'] or 'none',
            player_title_guarantee=bool(war_data['player_title_guarantee']),
            player_withdrew=bool(war_data['player_withdrew']),
            rival_bids=rival_bids,
            events=bidding_events,
            winner=war_data['winner'],
            winning_salary=war_data['winning_salary'],
            decided_year=war_data['decided_year'],
            decided_week=war_data['decided_week'],
            outcome_reason=war_data['outcome_reason'],
            started_year=war_data['started_year'],
            started_week=war_data['started_week'],
            deadline_year=war_data['deadline_year'],
            deadline_week=war_data['deadline_week'],
        )


# ======================================================================== #
# Utility                                                                    #
# ======================================================================== #

def fa_name_placeholder(war: BiddingWar) -> str:
    """Helper for readable notifications."""
    return war.fa_name