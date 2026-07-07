"""
Rival Promotion Interest Generation Engine
STEP 126: Generates and manages rival promotion interest in free agents
STEP 127: Bidding round structure
STEP 128: Blind vs Open bidding
STEP 129: Bidding escalation events
STEP 130: Outbid notifications
STEP 131: Strategic bidding decisions
STEP 132: Post-bidding relationship effects
"""

import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from models.rival_promotion import RivalPromotion, RivalPromotionTier, DEFAULT_RIVAL_PROMOTIONS
from models.free_agent import FreeAgent, RivalInterest


class BiddingRound:
    """Represents one round of a bidding war"""
    def __init__(
        self,
        round_number: int,
        free_agent_id: str,
        offers: List[Dict[str, Any]]  # [{promotion_id, promotion_name, salary, is_player}]
    ):
        self.round_number = round_number
        self.free_agent_id = free_agent_id
        self.offers = offers
        self.timestamp = datetime.now().isoformat()

    def get_highest_offer(self) -> Dict[str, Any]:
        """Get the highest offer this round"""
        return max(self.offers, key=lambda o: o['salary']) if self.offers else {}

    def get_player_offer(self) -> Optional[Dict[str, Any]]:
        """Get the player's offer if present"""
        for offer in self.offers:
            if offer.get('is_player'):
                return offer
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'round_number': self.round_number,
            'free_agent_id': self.free_agent_id,
            'offers': self.offers,
            'highest_offer': self.get_highest_offer(),
            'player_offer': self.get_player_offer(),
            'timestamp': self.timestamp
        }


class BiddingWar:
    """
    STEP 127: Manages a structured bidding war for a free agent.

    Phases:
    Round 1 - Initial offers submitted
    Round 2 - Wrestlers share competing offers, request improvements
    Round 3 - Final offers
    Decision - Wrestler chooses based on full package
    """

    MAX_ROUNDS = 3

    def __init__(
        self,
        free_agent: FreeAgent,
        is_open_bidding: bool = False  # STEP 128
    ):
        self.free_agent = free_agent
        self.is_open_bidding = is_open_bidding  # STEP 128: Blind vs Open
        self.rounds: List[BiddingRound] = []
        self.current_round = 0
        self.active = True
        self.winner_promotion_id: Optional[str] = None
        self.final_salary: Optional[int] = None
        self.outcome_message: str = ""
        self.escalation_events: List[Dict] = []  # STEP 129
        self.created_at = datetime.now().isoformat()

    def add_round(self, offers: List[Dict[str, Any]]) -> BiddingRound:
        """Add a new round of offers"""
        self.current_round += 1
        round_obj = BiddingRound(
            round_number=self.current_round,
            free_agent_id=self.free_agent.id,
            offers=offers
        )
        self.rounds.append(round_obj)
        return round_obj

    def is_complete(self) -> bool:
        return self.current_round >= self.MAX_ROUNDS or not self.active

    def get_current_highest_offer(self) -> int:
        """Get highest offer across all rounds"""
        all_offers = []
        for round_obj in self.rounds:
            all_offers.extend(round_obj.offers)
        return max([o['salary'] for o in all_offers], default=0)

    def get_all_participants(self) -> List[str]:
        """Get all promotion IDs that have made offers"""
        participants = set()
        for round_obj in self.rounds:
            for offer in round_obj.offers:
                participants.add(offer['promotion_id'])
        return list(participants)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'free_agent_id': self.free_agent.id,
            'free_agent_name': self.free_agent.wrestler_name,
            'is_open_bidding': self.is_open_bidding,
            'current_round': self.current_round,
            'max_rounds': self.MAX_ROUNDS,
            'active': self.active,
            'winner_promotion_id': self.winner_promotion_id,
            'final_salary': self.final_salary,
            'outcome_message': self.outcome_message,
            'rounds': [r.to_dict() for r in self.rounds],
            'escalation_events': self.escalation_events,
            'current_highest_offer': self.get_current_highest_offer(),
            'all_participants': self.get_all_participants()
        }


class RivalInterestEngine:
    """
    Core engine for managing rival promotion interest in free agents.

    Handles:
    - Interest generation (STEP 126)
    - Bidding round structure (STEP 127)
    - Blind vs open bidding (STEP 128)
    - Escalation events (STEP 129)
    - Outbid notifications (STEP 130)
    - Strategic decisions (STEP 131)
    - Post-bidding effects (STEP 132)
    """

    def __init__(self):
        self.rival_promotions: List[RivalPromotion] = []
        self.active_bidding_wars: Dict[str, BiddingWar] = {}  # fa_id -> BiddingWar
        self.completed_bidding_wars: List[Dict] = []
        self.outbid_notifications: List[Dict] = []  # STEP 130

    def initialize_default_rivals(self) -> None:
        """Load default rival promotions if none exist"""
        if not self.rival_promotions:
            self.rival_promotions = list(DEFAULT_RIVAL_PROMOTIONS)

    def load_from_db(self, db) -> None:
        """Load rival promotions from database"""
        from persistence.rival_promotion_db import load_rival_promotions
        from models.rival_promotion import RivalPromotion

        rows = load_rival_promotions(db)
        if rows:
            self.rival_promotions = [RivalPromotion.from_dict(r) for r in rows]
        else:
            self.initialize_default_rivals()
            self.save_to_db(db)

    def save_to_db(self, db) -> None:
        """Save all rival promotions to database"""
        from persistence.rival_promotion_db import save_rival_promotion

        for promotion in self.rival_promotions:
            save_rival_promotion(db, promotion)
        db.conn.commit()

    def get_promotion_by_id(self, promotion_id: str) -> Optional[RivalPromotion]:
        """Get a rival promotion by ID"""
        for p in self.rival_promotions:
            if p.promotion_id == promotion_id:
                return p
        return None

    # =========================================================
    # STEP 126: Interest Generation
    # =========================================================

    def generate_interest_for_free_agent(
        self,
        free_agent: FreeAgent,
        current_year: int,
        current_week: int,
        db=None
    ) -> List[Dict[str, Any]]:
        """
        STEP 126: Generate rival promotion interest in a free agent.

        Returns list of interested promotions with their interest levels.
        """
        interested = []

        for promotion in self.rival_promotions:
            # Skip if roster full
            if promotion.roster_size >= promotion.max_roster_size:
                continue

            # Skip if already pursuing this free agent
            if free_agent.id in promotion.active_pursuits:
                continue

            interest_level = promotion.calculate_interest_level(free_agent)

            # Only register real interest (>= 30)
            if interest_level >= 30:
                interested.append({
                    'promotion_id': promotion.promotion_id,
                    'promotion_name': promotion.name,
                    'abbreviation': promotion.abbreviation,
                    'tier': promotion.tier.value,
                    'prestige': promotion.prestige,
                    'interest_level': interest_level,
                    'can_afford': promotion.can_afford(free_agent.demands.asking_salary)
                })

                # Update free agent's rival interest list
                free_agent.add_rival_interest(promotion.name, interest_level)

                # Track in promotion
                if free_agent.id not in promotion.active_pursuits:
                    promotion.active_pursuits.append(free_agent.id)

        # Sort by interest level
        interested.sort(key=lambda x: x['interest_level'], reverse=True)

        # Save to database if provided
        if db and interested:
            from persistence.rival_promotion_db import save_rival_bid

            for entry in interested:
                bid_id = f"bid_{entry['promotion_id']}_{free_agent.id}_{current_year}_{current_week}"
                save_rival_bid(db, {
                    'bid_id': bid_id,
                    'promotion_id': entry['promotion_id'],
                    'free_agent_id': free_agent.id,
                    'wrestler_name': free_agent.wrestler_name,
                    'interest_level': entry['interest_level'],
                    'status': 'interested'
                })

            self.save_to_db(db)

        return interested

    def get_interest_summary_for_free_agent(
        self,
        free_agent: FreeAgent,
        db=None
    ) -> Dict[str, Any]:
        """Get a formatted summary of rival interest for display"""
        if db:
            from persistence.rival_promotion_db import get_active_bids_for_free_agent
            bids = get_active_bids_for_free_agent(db, free_agent.id)
        else:
            bids = []

        # Fall back to free agent's rival_interest list
        if not bids:
            bids = [
                {
                    'promotion_name': r.promotion_name,
                    'interest_level': r.interest_level,
                    'offered_salary': r.offer_salary,
                    'offer_made': r.offer_made
                }
                for r in free_agent.rival_interest
            ]

        total_interest = len(bids)
        has_offers = any(b.get('offer_made') or b.get('offered_salary', 0) > 0 for b in bids)
        highest_offer = max((b.get('offered_salary', 0) for b in bids), default=0)

        return {
            'total_interested': total_interest,
            'has_active_offers': has_offers,
            'highest_rival_offer': highest_offer,
            'interested_promotions': bids,
            'bidding_war_active': total_interest >= 2 and has_offers,
            'market_heat': 'hot' if total_interest >= 3 else 'warm' if total_interest >= 1 else 'cold'
        }

    # =========================================================
    # STEP 127: Bidding Round Structure
    # =========================================================

    def initiate_bidding_war(
        self,
        free_agent: FreeAgent,
        current_year: int,
        current_week: int,
        player_initial_offer: Optional[int] = None
    ) -> BiddingWar:
        """
        STEP 127: Start a structured bidding war for a free agent.

        Called when multiple promotions (including player) want the same FA.
        """
        # STEP 128: Determine if bidding is open or blind
        is_open = self._determine_bidding_type(free_agent)

        war = BiddingWar(free_agent=free_agent, is_open_bidding=is_open)

        # Round 1: Generate initial offers from all interested parties
        initial_offers = self._generate_round_offers(
            free_agent=free_agent,
            round_number=1,
            player_offer=player_initial_offer,
            previous_highest=0
        )

        war.add_round(initial_offers)
        self.active_bidding_wars[free_agent.id] = war

        return war

    def advance_bidding_round(
        self,
        free_agent_id: str,
        player_offer: Optional[int],
        current_year: int,
        current_week: int
    ) -> Dict[str, Any]:
        """
        STEP 127: Advance to next bidding round with player's new offer.

        Returns result dict with round info, notifications, and whether war is resolved.
        """
        war = self.active_bidding_wars.get(free_agent_id)
        if not war:
            return {'error': 'No active bidding war for this free agent'}

        if war.is_complete():
            return {'error': 'Bidding war already complete', 'war': war.to_dict()}

        previous_highest = war.get_current_highest_offer()

        # Check for escalation events (STEP 129)
        escalation = self._check_escalation_events(war, war.free_agent, current_year, current_week)
        if escalation:
            war.escalation_events.append(escalation)

        # Generate new round offers
        new_offers = self._generate_round_offers(
            free_agent=war.free_agent,
            round_number=war.current_round + 1,
            player_offer=player_offer,
            previous_highest=previous_highest
        )

        round_obj = war.add_round(new_offers)

        # STEP 130: Check if player was outbid
        outbid_notification = self._check_outbid(
            war=war,
            player_offer=player_offer,
            round_obj=round_obj,
            current_year=current_year,
            current_week=current_week
        )

        result = {
            'round': round_obj.to_dict(),
            'war_status': war.to_dict(),
            'outbid_notification': outbid_notification,
            'escalation_event': escalation,
            'is_final_round': war.current_round >= BiddingWar.MAX_ROUNDS
        }

        # If final round, resolve the war
        if war.is_complete():
            resolution = self._resolve_bidding_war(war, player_offer, current_year, current_week)
            result['resolution'] = resolution

        return result

    def _generate_round_offers(
        self,
        free_agent: FreeAgent,
        round_number: int,
        player_offer: Optional[int],
        previous_highest: int
    ) -> List[Dict[str, Any]]:
        """Generate offers from all parties for a bidding round"""
        offers = []

        # Player offer
        if player_offer is not None:
            offers.append({
                'promotion_id': 'player',
                'promotion_name': 'Ring of Champions',
                'salary': player_offer,
                'is_player': True,
                'round': round_number
            })

        # Rival offers
        for rival in free_agent.rival_interest:
            promotion = self._get_promotion_by_name(rival.promotion_name)
            if not promotion:
                continue

            interest = rival.interest_level
            if interest < 30:
                continue  # Lost interest

            # Escalate offers in later rounds
            round_multiplier = 1.0 + (round_number - 1) * 0.08  # +8% per round

            base_offer = promotion.generate_offer_salary(free_agent, interest)
            escalated_offer = int(base_offer * round_multiplier)

            # If open bidding: try to beat highest by 5-15%
            if previous_highest > 0:
                beat_by = random.uniform(1.05, 1.15)
                escalated_offer = max(escalated_offer, int(previous_highest * beat_by))

            # Cap at budget
            if not promotion.can_afford(escalated_offer):
                escalated_offer = int(promotion.remaining_budget / 52 / 3)
                if escalated_offer < free_agent.demands.minimum_salary:
                    continue  # Drop out

            offers.append({
                'promotion_id': promotion.promotion_id,
                'promotion_name': promotion.name,
                'salary': escalated_offer,
                'is_player': False,
                'round': round_number,
                'prestige': promotion.prestige
            })

            # Update free agent's rival interest with offer
            rival.offer_made = True
            rival.offer_salary = escalated_offer

        return offers

    def _resolve_bidding_war(
        self,
        war: BiddingWar,
        player_final_offer: Optional[int],
        current_year: int,
        current_week: int
    ) -> Dict[str, Any]:
        """Resolve the bidding war and determine who wins"""
        free_agent = war.free_agent
        all_offers = []

        for round_obj in war.rounds:
            all_offers.extend(round_obj.offers)

        if not all_offers:
            war.active = False
            war.outcome_message = "No offers were made."
            return {'winner': None, 'reason': 'No offers'}

        # Group by promoter, keep highest offer
        best_by_promoter = {}
        for offer in all_offers:
            pid = offer['promotion_id']
            if pid not in best_by_promoter or offer['salary'] > best_by_promoter[pid]['salary']:
                best_by_promoter[pid] = offer

        player_best = best_by_promoter.get('player', {}).get('salary', 0)
        rival_offers = {pid: o for pid, o in best_by_promoter.items() if pid != 'player'}
        rival_best = max((o['salary'] for o in rival_offers.values()), default=0)

        # Wrestler decision factors
        asking = free_agent.demands.asking_salary
        minimum = free_agent.demands.minimum_salary

        # Can player's offer satisfy the wrestler?
        player_satisfies = player_final_offer is not None and player_final_offer >= minimum

        if not player_satisfies and rival_best < minimum:
            # Nobody met minimum
            war.active = False
            war.outcome_message = f"{free_agent.wrestler_name} rejected all offers — demands too high."
            self._complete_bidding_war(war, winner=None)
            return {
                'winner': None,
                'reason': 'demands_not_met',
                'message': war.outcome_message
            }

        # Compare player vs rivals
        if player_final_offer is not None and player_final_offer >= minimum:
            # Wrestler considers all factors (prestige, creative, etc.)
            # Money is primary but not everything
            salary_gap = rival_best - player_final_offer

            # Base chance player wins = salary-based
            if player_final_offer >= rival_best:
                player_win_chance = 0.75  # We have the better offer
            elif salary_gap <= 1000:
                player_win_chance = 0.60  # Very close
            elif salary_gap <= 3000:
                player_win_chance = 0.45
            elif salary_gap <= 7000:
                player_win_chance = 0.30
            else:
                player_win_chance = 0.15  # Rival much higher

            # Mood modifier
            mood_val = free_agent.mood.value if hasattr(free_agent.mood, 'value') else str(free_agent.mood)
            if mood_val == 'desperate':
                player_win_chance += 0.15  # Desperate = takes first good offer
            elif mood_val == 'arrogant':
                player_win_chance -= 0.10  # Arrogant = holds out for best deal

            if random.random() < player_win_chance:
                war.active = False
                war.winner_promotion_id = 'player'
                war.final_salary = player_final_offer
                war.outcome_message = f"{free_agent.wrestler_name} chose Ring of Champions!"
                self._complete_bidding_war(war, winner='player', current_year=current_year, current_week=current_week)

                # STEP 132: Relationship effects
                self._apply_post_bidding_effects(war, winner='player')

                return {
                    'winner': 'player',
                    'final_salary': player_final_offer,
                    'message': war.outcome_message,
                    'rival_best': rival_best
                }

        # Rival wins
        winning_rival = max(rival_offers.values(), key=lambda o: o['salary']) if rival_offers else None

        if winning_rival:
            winner_name = winning_rival['promotion_name']
            winner_salary = winning_rival['salary']
            war.active = False
            war.winner_promotion_id = winning_rival['promotion_id']
            war.final_salary = winner_salary
            war.outcome_message = f"{free_agent.wrestler_name} signed with {winner_name} for ${winner_salary:,}/show."

            self._complete_bidding_war(war, winner=winning_rival['promotion_id'], current_year=current_year, current_week=current_week)
            self._apply_post_bidding_effects(war, winner=winning_rival['promotion_id'])

            return {
                'winner': winning_rival['promotion_id'],
                'winner_name': winner_name,
                'final_salary': winner_salary,
                'message': war.outcome_message,
                'player_offer': player_final_offer
            }

        war.active = False
        war.outcome_message = "Bidding war ended inconclusively."
        return {'winner': None, 'reason': 'inconclusive'}

    def _complete_bidding_war(
        self,
        war: BiddingWar,
        winner: Optional[str],
        current_year: int = 1,
        current_week: int = 1
    ) -> None:
        """Archive completed bidding war"""
        war_dict = war.to_dict()
        war_dict['resolved_year'] = current_year
        war_dict['resolved_week'] = current_week
        self.completed_bidding_wars.append(war_dict)

        fa_id = war.free_agent.id
        if fa_id in self.active_bidding_wars:
            del self.active_bidding_wars[fa_id]

    # =========================================================
    # STEP 128: Blind vs Open Bidding
    # =========================================================

    def _determine_bidding_type(self, free_agent: FreeAgent) -> bool:
        """
        STEP 128: Determine if bidding is open (leaked) or blind.

        Open bidding = promotions know each other's offers.
        Happens when wrestler or their agent leaks information.
        """
        # Agent with high publicity-seeking leaks info
        if hasattr(free_agent.agent, 'agent_type') and free_agent.agent.agent_type.value != 'none':
            if random.random() < 0.35:  # 35% chance agent leaks
                return True

        # Major superstars attract media attention
        if free_agent.is_major_superstar and random.random() < 0.25:
            return True

        # High popularity = media scrutiny
        if free_agent.popularity >= 75 and random.random() < 0.20:
            return True

        return False  # Default: blind bidding

    # =========================================================
    # STEP 129: Bidding Escalation Events
    # =========================================================

    def _check_escalation_events(
        self,
        war: BiddingWar,
        free_agent: FreeAgent,
        current_year: int,
        current_week: int
    ) -> Optional[Dict[str, Any]]:
        """
        STEP 129: Check for and generate mid-negotiation escalation events.

        These shake up the bidding war unpredictably.
        """
        # Only trigger on round 2+
        if war.current_round < 1:
            return None

        # ~30% chance of event per round
        if random.random() > 0.30:
            return None

        events = [
            self._event_rival_dramatic_increase,
            self._event_wrestler_demands_increase,
            self._event_promotion_drops_out,
            self._event_injury_revelation,
            self._event_controversy_emerges
        ]

        # Weight events by likelihood
        weights = [0.30, 0.25, 0.20, 0.15, 0.10]

        event_fn = random.choices(events, weights=weights, k=1)[0]
        return event_fn(war, free_agent, current_year, current_week)

    def _event_rival_dramatic_increase(self, war, free_agent, year, week) -> Dict:
        boost_pct = random.uniform(0.15, 0.35)
        current_high = war.get_current_highest_offer()
        new_high = int(current_high * (1 + boost_pct))

        # Apply to a random rival
        if free_agent.rival_interest:
            rival = random.choice(free_agent.rival_interest)
            rival.offer_salary = new_high
            rival.offer_made = True

        return {
            'type': 'rival_dramatic_increase',
            'title': '💰 RIVAL MAKES DRAMATIC MOVE',
            'description': f'A competing promotion has dramatically increased their offer by {int(boost_pct*100)}%!',
            'effect': f'New rival offer: ${new_high:,}/show',
            'impact': 'negative',
            'new_value': new_high
        }

    def _event_wrestler_demands_increase(self, war, free_agent, year, week) -> Dict:
        increase_pct = random.uniform(0.10, 0.20)
        old_asking = free_agent.demands.asking_salary
        new_asking = int(old_asking * (1 + increase_pct))
        free_agent.demands.asking_salary = new_asking
        free_agent.demands.minimum_salary = int(new_asking * 0.75)

        return {
            'type': 'wrestler_demands_increase',
            'title': '📈 DEMANDS HAVE INCREASED',
            'description': f"{free_agent.wrestler_name}'s camp has increased their asking price.",
            'effect': f'New asking salary: ${new_asking:,}/show (was ${old_asking:,})',
            'impact': 'negative',
            'new_value': new_asking
        }

    def _event_promotion_drops_out(self, war, free_agent, year, week) -> Dict:
        if len(free_agent.rival_interest) <= 1:
            return self._event_wrestler_demands_increase(war, free_agent, year, week)

        dropped = random.choice(free_agent.rival_interest)
        dropped.interest_level = 0
        dropped.offer_made = False

        return {
            'type': 'promotion_drops_out',
            'title': '🚪 RIVAL PROMOTION WITHDRAWS',
            'description': f'{dropped.promotion_name} has withdrawn from negotiations.',
            'effect': 'One less bidder in the war',
            'impact': 'positive',
            'promotion_dropped': dropped.promotion_name
        }

    def _event_injury_revelation(self, war, free_agent, year, week) -> Dict:
        # Reduce all rival offers by 10-20%
        reduction = random.uniform(0.10, 0.20)
        for rival in free_agent.rival_interest:
            if rival.offer_salary > 0:
                rival.offer_salary = int(rival.offer_salary * (1 - reduction))

        old_value = free_agent.market_value
        free_agent.market_value = int(old_value * (1 - reduction))

        return {
            'type': 'injury_revelation',
            'title': '🏥 INJURY HISTORY REVEALED',
            'description': f'Medical reports show {free_agent.wrestler_name} has concerning injury history.',
            'effect': f'Market value decreased {int(reduction*100)}% — rival offers reduced',
            'impact': 'positive',
            'value_change': free_agent.market_value - old_value
        }

    def _event_controversy_emerges(self, war, free_agent, year, week) -> Dict:
        # Major rivals drop out
        dropped = []
        for rival in free_agent.rival_interest:
            if rival.interest_level >= 60 and random.random() < 0.5:
                rival.interest_level = max(0, rival.interest_level - 40)
                dropped.append(rival.promotion_name)

        return {
            'type': 'controversy_emerges',
            'title': '⚠️ CONTROVERSY SURFACES',
            'description': f'Backstage concerns about {free_agent.wrestler_name} have become public.',
            'effect': f'{len(dropped)} promotions reduced interest significantly' if dropped else 'Minor impact on negotiations',
            'impact': 'positive',
            'promotions_affected': dropped
        }

    # =========================================================
    # STEP 130: Outbid Notifications
    # =========================================================

    def _check_outbid(
        self,
        war: BiddingWar,
        player_offer: Optional[int],
        round_obj: BiddingRound,
        current_year: int,
        current_week: int
    ) -> Optional[Dict[str, Any]]:
        """
        STEP 130: Generate outbid notification if rival exceeds player offer.
        """
        if player_offer is None:
            return None

        rival_offers = [o for o in round_obj.offers if not o.get('is_player')]
        if not rival_offers:
            return None

        highest_rival = max(rival_offers, key=lambda o: o['salary'])
        highest_salary = highest_rival['salary']

        if highest_salary <= player_offer:
            return None  # Player is winning

        gap = highest_salary - player_offer
        deadline_week = current_week + 2  # 48 hours = ~2 weeks in game time

        notification = {
            'type': 'outbid',
            'title': '🚨 YOU HAVE BEEN OUTBID',
            'rival_promotion': highest_rival['promotion_name'],
            'rival_offer': highest_salary,
            'your_offer': player_offer,
            'gap': gap,
            'free_agent_name': war.free_agent.wrestler_name,
            'free_agent_id': war.free_agent.id,
            'deadline_year': current_year,
            'deadline_week': deadline_week,
            'message': (
                f"ALERT: {highest_rival['promotion_name']} has offered "
                f"{war.free_agent.wrestler_name} ${highest_salary:,}/show — "
                f"${gap:,} more than your current offer. "
                f"They're giving you until Week {deadline_week} to respond before accepting their deal."
            )
        }

        self.outbid_notifications.append(notification)
        return notification

    def get_pending_outbid_notifications(self, current_year: int, current_week: int) -> List[Dict]:
        """STEP 130: Get all pending outbid notifications"""
        active = []
        for n in self.outbid_notifications:
            if (n['deadline_year'] > current_year or
                (n['deadline_year'] == current_year and n['deadline_week'] >= current_week)):
                active.append(n)
        return active

    def dismiss_outbid_notification(self, free_agent_id: str) -> bool:
        """Dismiss outbid notification for a specific free agent"""
        before = len(self.outbid_notifications)
        self.outbid_notifications = [
            n for n in self.outbid_notifications
            if n.get('free_agent_id') != free_agent_id
        ]
        return len(self.outbid_notifications) < before

    # =========================================================
    # STEP 131: Strategic Bidding Decisions
    # =========================================================

    def get_strategic_options(
        self,
        free_agent: FreeAgent,
        current_player_offer: Optional[int],
        current_year: int,
        current_week: int
    ) -> Dict[str, Any]:
        """
        STEP 131: Return available strategic options during a bidding war.

        Options:
        - match_offer: Match the rival's highest offer exactly
        - exceed_offer: Exceed by 10-15%
        - sweeten_non_monetary: Add creative perks instead of more money
        - hold_firm: Don't change offer
        - withdraw: Pull out of the bidding war
        - request_meeting: Attempt personal pitch to improve chances
        """
        war = self.active_bidding_wars.get(free_agent.id)
        highest_rival = free_agent.highest_rival_offer

        options = []

        # Match offer
        if highest_rival > 0:
            options.append({
                'action': 'match_offer',
                'label': '⚖️ Match Rival Offer',
                'cost': highest_rival,
                'description': f'Offer ${highest_rival:,}/show to match the top competing bid.',
                'success_boost': '+10% acceptance chance',
                'risk': 'Low — evens the playing field'
            })

        # Exceed offer
        exceed_amount = int(highest_rival * 1.12) if highest_rival > 0 else (
            int((current_player_offer or free_agent.demands.asking_salary) * 1.12)
        )
        options.append({
            'action': 'exceed_offer',
            'label': '💰 Exceed Top Offer',
            'cost': exceed_amount,
            'description': f'Offer ${exceed_amount:,}/show — 12% above the current top bid.',
            'success_boost': '+25% acceptance chance',
            'risk': 'Medium — costs more but sends strong signal'
        })

        # Sweeten with non-monetary perks
        options.append({
            'action': 'sweeten_non_monetary',
            'label': '🎁 Sweeten With Perks',
            'cost': current_player_offer or 0,
            'description': 'Keep same salary but add creative control, title shot promise, or schedule flexibility.',
            'success_boost': '+15% acceptance (if aligned with wrestler priorities)',
            'risk': 'Low cost, but only works if money isn\'t their top priority'
        })

        # Hold firm
        options.append({
            'action': 'hold_firm',
            'label': '🛑 Hold Firm',
            'cost': current_player_offer or 0,
            'description': 'Do not change your offer. Bet that the wrestler values your promotion over money.',
            'success_boost': 'No bonus — depends entirely on current offer quality',
            'risk': 'High if rival offer is significantly better'
        })

        # Request meeting
        options.append({
            'action': 'request_meeting',
            'label': '🤝 Personal Pitch',
            'cost': 0,
            'description': 'Request a direct meeting to personally pitch your promotion. Uses relationship capital.',
            'success_boost': '+10-20% based on promotion prestige and wrestler compatibility',
            'risk': 'Low — costs nothing but may be declined'
        })

        # Withdraw
        options.append({
            'action': 'withdraw',
            'label': '🚪 Withdraw',
            'cost': 0,
            'description': 'Pull out of the bidding war entirely.',
            'success_boost': 'N/A — saves budget for other targets',
            'risk': 'Lose the wrestler entirely'
        })

        return {
            'free_agent_id': free_agent.id,
            'free_agent_name': free_agent.wrestler_name,
            'current_player_offer': current_player_offer,
            'highest_rival_offer': highest_rival,
            'wrestler_asking': free_agent.demands.asking_salary,
            'wrestler_minimum': free_agent.demands.minimum_salary,
            'options': options
        }

    def apply_strategic_decision(
        self,
        free_agent: FreeAgent,
        action: str,
        player_offer: Optional[int],
        non_monetary_perks: Optional[Dict] = None,
        current_year: int = 1,
        current_week: int = 1
    ) -> Dict[str, Any]:
        """
        STEP 131: Apply a strategic decision and return the result.
        """
        war = self.active_bidding_wars.get(free_agent.id)

        if action == 'withdraw':
            if war:
                war.active = False
                war.outcome_message = "Ring of Champions withdrew from negotiations."
                self._complete_bidding_war(war, winner=None, current_year=current_year, current_week=current_week)
                # Mark rival as likely winner
                self._apply_post_bidding_effects(war, winner='rival_winner')
            return {
                'action': 'withdraw',
                'success': True,
                'message': f'You withdrew from bidding for {free_agent.wrestler_name}.',
                'effect': 'Budget preserved for other targets.'
            }

        if action == 'match_offer':
            rival_high = free_agent.highest_rival_offer
            return {
                'action': 'match_offer',
                'new_offer': rival_high,
                'message': f'You matched the rival offer of ${rival_high:,}/show.',
                'note': 'Advance the bidding round with this offer.'
            }

        if action == 'exceed_offer':
            rival_high = free_agent.highest_rival_offer
            new_offer = int(rival_high * 1.12)
            return {
                'action': 'exceed_offer',
                'new_offer': new_offer,
                'message': f'You exceeded rivals with ${new_offer:,}/show.',
                'note': 'Strong signal of commitment. Advance the bidding round.'
            }

        if action == 'sweeten_non_monetary':
            perks_applied = []
            if non_monetary_perks:
                if non_monetary_perks.get('title_promise'):
                    perks_applied.append('Title shot promise within 6 months')
                if non_monetary_perks.get('creative_control'):
                    perks_applied.append('Creative consultation rights')
                if non_monetary_perks.get('schedule_flexibility'):
                    perks_applied.append('Flexible schedule (max 150 shows/year)')
            return {
                'action': 'sweeten_non_monetary',
                'perks': perks_applied,
                'message': f'Non-monetary offer enhanced for {free_agent.wrestler_name}.',
                'note': 'Advance the bidding round with same salary + perks.'
            }

        if action == 'hold_firm':
            return {
                'action': 'hold_firm',
                'current_offer': player_offer,
                'message': 'You held your position. Advancing to next round unchanged.',
                'note': 'Risky if rivals are significantly higher.'
            }

        if action == 'request_meeting':
            # Meeting gives a flat boost to player's acceptance chance
            meeting_boost = random.randint(10, 20)
            return {
                'action': 'request_meeting',
                'bonus': meeting_boost,
                'message': f'{free_agent.wrestler_name} agreed to a sit-down meeting.',
                'note': f'Your promotion will receive a +{meeting_boost}% acceptance bonus in the final round.'
            }

        return {'error': f'Unknown action: {action}'}

    # =========================================================
    # STEP 132: Post-Bidding Relationship Effects
    # =========================================================

    def _apply_post_bidding_effects(
        self,
        war: BiddingWar,
        winner: Optional[str]
    ) -> None:
        """
        STEP 132: Apply relationship effects after a bidding war resolves.

        - Losing: Can damage relationships with the wrestler for future
        - Winning: Boosts relationship with signed wrestler
        - Beating rivals: Creates competitive rivalry
        - Overpaying: Sets precedent affecting future negotiations
        """
        free_agent = war.free_agent
        final_salary = war.final_salary or 0

        if winner == 'player':
            # Player won: positive notes
            rival_count = len(war.get_all_participants()) - 1

            if rival_count >= 2:
                # Won a competitive war
                free_agent.update_reputation(5, "Signed with winning promotion in competitive market")

            # Check for overpay
            asking = free_agent.demands.asking_salary
            if final_salary > asking * 1.2:
                # Overpaid — sets precedent
                free_agent.backstage_reputation = min(100, free_agent.backstage_reputation + 3)

            # Update rival promotion stats
            for rival_id in war.get_all_participants():
                if rival_id == 'player':
                    continue
                promotion = self.get_promotion_by_id(rival_id)
                if promotion:
                    promotion.lost_bidding_wars += 1
                    promotion.relationship_with_player = max(0, promotion.relationship_with_player - 5)

        elif winner and winner != 'player':
            # Rival won: player lost
            winning_promo = self.get_promotion_by_id(winner)
            if winning_promo:
                winning_promo.won_bidding_wars += 1
                winning_promo.signed_this_year += 1
                winning_promo.roster_size += 1
                winning_promo.remaining_budget = max(
                    0, winning_promo.remaining_budget - (final_salary * 52 * 3)
                )

            # Free agent who rejected you: slight reputation note
            free_agent.update_reputation(-2, "Chose rival promotion over Ring of Champions")

    # =========================================================
    # Utilities
    # =========================================================

    def _get_promotion_by_name(self, name: str) -> Optional[RivalPromotion]:
        """Find promotion by name"""
        for p in self.rival_promotions:
            if p.name == name:
                return p
        return None

    def get_all_outbid_notifications(self) -> List[Dict]:
        """STEP 130: Get all outbid notifications"""
        return self.outbid_notifications

    def clear_resolved_wars(self) -> int:
        """Remove completed bidding wars from active tracking"""
        before = len(self.active_bidding_wars)
        self.active_bidding_wars = {
            fa_id: war
            for fa_id, war in self.active_bidding_wars.items()
            if war.active
        }
        return before - len(self.active_bidding_wars)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rival_promotions': [p.to_dict() for p in self.rival_promotions],
            'active_bidding_wars': {
                fa_id: war.to_dict()
                for fa_id, war in self.active_bidding_wars.items()
            },
            'completed_bidding_wars_count': len(self.completed_bidding_wars),
            'outbid_notifications_count': len(self.outbid_notifications)
        }


# Global singleton
rival_interest_engine = RivalInterestEngine()