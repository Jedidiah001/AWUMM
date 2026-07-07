from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from repositories.phase_expansion_repository import PhaseExpansionRepository, new_id


class PostShowFalloutService:
    """Creates persistent post-show consequences that keep the world moving."""

    URGENCY_WEIGHT = {"low": 20, "medium": 45, "high": 75, "critical": 95}

    def __init__(self, database):
        self.database = database
        self.repo = PhaseExpansionRepository(database)
        self._tables_ready = False

    def now(self) -> str:
        return datetime.now().isoformat()

    def _ensure_tables(self) -> None:
        if self._tables_ready:
            return
        row = self.repo.fetch_one(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'post_show_fallout_reports'"
        )
        item_row = self.repo.fetch_one(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'post_show_fallout_items'"
        )
        approval_row = self.repo.fetch_one(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'booker_approval_queue'"
        )
        if row and item_row and approval_row:
            self._tables_ready = True
            return

        from persistence.phase_expansion_db import create_phase_expansion_tables
        create_phase_expansion_tables(self.database)
        self._tables_ready = True

    def generate_for_show(
        self,
        show_draft,
        show_result,
        universe=None,
        seed: int | None = None,
        force: bool = False,
        autonomy_level: str = "balanced",
    ) -> dict:
        self._ensure_tables()
        show_id = self._get(show_result, "show_id") or self._get(show_draft, "show_id")
        year = int(self._get(show_result, "year") or self._get(show_draft, "year") or 1)
        week = int(self._get(show_result, "week") or self._get(show_draft, "week") or 1)

        existing = self.repo.get_post_show_fallout_by_show(show_id, year, week)
        if existing and not force:
            return {"already_exists": True, "report": existing}

        rng = random.Random(seed if seed is not None else (year * 7919 + week * 311 + len(show_id or "")))
        show_name = self._get(show_result, "show_name") or self._get(show_draft, "show_name") or "Show"
        brand = self._get(show_result, "brand") or self._get(show_draft, "brand") or "Cross-Brand"
        show_type = self._get(show_result, "show_type") or self._get(show_draft, "show_type") or "weekly_tv"
        overall = float(self._get(show_result, "overall_rating") or 0)
        matches = [self._match_to_dict(match) for match in (self._get(show_result, "match_results") or [])]
        segments = [self._segment_to_dict(seg) for seg in (self._get(show_result, "segment_results") or [])]
        events = list(self._get(show_result, "events") or [])
        roster = self._active_roster(brand)
        roster_by_name = {row["name"]: row for row in roster}
        title_lookup = self._title_lookup()

        items: list[dict] = []
        headlines: list[str] = []

        high_match = max(matches, key=lambda m: float(m.get("star_rating") or 0), default={})
        low_match = min(matches, key=lambda m: float(m.get("star_rating") or 5), default={})
        title_matches = [m for m in matches if m.get("is_title_match")]
        title_change = next((m for m in title_matches if m.get("title_changed_hands")), None)
        breakout_name = self._first_name(high_match.get("winner_names")) or self._first_match_participant(high_match)
        angry_loser = self._select_angry_loser(matches, roster_by_name)
        champion_name = self._champion_name(title_change, title_matches, title_lookup) or breakout_name

        if breakout_name:
            headlines.append(f"{breakout_name} has fresh post-show buzz.")
            items.append(self._item(
                "breakout_star",
                "medium",
                "Unexpected breakout reaction",
                f"The crowd response made {breakout_name} feel hotter than planned. The AI has already nudged momentum upward.",
                {
                    "wrestler_name": breakout_name,
                    "match_id": high_match.get("match_id"),
                    "star_rating": high_match.get("star_rating"),
                    "crowd_energy": high_match.get("crowd_energy"),
                },
                ["Feature them in a follow-up promo", "Test them against a stronger opponent", "Keep the push subtle for one week"],
                [
                    self._effect("wrestler", "momentum", 4, breakout_name, roster_by_name),
                    self._effect("wrestler", "popularity", 2, breakout_name, roster_by_name),
                ],
                requires_response=False,
            ))

        if angry_loser:
            headlines.append(f"{angry_loser} is unhappy with the finish.")
            items.append(self._item(
                "locker_room",
                "high",
                "Top star furious after losing clean",
                f"{angry_loser} left the ring hot and is demanding a follow-up conversation before the next booking cycle.",
                {"wrestler_name": angry_loser, "trigger": "loss_after_show", "source": show_name},
                ["Hold a one-on-one meeting", "Promise a protected follow-up", "Stand firm and risk morale damage"],
                [self._effect("wrestler", "morale", -4, angry_loser, roster_by_name)],
                requires_response=True,
                auto_execute_allowed=True,
                approval={
                    "priority": "high",
                    "autonomy_policy": "auto_if_unanswered",
                    "recommendation": {
                        "recommended_action": "Hold a short meeting and give them a visible rebound beat next week.",
                        "risk_if_ignored": "Morale dip, possible creative resistance, and locker room chatter.",
                    },
                },
            ))

        if self._should_trigger_urgent(rng, overall, matches, title_change, events):
            urgent_item = self._urgent_interruption(
                rng, show_name, brand, champion_name, angry_loser, breakout_name, roster, roster_by_name, title_matches
            )
            if urgent_item:
                headlines.append(urgent_item["title"])
                items.append(urgent_item)

        poor_title_match = next(
            (m for m in title_matches if float(m.get("star_rating") or 0) < 2.6 or str(m.get("finish_type", "")).lower() in {"dq", "countout", "no_contest"}),
            None,
        )
        if poor_title_match:
            title_name = poor_title_match.get("title_name") or "a championship"
            headlines.append(f"{title_name} took a prestige hit.")
            items.append(self._item(
                "title_prestige",
                "high",
                "Poor finish damaged title prestige",
                f"The audience rejected the finish to {title_name}. The title scene needs a credibility repair beat.",
                {"title_name": title_name, "match_id": poor_title_match.get("match_id"), "finish_type": poor_title_match.get("finish_type")},
                ["Book a decisive rematch", "Have the champion address the controversy", "Escalate to a stipulation match"],
                [self._effect("championship", "prestige", -2, title_name, title_lookup)],
                requires_response=True,
                auto_execute_allowed=False,
                approval={
                    "priority": "high",
                    "autonomy_policy": "ask",
                    "recommendation": {
                        "recommended_action": "Book a decisive follow-up angle to restore title credibility.",
                        "risk_if_ignored": "Prestige decay and weaker audience investment in the championship.",
                    },
                },
            ))

        if segments or rng.random() < 0.45:
            speaker = breakout_name or champion_name or (roster[0]["name"] if roster else "A wrestler")
            items.append(self._item(
                "creative_ripple",
                "medium",
                "Improvised promo created a storyline seed",
                f"{speaker} ad-libbed a line that production is replaying online. The AI can turn it into next week's segment.",
                {"wrestler_name": speaker, "source": "post_show_replay"},
                ["Approve the new storyline seed", "Counter-pitch a safer version", "Ignore it and let the buzz fade"],
                [self._effect("wrestler", "momentum", 2, speaker, roster_by_name)],
                requires_response=True,
                auto_execute_allowed=True,
                approval={
                    "priority": "medium",
                    "autonomy_policy": "auto_if_unanswered",
                    "recommendation": {
                        "segment_type": "promo",
                        "hook": f"{speaker} explains the line everyone is talking about.",
                        "mechanical_goal": "Convert social buzz into feud/story momentum.",
                    },
                },
            ))

        if rng.random() < 0.42 and roster:
            target = self._low_morale_star(roster) or angry_loser or roster[min(len(roster) - 1, 2)]["name"]
            items.append(self._item(
                "rival_ai",
                "high",
                "Rival promotion contacted unhappy talent",
                f"Industry chatter says a rival made quiet contact with {target}. This is now a contract and morale risk.",
                {"wrestler_name": target, "source": "rival_poaching_signal"},
                ["Open retention talks", "Use them strongly next week", "Let the rival waste time"],
                [self._effect("wrestler", "morale", -2, target, roster_by_name)],
                requires_response=True,
                auto_execute_allowed=True,
                approval={
                    "priority": "high",
                    "autonomy_policy": "auto_if_unanswered",
                    "recommendation": {
                        "recommended_action": "Offer a creative reassurance or visible booking opportunity.",
                        "connected_systems": ["contracts", "morale", "rival_ai"],
                    },
                },
            ))

        items.append(self._item(
            "media_fallout",
            "low" if overall >= 3.2 else "medium",
            "Media desk filed its post-show read",
            self._media_summary(show_name, overall, matches, events),
            {"overall_rating": overall, "event_count": len(events), "match_count": len(matches)},
            ["Lean into the best headline", "Protect weak finishes", "Feed one quote to the media system"],
            [],
            requires_response=False,
        ))

        if not items:
            items.append(self._item(
                "quiet_show",
                "low",
                "Quiet professional night",
                "No major crisis erupted, but the locker room expects visible follow-up from the strongest act.",
                {"overall_rating": overall},
                ["Stay the course", "Give underused talent a house show test"],
                [],
                requires_response=False,
            ))

        report_id = new_id("fallout")
        urgency_score = round(sum(self.URGENCY_WEIGHT.get(item["urgency"], 45) for item in items) / max(1, len(items)), 2)
        report = {
            "id": report_id,
            "show_id": show_id,
            "show_name": show_name,
            "brand": brand,
            "show_type": show_type,
            "year": year,
            "week": week,
            "autonomy_level": autonomy_level,
            "overall_rating": overall,
            "urgency_score": urgency_score,
            "summary": self._report_summary(show_name, items),
            "headlines": headlines[:5],
            "status": "open",
        }
        for item in items:
            item["report_id"] = report_id
            if item.get("approval"):
                item["approval"]["id"] = new_id("approval")
                item["approval"]["source_type"] = "post_show_fallout"
                item["approval"]["deadline_year"] = year
                item["approval"]["deadline_week"] = week + 1
                if item["approval"].get("autonomy_policy") == "auto_if_unanswered":
                    item["approval"]["auto_execute_after_week"] = week + 1

        all_effects = [effect for item in items for effect in item.get("mechanical_effects", []) if effect.get("apply_immediately")]
        applied_effects = self.repo.apply_post_show_effects(all_effects)
        self._apply_universe_effects(universe, applied_effects)

        saved = self.repo.save_post_show_fallout(
            report,
            items,
            {
                "id": new_id("job"),
                "job_type": "post_show_fallout",
                "status": "completed",
                "reads": ["show_result", "wrestlers", "championships", "booker_approval_queue"],
                "writes": ["post_show_fallout_reports", "post_show_fallout_items", "booker_approval_queue", "wrestlers", "championships"],
                "result": {"report_id": report_id, "items": len(items), "applied_effects": len(applied_effects)},
            },
        )
        return {"already_exists": False, "report": saved, "applied_effects": applied_effects}

    def get_latest(self, show_id: str | None = None, year: int | None = None, week: int | None = None, limit: int = 8) -> dict:
        self._ensure_tables()
        if show_id and year is not None and week is not None:
            report = self.repo.get_post_show_fallout_by_show(show_id, int(year), int(week))
            return {"report": report, "reports": [report] if report else []}
        reports = self.repo.latest_post_show_fallouts(limit)
        return {"report": reports[0] if reports else None, "reports": reports}

    def decide_item(self, item_id: str, data: dict) -> dict:
        self._ensure_tables()
        decision = str(data.get("decision") or data.get("action") or "acknowledge").lower()
        status_map = {
            "approve": "approved",
            "counter": "countered",
            "reject": "rejected",
            "dismiss": "dismissed",
            "acknowledge": "acknowledged",
            "auto_execute": "auto_executed",
        }
        if decision not in status_map:
            raise ValueError("Decision must be approve, counter, reject, dismiss, acknowledge, or auto_execute.")
        item = self.repo.fetch_one("SELECT * FROM post_show_fallout_items WHERE id = ? AND deleted_at IS NULL", (item_id,))
        if not item:
            raise ValueError("Post-show fallout item not found.")
        response = {
            "decision": decision,
            "notes": data.get("notes", ""),
            "counter_pitch": data.get("counter_pitch", ""),
            "decided_at": self.now(),
        }
        updated = self.repo.decide_post_show_fallout_item(item_id, status_map[decision], response)
        approval_id = item.get("approval_id")
        if approval_id:
            try:
                from services.ai_showrunner_service import AIShowrunnerService

                AIShowrunnerService(self.database).decide_approval(
                    approval_id,
                    {
                        "decision": "auto_execute" if decision == "auto_execute" else decision,
                        "notes": response["notes"] or f"Resolved from post-show fallout: {decision}",
                        "counter_pitch": response["counter_pitch"],
                    },
                )
            except Exception:
                pass
        return updated

    def auto_handle_report(self, report_id: str) -> dict:
        self._ensure_tables()
        report = self.repo.get_post_show_fallout(report_id)
        if not report:
            raise ValueError("Post-show fallout report not found.")
        resolved = []
        for item in report.get("items", []):
            if item.get("status") != "open":
                continue
            decision = "auto_execute" if item.get("auto_execute_allowed") else "acknowledge"
            resolved.append(self.decide_item(item["id"], {"decision": decision, "notes": "AI handled from post-show desk."}))
        return {"resolved": len(resolved), "items": resolved, "report": self.repo.get_post_show_fallout(report_id)}

    def _item(
        self,
        item_type: str,
        urgency: str,
        title: str,
        summary: str,
        details: dict,
        suggested_actions: list[str],
        mechanical_effects: list[dict],
        requires_response: bool,
        auto_execute_allowed: bool = False,
        approval: dict | None = None,
    ) -> dict:
        return {
            "id": new_id("fallout_item"),
            "item_type": item_type,
            "urgency": urgency,
            "title": title,
            "summary": summary,
            "details": details,
            "suggested_actions": suggested_actions,
            "mechanical_effects": [effect for effect in mechanical_effects if effect],
            "requires_response": requires_response,
            "auto_execute_allowed": auto_execute_allowed,
            "status": "open",
            "approval": approval,
        }

    def _urgent_interruption(self, rng, show_name, brand, champion_name, angry_loser, breakout_name, roster, roster_by_name, title_matches):
        templates = ["media_scrum_refusal", "rival_contact", "backstage_attack", "improvised_promo"]
        if title_matches:
            templates.append("title_scene_crisis")
        choice = rng.choice(templates)
        primary = champion_name or breakout_name or (roster[0]["name"] if roster else "Your top star")
        secondary = angry_loser or breakout_name or (roster[1]["name"] if len(roster) > 1 else primary)

        if choice == "media_scrum_refusal":
            return self._item(
                "urgent_media",
                "critical",
                "Champion refused the planned media scrum",
                f"{primary} skipped the post-show media room. Reporters are already asking whether this is storyline or real frustration.",
                {"wrestler_name": primary, "brand": brand, "source": show_name},
                ["Send management to calm them down", "Let them cut an unscripted explanation", "Fine them and risk backlash"],
                [self._effect("wrestler", "morale", -3, primary, roster_by_name)],
                True,
                True,
                {"priority": "urgent", "autonomy_policy": "auto_if_unanswered", "recommendation": {"response": "Convert it into a controlled in-ring explanation next week."}},
            )
        if choice == "backstage_attack":
            return self._item(
                "backstage_incident",
                "critical",
                "Faction-style backstage attack after the show",
                f"Security reports that {primary} and {secondary} were involved in a pull-apart after cameras stopped rolling.",
                {"primary_name": primary, "secondary_name": secondary, "source": "post_show_backstage"},
                ["Open a disciplinary review", "Turn it into next week's cold open", "Keep it quiet and risk rumors"],
                [self._effect("wrestler", "fatigue", 3, primary, roster_by_name), self._effect("wrestler", "morale", -2, secondary, roster_by_name)],
                True,
                False,
                {"priority": "urgent", "autonomy_policy": "ask", "recommendation": {"response": "Review before deciding whether this becomes story or discipline."}},
            )
        if choice == "title_scene_crisis":
            title_name = (title_matches[0] or {}).get("title_name") or "the championship"
            return self._item(
                "title_scene",
                "high",
                "Title scene erupted in post-show controversy",
                f"The finish around {title_name} has split fans and talent. The AI wants a fast correction beat.",
                {"title_name": title_name, "wrestler_name": primary},
                ["Book a title clarification promo", "Announce a number-one contender match", "Let controversy simmer"],
                [self._effect("championship", "prestige", -1, title_name, self._title_lookup())],
                True,
                True,
                {"priority": "high", "autonomy_policy": "auto_if_unanswered", "recommendation": {"response": "Book a clarification segment next week."}},
            )
        return self._item(
            "creative_ripple",
            "high",
            "Unscripted post-show promo caught fire",
            f"{primary} grabbed a camera after the show and said something production did not clear. Fans are treating it like canon.",
            {"wrestler_name": primary, "source": "unscripted_post_show"},
            ["Canonize it", "Edit around it", "Make them apologize on air"],
            [self._effect("wrestler", "momentum", 3, primary, roster_by_name)],
            True,
            True,
            {"priority": "high", "autonomy_policy": "auto_if_unanswered", "recommendation": {"response": "Canonize the best line and build a promo beat."}},
        )

    def _effect(self, target_type: str, impact_type: str, delta: float, target_name: str | None, lookup: dict[str, dict]) -> dict | None:
        if not target_name:
            return None
        row = lookup.get(target_name, {})
        return {
            "target_type": target_type,
            "target_id": row.get("id"),
            "target_name": target_name,
            "impact_type": impact_type,
            "delta": delta,
            "apply_immediately": True,
        }

    def _active_roster(self, brand: str) -> list[dict]:
        rows = self.repo.fetch_all(
            """
            SELECT id, name, role, primary_brand, popularity, momentum, morale, fatigue,
                   contract_weeks_remaining
            FROM wrestlers
            WHERE COALESCE(is_retired, 0) = 0
            ORDER BY popularity DESC, momentum DESC, name
            """
        )
        if brand and brand != "Cross-Brand":
            branded = [row for row in rows if row.get("primary_brand") in {brand, "Cross-Brand"}]
            return branded or rows
        return rows

    def _title_lookup(self) -> dict[str, dict]:
        rows = self.repo.fetch_all("SELECT id, name, prestige, current_holder_name FROM championships ORDER BY prestige DESC")
        return {row["name"]: row for row in rows}

    def _select_angry_loser(self, matches: list[dict], roster_by_name: dict[str, dict]) -> str | None:
        candidates = []
        for match in matches:
            weight = float(match.get("star_rating") or 0)
            if match.get("is_title_match"):
                weight += 1.2
            if match.get("card_position"):
                weight += int(match.get("card_position") or 0) * 0.03
            for name in match.get("loser_names") or []:
                row = roster_by_name.get(name, {})
                candidates.append((weight + (row.get("popularity") or 0) / 100, name))
        candidates.sort(reverse=True)
        return candidates[0][1] if candidates else None

    def _champion_name(self, title_change: dict | None, title_matches: list[dict], title_lookup: dict[str, dict]) -> str | None:
        if title_change:
            return title_change.get("new_champion_name") or self._first_name(title_change.get("winner_names"))
        if title_matches:
            title = title_lookup.get(title_matches[0].get("title_name"))
            if title:
                return title.get("current_holder_name")
        return None

    def _low_morale_star(self, roster: list[dict]) -> str | None:
        unhappy = [row for row in roster if (row.get("morale") or 50) < 45]
        unhappy.sort(key=lambda row: (row.get("popularity") or 0, row.get("momentum") or 0), reverse=True)
        return unhappy[0]["name"] if unhappy else None

    def _should_trigger_urgent(self, rng, overall: float, matches: list[dict], title_change: dict | None, events: list[dict]) -> bool:
        chance = 0.38
        if overall < 2.8:
            chance += 0.18
        if overall >= 4.1:
            chance += 0.12
        if title_change:
            chance += 0.18
        if any((event.get("type") or "").lower() in {"live_interruption", "injury", "title_change"} for event in events):
            chance += 0.12
        if any(match.get("is_upset") for match in matches):
            chance += 0.1
        return rng.random() < min(0.82, chance)

    def _media_summary(self, show_name: str, overall: float, matches: list[dict], events: list[dict]) -> str:
        if overall >= 4:
            return f"Media reaction to {show_name} is hot. The show has at least one clip the company can push immediately."
        if overall < 2.5:
            return f"Media reaction to {show_name} is uneasy. Reporters are focusing on weak finishes and restless fan response."
        if events:
            return f"Media reaction to {show_name} is centered on the unexpected moments more than the advertised card."
        return f"Media reaction to {show_name} is steady, with no single crisis dominating the desk."

    def _report_summary(self, show_name: str, items: list[dict]) -> str:
        urgent = len([item for item in items if item.get("urgency") in {"critical", "high"}])
        return f"{show_name} generated {len(items)} fallout item(s), including {urgent} high-priority situation(s)."

    def _apply_universe_effects(self, universe, effects: list[dict]) -> None:
        if not universe:
            return
        for effect in effects:
            target_name = effect.get("target_name")
            target_id = effect.get("target_id")
            impact = effect.get("impact_type")
            delta = float(effect.get("delta", 0))
            if effect.get("target_type") == "wrestler":
                for wrestler in getattr(universe, "wrestlers", []) or []:
                    if getattr(wrestler, "id", None) == target_id or getattr(wrestler, "name", None) == target_name:
                        current = getattr(wrestler, impact, None)
                        if isinstance(current, (int, float)):
                            setattr(wrestler, impact, max(0, min(100, current + delta)))
                        break
            elif effect.get("target_type") == "championship" and impact == "prestige":
                for title in getattr(universe, "championships", []) or []:
                    if getattr(title, "id", None) == target_id or getattr(title, "name", None) == target_name:
                        current = getattr(title, "prestige", None)
                        if isinstance(current, (int, float)):
                            setattr(title, "prestige", max(0, min(100, current + delta)))
                        break

    def _match_to_dict(self, match) -> dict:
        if hasattr(match, "to_dict"):
            return match.to_dict()
        return dict(match or {})

    def _segment_to_dict(self, segment) -> dict:
        if hasattr(segment, "to_dict"):
            return segment.to_dict()
        return dict(segment or {})

    def _get(self, obj: Any, key: str, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _first_name(self, names) -> str | None:
        if isinstance(names, list) and names:
            return names[0]
        if isinstance(names, str):
            return names
        return None

    def _first_match_participant(self, match: dict) -> str | None:
        for side_key in ("side_a", "side_b"):
            names = (match.get(side_key) or {}).get("wrestler_names") or []
            if names:
                return names[0]
        return None
