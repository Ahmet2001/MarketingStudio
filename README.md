# MarketingStudio

Tools for producing marketing content: product ad creatives, narrated story
videos, documentary explainers, and social-media distribution.

## Layout

| Path | What it is | Stack |
|---|---|---|
| `apps/studio-web` | ProductMarketer: product-ad creative studio (React frontend + Express/SQLite API in `server/`) | React, Vite, Express |
| `apps/studio-api` | Storyforge API: projects, Celery generation tasks, scheduler | FastAPI, Celery, Redis |
| `apps/storyforge-web` | Storyforge frontend: creator workspace and workflow canvas | React, Vite |
| `engines/story-video` | Topic to narrated vertical story video (Gemini, Replicate, ElevenLabs, FFmpeg) | Python |
| `engines/documentary-video` | Topic to documentary explainer using licensed real archive photos | Python |
| `engines/local-image` | Local image generation: Ideogram 4 code plus Stable Diffusion storyboard pipeline (`story_image_pipeline.py`) | Python, diffusers |
| `engines/product-ads` | Placeholder for the product-ad engine | n/a |
| `connectors/` | Reddit, X, Instagram and YouTube toolboxes for publishing and research | Python |
| `docs/` | Research and architecture notes (AdCreative.ai study, Storyforge) | Markdown |

## Running

- Product studio: `cd apps/studio-web && npm install && npm run dev`
- Storyforge: `docker compose up --build` from the repo root, then
  `cd apps/storyforge-web && npm install && npm run dev`
- Engines run standalone, see the README inside each engine folder.

## Secrets

Each component reads its own `.env`; see `.env.example`. Real `.env` files,
generated media, `node_modules` and virtualenvs are git-ignored.

## Notes

- `connectors/main.py` imports a `MarketingApp` package that is not part of this repo yet.
- `engines/local-image/` contains the upstream Ideogram 4 source (see its `LICENSE.md` and `model_licenses/`).
