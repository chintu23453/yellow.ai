# 🌦️ Weather-Aware Delivery Checker

Checks live weather for each order's destination city **concurrently** and automatically flags delivery delays, generating AI-powered apology messages using Google Gemini.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

Copy the sample environment file and add your keys:
```bash
cp .env.example .env
```

Edit your new `.env` file and paste your real keys:
```env
OPENWEATHER_API_KEY=your_openweathermap_key
GEMINI_API_KEY=your_gemini_key
```

### 3. Run the application

```bash
python weather_checker.py
```

---

## What It Does

| Feature | Implementation |
|---|---|
| **Parallel Fetching** | Uses `asyncio.gather` to fetch all cities simultaneously. |
| **Delay Detection** | Flags weather conditions: Rain, Snow, Extreme, Thunderstorm, Tornado, Squall. |
| **AI Apology Messages** | Google Gemini API generates personalized messages per delayed order. |
| **Error Resilience** | Handles 404 (City Not Found) for `InvalidCity123` safely without crashing. |
| **Security** | API keys are securely loaded from a `.env` file. |

---

## Project Structure

```text
weather-delivery/
├── weather_checker.py   # Main async Python script
├── orders.json          # Input/output order database
├── requirements.txt     # Python dependencies
├── .env.example         # Template for API keys
├── .env                 # Your actual keys (Not tracked by Git)
├── ai_log.txt           # AI prompt log for assignment submission
└── README.md            # This file
```
