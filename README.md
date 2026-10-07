# MarketingStudio

MarketingStudio is a collection of tools for producing marketing content in one place: product ad creatives, narrated short-form story videos, documentary-style explainers, and the connectors needed to research and distribute that content on social platforms.

## Why this project

Marketing content usually needs several separate tools: an ad designer, a video generator, an image model, and scripts for each social platform. MarketingStudio keeps them in one repository with a shared layout, so each generator can be used on its own or wired into a common studio and scheduler.

## What is inside

| Path | What it does | Stack |
|---|---|---|
| [apps/studio-web](apps/studio-web) | Product ad creative studio (ProductMarketer): uploads, projects, generations, revisions, UGC storyboards, provider/model routing. React frontend with an Express and SQLite API in `server/`. | React, Vite, Express |
| [apps/studio-api](apps/studio-api) | Storyforge API: projects, Celery generation tasks, scheduler. | FastAPI, Celery, Redis |
| [apps/storyforge-web](apps/storyforge-web) | Storyforge creator workspace and visual workflow canvas. | React, Vite |
| [engines/story-video](engines/story-video) | Topic to narrated 9:16 story video (Gemini, Replicate, ElevenLabs, FFmpeg). | Python |
| [engines/documentary-video](engines/documentary-video) | Topic to documentary explainer using licensed real archive photos (Openverse, Wikimedia Commons). | Python |
| [engines/local-image](engines/local-image) | Local image generation: Ideogram 4 source and a Stable Diffusion storyboard pipeline. | Python, diffusers |
| [engines/product-ads](engines/product-ads) | Placeholder for the product-ad engine, currently inside `apps/studio-web/server`. | n/a |
| [connectors](connectors) | Reddit, X, Instagram and YouTube toolboxes. | Python |
| [docs](docs) | Research and architecture notes. | Markdown |

## Getting started

Prerequisites: Node.js 20+, Python 3.12+, FFmpeg, and Docker with Docker Compose for Storyforge. Each component reads its own `.env`; copy the `.env.example` next to it first (see [.env.example](.env.example)).

**Product ad studio**

```bash
cd apps/studio-web
npm install
npm run dev
```

The frontend runs at `http://127.0.0.1:4173` and the API at `http://127.0.0.1:8787`. More detail in [apps/studio-web/README.md](apps/studio-web/README.md).

**Storyforge**

```bash
docker compose up --build
cd apps/storyforge-web && npm install && npm run dev
```

Open `http://localhost:5173`. More detail in [docs/storyforge.md](docs/storyforge.md).

**Video engines**

Each engine runs standalone. See [engines/story-video/README.md](engines/story-video/README.md) and [engines/documentary-video/README.md](engines/documentary-video/README.md).

## Secrets and generated files

Real `.env` files, generated media (`outputs/`, mp4, wav, mp3), `node_modules`, virtualenvs and runtime databases are git-ignored. Never commit API keys.

## Known limitations

- `connectors/main.py` imports a `MarketingApp` package that is not part of this repository yet.
- The product studio's default provider produces SVG mockups, not photographic output.
- Storyforge's final social-upload step is connector-specific and not finished.

## Help

Open an [issue](https://github.com/Ahmet2001/MarketingStudio/issues) for bugs or questions.

## Maintainer

[@Ahmet2001](https://github.com/Ahmet2001)

## License

This repository does not have a top-level license yet. [engines/local-image](engines/local-image) contains upstream Ideogram 4 code under the Apache License 2.0 ([LICENSE.md](engines/local-image/LICENSE.md)) and model licenses in [model_licenses](engines/local-image/model_licenses).

## Contributing

Contributions are welcome. Open an issue to discuss a change before sending a pull request, keep each pull request to one component, and do not include secrets or generated media.
