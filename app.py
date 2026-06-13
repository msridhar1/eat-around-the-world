"""
app.py — Flask server for Eat Around the World dashboard.
Run: python app.py
Access: http://localhost:5050  (or http://<your-ip>:5050 from your boyfriend's device)
"""

import csv
import os
import sqlite3
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="frontend", static_url_path="")
DB_PATH = "eataroundtheworld.db"
CSV_PATH = "restaurants.csv"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db_if_needed():
    if not os.path.exists(DB_PATH):
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
                source TEXT DEFAULT 'manual'
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
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_restaurants_name ON restaurants(name COLLATE NOCASE)")
        conn.commit()
        conn.close()


# ── Static dashboard ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


# ── API: Countries ───────────────────────────────────────────────────────────

@app.route("/api/countries")
def api_countries():
    conn = get_db()
    done_rows = conn.execute("SELECT * FROM countries_done ORDER BY country").fetchall()
    done = []
    for row in done_rows:
        rests = [dict(r) for r in conn.execute(
            "SELECT name, manasi_score, preddy_score, avg_score FROM restaurants WHERE country=? COLLATE NOCASE ORDER BY avg_score DESC",
            (row["country"],)
        ).fetchall()]
        # For multi-country restaurants the primary country differs — add by name if missing
        rn = row["restaurant_name"]
        if rn and not any(r["name"].lower() == rn.lower() for r in rests):
            extra = conn.execute(
                "SELECT name, manasi_score, preddy_score, avg_score FROM restaurants WHERE name=? COLLATE NOCASE",
                (rn,)
            ).fetchone()
            if extra:
                rests.append(dict(extra))
        d = dict(row)
        d["restaurants"] = rests
        done.append(d)
    conn.close()
    return jsonify({"done": done, "count": len(done)})


# ── API: Restaurants ─────────────────────────────────────────────────────────

@app.route("/api/restaurants")
def api_restaurants():
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM restaurants ORDER BY avg_score DESC"
    ).fetchall()]
    conn.close()
    return jsonify({"restaurants": rows, "count": len(rows)})


@app.route("/api/top5")
def api_top5():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("""
        SELECT name, cuisine, country, manasi_score, preddy_score, avg_score
        FROM restaurants
        WHERE avg_score IS NOT NULL
        ORDER BY avg_score DESC
        LIMIT 5
    """).fetchall()]
    conn.close()
    return jsonify(rows)


# ── API: Manual add restaurant ───────────────────────────────────────────────

@app.route("/api/restaurants", methods=["POST"])
def add_restaurant():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    cuisine = data.get("cuisine", "").strip() or None
    # Accept either a 'countries' list or a legacy single 'country' string
    countries_raw = data.get("countries") or ([data["country"]] if data.get("country") else [])
    countries = [c.strip() for c in countries_raw if c and c.strip()]
    primary_country = countries[0] if countries else None

    manasi_score = data.get("manasi_score")
    preddy_score = data.get("preddy_score")
    scores = [s for s in [manasi_score, preddy_score] if s is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    conn = get_db()
    cursor = conn.execute("""
        INSERT OR IGNORE INTO restaurants (name, cuisine, country, manasi_score, preddy_score, avg_score, source)
        VALUES (?, ?, ?, ?, ?, ?, 'manual')
    """, (name, cuisine, primary_country, manasi_score, preddy_score, avg_score))

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "restaurant already logged"}), 409

    for country in countries:
        conn.execute("""
            INSERT OR REPLACE INTO countries_done (country, restaurant_name, avg_score)
            VALUES (?, ?, ?)
        """, (country, name, avg_score))

    conn.commit()
    conn.close()

    # Keep CSV in sync, sorted alphabetically
    country_str = " / ".join(countries) if countries else ""
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    rows.append([name, country_str])
    rows.sort(key=lambda r: r[0].strip().lower())
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    return jsonify({"success": True, "message": f"Added {name}"}), 201


# ── API: Update restaurant ───────────────────────────────────────────────────

@app.route("/api/restaurants/<int:rid>", methods=["PATCH"])
def update_restaurant(rid):
    data = request.json
    conn = get_db()
    row = conn.execute("SELECT * FROM restaurants WHERE id=?", (rid,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404

    country = data.get("country", row["country"])
    cuisine = data.get("cuisine", row["cuisine"])

    conn.execute("UPDATE restaurants SET country=?, cuisine=? WHERE id=?", (country, cuisine, rid))

    if country:
        conn.execute("""
            INSERT OR REPLACE INTO countries_done (country, restaurant_name, avg_score)
            VALUES (?, ?, ?)
        """, (country, row["name"], row["avg_score"]))

    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ── API: Delete restaurant ───────────────────────────────────────────────────

@app.route("/api/restaurants/<int:rid>", methods=["DELETE"])
def delete_restaurant(rid):
    conn = get_db()
    conn.execute("DELETE FROM restaurants WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ── API: Stats ───────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    conn = get_db()
    countries_done = conn.execute("SELECT COUNT(*) FROM countries_done").fetchone()[0]
    restaurants_total = conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0]
    conn.close()
    return jsonify({
        "countries_done": countries_done,
        "countries_remaining": 195 - countries_done,
        "total_countries": 195,
        "restaurants_logged": restaurants_total,
    })


if __name__ == "__main__":
    init_db_if_needed()
    local_ip = os.popen("ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}'").read().strip()
    print("\n🌍 Eat Around the World Dashboard")
    print(f"   Local:   http://localhost:5050")
    if local_ip:
        print(f"   Network: http://{local_ip}:5050  ← share with your boyfriend")
    print("\nPress Ctrl+C to stop.\n")
    app.run(host="0.0.0.0", port=5050, debug=False)