# Atlas Financial Assistant Backend

Atlas is a Telegram-first AI financial research assistant built with FastAPI.

This first milestone implements:

```text
Telegram webhook -> SQLite persistence -> Gemini response -> Telegram reply
```

The code keeps Telegram, LLM, finance tools, and persistence isolated so watchlists, memory, alerts, voice, images, and external integrations can be added later without rewriting the webhook.

## Requirements

- Python 3.12+
- SQLite
- A Telegram bot token
- A Gemini API key
- A Finnhub API key

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
DATABASE_URL=sqlite+aiosqlite:///./atlas.db
APP_ENV=development
```

The default `DATABASE_URL` creates `atlas.db` in the project root. Use an absolute SQLite path if you deploy from a process manager with a different working directory.

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

## Prepare SQLite

Run migrations from the activated virtual environment:

```bash
alembic upgrade head
```

This creates the SQLite database file if it does not already exist.

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
