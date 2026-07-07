"""
Controversy Case System — Steps 191-197

Step 191: Controversy Case Identification
Step 192: Risk-Reward Assessment Framework
Step 193: Redemption Arc Potential Calculation
Step 194: Sponsor / Partner Considerations
Step 195: Locker Room Reaction Assessment
Step 196: Probationary Contract Structure
Step 197: Rehabilitation Support System
"""

import random
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


# ============================================================================
# STEP 191: Controversy Type Classification
# ============================================================================

class ControversyType(Enum):
    BEHAVIORAL_INCIDENT  = "behavioral_incident"
    SUBSTANCE_ABUSE      = "substance_abuse"
    SOCIAL_MEDIA_SCANDAL = "social_media_scandal"
    LEGAL_TROUBLE        = "legal_trouble"
    LOCKER_ROOM_ISSUE    = "locker_room_issue"
    PERFORMANCE_DECLINE  = "performance_decline"
    CONTRACT_DISPUTE     = "contract_dispute"
    WELLNESS_VIOLATION   = "wellness_violation"
    FINANCIAL_MISCONDUCT = "financial_misconduct"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def base_severity_range(self):
        ranges = {
            "behavioral_incident":   (20, 60),
            "substance_abuse":       (40, 90),
            "social_media_scandal":  (15, 65),
            "legal_trouble":         (50, 100),
            "locker_room_issue":     (20, 55),
            "performance_decline":   (10, 40),
            "contract_dispute":      (15, 50),
            "wellness_violation":    (45, 85),
            "financial_misconduct":  (55, 95),
        }
        return ranges.get(self.value, (20, 60))

    @property
    def sponsor_impact(self) -> str:
        high = {"legal_trouble", "substance_abuse", "wellness_violation", "financial_misconduct"}
        med  = {"social_media_scandal", "behavioral_incident"}
        if self.value in high: return "high"
        if self.value in med:  return "medium"
        return "low"

    @property
    def media_scrutiny(self) -> str:
        high = {"legal_trouble", "social_media_scandal", "wellness_violation"}
        return "high" if self.value in high else "moderate"

    @property
    def locker_room_concern(self) -> str:
        personal = {"behavioral_incident", "locker_room_issue", "financial_misconduct"}
        return "high" if self.value in personal else "moderate"

    @property
    def description(self) -> str:
        descs = {
            "behavioral_incident":   "Unprofessional conduct or locker room altercation",
            "substance_abuse":       "Substance abuse issue requiring treatment",
            "social_media_scandal":  "Controversial public statements or social media incident",
            "legal_trouble":         "Legal proceedings (arrest, lawsuit, or civil matter)",
            "locker_room_issue":     "Refusing to cooperate with creative or fellow talent",
            "performance_decline":   "Attitude problems or lack of effort in recent performances",
            "contract_dispute":      "Public dispute over contract terms or promotion",
            "wellness_violation":    "Failed a wellness policy test",
            "financial_misconduct":  "Alleged financial fraud or misconduct",
        }
        return descs.get(self.value, "Unknown controversy")


# ============================================================================
# STEP 192: Risk-Reward Assessment
# ============================================================================

@dataclass
class RiskRewardAssessment:
    talent_level: int            = 60
    peak_popularity: int         = 50
    remaining_career_years: int  = 5
    controversy_severity: int         = 50
    time_since_incident_weeks: int    = 0
    rehabilitation_evidence: int      = 0
    support_systems_in_place: bool    = False
    media_scrutiny_level: str         = "moderate"
    sponsor_risk_score: int           = 50
    locker_room_readiness: int        = 50

    def overall_risk_score(self) -> int:
        base = float(self.controversy_severity)
        time_reduction = max(0.0, (self.time_since_incident_weeks - 26) * 0.4)
        base = max(0.0, base - time_reduction)
        base = max(0.0, base - self.rehabilitation_evidence * 0.35)
        if self.support_systems_in_place:
            base = max(0.0, base - 10.0)
        scrutiny_map = {"low": -5, "moderate": 0, "high": 15}
        base += scrutiny_map.get(self.media_scrutiny_level, 0)
        return max(0, min(100, int(base)))

    def overall_reward_score(self) -> int:
        reward = int(
            self.talent_level * 0.50 +
            self.peak_popularity * 0.30 +
            min(10, self.remaining_career_years) * 2
        )
        return max(0, min(100, reward))

    def risk_label(self) -> str:
        r = self.overall_risk_score()
        if r >= 75: return "Very High"
        if r >= 55: return "High"
        if r >= 35: return "Moderate"
        if r >= 15: return "Low"
        return "Minimal"

    def reward_label(self) -> str:
        r = self.overall_reward_score()
        if r >= 75: return "Exceptional"
        if r >= 55: return "High"
        if r >= 35: return "Moderate"
        return "Low"

    def recommendation(self) -> str:
        risk   = self.overall_risk_score()
        reward = self.overall_reward_score()
        ratio  = reward / max(risk, 1)
        if risk <= 20:
            return "Low risk — the controversy is minor or fading. Sign them."
        if risk >= 80:
            return "Very high risk. Only consider with a strict probationary deal and full rehab support."
        if ratio >= 1.8:
            return "Risky but the talent justifies it. Use a short probationary contract with behaviour clauses."
        if ratio >= 1.2:
            return "Borderline. Gauge locker room reaction first and require a public statement."
        return "Risk outweighs reward. Pass unless circumstances change significantly."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "talent_level": self.talent_level,
            "peak_popularity": self.peak_popularity,
            "remaining_career_years": self.remaining_career_years,
            "controversy_severity": self.controversy_severity,
            "time_since_incident_weeks": self.time_since_incident_weeks,
            "rehabilitation_evidence": self.rehabilitation_evidence,
            "support_systems_in_place": self.support_systems_in_place,
            "media_scrutiny_level": self.media_scrutiny_level,
            "sponsor_risk_score": self.sponsor_risk_score,
            "locker_room_readiness": self.locker_room_readiness,
            "overall_risk_score": self.overall_risk_score(),
            "overall_reward_score": self.overall_reward_score(),
            "risk_label": self.risk_label(),
            "reward_label": self.reward_label(),
            "recommendation": self.recommendation(),
        }


# ============================================================================
# STEP 193: Redemption Arc Potential
# ============================================================================

class RedemptionPotential(Enum):
    NONE        = "none"
    LOW         = "low"
    MODERATE    = "moderate"
    HIGH        = "high"
    EXCEPTIONAL = "exceptional"

    @property
    def booking_bonus(self) -> int:
        return {"none": 0, "low": 5, "moderate": 15, "high": 25, "exceptional": 40}[self.value]

    @property
    def label(self) -> str:
        return self.value.title()

    @property
    def description(self) -> str:
        descs = {
            "none":        "No compelling story angle — signing is purely a business calculation.",
            "low":         "Minor arc possible but unlikely to resonate with fans.",
            "moderate":    "Solid redemption story if booked correctly and given time.",
            "high":        "Classic redemption arc — fans will buy into this if the storytelling is good.",
            "exceptional": "Career-defining comeback story. This could be the angle of the year.",
        }
        return descs[self.value]


def assess_redemption_potential(
    controversy_type: ControversyType,
    severity: int,
    popularity: int,
    years_in_business: int,
    time_since_incident_weeks: int,
) -> RedemptionPotential:
    score = 0
    if popularity >= 75: score += 30
    elif popularity >= 55: score += 15
    elif popularity >= 35: score += 5
    if years_in_business >= 12: score += 20
    elif years_in_business >= 6: score += 10
    if 26 <= time_since_incident_weeks <= 104:
        score += 20
    elif time_since_incident_weeks > 104:
        score += 5
    elif time_since_incident_weeks >= 13:
        score += 10
    good_arc_types = {
        ControversyType.SUBSTANCE_ABUSE,
        ControversyType.WELLNESS_VIOLATION,
        ControversyType.BEHAVIORAL_INCIDENT,
        ControversyType.PERFORMANCE_DECLINE,
    }
    if controversy_type in good_arc_types:
        score += 15
    if severity >= 85: score -= 30
    elif severity >= 70: score -= 20
    elif severity >= 55: score -= 10
    if score >= 65: return RedemptionPotential.EXCEPTIONAL
    if score >= 50: return RedemptionPotential.HIGH
    if score >= 30: return RedemptionPotential.MODERATE
    if score >= 10: return RedemptionPotential.LOW
    return RedemptionPotential.NONE


# ============================================================================
# STEP 194: Sponsor and Partner Considerations
# ============================================================================

SPONSOR_POOL = [
    "ActionWear Apparel", "PowerDrink Energy", "FightZone Gaming",
    "RingGear Equipment", "ChampionBet Sports", "MaxFit Nutrition",
    "IronCrest Insurance", "SkyView Media",
]


@dataclass
class SponsorImpactReport:
    affected_sponsors:          List[str] = field(default_factory=list)
    at_risk_revenue_estimate:   int       = 0
    tv_network_concern:         bool      = False
    arena_morality_clause_risk: bool      = False
    recommended_actions:        List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "affected_sponsors":           self.affected_sponsors,
            "at_risk_revenue_estimate":    self.at_risk_revenue_estimate,
            "tv_network_concern":          self.tv_network_concern,
            "arena_morality_clause_risk":  self.arena_morality_clause_risk,
            "recommended_actions":         self.recommended_actions,
        }

    @staticmethod
    def generate(controversy_type: ControversyType, severity: int) -> "SponsorImpactReport":
        report = SponsorImpactReport()
        if severity >= 60 or controversy_type.sponsor_impact == "high":
            k = random.randint(2, min(4, len(SPONSOR_POOL)))
            report.affected_sponsors          = random.sample(SPONSOR_POOL, k=k)
            report.at_risk_revenue_estimate   = random.randint(75_000, 300_000)
            report.tv_network_concern         = severity >= 65
            report.arena_morality_clause_risk = severity >= 72
            report.recommended_actions = [
                "Issue a joint statement with the talent before any debut announcement.",
                "Keep the initial return low-key — avoid marquee PPV debut.",
                "Review all active sponsor contracts for morality clause exposure.",
                "Brief your TV network partner before the announcement goes public.",
            ]
        elif controversy_type.sponsor_impact == "medium":
            report.affected_sponsors        = random.sample(SPONSOR_POOL, k=1)
            report.at_risk_revenue_estimate = random.randint(10_000, 60_000)
            report.recommended_actions = [
                "Brief key sponsors ahead of the signing announcement.",
                "Prepare a holding statement in case media questions arise.",
            ]
        else:
            report.recommended_actions = [
                "Minimal sponsor concern — standard announcement process is fine."
            ]
        return report


# ============================================================================
# STEP 195: Locker Room Reaction
# ============================================================================

class LockerRoomReaction(Enum):
    SUPPORTIVE = "supportive"
    MIXED      = "mixed"
    RESISTANT  = "resistant"
    HOSTILE    = "hostile"

    @property
    def morale_impact(self) -> int:
        return {"supportive": 5, "mixed": -3, "resistant": -10, "hostile": -20}[self.value]

    @property
    def label(self) -> str:
        return self.value.title()

    @property
    def guidance(self) -> str:
        msgs = {
            "supportive": "The locker room is largely open to giving them another chance.",
            "mixed":      "Opinion is divided. A respected veteran vouching for them would help.",
            "resistant":  "Several key roster members have concerns. Address these before signing.",
            "hostile":    "The locker room is united in opposition. Signing risks significant morale damage.",
        }
        return msgs[self.value]


def assess_locker_room_reaction(
    controversy_type: ControversyType,
    severity: int,
    time_since_incident_weeks: int,
    roster_morale_avg: int = 60,
) -> LockerRoomReaction:
    concern = float(severity)
    if controversy_type.locker_room_concern == "high":
        concern += 18
    concern -= min(30.0, time_since_incident_weeks / 3.5)
    if roster_morale_avg < 40:
        concern += 15
    elif roster_morale_avg < 55:
        concern += 5
    concern = max(0.0, min(100.0, concern))
    if concern >= 72: return LockerRoomReaction.HOSTILE
    if concern >= 52: return LockerRoomReaction.RESISTANT
    if concern >= 28: return LockerRoomReaction.MIXED
    return LockerRoomReaction.SUPPORTIVE


# ============================================================================
# STEP 196: Probationary Contract
# ============================================================================

@dataclass
class ProbationaryContract:
    salary_per_show:              int  = 5000
    contract_length_weeks:        int  = 26
    immediate_release_clause:     bool = True
    behaviour_clause:             bool = True
    public_apology_required:      bool = False
    counseling_mandated:          bool = False
    social_media_monitoring:      bool = False
    max_strikes_before_release:   int  = 2
    current_strikes:              int  = 0
    probation_period_weeks:       int  = 13
    performance_review_week:      int  = 13
    pathway_to_standard_contract: bool = True

    def is_terminated(self) -> bool:
        return self.current_strikes >= self.max_strikes_before_release

    def strikes_remaining(self) -> int:
        return max(0, self.max_strikes_before_release - self.current_strikes)

    def issue_strike(self, reason: str) -> Dict[str, Any]:
        self.current_strikes += 1
        terminated = self.is_terminated()
        return {
            "strike_number": self.current_strikes,
            "max_strikes":   self.max_strikes_before_release,
            "reason":        reason,
            "terminated":    terminated,
            "message": (
                f"Strike {self.current_strikes}/{self.max_strikes_before_release}: {reason}. "
                + ("Contract immediately terminated per behaviour clause."
                   if terminated
                   else f"{self.strikes_remaining()} strike(s) remaining before termination.")
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "salary_per_show":             self.salary_per_show,
            "contract_length_weeks":       self.contract_length_weeks,
            "immediate_release_clause":    self.immediate_release_clause,
            "behaviour_clause":            self.behaviour_clause,
            "public_apology_required":     self.public_apology_required,
            "counseling_mandated":         self.counseling_mandated,
            "social_media_monitoring":     self.social_media_monitoring,
            "max_strikes_before_release":  self.max_strikes_before_release,
            "current_strikes":             self.current_strikes,
            "strikes_remaining":           self.strikes_remaining(),
            "probation_period_weeks":      self.probation_period_weeks,
            "performance_review_week":     self.performance_review_week,
            "pathway_to_standard_contract": self.pathway_to_standard_contract,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProbationaryContract":
        pc = ProbationaryContract()
        for k in ["salary_per_show", "contract_length_weeks", "immediate_release_clause",
                  "behaviour_clause", "public_apology_required", "counseling_mandated",
                  "social_media_monitoring", "max_strikes_before_release", "current_strikes",
                  "probation_period_weeks", "performance_review_week",
                  "pathway_to_standard_contract"]:
            if k in data:
                setattr(pc, k, data[k])
        return pc

    @staticmethod
    def generate_for_severity(severity: int, base_salary: int) -> "ProbationaryContract":
        pc = ProbationaryContract()
        discount = 0.20 if severity >= 70 else 0.12
        pc.salary_per_show            = int(base_salary * (1 - discount))
        pc.contract_length_weeks      = 13 if severity >= 80 else 26
        pc.public_apology_required    = severity >= 60
        pc.counseling_mandated        = severity >= 70
        pc.social_media_monitoring    = severity >= 55
        pc.max_strikes_before_release = 1 if severity >= 80 else 2
        return pc


# ============================================================================
# STEP 197: Rehabilitation Support System
# ============================================================================

@dataclass
class RehabilitationPlan:
    counseling_access:             bool           = False
    sobriety_support:              bool           = False
    mentor_assigned:               bool           = False
    mentor_wrestler_id:            Optional[str]  = None
    mentor_wrestler_name:          Optional[str]  = None
    reduced_schedule:              bool           = False
    clear_expectations_documented: bool           = True
    weekly_check_in:               bool           = False
    weeks_on_plan:                 int            = 0
    compliance_score:              int            = 100

    def plan_quality(self) -> int:
        score = 0
        if self.counseling_access:             score += 25
        if self.sobriety_support:              score += 20
        if self.mentor_assigned:               score += 20
        if self.reduced_schedule:              score += 10
        if self.clear_expectations_documented: score += 15
        if self.weekly_check_in:               score += 10
        return min(100, score)

    def severity_reduction_per_week(self) -> float:
        return round(0.5 + (self.plan_quality() / 100) * 1.5, 2)

    def advance_week(self, incident_occurred: bool = False) -> Dict[str, Any]:
        self.weeks_on_plan += 1
        severity_reduced = 0.0
        if incident_occurred:
            self.compliance_score = max(0, self.compliance_score - 25)
            msg = f"Incident during rehabilitation — compliance score dropped to {self.compliance_score}."
        else:
            severity_reduced = self.severity_reduction_per_week()
            msg = f"Week {self.weeks_on_plan} on plan. Severity reduced by {severity_reduced:.1f} pts."
        return {
            "weeks_on_plan":    self.weeks_on_plan,
            "severity_reduced": severity_reduced,
            "compliance_score": self.compliance_score,
            "plan_quality":     self.plan_quality(),
            "message":          msg,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "counseling_access":             self.counseling_access,
            "sobriety_support":              self.sobriety_support,
            "mentor_assigned":               self.mentor_assigned,
            "mentor_wrestler_id":            self.mentor_wrestler_id,
            "mentor_wrestler_name":          self.mentor_wrestler_name,
            "reduced_schedule":              self.reduced_schedule,
            "clear_expectations_documented": self.clear_expectations_documented,
            "weekly_check_in":               self.weekly_check_in,
            "weeks_on_plan":                 self.weeks_on_plan,
            "compliance_score":              self.compliance_score,
            "plan_quality":                  self.plan_quality(),
            "severity_reduction_per_week":   self.severity_reduction_per_week(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RehabilitationPlan":
        rp = RehabilitationPlan()
        for k in ["counseling_access", "sobriety_support", "mentor_assigned",
                  "mentor_wrestler_id", "mentor_wrestler_name", "reduced_schedule",
                  "clear_expectations_documented", "weekly_check_in",
                  "weeks_on_plan", "compliance_score"]:
            if k in data:
                setattr(rp, k, data[k])
        return rp


# ============================================================================
# Core ControversyCase — wraps all steps
# ============================================================================

@dataclass
class ControversyCase:
    controversy_type:          ControversyType             = ControversyType.BEHAVIORAL_INCIDENT
    severity:                  int                         = 40
    incident_description:      str                         = ""
    time_since_incident_weeks: int                         = 0
    is_public_knowledge:       bool                        = True
    assessment:                Optional[RiskRewardAssessment]  = None
    redemption_potential:      RedemptionPotential         = RedemptionPotential.NONE
    redemption_arc_active:     bool                        = False
    sponsor_impact:            Optional[SponsorImpactReport]   = None
    locker_room_reaction:      LockerRoomReaction          = LockerRoomReaction.MIXED
    probationary_contract:     Optional[ProbationaryContract]  = None
    rehabilitation_plan:       Optional[RehabilitationPlan]    = None

    def build_full_assessment(
        self,
        talent_level: int,
        popularity: int,
        years_experience: int,
        roster_morale_avg: int = 60,
    ) -> None:
        rehab_evidence = self.rehabilitation_plan.compliance_score if self.rehabilitation_plan else 0
        rehab_support  = self.rehabilitation_plan is not None

        self.assessment = RiskRewardAssessment(
            talent_level              = talent_level,
            peak_popularity           = popularity,
            remaining_career_years    = max(1, 45 - years_experience),
            controversy_severity      = self.severity,
            time_since_incident_weeks = self.time_since_incident_weeks,
            rehabilitation_evidence   = rehab_evidence,
            support_systems_in_place  = rehab_support,
            media_scrutiny_level      = self.controversy_type.media_scrutiny,
            sponsor_risk_score        = min(100, self.severity + 10),
            locker_room_readiness     = max(0, 100 - self.severity),
        )
        self.redemption_potential = assess_redemption_potential(
            self.controversy_type, self.severity, popularity,
            years_experience, self.time_since_incident_weeks,
        )
        self.sponsor_impact = SponsorImpactReport.generate(
            self.controversy_type, self.severity
        )
        self.locker_room_reaction = assess_locker_room_reaction(
            self.controversy_type, self.severity,
            self.time_since_incident_weeks, roster_morale_avg,
        )

    def advance_week(self) -> None:
        self.time_since_incident_weeks += 1
        if self.rehabilitation_plan:
            result        = self.rehabilitation_plan.advance_week()
            self.severity = max(0, self.severity - result["severity_reduced"])
        elif self.time_since_incident_weeks % 4 == 0:
            self.severity = max(0, self.severity - 1)

    def generate_probationary_contract(self, base_salary: int) -> ProbationaryContract:
        self.probationary_contract = ProbationaryContract.generate_for_severity(
            self.severity, base_salary
        )
        return self.probationary_contract

    def to_dict(self) -> Dict[str, Any]:
        return {
            "controversy_type":          self.controversy_type.value,
            "controversy_type_label":    self.controversy_type.label,
            "controversy_description":   self.controversy_type.description,
            "severity":                  self.severity,
            "incident_description":      self.incident_description,
            "time_since_incident_weeks": self.time_since_incident_weeks,
            "is_public_knowledge":       self.is_public_knowledge,
            "sponsor_impact_level":      self.controversy_type.sponsor_impact,
            "media_scrutiny_level":      self.controversy_type.media_scrutiny,
            "locker_room_concern":       self.controversy_type.locker_room_concern,
            "assessment":       self.assessment.to_dict() if self.assessment else None,
            "redemption_potential":       self.redemption_potential.value,
            "redemption_potential_label": self.redemption_potential.label,
            "redemption_description":     self.redemption_potential.description,
            "redemption_booking_bonus":   self.redemption_potential.booking_bonus,
            "redemption_arc_active":      self.redemption_arc_active,
            "sponsor_impact": self.sponsor_impact.to_dict() if self.sponsor_impact else None,
            "locker_room_reaction":       self.locker_room_reaction.value,
            "locker_room_reaction_label": self.locker_room_reaction.label,
            "locker_room_guidance":       self.locker_room_reaction.guidance,
            "locker_room_morale_impact":  self.locker_room_reaction.morale_impact,
            "probationary_contract": self.probationary_contract.to_dict() if self.probationary_contract else None,
            "rehabilitation_plan":   self.rehabilitation_plan.to_dict() if self.rehabilitation_plan else None,
        }

    @staticmethod
    def generate_for_free_agent(
        fa_dict: Dict[str, Any],
        roster_morale_avg: int = 60,
    ) -> "ControversyCase":
        raw_type = fa_dict.get("controversy_type", "behavioral_incident")
        try:
            ctype = ControversyType(raw_type)
        except ValueError:
            ctype = ControversyType.BEHAVIORAL_INCIDENT

        severity   = int(fa_dict.get("controversy_severity", 40))
        time_since = int(fa_dict.get("time_since_incident_weeks", 0))
        popularity = int(fa_dict.get("popularity", 50))
        years_exp  = int(fa_dict.get("years_experience", 5))
        talent     = int((
            fa_dict.get("brawling", 50) +
            fa_dict.get("technical", 50) +
            fa_dict.get("psychology", 50)
        ) / 3)

        case = ControversyCase(
            controversy_type          = ctype,
            severity                  = severity,
            time_since_incident_weeks = time_since,
            incident_description      = fa_dict.get("incident_description", ctype.description),
            is_public_knowledge       = bool(fa_dict.get("is_public_knowledge", True)),
        )
        case.build_full_assessment(talent, popularity, years_exp, roster_morale_avg)
        return case