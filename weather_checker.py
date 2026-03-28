"""
Weather-Aware Delivery Delay Checker
=====================================
Checks weather for each order city concurrently and flags delivery delays.
Uses OpenWeatherMap API + Google Gemini AI for personalized apology messages.
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
import google.generativeai as genai

# ── Setup ──────────────────────────────────────────────────────────────────────
load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY")

OPENWEATHER_URL  = "https://api.openweathermap.org/data/2.5/weather"
DELAY_CONDITIONS = {"Rain", "Snow", "Extreme", "Thunderstorm", "Tornado", "Squall"}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("weather_checker.log"),
    ],
)
log = logging.getLogger(__name__)

# ── AI Apology Generator (Google Gemini) ──────────────────────────────────────
def generate_apology_message(customer: str, city: str, weather_description: str) -> str:
    """
    AI Challenge: Uses Google Gemini to write a personalized Weather-Aware Apology.
    Prompt: 'Write a short, warm, personalized delivery delay apology for
    {customer} whose order to {city} is delayed due to {weather}. Max 2 sentences.'
    """
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model  = genai.GenerativeModel("gemini-1.5-flash")   # free-tier model
        prompt = (
            f"Write a short, warm, personalized delivery delay apology message for a customer. "
            f"Customer name: {customer}. Destination city: {city}. "
            f"Weather condition causing delay: {weather_description}. "
            f"Format: Start with 'Hi {customer.split()[0]},' then one sentence about the delay "
            f"mentioning the city and weather, then one sentence expressing appreciation. "
            f"Keep it under 40 words. Sound human and caring."
        )
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as exc:
        log.warning(f"AI apology generation failed ({exc}), using fallback.")
        first_name = customer.split()[0]
        return (
            f"Hi {first_name}, your order to {city} is delayed due to {weather_description}. "
            f"We appreciate your patience!"
        )


# ── Weather Fetcher ────────────────────────────────────────────────────────────
async def fetch_weather(session: aiohttp.ClientSession, order: dict) -> dict:
    """
    Fetches weather for a single order's city asynchronously.
    Returns enriched order dict with weather data or error info.
    """
    city       = order["city"]
    order_id   = order["order_id"]
    customer   = order["customer"]
    result     = order.copy()

    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}

    try:
        async with session.get(OPENWEATHER_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 404:
                raise ValueError(f"City '{city}' not found (404). Skipping order {order_id}.")
            if resp.status == 401:
                raise PermissionError("Invalid OpenWeatherMap API key. Check your .env file.")
            resp.raise_for_status()

            data            = await resp.json()
            weather_main    = data["weather"][0]["main"]          # e.g. "Rain"
            weather_desc    = data["weather"][0]["description"]   # e.g. "heavy intensity rain"
            temp_c          = data["main"]["temp"]

            result["weather_main"]        = weather_main
            result["weather_description"] = weather_desc
            result["temperature_c"]       = temp_c
            result["fetch_error"]         = None

            # ── Golden Flow Logic ──────────────────────────────────────────────
            if weather_main in DELAY_CONDITIONS:
                result["status"]          = "Delayed"
                result["apology_message"] = generate_apology_message(customer, city, weather_desc)
                log.warning(
                    f"[Order {order_id}] {customer} → {city} | "
                    f"⚠  DELAYED ({weather_main}: {weather_desc}, {temp_c}°C)"
                )
            else:
                result["status"]          = "On Time"
                result["apology_message"] = None
                log.info(
                    f"[Order {order_id}] {customer} → {city} | "
                    f"✓  ON TIME ({weather_main}: {weather_desc}, {temp_c}°C)"
                )

    except (ValueError, PermissionError) as known_err:
        # Graceful handling for invalid city / bad API key
        log.error(f"[Order {order_id}] SKIPPED — {known_err}")
        result["status"]              = "Error"
        result["fetch_error"]         = str(known_err)
        result["weather_main"]        = None
        result["weather_description"] = None
        result["temperature_c"]       = None
        result["apology_message"]     = None

    except Exception as exc:
        # Catch-all: network issues, timeouts, etc.
        log.error(f"[Order {order_id}] Unexpected error for city '{city}': {exc}")
        result["status"]              = "Error"
        result["fetch_error"]         = str(exc)
        result["weather_main"]        = None
        result["weather_description"] = None
        result["temperature_c"]       = None
        result["apology_message"]     = None

    return result


# ── Main Orchestrator ──────────────────────────────────────────────────────────
async def main():
    log.info("=" * 60)
    log.info("  Weather-Aware Delivery Checker  —  Starting")
    log.info(f"  Run timestamp: {datetime.now().isoformat()}")
    log.info("=" * 60)

    # Validate env vars
    if not OPENWEATHER_API_KEY:
        log.critical("OPENWEATHER_API_KEY is missing from .env. Aborting.")
        return
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY missing — AI apologies will use fallback template.")

    # Load orders
    orders_path = Path(__file__).parent / "orders.json"
    with open(orders_path, "r") as f:
        orders = json.load(f)
    log.info(f"Loaded {len(orders)} orders from orders.json")

    # ── PARALLEL FETCH (Promise.all equivalent) ────────────────────────────────
    # All API calls are fired concurrently with asyncio.gather — NOT sequentially.
    async with aiohttp.ClientSession() as session:
        tasks   = [fetch_weather(session, order) for order in orders]
        results = await asyncio.gather(*tasks)   # <── concurrent execution

    # ── Save updated orders.json ───────────────────────────────────────────────
    with open(orders_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info(f"Updated orders.json saved to {orders_path}")

    # ── Print Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DELIVERY STATUS SUMMARY")
    print("=" * 60)

    delayed_count  = 0
    ontime_count   = 0
    error_count    = 0

    for r in results:
        status_icon = {"Delayed": "⚠ ", "On Time": "✓ ", "Error": "✗ "}.get(r["status"], "? ")
        print(f"\n  {status_icon} Order {r['order_id']} — {r['customer']} → {r['city']}")
        print(f"     Status      : {r['status']}")
        if r.get("weather_main"):
            print(f"     Weather     : {r['weather_description']} ({r['temperature_c']}°C)")
        if r.get("apology_message"):
            print(f"     AI Message  : {r['apology_message']}")
        if r.get("fetch_error"):
            print(f"     Error       : {r['fetch_error']}")

        if r["status"] == "Delayed":  delayed_count += 1
        elif r["status"] == "On Time": ontime_count += 1
        else:                          error_count  += 1

    print("\n" + "-" * 60)
    print(f"  Total: {len(results)} orders | "
          f"✓ On Time: {ontime_count} | "
          f"⚠  Delayed: {delayed_count} | "
          f"✗ Errors: {error_count}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # ── Keep-Alive Loop for Railway deployment ─────────────────────────────────
    # Runs the checker every 10 minutes so Railway doesn't think the app crashed.
    import time
    INTERVAL_MINUTES = 10
    while True:
        asyncio.run(main())
        log.info(f"Sleeping {INTERVAL_MINUTES} minutes before next check...")
        time.sleep(INTERVAL_MINUTES * 60)
