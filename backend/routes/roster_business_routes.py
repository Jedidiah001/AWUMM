from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import sqlite3
import threading

roster_business_bp = Blueprint('roster_business', __name__)
_business_tables_lock = threading.Lock()


def _db():
    return current_app.config['DATABASE'].conn


def _init_tables():
    conn = _db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS tv_deals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      promotion_name TEXT NOT NULL,
      network_name TEXT NOT NULL,
      network_tier TEXT NOT NULL,
      years INTEGER NOT NULL CHECK (years BETWEEN 1 AND 10),
      annual_value REAL NOT NULL,
      ppv_share_percent REAL NOT NULL,
      merch_share_percent REAL NOT NULL,
      digital_rights TEXT,
      status TEXT NOT NULL DEFAULT 'active',
      start_date TEXT NOT NULL,
      end_date TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tv_deals_end_date ON tv_deals(end_date)")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS merchandise_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      wrestler_id TEXT,
      name TEXT NOT NULL,
      product_type TEXT NOT NULL,
      sku TEXT NOT NULL UNIQUE,
      price REAL NOT NULL,
      unit_cost REAL NOT NULL,
      inventory INTEGER NOT NULL DEFAULT 0,
      popularity INTEGER NOT NULL DEFAULT 50,
      is_deleted INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_merch_wrestler ON merchandise_items(wrestler_id, is_deleted)")
    try:
        conn.commit()
    except sqlite3.OperationalError as exc:
        if str(exc).lower() != 'not an error':
            raise


@roster_business_bp.before_app_request
def ensure_business_tables():
    if current_app.config.get('BUSINESS_TABLES_READY'):
        return
    with _business_tables_lock:
        if current_app.config.get('BUSINESS_TABLES_READY'):
            return
        _init_tables()
        current_app.config['BUSINESS_TABLES_READY'] = True


@roster_business_bp.route('/api/roster/tv-deals', methods=['GET', 'POST'])
def tv_deals():
    conn = _db()
    if request.method == 'POST':
        data = request.get_json(force=True)
        now = datetime.utcnow().isoformat()
        conn.execute(
            """INSERT INTO tv_deals (promotion_name, network_name, network_tier, years, annual_value,
            ppv_share_percent, merch_share_percent, digital_rights, status, start_date, end_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
            (
                data['promotion_name'], data['network_name'], data['network_tier'], int(data['years']),
                float(data['annual_value']), float(data['ppv_share_percent']), float(data['merch_share_percent']),
                data.get('digital_rights', ''), data['start_date'], data['end_date'], now,
            ),
        )
        conn.commit()
        return jsonify({'ok': True}), 201

    rows = conn.execute("SELECT * FROM tv_deals ORDER BY created_at DESC").fetchall()
    return jsonify({'deals': [dict(r) for r in rows]})


@roster_business_bp.route('/api/roster/merchandise', methods=['GET', 'POST'])
def merchandise():
    conn = _db()
    if request.method == 'POST':
        data = request.get_json(force=True)
        conn.execute(
            """INSERT INTO merchandise_items (wrestler_id, name, product_type, sku, price, unit_cost, inventory, popularity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.get('wrestler_id'), data['name'], data['product_type'], data['sku'], float(data['price']),
             float(data['unit_cost']), int(data.get('inventory', 0)), int(data.get('popularity', 50)), datetime.utcnow().isoformat()),
        )
        conn.commit()
        return jsonify({'ok': True}), 201

    rows = conn.execute("SELECT * FROM merchandise_items WHERE is_deleted = 0 ORDER BY created_at DESC").fetchall()
    payload = []
    for row in rows:
        item = dict(row)
        item['profit_per_unit'] = round(item['price'] - item['unit_cost'], 2)
        payload.append(item)
    return jsonify({'items': payload})
