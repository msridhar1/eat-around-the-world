# 🌍 Eat Around the World Dashboard

A personal dashboard for Manasi & Preddy to track their mission to eat the cuisine of every country.

---

## Quick Start

### 1. Setup (once)
```bash
bash setup.sh
```

### 2. Run the dashboard
```bash
bash run.sh
```

Open **http://localhost:5050** on your computer.  
Your boyfriend opens **http://YOUR-IP:5050** on his device (same WiFi required).

---

## Adding Your Restaurants

### Option A: Sync from Beli (automatic)
Click **↻ Sync Beli** in the dashboard. This runs the Playwright scraper against both your public Beli profiles.

**Important note on the scraper:** Beli is a JavaScript-heavy single-page app. The scraper intercepts the API calls Beli makes when loading your profile. This works best if:
- Your profiles are public (they are ✓)
- You run it while connected to the internet

If the scraper gets 0 restaurants, Beli may have changed their API. In that case, use Option B.

### Option B: Manual entry (always works)
Click **+ Add Restaurant** and fill in:
- Restaurant name
- Cuisine (e.g. "Japanese")
- Country (e.g. "Japan") — type to autocomplete from all 195 countries
- Both your Beli scores

### Option C: Bulk import via JSON
Edit `beli_raw.json` directly (or use the template `beli_raw_template.json`), then run:
```bash
python3 sync.py
```

Format:
```json
{
  "manasi": {
    "username": "manasisridhar",
    "restaurants": [
      {"name": "Nobu", "score": 9.2, "cuisine": "Japanese", "country": "Japan"},
      {"name": "Le Bernardin", "score": 9.5, "cuisine": "French", "country": "France"}
    ]
  },
  "preddy": {
    "username": "preddy15", 
    "restaurants": [
      {"name": "Nobu", "score": 8.8, "cuisine": "Japanese", "country": "Japan"}
    ]
  }
}
```

Only restaurants in **both** lists will be added to the dashboard.

---

## Rules (as you defined them)
1. Each restaurant counts for one cuisine, even if fusion
2. Both of you must have eaten there for it to count

The sync script enforces rule 2 — only restaurants on **both** Beli lists are cross-referenced.

For rule 1, when a restaurant has multiple cuisines, assign the country manually using the + Add form.

---

## Assigning Countries to Restaurants

The scraper tries to auto-detect countries from cuisine names (e.g. "Italian" → Italy). If a restaurant doesn't get a country assigned, you'll see a warning in the terminal when you run `sync.py`.

Fix it by:
1. Using **+ Add Restaurant** with the country filled in
2. Or patching via the API: `PATCH /api/restaurants/{id}` with `{"country": "Japan"}`

---

## Auto-sync Schedule

To run the sync automatically (e.g. nightly), add to your Mac's crontab:
```bash
crontab -e
```
Add:
```
0 2 * * * cd /path/to/eat-around-the-world && python3 scraper.py && python3 sync.py
```

---

## File Structure
```
eat-around-the-world/
├── setup.sh           # one-time install
├── run.sh             # start dashboard
├── scraper.py         # Playwright Beli scraper
├── sync.py            # cross-reference + DB update
├── app.py             # Flask server + API
├── eataroundtheworld.db  # SQLite database (auto-created)
├── beli_raw.json      # raw scraped data (auto-created)
├── beli_raw_template.json  # template for manual entry
└── frontend/
    └── index.html     # full dashboard UI
```

---

## Troubleshooting

**Scraper gets 0 restaurants:**
Beli's app structure may have changed. Use manual entry or the JSON bulk import.

**Map doesn't load:**
The map requires internet to load the world GeoJSON from a CDN. Check your connection.

**Boyfriend can't connect:**
- Make sure you're both on the same WiFi network
- Check your Mac's firewall: System Settings → Network → Firewall → allow incoming connections on port 5050
- Find your IP: run `ipconfig getifaddr en0` in Terminal

**Port 5050 in use:**
Edit `app.py` and change `port=5050` to another number like `5051`.
