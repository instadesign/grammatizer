# 📟 The Great Automatic Grammatizator

A web app inspired by Roald Dahl's short story of the same name: pull the machine's
levers — category, theme, style, ending, length, and a bank of continuous mood dials —
and watch it compose a short story **live**, one line at a time, at reading pace. Move a
dial while it's writing and the next line bends in response, without ever rewriting what
you've already read.

The control set, the machine's physical description, and the interaction model (fixed
"pre-selector" settings vs. continuously-adjustable "foot pedal" dials) are drawn
directly from Dahl's text — see `docs/history/` for the original project spec and the
research that shaped this.

## Architecture

- **`backend/`** — FastAPI. One real endpoint, `POST /api/generate/beat`, called
  repeatedly by the frontend to compose the story a short beat (~120 characters) at a
  time — plus `POST /api/export/pdf` and a health check. Stateless: the frontend holds
  "the story so far" and resends it each call. BYOK (bring your own API key) for Gemini
  or Groq, with an optional server-side env var fallback.
- **`frontend/`** — plain HTML/CSS/JS, no build step, no framework. Three screens:
  connect an engine → an ignition boot sequence (new operators only) → the illustrated
  console, styled as a creaky, whimsical steampunk machine (brass, glass valves, gauges
  — Dahl's own description of the Grammatizator, not just an aesthetic choice).
- **`deploy/`** — reference Nginx config + systemd unit for the intended production
  target (DigitalOcean VPS, Nginx reverse-proxying to uvicorn). Not applied anywhere —
  adapt the paths/domain when you're ready to deploy.

## Local development

**Backend:**

```bash
cd backend
python3 -m venv .venv        # use a real Python 3.9+, not a broken system alias
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # optional — fill in keys to test the server-side fallback
uvicorn app.main:app --reload --port 8000
```

**Frontend** (a second terminal):

```bash
cd frontend
python3 -m http.server 5500
# open http://localhost:5500
```

`frontend/js/api.js` auto-detects this two-process local setup (port 5500) and points
at `http://localhost:8000` for API calls; in production, Nginx proxies `/api/*` on the
same origin, so no CORS configuration is needed there.

## Bring your own key

Paste a Gemini or Groq API key into the sidebar on first connect — it's kept only in
`sessionStorage` for that browser session (never `localStorage`, never sent anywhere but
your chosen engine's API) and is never stored server-side. Alternatively, set
`GEMINI_API_KEY` / `GROQ_API_KEY` in `backend/.env` (local) or the systemd
`EnvironmentFile` (production) as a fallback for when no key is supplied client-side.

- [Gemini API key](https://aistudio.google.com/app/apikey) — any Google account, no card.
- [Groq API key](https://console.groq.com/keys) — free sign-up, no card, much faster generation.

## Content

A fixed "Safety Governor" instruction is always appended server-side, regardless of any
dial setting: no heavy profanity, no explicit sexual content or graphic violence — but
saucy, suggestive, cheeky innuendo is explicitly encouraged (British-comedy tradition,
not blandness). See `backend/app/prompts.py`.

## Deploying

1. Copy `backend/` and `frontend/` to the server (e.g. `/var/www/grammatizer/`).
2. Build the backend venv there and install `backend/requirements.txt`.
3. Adapt and install `deploy/systemd/grammatizer.service`, with real keys in
   `/etc/grammatizer/grammatizer.env`.
4. Adapt and install `deploy/nginx/grammatizer.conf`, then run `certbot` for TLS.
