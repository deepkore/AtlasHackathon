# Atlas Financial Assistant Backend

Atlas is a Telegram-first AI financial research assistant built with FastAPI.

This first milestone implements:

```text
Telegram webhook -> PostgreSQL persistence -> Gemini response -> Telegram reply
```

The code keeps Telegram, LLM, finance tools, and persistence isolated so watchlists, memory, alerts, voice, images, and external integrations can be added later without rewriting the webhook.

## Requirements

- Python 3.10+
- PostgreSQL
- Telegram Bot Token (from BotFather)
- Finnhub API Key
- NewsAPI Key
- Google Gemini API Key

## Database Relationships

The database maintains the following primary relationships for managing users and context:

```text
User
 |
 +-- UserPreference (1:1) - Stores user role, timezone, and flexible interests.
 |
 +-- Watchlist (1:N)      - Stores specific stock ticker symbols the user is tracking.
 |
 +-- Messages (1:N)       - Stores conversation history with the agent.
```

## User Preferences

Atlas persists information about you to personalize its research. The `UserPreference` record stores:
- **Role**: Your professional context (e.g., Investor, Analyst).
- **Interests**: A flexible JSON list of topics, sectors, or themes you care about (e.g., `["AI", "Semiconductors"]`).

The agent uses these preferences as context when you ask broad questions like "What's happening today?", enabling it to prioritize news and data about your areas of interest.

## Watchlists

You can explicitly ask Atlas to track specific companies. Unlike general interests, a Watchlist contains explicit stock ticker symbols (e.g., `NVDA`, `MSFT`). Watchlists are managed via natural language.

### Examples

You can manage your preferences and watchlists using natural language without any slash commands:

* **Update role**: *"I'm an analyst interested in AI."*
* **Add to watchlist**: *"Track Nvidia."*
* **Add another company**: *"Also track AMD."*
* **Remove from watchlist**: *"Stop tracking Nvidia."*
* **Check watchlist**: *"What am I following?"*
* **Check preferences**: *"What are my interests?"*

## Create A Telegram Bot

1. Open Telegram and message `@BotFather`.
2. Send `/newbot`.
3. Choose a bot name and username.
4. Copy the bot token into `.env` as `TELEGRAM_BOT_TOKEN`.
5. Generate a long random value for `TELEGRAM_WEBHOOK_SECRET`. Telegram sends it back in the `X-Telegram-Bot-Api-Secret-Token` header.

## Gemini Credentials

1. Create or open a Google AI Studio project.
2. Create an API key for Gemini.
3. Add it to `.env` as `GEMINI_API_KEY`.
4. `LLM_MODEL` defaults to `gemini-2.5-flash`.

## Finnhub API Key

1. Create a Finnhub account.
2. Generate an API key.
3. Add it to `.env` as `FINNHUB_API_KEY`.

Only `get_stock_quote` is implemented in the first milestone. Other financial tools are scaffolded.

## Configure Environment

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Required variables:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
GEMINI_API_KEY=
LLM_MODEL=gemini-2.5-flash
FINNHUB_API_KEY=
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/atlas
APP_ENV=development
```

The default `DATABASE_URL` connects to a local `atlas` database. Create this database in your PostgreSQL instance before running migrations.

## Create A Virtual Environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

For production deployment, install runtime dependencies only:

```bash
python -m pip install -r requirements.txt
```

## Prepare PostgreSQL

Run migrations from the activated virtual environment:

```bash
alembic upgrade head
```

This applies the schema to the PostgreSQL database specified in `DATABASE_URL`. Make sure the database exists.

## Run The API

From the activated virtual environment:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Run Tests

Install dev dependencies, then run:

```bash
pytest
```
## Milestone 4: Scheduled Briefings & Proactive Intelligence

Atlas is now proactive. Users can schedule daily morning briefings or evening summaries using natural language.

### Scheduled Briefing Architecture
- **Scheduler**: A lightweight background task runs inside `main.py` that periodically checks for due scheduled tasks in the database.
- **BriefingService**: When a task is due, this service retrieves the user's preferences and watchlist, gathers the latest news and SEC filings, filters out previously sent items, and uses Gemini's structured output to decide if the information is meaningful enough to send. If `should_send` is true and the importance score passes the threshold, it sends a Telegram message.
- **Timezone Handling**: Scheduled tasks are stored with the user's IANA timezone (e.g. `America/New_York`). The scheduler calculates the exact UTC time for the next execution (`next_run_at`) based on this timezone.
- **Notification History**: Sent events (articles, filings) are recorded in the `notification_history` table to prevent sending duplicate information in successive briefings.

### Supported Briefing Types
- `morning_briefing`: Generally sent early in the day.
- `evening_summary`: Generally sent after market close.

### Natural Language Examples
Users can schedule briefings naturally in the Telegram chat:
- "Send me a morning briefing every day at 8:30 AM."
- "Give me an evening market summary every weekday at 6 PM."
- "Stop my morning briefing."
- "Show me my scheduled briefings."

### Environment Variables
New variables have been introduced:
- `BRIEFING_IMPORTANCE_THRESHOLD`: Minimum Gemini importance score to send a briefing (e.g. `0.75`).
- `SCHEDULER_ENABLED`: Boolean to enable/disable the background scheduler (default: `true`).
- `SCHEDULER_POLL_INTERVAL_SECONDS`: How often the scheduler checks for due tasks (default: `30`). **This does not poll financial APIs.**
- `MAX_BRIEFING_ARTICLES` / `MAX_WATCHLIST_ITEMS_PER_BRIEFING`: Limits for retrieved data per briefing.

### Database Migrations
Migrations have been generated for the `scheduled_tasks` and `notification_history` tables. Ensure you run:
```bash
alembic upgrade head
```

### Deployment Considerations
- **Local Development**: The built-in scheduler in FastAPI's lifespan is sufficient.
- **Production**: If deploying multiple instances (horizontal scaling), the current simple `SELECT ... FOR UPDATE SKIP LOCKED` inside the `ScheduledTaskRepository` allows basic concurrency control, preventing multiple instances from executing the same task.
- **Note**: Continuous financial API polling and event-triggered alerts (like 7% movement alerts or real-time price monitoring) are explicitly **not implemented** yet. Financial APIs are only queried when a user's scheduled briefing executes.
Tests mock Telegram, Gemini, and Finnhub. They do not make real external API calls.

## Test The Telegram Webhook Locally

1. Run migrations:

```bash
alembic upgrade head
```

2. Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

3. Expose `localhost:8000` using a tunneling service such as ngrok, Cloudflare Tunnel, or localtunnel.

Example with ngrok:

```bash
ngrok http 8000
```

4. Set the Telegram webhook:

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://YOUR_PUBLIC_TUNNEL_URL/webhooks/telegram","secret_token":"YOUR_TELEGRAM_WEBHOOK_SECRET"}'
```

5. Send a message to your bot in Telegram.

## Project Structure

```text
app/
  main.py
  api/telegram.py
  agent/agent.py
  agent/prompts.py
  agent/tools.py
  llm/base.py
  llm/gemini.py
  finance/finnhub.py
  finance/sec.py
  database/session.py
  database/models.py
  database/repositories.py
  services/conversation.py
  services/telegram.py
  schemas/telegram.py
  schemas/agent.py
tests/
alembic/
```

## Deployment Notes

Use Python 3.12+ on the server, create a virtual environment, install `requirements.txt`, configure environment variables, run `alembic upgrade head`, then run the app with a process manager.

Example application command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For production, place Uvicorn behind a reverse proxy or platform router that terminates HTTPS. Telegram webhooks require a public HTTPS URL.

## Known Limitations

This milestone does not implement Gmail, calendar, files, sheets, voice, image analysis, scheduled briefings, alert workers, vector search, or full SEC ticker-to-CIK lookup.

The current tool set only implements live stock quotes through Finnhub. Company profile, news, earnings, and SEC filings are scaffolded for function calling but return explicit unavailable messages until implemented.

## Recommended Next Milestone

Implement robust tool calling for company profile, news, earnings, and SEC filings, then add intent tests for common finance questions like "Tell me about Nvidia" and "Summarize Apple's latest earnings."
