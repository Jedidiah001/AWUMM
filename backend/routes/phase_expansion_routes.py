"""
Thin API routes for booking/story/media expansion features #64-72, #88-100,
and #126-137.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from services.booking_story_media_service import BookingStoryMediaService, ValidationError
from repositories.phase_expansion_repository import new_id


phase_expansion_bp = Blueprint("phase_expansion", __name__)


def get_database():
    return current_app.config["DATABASE"]


def get_universe():
    return current_app.config.get("UNIVERSE")


def get_service() -> BookingStoryMediaService:
    service = current_app.config.get("BOOKING_STORY_MEDIA_SERVICE")
    if service is None:
        service = BookingStoryMediaService(get_database())
        current_app.config["BOOKING_STORY_MEDIA_SERVICE"] = service
    return service


def ok(data=None, status=200, **extra):
    payload = {"success": True, "data": data}
    payload.update(extra)
    return jsonify(payload), status


def fail(message: str, status: int = 400, **extra):
    payload = {"success": False, "error": message}
    payload.update(extra)
    return jsonify(payload), status


def payload() -> dict:
    return request.get_json(silent=True) or {}


def with_calendar_defaults(data: dict) -> dict:
    merged = dict(data)
    try:
        state = get_database().get_game_state()
        merged.setdefault("year", state.get("current_year", 1))
        merged.setdefault("week", state.get("current_week", 1))
    except Exception:
        merged.setdefault("year", 1)
        merged.setdefault("week", 1)
    return merged


def handle(callable_):
    try:
        return ok(callable_())
    except ValidationError as exc:
        return fail(str(exc), 422)
    except Exception as exc:
        current_app.logger.exception("Phase expansion route failed")
        return fail(str(exc), 500)


@phase_expansion_bp.route("/api/phase-expansion/config", methods=["GET"])
def get_phase_config():
    return handle(lambda: get_service().get_config())


# ---------------------------------------------------------------------------
# Booking system enhancements
# ---------------------------------------------------------------------------


@phase_expansion_bp.route("/api/booking-enhancements/show-plan", methods=["POST"])
def save_show_plan():
    return handle(lambda: get_service().save_show_plan(payload(), get_universe()))


@phase_expansion_bp.route("/api/booking-enhancements/show-plan/<show_id>", methods=["GET"])
def get_show_plan(show_id):
    def _run():
        plan = get_service().repo.get_show_plan(show_id)
        if not plan:
            raise ValidationError("Show plan not found")
        return plan

    return handle(_run)


@phase_expansion_bp.route("/api/booking-enhancements/interference/project", methods=["POST"])
def project_interference():
    return handle(lambda: get_service().project_interference(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/booking-enhancements/interference", methods=["POST"])
def record_interference():
    return handle(lambda: get_service().record_interference(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/booking-enhancements/debut/vignette", methods=["POST"])
def schedule_debut_vignette():
    return handle(lambda: get_service().schedule_debut_vignette(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/booking-enhancements/debut", methods=["POST"])
def create_debut():
    return handle(lambda: get_service().create_debut(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/booking-enhancements/return/anticipation", methods=["POST"])
def schedule_return_anticipation():
    return handle(lambda: get_service().schedule_return_anticipation(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/booking-enhancements/return", methods=["POST"])
def create_return():
    return handle(lambda: get_service().create_return(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/booking-enhancements/commercial-break/project", methods=["POST"])
def project_commercial_break():
    def _run():
        data = payload()
        return get_service().calculate_commercial_break(
            data.get("show_id", "preview_show"),
            int(data.get("position_index", 1)),
            data,
        )

    return handle(_run)


@phase_expansion_bp.route("/api/booking-enhancements/themes", methods=["GET", "POST"])
def themes():
    service = get_service()
    if request.method == "GET":
        return handle(lambda: service.repo.list_theme_templates())

    def _create():
        data = payload()
        now = service.repo.now()
        row = {
            "id": data.get("id") or new_id("theme"),
            "name": data["name"],
            "category": data["category"],
            "description": data.get("description", ""),
            "requirements_json": service.repo.to_json(data.get("requirements", {})),
            "marketing_bonus": float(data.get("marketing_bonus", 0)),
            "ratings_bonus": float(data.get("ratings_bonus", 0)),
            "press_bonus": float(data.get("press_bonus", 0)),
            "created_by_user": 1,
            "created_at": now,
            "updated_at": now,
        }
        return service.repo.insert_simple("show_theme_templates", row)

    return handle(_create)


@phase_expansion_bp.route("/api/booking-enhancements/themes/apply", methods=["POST"])
def apply_theme():
    def _run():
        service = get_service()
        data = with_calendar_defaults(payload())
        theme = service.repo.get_theme_template(data["theme_id"])
        if not theme:
            raise ValidationError("Theme template not found")
        plan = service.repo.get_show_plan(data["show_id"]) or {}
        segments = plan.get("segments", [])
        requirements = theme.get("requirements_json") or {}
        score = 50.0
        title_pct = _pct(segments, lambda s: bool(s.get("title_id")))
        feud_pct = _pct(segments, lambda s: bool(s.get("feud_id")))
        stip_pct = _pct(segments, lambda s: bool((s.get("payload_json") or {}).get("stipulation") or (s.get("payload_json") or {}).get("special_match_type")))
        if requirements.get("minimum_title_matches_pct") and title_pct >= float(requirements["minimum_title_matches_pct"]):
            score += 20
        if requirements.get("minimum_feud_matches_pct") and feud_pct >= float(requirements["minimum_feud_matches_pct"]):
            score += 20
        if requirements.get("minimum_stipulation_matches_pct") and stip_pct >= float(requirements["minimum_stipulation_matches_pct"]):
            score += 20
        if requirements.get("minimum_tournament_matches_pct"):
            tournament_pct = _pct(segments, lambda s: "tournament" in (s.get("segment_type") or ""))
            if tournament_pct >= float(requirements["minimum_tournament_matches_pct"]):
                score += 20
        score = service.clamp(score)
        row = {
            "id": new_id("theme_application"),
            "show_id": data["show_id"],
            "theme_id": data["theme_id"],
            "execution_score": round(score, 2),
            "honored_requirements": 1 if score >= 70 else 0,
            "viewership_effect": round(float(theme.get("ratings_bonus", 0)) * (score / 100), 4),
            "social_effect": round(float(theme.get("marketing_bonus", 0)) * (score / 100), 2),
            "press_effect": round(float(theme.get("press_bonus", 0)) * (score / 100), 2),
            "assessment_json": service.repo.to_json({"title_pct": title_pct, "feud_pct": feud_pct, "stipulation_pct": stip_pct}),
            "year": int(data["year"]),
            "week": int(data["week"]),
        }
        return service.repo.insert_simple("show_theme_applications", row)

    return handle(_run)


def _pct(items, predicate) -> float:
    if not items:
        return 0.0
    return len([item for item in items if predicate(item)]) / len(items)


# ---------------------------------------------------------------------------
# Feuding, storylines, and booking integration
# ---------------------------------------------------------------------------


@phase_expansion_bp.route("/api/story-engine/dashboard", methods=["GET"])
def story_dashboard():
    return handle(lambda: get_service().story_dashboard())


@phase_expansion_bp.route("/api/story-arc-ai/dashboard", methods=["GET"])
def story_arc_ai_dashboard():
    return handle(lambda: get_service().story_arc_ai_dashboard())


@phase_expansion_bp.route("/api/story-arc-ai/weekly", methods=["POST"])
def story_arc_ai_weekly():
    def _run():
        data = with_calendar_defaults(payload())
        return get_service().run_story_arc_ai_week(
            int(data["year"]),
            int(data["week"]),
            data.get("seed"),
            auto=bool(data.get("auto", False)),
            force=bool(data.get("force", False)),
        )

    return handle(_run)


@phase_expansion_bp.route("/api/story-arc-ai/pulse", methods=["POST"])
def story_arc_ai_pulse():
    return handle(lambda: get_service().story_arc_ai_pulse(with_calendar_defaults(payload())))


@phase_expansion_bp.route("/api/story-arc-ai/reviews/<review_id>/decision", methods=["POST"])
def story_arc_ai_review_decision(review_id):
    return handle(lambda: get_service().decide_story_arc_review(review_id, payload()))


@phase_expansion_bp.route("/api/story-engine/feuds", methods=["GET", "POST"])
def story_feuds():
    service = get_service()
    if request.method == "GET":
        active_only = request.args.get("active_only", "false").lower() == "true"
        return handle(lambda: service.repo.list_story_feuds(active_only=active_only))
    return handle(lambda: service.create_story_feud(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/story-engine/feuds/<feud_id>/actions", methods=["POST"])
def add_story_action(feud_id):
    return handle(lambda: get_service().add_heat_action(feud_id, with_calendar_defaults(payload())))


@phase_expansion_bp.route("/api/story-engine/payoffs", methods=["POST"])
def create_payoff():
    return handle(lambda: get_service().create_payoff(payload()))


@phase_expansion_bp.route("/api/story-engine/swerves", methods=["POST"])
def create_swerve():
    return handle(lambda: get_service().create_swerve(with_calendar_defaults(payload())))


@phase_expansion_bp.route("/api/story-engine/promos", methods=["POST"])
def record_promo():
    return handle(lambda: get_service().record_promo(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/story-engine/backstage-segments", methods=["POST"])
def record_backstage_segment():
    return handle(lambda: get_service().record_backstage_segment(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/story-engine/arcs", methods=["POST"])
def create_story_arc():
    def _run():
        service = get_service()
        data = with_calendar_defaults(payload())
        row = {
            "id": new_id("arc"),
            "name": data["name"],
            "premise": data["premise"],
            "status": "active",
            "planned_duration_weeks": int(data.get("planned_duration_weeks", 12)),
            "start_year": int(data["year"]),
            "start_week": int(data["week"]),
            "cast_json": service.repo.to_json(data.get("cast", [])),
        }
        arc = service.repo.insert_simple("story_arcs", row)
        for index, chapter in enumerate(data.get("chapters", []), start=1):
            service.repo.insert_simple(
                "story_arc_chapters",
                {
                    "id": new_id("arc_chapter"),
                    "arc_id": arc["id"],
                    "chapter_name": chapter.get("chapter_name", f"Chapter {index}"),
                    "phase": chapter.get("phase", "build"),
                    "planned_start_week_offset": int(chapter.get("planned_start_week_offset", (index - 1) * 3)),
                    "planned_end_week_offset": int(chapter.get("planned_end_week_offset", index * 3)),
                    "planned_actions_json": service.repo.to_json(chapter.get("planned_actions", [])),
                    "status": "planned",
                },
            )
        return arc

    return handle(_run)


@phase_expansion_bp.route("/api/story-engine/short-programs", methods=["POST"])
def create_short_program():
    def _run():
        service = get_service()
        data = with_calendar_defaults(payload())
        participants = data.get("participants", [])
        participant_ids = [p.get("wrestler_id") or p.get("id") for p in participants if isinstance(p, dict)]
        for wrestler_id in participant_ids:
            existing = service.repo.fetch_one(
                """
                SELECT id FROM short_programs
                WHERE status = 'active' AND participants_json LIKE ? AND deleted_at IS NULL
                """,
                (f"%{wrestler_id}%",),
            )
            if existing:
                raise ValidationError(f"Wrestler {wrestler_id} is already in an active short program")
        return service.repo.insert_simple(
            "short_programs",
            {
                "id": new_id("short_program"),
                "name": data.get("name", "Short Program"),
                "status": "active",
                "phase": "setup",
                "participants_json": service.repo.to_json(participants),
                "designated_winner_id": data.get("designated_winner_id"),
                "start_year": int(data["year"]),
                "start_week": int(data["week"]),
                "target_end_year": data.get("target_end_year"),
                "target_end_week": data.get("target_end_week"),
            },
        )

    return handle(_run)


@phase_expansion_bp.route("/api/story-engine/authority-figures", methods=["POST"])
def create_authority_figure():
    def _run():
        service = get_service()
        data = payload()
        role = data.get("role", "general_manager")
        permissions = {
            "owner": ["make_matches", "fire_in_storyline", "override_gm", "career_decisions"],
            "general_manager": ["make_matches", "book_stipulations", "bar_from_ringside"],
            "commissioner": ["multi_show_oversight", "discipline", "title_rulings"],
            "investor": ["financial_pressure", "contract_leverage"],
            "corrupt_official": ["biased_rulings", "heel_faction_support"],
        }.get(role, ["make_matches"])
        return service.repo.insert_simple(
            "authority_figures",
            {
                "id": new_id("authority"),
                "name": data["name"],
                "role": role,
                "brand": data.get("brand"),
                "credibility_score": float(data.get("credibility_score", 70)),
                "narrative_permissions_json": service.repo.to_json(permissions),
                "status": "active",
            },
        )

    return handle(_run)


@phase_expansion_bp.route("/api/story-engine/authority-storylines", methods=["POST"])
def create_authority_storyline():
    def _run():
        service = get_service()
        data = payload()
        return service.repo.insert_simple(
            "authority_storylines",
            {
                "id": new_id("authority_story"),
                "authority_id": data["authority_id"],
                "angle_type": data.get("angle_type", "abuse_of_power"),
                "status": "active",
                "participants_json": service.repo.to_json(data.get("participants", [])),
                "credibility_effect": float(data.get("credibility_effect", 0)),
                "heat_score": float(data.get("heat_score", 25)),
            },
        )

    return handle(_run)


@phase_expansion_bp.route("/api/story-engine/tournaments", methods=["POST"])
def create_tournament():
    return handle(lambda: get_service().create_tournament(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/story-engine/romantic-angles", methods=["POST"])
def create_romantic_angle():
    return handle(lambda: get_service().create_romantic_angle(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/story-engine/legacy-relationships", methods=["POST"])
def create_legacy_relationship():
    return handle(lambda: get_service().record_legacy_relationship(payload(), get_universe()))


@phase_expansion_bp.route("/api/story-engine/torch-passes", methods=["POST"])
def create_torch_pass():
    return handle(lambda: get_service().record_torch_pass(with_calendar_defaults(payload()), get_universe()))


# ---------------------------------------------------------------------------
# Media, ratings, and business simulation
# ---------------------------------------------------------------------------


@phase_expansion_bp.route("/api/media-business/dashboard", methods=["GET"])
def media_business_dashboard():
    return handle(lambda: get_service().media_business_dashboard())


@phase_expansion_bp.route("/api/media-business/ratings", methods=["GET"])
def media_ratings():
    return handle(lambda: get_service().repo.get_recent_ratings(int(request.args.get("limit", 20))))


@phase_expansion_bp.route("/api/media-business/ratings/<show_id>", methods=["GET"])
def media_rating_detail(show_id):
    def _run():
        rating = get_service().repo.get_show_rating(show_id)
        if not rating:
            raise ValidationError("Rating not found")
        return rating

    return handle(_run)


@phase_expansion_bp.route("/api/media-business/jobs/weekly", methods=["POST"])
def run_weekly_jobs():
    data = with_calendar_defaults(payload())
    return handle(lambda: get_service().run_weekly_jobs(int(data["year"]), int(data["week"])))


@phase_expansion_bp.route("/api/media-business/content", methods=["POST"])
def create_digital_content():
    return handle(lambda: get_service().create_digital_content(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/media-business/media-appearances", methods=["POST"])
def create_media_appearance():
    return handle(lambda: get_service().save_media_appearance(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/media-business/streaming-deals", methods=["POST"])
def create_streaming_deal():
    return handle(lambda: get_service().negotiate_streaming_deal(with_calendar_defaults(payload())))


@phase_expansion_bp.route("/api/media-business/documentaries", methods=["POST"])
def create_documentary():
    return handle(lambda: get_service().create_documentary(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/media-business/video-game-licenses", methods=["POST"])
def create_video_game_license():
    return handle(lambda: get_service().create_video_game_license(payload()))


@phase_expansion_bp.route("/api/media-business/press-conferences", methods=["POST"])
def create_press_conference():
    return handle(lambda: get_service().stage_press_conference(with_calendar_defaults(payload()), get_universe()))


@phase_expansion_bp.route("/api/media-business/controversies/respond", methods=["POST"])
def respond_to_controversy():
    return handle(lambda: get_service().respond_to_controversy(with_calendar_defaults(payload()), get_universe()))
