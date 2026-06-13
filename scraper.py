"""
scraper.py — Beli profile scraper using Playwright
Run: python scraper.py
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright

PROFILES = {
    "manasi": "manasisridhar",
    "preddy": "preddy15",
}

OUTPUT_DIR = "."


async def scrape_profile(page, username: str) -> list[dict]:
    url = f"https://app.beliapp.com/lists/{username}"
    print(f"\n→ Loading {url}")

    restaurants = []
    api_responses = []

    async def handle_response(response):
        if "api" in response.url or "beli" in response.url:
            try:
                if response.status == 200 and "json" in response.headers.get("content-type", ""):
                    data = await response.json()
                    api_responses.append({"url": response.url, "data": data})
            except Exception:
                pass

    page.on("response", handle_response)

    await page.goto(url, wait_until="networkidle", timeout=30000)

    print(f"  Scrolling to load all restaurants...")
    for _ in range(15):
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(0.4)

    await asyncio.sleep(2)

    print(f"  Captured {len(api_responses)} API responses")
    for resp in api_responses:
        data = resp["data"]
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ["restaurants", "items", "results", "data", "list", "places"]:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break

        for item in items:
            if not isinstance(item, dict):
                continue
            name = (
                item.get("name") or item.get("restaurantName") or
                (item.get("restaurant", {}).get("name") if isinstance(item.get("restaurant"), dict) else None)
            )
            if not name:
                continue

            score = item.get("score") or item.get("userScore") or item.get("rating") or item.get("beliScore")
            cuisine = item.get("cuisine") or item.get("cuisineType") or item.get("category")
            country = (
                item.get("country") or
                (item.get("restaurant", {}).get("country") if isinstance(item.get("restaurant"), dict) else None) or
                (item.get("location", {}).get("country") if isinstance(item.get("location"), dict) else None)
            )

            restaurants.append({"name": name, "score": score, "cuisine": cuisine, "country": country})

    with open(f"{OUTPUT_DIR}/debug_{username}_api.json", "w") as f:
        json.dump(api_responses, f, indent=2, default=str)

    print(f"  ✓ Extracted {len(restaurants)} restaurants for @{username}")
    return restaurants


async def main():
    all_data = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for person, username in PROFILES.items():
            try:
                restaurants = await scrape_profile(page, username)
                all_data[person] = {
                    "username": username,
                    "restaurants": restaurants,
                    "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
            except Exception as e:
                print(f"  ✗ Error scraping {username}: {e}")
                all_data[person] = {"username": username, "restaurants": [], "error": str(e)}

        await browser.close()

    with open(f"{OUTPUT_DIR}/beli_raw.json", "w") as f:
        json.dump(all_data, f, indent=2, default=str)

    print(f"\n✓ Saved beli_raw.json")
    print(f"  Manasi: {len(all_data.get('manasi', {}).get('restaurants', []))} restaurants")
    print(f"  Preddy: {len(all_data.get('preddy', {}).get('restaurants', []))} restaurants")


if __name__ == "__main__":
    asyncio.run(main())