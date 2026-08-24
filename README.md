# InterviewOS

Practice high-stakes interviews when you do not have insider access.

InterviewOS is a mock-interview **environment**: a focused interview room, an adaptive interviewer, technical items with server-side answer keys, and a coaching debrief. It is not a chat window.

## Architecture

- `api/` — Python interview engine + FastAPI (`/v1/sessions`, SSE, scoring, history)
- `web/` — Next.js App Router UI (landing, setup, room, report, history)
- `design-system/interviewos/` — visual source of truth (Swiss/navy, dark interview stage)

Demo Mode runs with no `ANTHROPIC_API_KEY`. Live mode uses Claude when the key is set.

## Local setup

Requires Python 3.11+ and Node 20+.

```bash
# API
cd api
python3 -m pip install pydantic python-dotenv fastapi httpx sqlalchemy python-jose itsdangerous uvicorn pytest
PYTHONPATH=src python3 -m uvicorn interviewos.http.app:app --reload --port 8000

# Web (another terminal)
cd web
npm install
npm run dev
```

Open http://127.0.0.1:3000. The Next.js app proxies `/backend/*` to the API.

Optional Postgres:

```bash
docker compose up -d
export DATABASE_URL=postgresql+psycopg://interviewos:interviewos@localhost:5432/interviewos
```

Copy `.env.example` to `.env`. Set `INTERVIEWOS_AUTH_BYPASS=1` for local accounts without Clerk. Set Clerk keys to use real auth.

## Tests

```bash
cd api && PYTHONPATH=src python3 -m pytest tests -q
cd web && npx playwright test
```

Live Anthropic tests are skipped unless `ANTHROPIC_API_KEY` is set.

## Product loop

1. Landing (hero + features + CTA)
2. `/practice` — setup only
3. `/interview/[id]` — dark room, streaming question, timer, optional voice
4. `/report/[id]` — bars, KPIs, reviews, rewrite, drills, download
5. Sign in to save and compare attempts in `/history`

Voice uses the Web Speech API in the browser. You can edit the transcript before submit. The server still stores text.
