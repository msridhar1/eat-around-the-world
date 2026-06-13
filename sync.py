"""
sync.py — Cross-reference both Beli lists and update SQLite DB.
Run: python sync.py
"""

import json
import sqlite3
import os
import re

DB_PATH = "eataroundtheworld.db"
RAW_PATH = "beli_raw.json"

CUISINE_TO_COUNTRY = {
    "american": "United States", "mexican": "Mexico", "tex-mex": "Mexico",
    "brazilian": "Brazil", "peruvian": "Peru", "argentinian": "Argentina",
    "colombian": "Colombia", "venezuelan": "Venezuela", "cuban": "Cuba",
    "jamaican": "Jamaica", "haitian": "Haiti", "salvadoran": "El Salvador",
    "guatemalan": "Guatemala", "honduran": "Honduras", "nicaraguan": "Nicaragua",
    "costa rican": "Costa Rica", "chilean": "Chile", "ecuadorian": "Ecuador",
    "bolivian": "Bolivia", "uruguayan": "Uruguay", "trinidadian": "Trinidad and Tobago",
    "canadian": "Canada", "italian": "Italy", "french": "France", "spanish": "Spain",
    "greek": "Greece", "portuguese": "Portugal", "german": "Germany",
    "austrian": "Austria", "swiss": "Switzerland", "belgian": "Belgium",
    "dutch": "Netherlands", "swedish": "Sweden", "norwegian": "Norway",
    "danish": "Denmark", "finnish": "Finland", "icelandic": "Iceland",
    "british": "United Kingdom", "irish": "Ireland", "polish": "Poland",
    "czech": "Czech Republic", "hungarian": "Hungary", "romanian": "Romania",
    "bulgarian": "Bulgaria", "serbian": "Serbia", "croatian": "Croatia",
    "ukrainian": "Ukraine", "russian": "Russia", "georgian": "Georgia",
    "armenian": "Armenia", "turkish": "Turkey", "moroccan": "Morocco",
    "tunisian": "Tunisia", "egyptian": "Egypt", "lebanese": "Lebanon",
    "syrian": "Syria", "jordanian": "Jordan", "israeli": "Israel",
    "iraqi": "Iraq", "iranian": "Iran", "persian": "Iran",
    "saudi": "Saudi Arabia", "emirati": "United Arab Emirates", "yemeni": "Yemen",
    "ethiopian": "Ethiopia", "eritrean": "Eritrea", "somali": "Somalia",
    "kenyan": "Kenya", "ugandan": "Uganda", "tanzanian": "Tanzania",
    "nigerian": "Nigeria", "ghanaian": "Ghana", "senegalese": "Senegal",
    "south african": "South Africa", "indian": "India", "pakistani": "Pakistan",
    "bangladeshi": "Bangladesh", "sri lankan": "Sri Lanka", "nepali": "Nepal",
    "afghan": "Afghanistan", "chinese": "China", "japanese": "Japan",
    "korean": "South Korea", "taiwanese": "Taiwan", "vietnamese": "Vietnam",
    "thai": "Thailand", "cambodian": "Cambodia", "burmese": "Myanmar",
    "malaysian": "Malaysia", "singaporean": "Singapore", "indonesian": "Indonesia",
    "filipino": "Philippines", "mongolian": "Mongolia", "australian": "Australia",
    "new zealand": "New Zealand", "fijian": "Fiji",
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cuisine TEXT,
            country TEXT,
            manasi_score REAL,
            preddy_score REAL,
            avg_score REAL,
            added_at TEXT DEFAULT (datetime('now')),
            source TEXT DEFAULT 'beli'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS countries_done (
            country TEXT PRIMARY KEY,
            restaurant_name TEXT,
            avg_score REAL,
            completed_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def guess_country(cuisine, name):
    text = (cuisine or "").lower() + " " + (name or "").lower()
    for keyword, country in CUISINE_TO_COUNTRY.items():
        if keyword in text:
            return country
    return None


def cross_reference(manasi_list, preddy_list):
    def norm(s):
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    preddy_map = {norm(r["name"]): r for r in preddy_list if r.get("name")}
    shared = []

    for r in manasi_list:
        key = norm(r.get("name", ""))
        if not key or key not in preddy_map:
            continue
        preddy_r = preddy_map[key]
        manasi_score = r.get("score")
        preddy_score = preddy_r.get("score")
        scores = [s for s in [manasi_score, preddy_score] if s is not None]
        avg = sum(scores) / len(scores) if scores else None
        cuisine = r.get("cuisine") or preddy_r.get("cuisine")
        country = r.get("country") or preddy_r.get("country") or guess_country(cuisine, r.get("name"))
        shared.append({
            "name": r["name"], "cuisine": cuisine, "country": country,
            "manasi_score": manasi_score, "preddy_score": preddy_score, "avg_score": avg,
        })

    print(f"  ✓ {len(shared)} shared restaurants found")
    return shared


def upsert_restaurants(conn, shared):
    c = conn.cursor()
    inserted, updated = 0, 0
    for r in shared:
        c.execute("SELECT id FROM restaurants WHERE name = ?", (r["name"],))
        row = c.fetchone()
        if row:
            c.execute("""
                UPDATE restaurants SET cuisine=?, country=?, manasi_score=?, preddy_score=?, avg_score=?
                WHERE id=?
            """, (r["cuisine"], r["country"], r["manasi_score"], r["preddy_score"], r["avg_score"], row[0]))
            updated += 1
        else:
            c.execute("""
                INSERT INTO restaurants (name, cuisine, country, manasi_score, preddy_score, avg_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (r["name"], r["cuisine"], r["country"], r["manasi_score"], r["preddy_score"], r["avg_score"]))
            inserted += 1
    conn.commit()
    print(f"  DB: {inserted} inserted, {updated} updated")


def rebuild_countries(conn):
    c = conn.cursor()
    c.execute("DELETE FROM countries_done")
    c.execute("""
        INSERT INTO countries_done (country, restaurant_name, avg_score)
        SELECT country, name, MAX(avg_score)
        FROM restaurants
        WHERE country IS NOT NULL AND country != ''
        GROUP BY country
    """)
    conn.commit()
    count = c.execute("SELECT COUNT(*) FROM countries_done").fetchone()[0]
    print(f"  ✓ {count} countries marked as done")


def main():
    print("=== Eat Around the World — Sync ===\n")
    conn = init_db()

    if not os.path.exists(RAW_PATH):
        print(f"✗ {RAW_PATH} not found. Run python scraper.py first.")
        return

    with open(RAW_PATH) as f:
        raw = json.load(f)

    manasi_list = raw.get("manasi", {}).get("restaurants", [])
    preddy_list = raw.get("preddy", {}).get("restaurants", [])
    print(f"Loaded: {len(manasi_list)} Manasi, {len(preddy_list)} Preddy restaurants")

    shared = cross_reference(manasi_list, preddy_list)
    upsert_restaurants(conn, shared)
    rebuild_countries(conn)
    print(f"\n✓ Done. Run python app.py to start the dashboard.")


if __name__ == "__main__":
    main()