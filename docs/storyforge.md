# Storyforge

Storyforge combines the existing `Storyteller` and `HistoicalEventExplainer`
pipelines behind one API. The web frontend was removed; the API is the interface.

## Architecture

- `apps/studio-api/` — FastAPI project API and persistent SQLite project records
- `apps/studio-api/app/tasks.py` — Celery generation task
- `apps/studio-api/app/pipeline.py` — safe CLI adapters for both Python engines
- Redis — task broker and result backend
- Celery Beat — one centralized dispatcher for persistent scheduled projects

The working creation modes are AI-photo stories, Reddit/gameplay stories,
real-image stories, and historical documentaries. Stock-footage and AI-avatar
modes remain visibly marked as coming soon until they have real workers.

Workflows are stored as nodes and edges (`/api/workflows`): content generators
plus an optional scheduler and social destination, saved and run again later. A blank generator topic uses the AI prompt
assistant automatically. Publishing destinations are validated before a run;
the final provider upload step remains connector-specific.

## Run with Docker

1. Make sure the API keys in `Storyteller/.env` and
   `HistoicalEventExplainer/.env` are configured.
2. Start the API, Redis, one generation worker, and the scheduler:

```bash
docker compose up --build
```

3. The API is now available at `http://localhost:8000` (interactive docs at
   `/docs`).

## Test without spending API credits

Set these values in `backend/.env`:

```dotenv
STORYFORGE_TASKS_EAGER=true
STORYFORGE_MOCK_GENERATION=true
```

Then run the API locally:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Mock mode walks through every progress stage and renders a two-second sample MP4
with FFmpeg. Do not enable eager tasks for real generation because the API request
would remain open until rendering finishes.

Set `STORYFORGE_MOCK_CONNECTIONS=true` to exercise connect/disconnect flows without
leaving the local app.

The “I feel lucky today” prompt assistant uses `GEMINI_API_KEY`. Storyforge reads
it from the backend environment or either connected generator environment. Set
`STORYFORGE_PROMPT_AI_ENABLED=false` to use only the built-in mode-aware ideas.

## AI providers and model presets

Open **API & models** in the sidebar to save a Replicate, fal.ai, Together AI,
or Google Gemini API key and
manage reusable image-model presets. Keys are encrypted in the backend runtime
and are never returned to the browser. When
`STORYFORGE_TOKEN_ENCRYPTION_KEY` is not set, local development uses a generated
`backend/runtime/.credentials.key` file with owner-only permissions.

AI-photo projects show enabled presets during creation. The selected provider,
model identifier, and input JSON are copied into the project before it is queued,
so later edits to a preset do not change a scheduled or existing project. The
built-in example uses `black-forest-labs/flux-schnell` on Replicate. fal.ai
presets use model paths such as `fal-ai/flux/schnell`. Together AI includes a
`black-forest-labs/FLUX.1-schnell` preset using its image-generation API.
Google Gemini includes a `gemini-2.5-flash-image` preset. Google currently lists
native Gemini image generation as unavailable on the API free tier, so this
provider requires an API key and may require billing.

## Social app connections

YouTube and TikTok use server-side OAuth. Copy `backend/.env.example` values into
`backend/.env`, configure the provider credentials, and generate a Fernet key:

```bash
cd backend
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set the printed value as `STORYFORGE_TOKEN_ENCRYPTION_KEY`. Register these callback
URLs with the providers:

```text
http://localhost:8000/api/connections/youtube/callback
http://localhost:8000/api/connections/tiktok/callback
```

TikTok requires an HTTPS callback for a web app outside its permitted local
development configuration. Instagram is shown as planned until its publishing
connector is implemented. OAuth tokens are encrypted before they are persisted.

## API

Useful endpoints:

- `GET /api/health`
- `GET /api/projects`
- `POST /api/prompts/lucky`
- `GET /api/workflows`
- `POST /api/workflows`
- `PUT /api/workflows/{id}`
- `POST /api/workflows/{id}/run`
- `POST /api/projects`
- `POST /api/projects/{id}/generate`
- `POST /api/projects/{id}/cancel`
- `POST /api/projects/{id}/retry`
- `GET /api/projects/{id}/logs`
- `GET /api/projects/{id}/download`
- `GET /api/schedules`
- `POST /api/schedules`
- `POST /api/schedules/{id}/run-now`
- `DELETE /api/schedules/{id}`
- `GET /api/connections`
- `POST /api/connections/{provider}/connect`
- `DELETE /api/connections/{provider}`
- `GET /api/ai/providers`
- `PUT /api/ai/providers/{provider}`
- `DELETE /api/ai/providers/{provider}`
- `GET /api/ai/models`
- `POST /api/ai/models`
- `PUT /api/ai/models/{id}`
- `DELETE /api/ai/models/{id}`

Interactive API documentation is available at `http://localhost:8000/docs`.
