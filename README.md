# 🌦️ Weather-Aware Delivery Checker

Checks live weather for each order's city **concurrently** and automatically flags delivery delays, generating AI-powered apology messages via Claude.

---

## Quick Start

### 1. Clone / unzip the project

```bash
cd weather-delivery
```

### 2. Install dependencies

```bash



```

### 3. Configure API keys

```bash
cp .env.example .env
# Now edit .env and paste your real keys
```

**.env file:**
```
OPENWEATHER_API_KEY=abc123yourkey
ANTHROPIC_API_KEY=sk-ant-yourkey
```

> **Get keys:**
> - OpenWeatherMap (free): https://openweathermap.org/api
> - Anthropic: https://console.anthropic.com

### 4. Run

```bash
python weather_checker.py
```

---

## What It Does

| Feature | Implementation |
|---|---|
| **Parallel fetching** | `asyncio.gather(*tasks)` — all cities fetched simultaneously |
| **Delay detection** | Flags Rain, Snow, Extreme, Thunderstorm, Tornado, Squall |
| **AI apology messages** | Claude API generates personalized messages per delayed order |
| **Error resilience** | InvalidCity123 logs an error but script finishes all other orders |
| **Security** | API keys loaded from `.env`, never hardcoded |
| **Audit trail** | Full log written to `weather_checker.log` |

---

## Output

After running, `orders.json` is updated in-place with:

```json
{
  "order_id": "1001",
  "customer": "Alice Smith",
  "city": "New York",
  "status": "Delayed",
  "weather_main": "Rain",
  "weather_description": "heavy intensity rain",
  "temperature_c": 14.2,
  "apology_message": "Hi Alice, your order to New York is delayed due to heavy rain..."
}
```

---

## Project Structure

```
weather-delivery/
├── weather_checker.py   # Main script
├── orders.json          # Input/output order data
├── requirements.txt     # Python dependencies
├── .env.example         # API key template (commit this)
├── .env                 # Your actual keys (NEVER commit this)
├── AI_LOG.md            # Required AI prompt log
└── README.md            # This file
```

---

## Error Handling

- **404 (city not found):** Logged as error, order marked `"Error"`, script continues
- **401 (bad API key):** Logged as critical, script continues other orders
- **Network timeout:** Caught generically, order marked `"Error"`
- **AI API failure:** Falls back to a hardcoded template message
