# Forma Studio — Free CPU Edition

Create narrated video ads on a regular computer, without a GPU, API keys, accounts, or per-video API fees. The default workflow uses **editable script templates → offline synthetic narration → illustrated character animation → captions → MP4**.

This is illustrated animation, not a realistic human talking avatar. Mouth opening follows audio amplitude; it does not generate phoneme-level lip-sync. Caption timings are estimated. Default eSpeak voices sound synthetic. Running the software locally is free of API charges; your hardware, electricity, Internet connection for installation, and any third-party hosting are separate.

## Included

- FastAPI backend, React/Vite frontend, Tailwind styles, SQLAlchemy with SQLite or PostgreSQL.
- Password-protected single-agency workspace, persistent projects and scripts.
- Four script-template tones, short-form/YouTube lengths, and objective-based CTAs. Templates use your brief and never contact a language-model service. Edit copy before publishing.
- Three original illustrated characters, three offline English voice profiles, expression/movement intensity, audio-reactive mouth shapes and blinks.
- Background CPU rendering, persistent queue/status, errors, and progress polling.
- Captions burned into every local video and synthetic-media metadata.
- MP4 playback, rename, search, download, and cached vertical/square/landscape conversions with audio preserved.
- Historical demo/provider assets remain playable. Paid generation is an optional, explicit server configuration, never an automatic fallback.
- Optional loudkit neural speech on CPU, with a separate install/model download.

## Folder structure

```text
backend/
  .env.example
  requirements.txt             # default CPU stack, including bundled eSpeak NG
  requirements-loudkit.txt     # optional neural speech
  pytest.ini
  app/
    config.py                  # validated mode, authentication and storage settings
    models.py                  # SQLAlchemy tables
    schemas.py                 # validated API payloads
    main.py                    # API and additive legacy schema upgrade
    providers.py               # local templates and optional paid providers
    speech.py                  # local eSpeak / optional loudkit adapter
    local_video.py             # character drawing, audio analysis, captions
    worker.py                  # durable render worker and FFmpeg
  tests/                       # API, provider, CPU render, speech and recovery tests
frontend/
  package.json / package-lock.json
  vite.config.js / tailwind.config.js / postcss.config.js
  index.html
  src/App.jsx / main.jsx / styles.css
  public/characters/           # original local SVG illustrations
  public/portraits/            # retained licensed legacy sample assets
  tests/browser_smoke.py
compose.yaml
 deploy/Dockerfile.backend
 deploy/Dockerfile.frontend
 deploy/nginx.conf
.github/workflows/ci.yml
```

## Run on your computer

Tested on Linux with Python 3.12, Node 24, FFmpeg, and CPU only. Use Python 3.12+, Node 22+, and FFmpeg/ffprobe. No system eSpeak installation or separate model download is needed: `espeakng-loader` bundles the runtime and voice data in a roughly 10 MB package. A supported native wheel is required for your OS/architecture; Docker is an alternative on other systems.

Install FFmpeg (`sudo apt-get install ffmpeg fonts-dejavu-core` on Debian/Ubuntu, or `brew install ffmpeg` on macOS), then from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the generated value in `ENCRYPTION_KEY` inside `backend/.env`, and choose a unique `ADMIN_PASSWORD` of at least 12 characters. The encryption key protects any optional provider credentials. Back it up securely. Leave these defaults:

```dotenv
GENERATION_MODE=local
DEMO_MODE=false
LOCAL_TTS_ENGINE=espeak
```

Start the backend **from the backend directory**:

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173** and sign in with your configured password. Use `localhost` consistently; Vite proxies `/api` to the backend. Development API docs: http://localhost:8000/api/docs.

Create a project → draft or write a script → choose a character/voice/format → **Create free video** → Media library → preview/export MP4. No OpenAI or D-ID credentials are needed. After dependencies are installed, the default render workflow works without Internet access. Fonts and character art are bundled locally.

## How free generation works

The renderer synthesizes speech locally, normalizes it to PCM WAV, measures amplitude in 100 ms windows, draws a small cache of character/mouth/blink/caption frames, and encodes H.264/AAC MP4 using FFmpeg with two encoding threads. Rendering is sequential to bound resource use. Generated videos include synthetic-media metadata and a visible synthetic-voice label.

Local ads are limited to 220 spoken words and three minutes of synthesized audio. FFmpeg processing has a three-minute timeout. Speed depends on your CPU, script length, dimensions, and optional voice engine; measure it on your own machine. No performance promise is made for your device. The tested output resolutions are 720×1280, 720×720, and 1280×720.

A saved render keeps an immutable copy of its script and an `engine` field. Existing databases receive an additive `engine` column on startup; historical jobs default to their original provider/demo pipeline. No projects, scripts, or videos are deleted. Local jobs interrupted by a restart can be regenerated without API charges. Provider jobs retain duplicate-charge protection.

Alternate exports preserve existing content with padding. **For the best caption layout in a new ratio, create a new local render in that ratio**; local rendering incurs no provider charges. Cached export files are only exposed after an atomic file rename.

## Optional neural voice upgrade: loudkit

The default eSpeak engine is lightweight but robotic. For a neural voice, the optional integration follows the [loudkit integration skill](skill://plugins_6abe6d86380c819184783cc2602647be/add-offline-tts):

```bash
source .venv/bin/activate
python -m pip install -r backend/requirements-loudkit.txt
```

Set `LOCAL_TTS_ENGINE=loudkit`, keep `GENERATION_MODE=local`, and restart the backend. The adapter loads `loudreader/loudr-1`, release `v0.1.1`, explicitly on **CPU**, retains the engine between jobs, and uses the English `joe` voice (CC0, OHF-Voice donations). `loudkit` is pinned to `0.1.1`. It retains the Python WAV provenance note; final videos are also labeled synthetic.

**First synthesis downloads approximately 750 MB of model weights and voice data**, plus the PyTorch dependencies installed above. It needs Internet access to the model host the first time; cache it before offline use. Allow these hosts through your own environment’s supported network settings rather than bypassing a proxy. The reference-quality model is the default; you can compare `LOUDKIT_MODEL=loudreader/loudr-1-turbo` on your own text if latency matters more. Speed and quality must be measured on your CPU. Switching to loudkit exposes one neural voice; the three eSpeak profile names are not applied to it.

Loudkit is optional and has **not** been installed/downloaded or validated with real weights in this task. Its opt-in test explicitly synthesizes a sentence and checks for nonempty audio:

```bash
cd backend
# Run only when you choose to download/use the neural model:
RUN_LOUDKIT_MODEL_TEST=1 python -m pytest tests/test_local.py::test_optional_loudkit_sentence -q
```

Code: Apache-2.0. Joe voice: CC0. Full voice roster/licenses: https://github.com/loudreader/loudkit/blob/main/VOICES.md. Do not treat other voices as interchangeable in language or licensing.

## Tests and frontend build

```bash
# From repository root with the virtual environment active
cd backend
python -m pytest -q
cd ../frontend
npm run format:check
npm run build
```

Default tests use isolated temporary storage, real CPU speech, actual audio/video encoding in all three ratios, mouth-region frame variation, auth/origin checks, encrypted optional credentials, provider request mocks, downloads/ranges, and job recovery. A blocked `httpx.AsyncClient` in local tests ensures they cannot accidentally call a paid provider. The neural model test is skipped unless explicitly enabled.

An optional Chromium browser test creates a unique project and a real free-mode video, verifies playback, downloads a square export, visits settings/projects, and checks the mobile layout. Install `playwright` in your development environment and its Chromium browser, set `WORKSPACE_PASSWORD` securely in your shell, start both servers in local mode, then run:

```bash
python frontend/tests/browser_smoke.py
```

Screenshots and its exported MP4 go to `/tmp/forma-checks`. `BASE_URL`, `SCREENSHOT_DIR`, and `CHROMIUM_PATH` can override defaults. `CHROMIUM_NO_SANDBOX=true` is only for an already isolated container/CI runtime that requires it. Smoke-test projects/videos remain for inspection. CI runs backend tests and frontend format/build/audit checks.

## Data, security, and deployment

SQLite initializes at `backend/data/studio.db`. Persist and back up the entire `backend/data` directory, which also contains MP4s. Never commit `.env`, database files, credentials, or generated videos. PostgreSQL can be selected using `DATABASE_URL=postgresql+asyncpg://USER:URL_ENCODED_PASSWORD@HOST:5432/forma`; changing database URLs does not migrate existing data. PostgreSQL server integration and Docker deployment have not been tested in this task.

This is a single-agency application with one administrator login and expiring HttpOnly cookies. Run **exactly one backend replica with one Uvicorn worker**; PostgreSQL does not make the queue distributed. It has no public registration, individual staff roles, multi-tenant isolation, or billing. Authentication/origin checks and bounded local inputs remain active in free mode.

To deploy with the included non-root images:

1. Configure `backend/.env` with `APP_ENV=production`, your unique password/key, `GENERATION_MODE=local`, `DEMO_MODE=false`, and `FRONTEND_ORIGIN=https://your-domain.example`.
2. Run `docker compose up --build -d` from the repository root.
3. Put a TLS reverse proxy in front of the loopback-bound frontend on port 8080. Production session cookies require HTTPS. Configure HSTS at the TLS terminator. Do not expose the backend directly.
4. Back up the `studio-data` volume and encryption key. Monitor disk space and set a retention policy. `/api/health` checks database connectivity. Hosting is not supplied for free by this repository.

Compose defaults to SQLite in the persistent data volume; use a deployment `DATABASE_URL` variable for external PostgreSQL. Future schema changes need reviewed migrations. Password changes do not automatically revoke existing sessions: clear the sessions table during controlled maintenance if revocation is needed. Default sessions last 12 hours.

## Optional paid-provider mode

Free mode does not need any provider secrets previously requested in the cloud environment draft. Leave them empty. The app makes no paid-provider requests in local mode.

If you later deliberately want realistic talking-avatar videos, set `GENERATION_MODE=provider`, `DEMO_MODE=false`, configure `STUDIO_OPENAI_API_KEY` (or `OPENAI_API_KEY` locally) and `DID_API_KEY`, and restart. Only provider mode shows provider-key forms. D-ID key values are used after `Basic` in its Authorization header. Stored encrypted keys take precedence over environment defaults. Paid mode uses OpenAI Chat Completions and D-ID Talks, with a 15-minute polling bound per worker run. Provider availability, presenter permissions, credit balance, and pricing apply. Configure approved presenter URLs in `app/providers.py`.

For provider mode, preserve HTTPS/TLS verification and proxy routing. Allow API hosts and the actual media CDN hosts; `MEDIA_HOSTS` separately restricts backend downloads and rejects redirects. Provider payloads are tested with mocks, not real paid calls. Setting `GENERATION_MODE=provider, DEMO_MODE=true` retains the old silent five-second demo exports and is not equivalent to free local rendering.

## Attribution and troubleshooting

Original SVG/Pillow character illustrations are generated by this project. Bundled fonts retain the Fontsource package licenses. Legacy unused stock portraits retain Creative Tim’s MIT license in `frontend/public/portraits/`. eSpeak NG is GPLv3 software; `espeakng-loader` bundles its native library/data. See https://github.com/espeak-ng/espeak-ng for license and source, and preserve upstream notices when redistributing that runtime. The app clearly labels synthesized narration.

- **No voice runtime / unsupported wheel:** reinstall `requirements.txt` for a supported platform or use Docker. No root-level eSpeak installation is required.
- **Failed local render:** inspect the media-library error and server log; check FFmpeg, font availability, disk space, and the 220-word limit.
- **403 mutation:** `FRONTEND_ORIGIN` must exactly match your browser origin.
- **Missing MP4:** restore the media volume; database backups alone do not contain video files.
- **Neural model/network issue:** stay with `LOCAL_TTS_ENGINE=espeak` for the fully tested, download-free runtime. There is no automatic paid fallback.

## One-click Render deployment

`render.yaml` deploys the frontend and backend together as one **free-plan** Docker web service, using `deploy/Dockerfile.render`. In Render, create a Blueprint from this repository, choose a unique `ADMIN_PASSWORD` (12+ characters), and deploy. No OpenAI, D-ID, or loudkit model keys are requested. Render generates `ENCRYPTION_SEED`; the app derives its Fernet key from that seed. Keep the seed stable if you later move to persistent storage. An explicitly supplied `ENCRYPTION_KEY` still takes precedence.

Render's `RENDER_EXTERNAL_URL` automatically supplies the HTTPS frontend origin unless you set `FRONTEND_ORIGIN` explicitly. The service listens on Render's `PORT`, serves the built dashboard and `/api` from one origin, and uses HTTPS-only session cookies. Once Render reports a healthy deployment, its dashboard shows the actual public `https://….onrender.com` URL. Service names and URLs are allocated by Render; no public address is assumed in advance.

**Free-hosting limitation:** this blueprint uses ephemeral SQLite/media storage and does not add a paid disk. Files, projects, scripts, and sessions can disappear after restarts, spin-downs, or redeploys. The dashboard displays this limitation. Download videos you want to keep. Free hosting also has CPU/RAM/runtime limits; validate a short ad first. For durable production storage, configure a database and shared persistent media store separately. This repository does not promise permanent free hosting or unrestricted rendering capacity.
