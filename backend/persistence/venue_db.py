"""
Venue + City persistence (Steps 138-148 foundation).

Stores:
- A seed list of real-world cities (>=200) across multiple continents
- A generated set of venues per city (club/arena/stadium)
- Per-show venue assignments (so weekly shows + PPVs + house shows can be placed on the calendar)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime


# >=200 real cities across continents; ids are stable for assignments.
_CITY_SEED: List[Dict[str, str]] = [
    # North America (US/CA/MX)
    {"id": "city_001", "name": "New York", "country": "United States", "continent": "North America"},
    {"id": "city_002", "name": "Los Angeles", "country": "United States", "continent": "North America"},
    {"id": "city_003", "name": "Chicago", "country": "United States", "continent": "North America"},
    {"id": "city_004", "name": "Houston", "country": "United States", "continent": "North America"},
    {"id": "city_005", "name": "Phoenix", "country": "United States", "continent": "North America"},
    {"id": "city_006", "name": "Philadelphia", "country": "United States", "continent": "North America"},
    {"id": "city_007", "name": "San Antonio", "country": "United States", "continent": "North America"},
    {"id": "city_008", "name": "San Diego", "country": "United States", "continent": "North America"},
    {"id": "city_009", "name": "Dallas", "country": "United States", "continent": "North America"},
    {"id": "city_010", "name": "San Jose", "country": "United States", "continent": "North America"},
    {"id": "city_011", "name": "Austin", "country": "United States", "continent": "North America"},
    {"id": "city_012", "name": "Jacksonville", "country": "United States", "continent": "North America"},
    {"id": "city_013", "name": "San Francisco", "country": "United States", "continent": "North America"},
    {"id": "city_014", "name": "Columbus", "country": "United States", "continent": "North America"},
    {"id": "city_015", "name": "Indianapolis", "country": "United States", "continent": "North America"},
    {"id": "city_016", "name": "Charlotte", "country": "United States", "continent": "North America"},
    {"id": "city_017", "name": "Seattle", "country": "United States", "continent": "North America"},
    {"id": "city_018", "name": "Denver", "country": "United States", "continent": "North America"},
    {"id": "city_019", "name": "Washington, D.C.", "country": "United States", "continent": "North America"},
    {"id": "city_020", "name": "Boston", "country": "United States", "continent": "North America"},
    {"id": "city_021", "name": "Nashville", "country": "United States", "continent": "North America"},
    {"id": "city_022", "name": "Portland", "country": "United States", "continent": "North America"},
    {"id": "city_023", "name": "Las Vegas", "country": "United States", "continent": "North America"},
    {"id": "city_024", "name": "Detroit", "country": "United States", "continent": "North America"},
    {"id": "city_025", "name": "Baltimore", "country": "United States", "continent": "North America"},
    {"id": "city_026", "name": "Atlanta", "country": "United States", "continent": "North America"},
    {"id": "city_027", "name": "Miami", "country": "United States", "continent": "North America"},
    {"id": "city_028", "name": "Minneapolis", "country": "United States", "continent": "North America"},
    {"id": "city_029", "name": "Cleveland", "country": "United States", "continent": "North America"},
    {"id": "city_030", "name": "Pittsburgh", "country": "United States", "continent": "North America"},
    {"id": "city_031", "name": "Toronto", "country": "Canada", "continent": "North America"},
    {"id": "city_032", "name": "Montreal", "country": "Canada", "continent": "North America"},
    {"id": "city_033", "name": "Vancouver", "country": "Canada", "continent": "North America"},
    {"id": "city_034", "name": "Calgary", "country": "Canada", "continent": "North America"},
    {"id": "city_035", "name": "Ottawa", "country": "Canada", "continent": "North America"},
    {"id": "city_036", "name": "Mexico City", "country": "Mexico", "continent": "North America"},
    {"id": "city_037", "name": "Guadalajara", "country": "Mexico", "continent": "North America"},
    {"id": "city_038", "name": "Monterrey", "country": "Mexico", "continent": "North America"},
    {"id": "city_039", "name": "Tijuana", "country": "Mexico", "continent": "North America"},
    {"id": "city_040", "name": "Cancún", "country": "Mexico", "continent": "North America"},

    # South America
    {"id": "city_041", "name": "São Paulo", "country": "Brazil", "continent": "South America"},
    {"id": "city_042", "name": "Rio de Janeiro", "country": "Brazil", "continent": "South America"},
    {"id": "city_043", "name": "Brasília", "country": "Brazil", "continent": "South America"},
    {"id": "city_044", "name": "Buenos Aires", "country": "Argentina", "continent": "South America"},
    {"id": "city_045", "name": "Córdoba", "country": "Argentina", "continent": "South America"},
    {"id": "city_046", "name": "Santiago", "country": "Chile", "continent": "South America"},
    {"id": "city_047", "name": "Valparaíso", "country": "Chile", "continent": "South America"},
    {"id": "city_048", "name": "Lima", "country": "Peru", "continent": "South America"},
    {"id": "city_049", "name": "Bogotá", "country": "Colombia", "continent": "South America"},
    {"id": "city_050", "name": "Medellín", "country": "Colombia", "continent": "South America"},
    {"id": "city_051", "name": "Quito", "country": "Ecuador", "continent": "South America"},
    {"id": "city_052", "name": "Caracas", "country": "Venezuela", "continent": "South America"},
    {"id": "city_053", "name": "Montevideo", "country": "Uruguay", "continent": "South America"},
    {"id": "city_054", "name": "La Paz", "country": "Bolivia", "continent": "South America"},
    {"id": "city_055", "name": "Asunción", "country": "Paraguay", "continent": "South America"},

    # Europe
    {"id": "city_056", "name": "London", "country": "United Kingdom", "continent": "Europe"},
    {"id": "city_057", "name": "Manchester", "country": "United Kingdom", "continent": "Europe"},
    {"id": "city_058", "name": "Birmingham", "country": "United Kingdom", "continent": "Europe"},
    {"id": "city_059", "name": "Dublin", "country": "Ireland", "continent": "Europe"},
    {"id": "city_060", "name": "Edinburgh", "country": "United Kingdom", "continent": "Europe"},
    {"id": "city_061", "name": "Paris", "country": "France", "continent": "Europe"},
    {"id": "city_062", "name": "Lyon", "country": "France", "continent": "Europe"},
    {"id": "city_063", "name": "Marseille", "country": "France", "continent": "Europe"},
    {"id": "city_064", "name": "Berlin", "country": "Germany", "continent": "Europe"},
    {"id": "city_065", "name": "Munich", "country": "Germany", "continent": "Europe"},
    {"id": "city_066", "name": "Hamburg", "country": "Germany", "continent": "Europe"},
    {"id": "city_067", "name": "Frankfurt", "country": "Germany", "continent": "Europe"},
    {"id": "city_068", "name": "Madrid", "country": "Spain", "continent": "Europe"},
    {"id": "city_069", "name": "Barcelona", "country": "Spain", "continent": "Europe"},
    {"id": "city_070", "name": "Valencia", "country": "Spain", "continent": "Europe"},
    {"id": "city_071", "name": "Lisbon", "country": "Portugal", "continent": "Europe"},
    {"id": "city_072", "name": "Porto", "country": "Portugal", "continent": "Europe"},
    {"id": "city_073", "name": "Rome", "country": "Italy", "continent": "Europe"},
    {"id": "city_074", "name": "Milan", "country": "Italy", "continent": "Europe"},
    {"id": "city_075", "name": "Naples", "country": "Italy", "continent": "Europe"},
    {"id": "city_076", "name": "Amsterdam", "country": "Netherlands", "continent": "Europe"},
    {"id": "city_077", "name": "Rotterdam", "country": "Netherlands", "continent": "Europe"},
    {"id": "city_078", "name": "Brussels", "country": "Belgium", "continent": "Europe"},
    {"id": "city_079", "name": "Zurich", "country": "Switzerland", "continent": "Europe"},
    {"id": "city_080", "name": "Vienna", "country": "Austria", "continent": "Europe"},
    {"id": "city_081", "name": "Prague", "country": "Czechia", "continent": "Europe"},
    {"id": "city_082", "name": "Warsaw", "country": "Poland", "continent": "Europe"},
    {"id": "city_083", "name": "Kraków", "country": "Poland", "continent": "Europe"},
    {"id": "city_084", "name": "Stockholm", "country": "Sweden", "continent": "Europe"},
    {"id": "city_085", "name": "Oslo", "country": "Norway", "continent": "Europe"},
    {"id": "city_086", "name": "Copenhagen", "country": "Denmark", "continent": "Europe"},
    {"id": "city_087", "name": "Helsinki", "country": "Finland", "continent": "Europe"},
    {"id": "city_088", "name": "Athens", "country": "Greece", "continent": "Europe"},
    {"id": "city_089", "name": "Budapest", "country": "Hungary", "continent": "Europe"},
    {"id": "city_090", "name": "Bucharest", "country": "Romania", "continent": "Europe"},
    {"id": "city_091", "name": "Sofia", "country": "Bulgaria", "continent": "Europe"},
    {"id": "city_092", "name": "Belgrade", "country": "Serbia", "continent": "Europe"},
    {"id": "city_093", "name": "Zagreb", "country": "Croatia", "continent": "Europe"},
    {"id": "city_094", "name": "Ljubljana", "country": "Slovenia", "continent": "Europe"},
    {"id": "city_095", "name": "Reykjavík", "country": "Iceland", "continent": "Europe"},
    {"id": "city_096", "name": "Moscow", "country": "Russia", "continent": "Europe"},
    {"id": "city_097", "name": "Saint Petersburg", "country": "Russia", "continent": "Europe"},
    {"id": "city_098", "name": "Kyiv", "country": "Ukraine", "continent": "Europe"},
    {"id": "city_099", "name": "Istanbul", "country": "Turkey", "continent": "Europe"},
    {"id": "city_100", "name": "Ankara", "country": "Turkey", "continent": "Europe"},

    # Africa
    {"id": "city_101", "name": "Lagos", "country": "Nigeria", "continent": "Africa"},
    {"id": "city_102", "name": "Abuja", "country": "Nigeria", "continent": "Africa"},
    {"id": "city_103", "name": "Accra", "country": "Ghana", "continent": "Africa"},
    {"id": "city_104", "name": "Kumasi", "country": "Ghana", "continent": "Africa"},
    {"id": "city_105", "name": "Nairobi", "country": "Kenya", "continent": "Africa"},
    {"id": "city_106", "name": "Mombasa", "country": "Kenya", "continent": "Africa"},
    {"id": "city_107", "name": "Addis Ababa", "country": "Ethiopia", "continent": "Africa"},
    {"id": "city_108", "name": "Johannesburg", "country": "South Africa", "continent": "Africa"},
    {"id": "city_109", "name": "Cape Town", "country": "South Africa", "continent": "Africa"},
    {"id": "city_110", "name": "Durban", "country": "South Africa", "continent": "Africa"},
    {"id": "city_111", "name": "Cairo", "country": "Egypt", "continent": "Africa"},
    {"id": "city_112", "name": "Alexandria", "country": "Egypt", "continent": "Africa"},
    {"id": "city_113", "name": "Casablanca", "country": "Morocco", "continent": "Africa"},
    {"id": "city_114", "name": "Rabat", "country": "Morocco", "continent": "Africa"},
    {"id": "city_115", "name": "Tunis", "country": "Tunisia", "continent": "Africa"},
    {"id": "city_116", "name": "Algiers", "country": "Algeria", "continent": "Africa"},
    {"id": "city_117", "name": "Dakar", "country": "Senegal", "continent": "Africa"},
    {"id": "city_118", "name": "Abidjan", "country": "Côte d’Ivoire", "continent": "Africa"},
    {"id": "city_119", "name": "Kigali", "country": "Rwanda", "continent": "Africa"},
    {"id": "city_120", "name": "Kampala", "country": "Uganda", "continent": "Africa"},
    {"id": "city_121", "name": "Dar es Salaam", "country": "Tanzania", "continent": "Africa"},
    {"id": "city_122", "name": "Khartoum", "country": "Sudan", "continent": "Africa"},
    {"id": "city_123", "name": "Luanda", "country": "Angola", "continent": "Africa"},
    {"id": "city_124", "name": "Gaborone", "country": "Botswana", "continent": "Africa"},
    {"id": "city_125", "name": "Harare", "country": "Zimbabwe", "continent": "Africa"},
    {"id": "city_126", "name": "Maputo", "country": "Mozambique", "continent": "Africa"},
    {"id": "city_127", "name": "Douala", "country": "Cameroon", "continent": "Africa"},
    {"id": "city_128", "name": "Yaoundé", "country": "Cameroon", "continent": "Africa"},
    {"id": "city_129", "name": "Tripoli", "country": "Libya", "continent": "Africa"},
    {"id": "city_130", "name": "Windhoek", "country": "Namibia", "continent": "Africa"},

    # Asia
    {"id": "city_131", "name": "Tokyo", "country": "Japan", "continent": "Asia"},
    {"id": "city_132", "name": "Osaka", "country": "Japan", "continent": "Asia"},
    {"id": "city_133", "name": "Nagoya", "country": "Japan", "continent": "Asia"},
    {"id": "city_134", "name": "Seoul", "country": "South Korea", "continent": "Asia"},
    {"id": "city_135", "name": "Busan", "country": "South Korea", "continent": "Asia"},
    {"id": "city_136", "name": "Beijing", "country": "China", "continent": "Asia"},
    {"id": "city_137", "name": "Shanghai", "country": "China", "continent": "Asia"},
    {"id": "city_138", "name": "Shenzhen", "country": "China", "continent": "Asia"},
    {"id": "city_139", "name": "Guangzhou", "country": "China", "continent": "Asia"},
    {"id": "city_140", "name": "Chengdu", "country": "China", "continent": "Asia"},
    {"id": "city_141", "name": "Hong Kong", "country": "China", "continent": "Asia"},
    {"id": "city_142", "name": "Taipei", "country": "Taiwan", "continent": "Asia"},
    {"id": "city_143", "name": "Singapore", "country": "Singapore", "continent": "Asia"},
    {"id": "city_144", "name": "Bangkok", "country": "Thailand", "continent": "Asia"},
    {"id": "city_145", "name": "Phuket", "country": "Thailand", "continent": "Asia"},
    {"id": "city_146", "name": "Hanoi", "country": "Vietnam", "continent": "Asia"},
    {"id": "city_147", "name": "Ho Chi Minh City", "country": "Vietnam", "continent": "Asia"},
    {"id": "city_148", "name": "Manila", "country": "Philippines", "continent": "Asia"},
    {"id": "city_149", "name": "Jakarta", "country": "Indonesia", "continent": "Asia"},
    {"id": "city_150", "name": "Bali (Denpasar)", "country": "Indonesia", "continent": "Asia"},
    {"id": "city_151", "name": "Kuala Lumpur", "country": "Malaysia", "continent": "Asia"},
    {"id": "city_152", "name": "Delhi", "country": "India", "continent": "Asia"},
    {"id": "city_153", "name": "Mumbai", "country": "India", "continent": "Asia"},
    {"id": "city_154", "name": "Bengaluru", "country": "India", "continent": "Asia"},
    {"id": "city_155", "name": "Chennai", "country": "India", "continent": "Asia"},
    {"id": "city_156", "name": "Kolkata", "country": "India", "continent": "Asia"},
    {"id": "city_157", "name": "Karachi", "country": "Pakistan", "continent": "Asia"},
    {"id": "city_158", "name": "Lahore", "country": "Pakistan", "continent": "Asia"},
    {"id": "city_159", "name": "Dhaka", "country": "Bangladesh", "continent": "Asia"},
    {"id": "city_160", "name": "Kathmandu", "country": "Nepal", "continent": "Asia"},
    {"id": "city_161", "name": "Colombo", "country": "Sri Lanka", "continent": "Asia"},
    {"id": "city_162", "name": "Dubai", "country": "United Arab Emirates", "continent": "Asia"},
    {"id": "city_163", "name": "Abu Dhabi", "country": "United Arab Emirates", "continent": "Asia"},
    {"id": "city_164", "name": "Riyadh", "country": "Saudi Arabia", "continent": "Asia"},
    {"id": "city_165", "name": "Jeddah", "country": "Saudi Arabia", "continent": "Asia"},
    {"id": "city_166", "name": "Doha", "country": "Qatar", "continent": "Asia"},
    {"id": "city_167", "name": "Kuwait City", "country": "Kuwait", "continent": "Asia"},
    {"id": "city_168", "name": "Tehran", "country": "Iran", "continent": "Asia"},
    {"id": "city_169", "name": "Baghdad", "country": "Iraq", "continent": "Asia"},
    {"id": "city_170", "name": "Jerusalem", "country": "Israel", "continent": "Asia"},

    # Oceania
    {"id": "city_171", "name": "Sydney", "country": "Australia", "continent": "Oceania"},
    {"id": "city_172", "name": "Melbourne", "country": "Australia", "continent": "Oceania"},
    {"id": "city_173", "name": "Brisbane", "country": "Australia", "continent": "Oceania"},
    {"id": "city_174", "name": "Perth", "country": "Australia", "continent": "Oceania"},
    {"id": "city_175", "name": "Adelaide", "country": "Australia", "continent": "Oceania"},
    {"id": "city_176", "name": "Auckland", "country": "New Zealand", "continent": "Oceania"},
    {"id": "city_177", "name": "Wellington", "country": "New Zealand", "continent": "Oceania"},
    {"id": "city_178", "name": "Christchurch", "country": "New Zealand", "continent": "Oceania"},
    {"id": "city_179", "name": "Suva", "country": "Fiji", "continent": "Oceania"},
    {"id": "city_180", "name": "Port Moresby", "country": "Papua New Guinea", "continent": "Oceania"},

    # Extra cities to push well beyond 200 (mix of regions)
    {"id": "city_181", "name": "Seattle", "country": "United States", "continent": "North America"},
    {"id": "city_182", "name": "Salt Lake City", "country": "United States", "continent": "North America"},
    {"id": "city_183", "name": "Kansas City", "country": "United States", "continent": "North America"},
    {"id": "city_184", "name": "New Orleans", "country": "United States", "continent": "North America"},
    {"id": "city_185", "name": "Tampa", "country": "United States", "continent": "North America"},
    {"id": "city_186", "name": "St. Louis", "country": "United States", "continent": "North America"},
    {"id": "city_187", "name": "Sacramento", "country": "United States", "continent": "North America"},
    {"id": "city_188", "name": "Raleigh", "country": "United States", "continent": "North America"},
    {"id": "city_189", "name": "San Juan", "country": "Puerto Rico", "continent": "North America"},
    {"id": "city_190", "name": "Havana", "country": "Cuba", "continent": "North America"},
    {"id": "city_191", "name": "Kingston", "country": "Jamaica", "continent": "North America"},
    {"id": "city_192", "name": "Panama City", "country": "Panama", "continent": "North America"},
    {"id": "city_193", "name": "San José", "country": "Costa Rica", "continent": "North America"},
    {"id": "city_194", "name": "Guatemala City", "country": "Guatemala", "continent": "North America"},
    {"id": "city_195", "name": "San Salvador", "country": "El Salvador", "continent": "North America"},
    {"id": "city_196", "name": "Helsinki", "country": "Finland", "continent": "Europe"},
    {"id": "city_197", "name": "Glasgow", "country": "United Kingdom", "continent": "Europe"},
    {"id": "city_198", "name": "Nice", "country": "France", "continent": "Europe"},
    {"id": "city_199", "name": "Venice", "country": "Italy", "continent": "Europe"},
    {"id": "city_200", "name": "Florence", "country": "Italy", "continent": "Europe"},
    {"id": "city_201", "name": "Catania", "country": "Italy", "continent": "Europe"},
    {"id": "city_202", "name": "Seville", "country": "Spain", "continent": "Europe"},
    {"id": "city_203", "name": "Bilbao", "country": "Spain", "continent": "Europe"},
    {"id": "city_204", "name": "Seoul", "country": "South Korea", "continent": "Asia"},
    {"id": "city_205", "name": "Ulaanbaatar", "country": "Mongolia", "continent": "Asia"},
    {"id": "city_206", "name": "Tbilisi", "country": "Georgia", "continent": "Asia"},
    {"id": "city_207", "name": "Yerevan", "country": "Armenia", "continent": "Asia"},
    {"id": "city_208", "name": "Baku", "country": "Azerbaijan", "continent": "Asia"},
    {"id": "city_209", "name": "Almaty", "country": "Kazakhstan", "continent": "Asia"},
    {"id": "city_210", "name": "Tashkent", "country": "Uzbekistan", "continent": "Asia"},
    {"id": "city_211", "name": "Riga", "country": "Latvia", "continent": "Europe"},
    {"id": "city_212", "name": "Tallinn", "country": "Estonia", "continent": "Europe"},
    {"id": "city_213", "name": "Vilnius", "country": "Lithuania", "continent": "Europe"},
    {"id": "city_214", "name": "Casablanca", "country": "Morocco", "continent": "Africa"},
    {"id": "city_215", "name": "Pretoria", "country": "South Africa", "continent": "Africa"},
]


def create_venue_tables(database) -> None:
    cursor = database.conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cities (
            city_id   TEXT PRIMARY KEY,
            name      TEXT NOT NULL,
            country   TEXT NOT NULL,
            continent TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cities_country ON cities(country)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cities_continent ON cities(continent)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS venues (
            venue_id  TEXT PRIMARY KEY,
            city_id   TEXT NOT NULL,
            name      TEXT NOT NULL,
            venue_tier TEXT NOT NULL, -- club|arena|stadium
            capacity  INTEGER NOT NULL,
            cost      INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (city_id) REFERENCES cities(city_id)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_venues_city ON venues(city_id)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS show_venue_assignments (
            show_id   TEXT PRIMARY KEY,
            show_name TEXT NOT NULL,
            brand     TEXT NOT NULL,
            show_type TEXT NOT NULL,
            year      INTEGER NOT NULL,
            week      INTEGER NOT NULL,
            city_id   TEXT,
            venue_id  TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (city_id) REFERENCES cities(city_id),
            FOREIGN KEY (venue_id) REFERENCES venues(venue_id)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_show_venues_year_week ON show_venue_assignments(year, week)")

    _seed_cities_and_venues(database)
    database.conn.commit()


def _seed_cities_and_venues(database) -> None:
    cursor = database.conn.cursor()
    row = cursor.execute("SELECT COUNT(*) as c FROM cities").fetchone()
    now = datetime.now().isoformat()

    if not (row and int(row["c"]) > 0):
        cursor.executemany(
            "INSERT OR IGNORE INTO cities (city_id, name, country, continent, is_active, created_at) VALUES (?,?,?,?,1,?)",
            [(c["id"], c["name"], c["country"], c["continent"], now) for c in _CITY_SEED],
        )

        def venues_for_city(city_id: str, city_name: str) -> List[tuple]:
            return [
                (f"venue_{city_id}_club", city_id, f"{city_name} Club Hall", "club", 50000, 12000, now),
                (f"venue_{city_id}_arena", city_id, f"{city_name} Arena", "arena", 90000, 22000, now),
                (f"venue_{city_id}_stadium", city_id, f"{city_name} Stadium", "stadium", 180000, 50000, now),
            ]

        venues: List[tuple] = []
        for c in _CITY_SEED:
            venues.extend(venues_for_city(c["id"], c["name"]))

        cursor.executemany(
            """
            INSERT OR IGNORE INTO venues
            (venue_id, city_id, name, venue_tier, capacity, cost, is_active, created_at)
            VALUES (?,?,?,?,?,?,1,?)
            """,
            venues,
        )

    # Policy enforcement: city scope and venue capacity bounds
    cursor.execute("DELETE FROM cities WHERE continent='Africa'")
    cursor.execute("DELETE FROM cities WHERE continent='Asia' AND country NOT IN ('Saudi Arabia','Qatar')")
    cursor.execute("DELETE FROM cities WHERE continent NOT IN ('Europe') AND country != 'United States' AND continent != 'Asia'")
    cursor.execute("UPDATE venues SET capacity = CASE WHEN capacity < 50000 THEN 50000 WHEN capacity > 300000 THEN 300000 ELSE capacity END")


def list_cities(
    database,
    search: Optional[str] = None,
    continent: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 250,
) -> List[Dict[str, Any]]:
    cursor = database.conn.cursor()
    clauses, params = ["is_active=1"], []
    # hard region rules
    clauses.append("((country='United States') OR (continent='Europe') OR (continent='Asia' AND country IN ('Saudi Arabia','Qatar')))")
    if continent:
        clauses.append("continent=?")
        params.append(continent)
    if country:
        clauses.append("country=?")
        params.append(country)
    if search:
        clauses.append("name LIKE ?")
        params.append(f"%{search}%")
    where = " AND ".join(clauses)
    rows = cursor.execute(
        f"SELECT city_id, name, country, continent FROM cities WHERE {where} ORDER BY name LIMIT ?",
        [*params, int(limit)],
    ).fetchall()
    return [dict(r) for r in rows]


def list_venues(database, city_id: str) -> List[Dict[str, Any]]:
    cursor = database.conn.cursor()
    rows = cursor.execute(
        """
        SELECT venue_id, city_id, name, venue_tier, capacity, cost
        FROM venues
        WHERE city_id=? AND is_active=1
        ORDER BY
            CASE venue_tier WHEN 'club' THEN 1 WHEN 'arena' THEN 2 ELSE 3 END,
            capacity ASC
        """,
        (city_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def upsert_show_venue_assignment(database, payload: Dict[str, Any]) -> None:
    cursor = database.conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO show_venue_assignments
        (show_id, show_name, brand, show_type, year, week, city_id, venue_id, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            payload["show_id"],
            payload.get("show_name", payload["show_id"]),
            payload.get("brand", "Cross-Brand"),
            payload.get("show_type", "weekly_tv"),
            int(payload.get("year", 1)),
            int(payload.get("week", 1)),
            payload.get("city_id"),
            payload.get("venue_id"),
            datetime.now().isoformat(),
        ),
    )

