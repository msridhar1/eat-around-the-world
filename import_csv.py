"""
import_csv.py — One-time import of restaurants.csv into the database.
Run: python3 import_csv.py
"""

import csv
import sqlite3
import os

DB_PATH = "eataroundtheworld.db"
CSV_PATH = "restaurants.csv"


def init_db(conn):
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
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    c = conn.cursor()

    inserted = 0
    countries_added = set()

    with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Restaurant Name", "").strip()
            country_raw = row.get("Country", "").strip()

            if not name:
                continue

            # Split multi-country entries like "Mexico / India"
            countries = [c.strip() for c in country_raw.replace(" / ", "/").split("/") if c.strip()]
            primary_country = countries[0] if countries else None

            # Insert restaurant once with primary country; skip if already exists
            c.execute("""
                INSERT OR IGNORE INTO restaurants (name, country, source)
                VALUES (?, ?, 'csv')
            """, (name, primary_country))
            inserted += 1

            # Mark all countries as done
            for country in countries:
                if country:
                    c.execute("""
                        INSERT OR REPLACE INTO countries_done (country, restaurant_name)
                        VALUES (?, ?)
                    """, (country, name))
                    countries_added.add(country)

    conn.commit()
    conn.close()

    print(f"✓ Imported {inserted} restaurants")
    print(f"✓ {len(countries_added)} countries marked as done:")
    for c in sorted(countries_added):
        print(f"   • {c}")
    print(f"\nRun: python3 app.py")


if __name__ == "__main__":
    main()
