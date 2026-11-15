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
  "the story so far" and resends it each call. BYOK (bring your own API key) for any
  of four engines (Gemini, Groq, ChatGPT, Claude), with an optional server-side env var
  fallback.
- **`index.html`, `css/`, `js/`, `assets/`** (repo root) — plain HTML/CSS/JS, no build
  step, no framework, deliberately sitting at the root rather than under a `frontend/`
  subfolder so a plain static-file upload (FTP, hPanel File Manager, etc.) can drop
  these straight into a hosting subfolder with no restructuring. Three screens: connect
  an engine (a title page) → a boot sequence (new operators only) → the console, which
  is one pen-and-watercolour drawing of the machine that you operate directly: drums
  for the pre-selectors, organ stops that pull out, foot pedals with gauges, a lever.
  See "The drawing" below.
- **`tools/draw/`** — the Python that draws every SVG in `assets/svg/`. Not part of
  the site and not needed to run or deploy it; the SVGs it writes are committed.
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

**Frontend** (a second terminal, from the repo root):

```bash
python3 serve.py 5500
# open http://localhost:5500
```

(`serve.py` is `http.server` with `Cache-Control: no-store` added — plain
`python3 -m http.server` works too, but its default caching has repeatedly served
stale CSS/JS mid-session during development.)

`js/api.js` auto-detects this two-process local setup (port 5500) and points at
`http://localhost:8000` for API calls; in production, Nginx proxies `/api/*` on the
same origin, so no CORS configuration is needed there. Deploying the frontend
somewhere that can't also proxy `/api/*` on the same origin (e.g. static hosting with
the backend elsewhere) needs `ALLOWED_ORIGINS` set on the backend and
`window.GRAMMATIZER_API_BASE` set before `js/api.js` loads.

## The drawing

The console is a fixed 1600 × 900 scene scaled as a whole to fit the window (see the
comment at the top of `css/stage.css`), not a layout that reflows. That is a deliberate
trade: the illustration comes first and the app is **desktop only**. Small laptop
windows scroll around the drawing rather than shrinking it past legibility; phones get
a notice.

- `assets/svg/plates/console.svg` is everything that never moves. Anything that moves,
  lights up or repeats is its own file in `assets/svg/parts/`, laid over the plate by
  `css/stage.css` and `css/console.css`.
- Every control is still a native form element underneath the artwork, which is what
  keeps keyboard and screen-reader use working.
- `js/machine.js` turns what the app is doing into motion and sound; `js/sound.js`
  synthesises the sounds (no audio files). Sound starts at the first pull of the lever
  and the ear-trumpet on the machine mutes it.
- Motion comes from two places. What the *machine* does (cogs driven while it writes,
  the lever, the gauges) is page CSS in `css/animations.css`, keyed off the machine's
  state; at rest the gearing creeps round, and stops only for a pause or a jam. What a
  *drawing* does by itself (the four engines on the title page, the key, and the
  workshop's small lives: the cat, the kettle, the mouse, the lamps, the fire, someone
  behind the spy-hole) is written into its own SVG file by the drawing code, as CSS
  animation: `d.part(...)`, `d.keyframes(...)`, `d.animate(...)` in `tools/draw/ink.py`.
- Those files animate by themselves in a plain `<img>`, which is how `index.html`
  uses them, but that is costly: the browser repaints an animated image whole on every
  frame, and these drawings are slow to paint. So `js/art.js` takes each one apart
  into layers, one per moving part, which the browser can slide and turn without
  repainting. Measured on the console, ten small pictures kept nearly half a
  processor core busy as images and under a third of that as layers. Do not add motion
  to a drawing that is not on its list, and never to the plate itself.
- The workshop's lives are drawn on the plate in place and then lifted out of it into
  `assets/svg/parts/life-*.svg` (`d.lift(...)`; their boxes are `LIFE` in `layout.py`).
  Lifting takes the same strokes out of the same random stream, so it changes nothing
  else on the plate. Anything NEW has to be drawn last, or it re-rolls the wobble of
  every stroke after it.
- `python3 -m tools.draw.frames sheet.html engine-openai:8:16` writes a contact sheet:
  a drawing's motion as sixteen stills across eight seconds. Motion cannot be judged
  from one screenshot, and a headless browser's clock is not a way to catch a pose.
- Everything that moves only to be looked at stops for "reduce motion", and pauses
  when the page has not been touched for three minutes (never while it is writing).
- Positions live in one place, `tools/draw/layout.py`, which writes `css/layout.css`.
  To move something, change it there and run `python3 -m tools.draw.build` from the
  repo root (standard library only). Don't edit `css/layout.css` or the SVGs by hand.
- `tools/style-sheet.html` shows the main parts on one page, working.
- Add `?mock=1` to the address to watch the machine write a canned story with no key,
  no backend and no quota; `?mock=jam` makes it jam once part-way through.

## Bring your own key

Choose an engine on the title page and paste a key for it — it's kept only in
`sessionStorage` for that browser session (never `localStorage`, never sent anywhere but
your chosen engine's API) and is never stored server-side. Alternatively, set
`GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in
`backend/.env` (local) or the host's environment (production) as a fallback for when no
key is supplied client-side.

Two engines are free:

- [Gemini API key](https://aistudio.google.com/app/apikey) — any Google account, no card.
- [Groq API key](https://console.groq.com/keys) — free sign-up, no card, much faster generation.

Two are paid by use, and need an API account with credit on it. A ChatGPT or Claude
subscription is billed separately and does **not** include any; a key from an account
with no credit is sent back to the title page with a message saying so.

- [OpenAI API key](https://platform.openai.com/api-keys) — the "ChatGPT" engine.
- [Anthropic API key](https://platform.claude.com/settings/keys) — the "Claude" engine.

Which model each engine runs is one line per engine in `backend/app/engines.py`
(`ENGINES`), with the prices noted beside it; `ENGINE_MODEL_NAMES` in
`js/screens/console.js` repeats the names for the PDF's colophon. Adding an engine
touches those two, `Engine` in `backend/app/schemas.py`, `translate_exception` in
`backend/app/errors.py`, a card in `index.html` and a drawing in `tools/draw/parts.py`.

## Content

A fixed "Safety Governor" instruction is always appended server-side, regardless of any
dial setting: no heavy profanity, no explicit sexual content or graphic violence — but
saucy, suggestive, cheeky innuendo is explicitly encouraged (British-comedy tradition,
not blandness). See `backend/app/prompts.py`.

## Deploying

The frontend (`index.html`, `css/`, `js/`, `assets/`) is just static files — it can go
anywhere, including a subfolder of an existing site via plain FTP/File Manager upload.
`tools/` is not part of it and does not need uploading.
The backend needs somewhere that can run a persistent Python process (a VPS, not
typical shared hosting) — until it's deployed and reachable at `/api/*`, the console
will pull the lever and get a generic "The machine refused that," since nothing is
answering the request yet, not a real per-engine error.

### The live site (josieandhenry.co.uk/grammatizator/)

The live copy is embedded in a WordPress page, not served as a folder:

- The page holds one shortcode, `[php_snippet id="181"]`. That snippet (ASE Pro's Code
  Snippets Manager; file `wp-content/code-snippets/181.php`, also stored in post 181)
  prints the app's markup. `python3 -m tools.embed_wordpress <release>` writes it from
  `index.html`; its docstring explains what it adds for the live site.
- `css/`, `js/` and `assets/` go in `wp-content/uploads/grammatizer/<release>/`, a new
  folder per release (e.g. `v020b`). Uploaded files are cached for a week, so never
  overwrite a release in place; a new folder is also what makes rollback instant.
- To release: upload the three folders to a new release folder, generate the snippet
  for that folder, `php -l` it, keep a copy of the current `181.php`, then replace
  `181.php` and update post 181's content to match. The plugin revalidates the file on
  the next page load. To roll back, put the previous `181.php` back.
- The backend is a separate deploy (Render, from `render.yaml`). When a release needs
  a backend change (a new engine, a new field), the backend goes first: the old page
  works against a newer backend, but a new page asking an old backend for an engine it
  has never heard of gets a validation error on every pull of the lever.
- The backend is the Render service at `api.josieandhenry.co.uk` (`render.yaml`). On the
  free plan it sleeps, so the first request after a quiet spell can take most of a minute.

Full VPS deploy (frontend + backend together, single origin, no CORS needed):

1. Copy the whole repo to the server (e.g. `/var/www/grammatizer/`).
2. Build the backend venv there and install `backend/requirements.txt`.
3. Adapt and install `deploy/systemd/grammatizer.service`, with real keys in
   `/etc/grammatizer/grammatizer.env`.
4. Adapt and install `deploy/nginx/grammatizer.conf`, then run `certbot` for TLS. Note
   this config's `root` now points at the full repo checkout (no more `frontend/`
   subfolder boundary) — its deny rules for `backend/`, `deploy/`, `docs/`, `tools/`, etc. are
   load-bearing, not optional. Prefer deploying only the public files to a dedicated
   directory instead, if you'd rather not rely on those rules.

Split deploy (frontend on existing static hosting, backend elsewhere — e.g. a
Hostinger VPS, Render, Fly.io): set `ALLOWED_ORIGINS` on the backend to the frontend's
origin, and set `window.GRAMMATIZER_API_BASE = "https://your-backend-host"` in a small
inline `<script>` before `js/api.js` loads in the deployed `index.html`.
