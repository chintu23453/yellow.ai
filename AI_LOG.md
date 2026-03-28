# AI Log — Weather-Aware Delivery Checker

> A record of every AI prompt used to build key parts of this project.

---

## 1. Parallel Fetching Logic

**Goal:** Fire all OpenWeatherMap API calls concurrently instead of sequentially.

**Prompt used:**
> "I have a list of orders in a JSON file. Each order has a city. I need to fetch the current weather for every city at the same time (not one by one) using Python's asyncio. Show me the correct pattern using aiohttp.ClientSession and asyncio.gather, and explain why gather is better than a for-loop with await."

**What Claude produced:**
```python
async with aiohttp.ClientSession() as session:
    tasks   = [fetch_weather(session, order) for order in orders]
    results = await asyncio.gather(*tasks)
```
`asyncio.gather(*tasks)` schedules all coroutines on the event loop simultaneously, so all 4 API requests fly out at once and we collect results only after all of them complete — drastically faster than sequential `await`s.

---

## 2. Error Handling for Invalid Cities

**Goal:** The script must not crash when OpenWeatherMap returns a 404 for `InvalidCity123`.

**Prompt used:**
> "My async weather-fetch function hits the OpenWeatherMap API. If the city doesn't exist the API returns HTTP 404. If the API key is wrong it returns 401. I also need to catch generic network timeouts. Write a try/except block that handles each case separately, logs a clear error, marks the order status as 'Error', and lets the rest of the orders continue processing."

**What Claude produced (condensed):**
```python
try:
    async with session.get(...) as resp:
        if resp.status == 404:
            raise ValueError(f"City '{city}' not found (404). Skipping order {order_id}.")
        if resp.status == 401:
            raise PermissionError("Invalid API key.")
        resp.raise_for_status()
        ...
except (ValueError, PermissionError) as known_err:
    log.error(f"[Order {order_id}] SKIPPED — {known_err}")
    result["status"] = "Error"
except Exception as exc:
    log.error(f"[Order {order_id}] Unexpected error: {exc}")
    result["status"] = "Error"
```
Because each order runs inside its own coroutine, a failure in one never affects the others — `asyncio.gather` collects all results regardless.

---

## 3. AI-Powered Apology Message Generator

**Goal:** Generate a warm, personalized delay message for each affected customer.

**Prompt used (sent to Claude API at runtime):**
> "Write a short, warm, personalized delivery delay apology message for a customer. Customer name: {customer}. Destination city: {city}. Weather condition causing delay: {weather_description}. Format: Start with 'Hi {first_name},' then one sentence about the delay mentioning the city and weather, then one sentence expressing appreciation. Keep it under 40 words. Sound human and caring."

**Example output for Alice Smith / New York / heavy rain:**
> "Hi Alice, your order to New York is currently delayed due to heavy rain making safe delivery impossible right now. We truly appreciate your patience and will get it to you as soon as conditions improve!"

---

## 4. Project Structure & .env Security Pattern

**Prompt used:**
> "How do I load API keys from a .env file in Python and make sure the key is never hardcoded in the source? Show me the dotenv pattern and what a safe .env.example file looks like."

**Result:**
- All secrets stored in `.env` (git-ignored)
- `.env.example` committed to repo as a template
- `python-dotenv` loads vars at startup with `load_dotenv()`

---

## 5. Golden Flow Condition Set

**Prompt used:**
> "OpenWeatherMap returns a 'main' weather field. Which values should trigger a delivery delay? List all the dangerous or disruptive ones."

**Result:** `{"Rain", "Snow", "Extreme", "Thunderstorm", "Tornado", "Squall"}`

---

*All prompts were written and tested by the developer; Claude was used as a coding assistant.*
