"""
Weather-Aware Delivery Checker — Flask Web App
===============================================
A web interface to check weather for each order city
and flag delivery delays with AI-generated apology messages.
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template
import google.generativeai as genai

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY")
OPENWEATHER_URL     = "https://api.openweathermap.org/data/2.5/weather"
DELAY_CONDITIONS    = {"Rain", "Snow", "Extreme", "Thunderstorm", "Tornado", "Squall"}

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)

# ── AI Apology Generator ───────────────────────────────────────────────────────
def generate_apology_message(customer: str, city: str, weather_description: str) -> str:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model  = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"Write a short, warm, personalized delivery delay apology message. "
            f"Customer name: {customer}. City: {city}. Weather: {weather_description}. "
            f"Start with 'Hi {customer.split()[0]},' then one sentence about the delay, "
            f"then one sentence of appreciation. Max 40 words. Sound human and caring."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        log.warning(f"Gemini failed: {exc}")
        first_name = customer.split()[0]
        return (
            f"Hi {first_name}, your order to {city} is delayed due to {weather_description}. "
            f"We appreciate your patience!"
        )


# ── Async Weather Fetcher ──────────────────────────────────────────────────────
async def fetch_weather(session: aiohttp.ClientSession, order: dict) -> dict:
    city     = order["city"]
    order_id = order["order_id"]
    customer = order["customer"]
    result   = order.copy()

    params = {"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}

    try:
        async with session.get(OPENWEATHER_URL, params=params,
                               timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 404:
                raise ValueError(f"City '{city}' not found.")
            if resp.status == 401:
                raise PermissionError("Invalid OpenWeatherMap API key.")
            resp.raise_for_status()

            data         = await resp.json()
            weather_main = data["weather"][0]["main"]
            weather_desc = data["weather"][0]["description"]
            temp_c       = data["main"]["temp"]
            humidity     = data["main"]["humidity"]
            icon         = data["weather"][0]["icon"]

            result.update({
                "weather_main":        weather_main,
                "weather_description": weather_desc,
                "temperature_c":       temp_c,
                "humidity":            humidity,
                "icon":                f"https://openweathermap.org/img/wn/{icon}@2x.png",
                "fetch_error":         None,
            })

            if weather_main in DELAY_CONDITIONS:
                result["status"]          = "Delayed"
                result["apology_message"] = generate_apology_message(customer, city, weather_desc)
            else:
                result["status"]          = "On Time"
                result["apology_message"] = None

    except (ValueError, PermissionError) as e:
        log.error(f"[Order {order_id}] {e}")
        result.update({"status": "Error", "fetch_error": str(e),
                       "weather_main": None, "weather_description": None,
                       "temperature_c": None, "humidity": None,
                       "icon": None, "apology_message": None})
    except Exception as e:
        log.error(f"[Order {order_id}] Unexpected: {e}")
        result.update({"status": "Error", "fetch_error": str(e),
                       "weather_main": None, "weather_description": None,
                       "temperature_c": None, "humidity": None,
                       "icon": None, "apology_message": None})
    return result


async def run_all_checks(orders):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_weather(session, order) for order in orders]
        return await asyncio.gather(*tasks)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/check", methods=["GET"])
def check_orders():
    orders_path = Path(__file__).parent / "orders.json"
    with open(orders_path) as f:
        raw = json.load(f)

    # Reset statuses to Pending before each run
    orders = [{k: v for k, v in o.items()
               if k in ("order_id", "customer", "city", "status")} for o in raw]
    for o in orders:
        o["status"] = "Pending"

    results = asyncio.run(run_all_checks(orders))

    # Save updated orders.json
    with open(orders_path, "w") as f:
        json.dump(results, f, indent=2)

    summary = {
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total":       len(results),
        "on_time":     sum(1 for r in results if r["status"] == "On Time"),
        "delayed":     sum(1 for r in results if r["status"] == "Delayed"),
        "errors":      sum(1 for r in results if r["status"] == "Error"),
        "orders":      results,
    }
    return jsonify(summary)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
