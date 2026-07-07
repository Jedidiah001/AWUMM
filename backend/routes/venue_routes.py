"""
Venue Routes (Steps 138-148 foundation)
"""

from flask import Blueprint, jsonify, request, current_app

venue_bp = Blueprint("venues", __name__, url_prefix="/api/venues")


def _db():
    return current_app.config["DATABASE"]


@venue_bp.route("/cities")
def api_list_cities():
    db = _db()
    try:
        from persistence.venue_db import list_cities

        search = request.args.get("search")
        continent = request.args.get("continent")
        country = request.args.get("country")
        limit = request.args.get("limit", 250, type=int)

        cities = list_cities(
            db,
            search=search,
            continent=continent,
            country=country,
            limit=max(1, min(int(limit), 500)),
        )
        return jsonify({"success": True, "total": len(cities), "cities": cities})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@venue_bp.route("/venues")
def api_list_venues():
    db = _db()
    try:
        from persistence.venue_db import list_venues

        city_id = request.args.get("city_id")
        if not city_id:
            return jsonify({"success": False, "error": "city_id is required"}), 400

        venues = list_venues(db, city_id=city_id)
        return jsonify({"success": True, "total": len(venues), "venues": venues})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@venue_bp.route("/shows/<show_id>", methods=["GET"])
def api_get_show_venue_assignment(show_id: str):
    db = _db()
    try:
        cursor = db.conn.cursor()
        row = cursor.execute(
            """
            SELECT sva.*, c.name as city_name, c.country as city_country, c.continent as city_continent,
                   v.name as venue_name, v.venue_tier as venue_tier, v.capacity as venue_capacity, v.cost as venue_cost
            FROM show_venue_assignments sva
            LEFT JOIN cities c ON c.city_id = sva.city_id
            LEFT JOIN venues v ON v.venue_id = sva.venue_id
            WHERE sva.show_id=?
            """,
            (show_id,),
        ).fetchone()
        return jsonify({"success": True, "assignment": dict(row) if row else None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@venue_bp.route("/shows/<show_id>", methods=["PUT"])
def api_put_show_venue_assignment(show_id: str):
    db = _db()
    try:
        from persistence.venue_db import upsert_show_venue_assignment

        payload = request.get_json() or {}
        payload["show_id"] = show_id
        upsert_show_venue_assignment(db, payload)
        db.conn.commit()
        return jsonify({"success": True, "show_id": show_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

