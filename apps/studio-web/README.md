# ProductMarketer

A full-stack product creative studio prototype. The React frontend is backed by
an Express API, persistent SQLite records, durable local media storage, and an
asynchronous generation engine.

## Run locally

```bash
npm install
npm run dev
```

- Frontend: `http://127.0.0.1:4173`
- API: `http://127.0.0.1:8787`
- Health check: `http://127.0.0.1:8787/api/health`

`npm run dev` starts the API and Vite together. Copy `.env.example` to `.env`
only when you need to change the default ports or storage paths.

## What is persisted

- Demo user profile and workspace settings
- Product uploads and their stable media URLs
- Projects and creation-tool configuration
- Every generation before processing starts
- Provider/model, status, inputs, usage, and estimated cost
- Generated output files and metadata
- UGC storyboard scenes
- Revision lineage through `parentGenerationId`
- Selected and approved outputs

SQLite data lives in `storage/productmarketer.sqlite`. Uploaded and generated
files live under `storage/uploads` and `storage/generated`. These runtime files
are intentionally ignored by Git.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | API/database/provider health |
| `GET` | `/api/catalog` | Available creation workflows |
| `GET/PATCH` | `/api/me` | Profile persistence |
| `GET/PATCH` | `/api/settings` | Workspace preferences |
| `GET` | `/api/model-providers` | Provider catalog, masked connection state, and routes |
| `PUT/DELETE` | `/api/model-providers/:provider` | Save or remove an encrypted provider connection |
| `POST` | `/api/model-providers/:provider/test` | Test credentials and provider reachability |
| `GET/PUT` | `/api/model-routes` | Assign providers/models to LLM, VLM, image, and video roles |
| `GET` | `/api/projects` | Persistent project history |
| `POST` | `/api/uploads` | Multipart product-image upload |
| `POST` | `/api/generations` | Create project and queued generation |
| `GET` | `/api/generations/:id` | Poll an addressable generation |
| `POST` | `/api/generations/:id/revisions` | Create a saved child revision |
| `POST` | `/api/generations/:id/approve` | Approve a selected output |
| `PATCH` | `/api/scenes/:id` | Revise or approve a UGC scene |
| `GET` | `/api/videos` | Generated video project history |

## Generation provider

The default local provider generates durable SVG campaign mockups, so the whole
workflow works without paid API keys. Its persistence and job contract are
provider-neutral: a production image/video adapter can replace the local media
generation step while retaining the same IDs, API responses, revision history,
and frontend.

The backend currently uses a demo user rather than production authentication.
Authentication, object storage, a distributed job queue, and a real image/video
provider are the next deployment-stage services.

## Configure LLMs and VLMs

Open **AI models** in the application sidebar. The configuration interface
supports OpenAI, Anthropic, Google Gemini, Replicate, fal, Hugging Face, Ollama,
and custom OpenAI-compatible endpoints.

For each connection you can:

- Set a custom API base URL
- Save an API key through the encrypted credential vault
- Enter default LLM, VLM, image, and video model IDs
- Enable or disable the provider
- Test provider reachability and authentication
- Assign connected providers to application roles

API keys use AES-256-GCM encryption. The local encryption key is created at
`storage/credentials.key` with owner-only permissions and is ignored by Git.
Production deployments should provide a stable `CREDENTIAL_ENCRYPTION_KEY` as
documented in `.env.example`; losing that key makes saved credentials
unrecoverable.
