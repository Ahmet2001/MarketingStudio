# Storyforge frontend

A unified React frontend for the Storyteller and TopicExplainer Python video
pipelines. It connects to the API in `../backend` through Vite's `/api` proxy.

## Run locally

```bash
npm install
npm run dev
```

Start the API, Redis, and worker first using the root project instructions. The
interface creates persistent projects, starts generation jobs, polls progress,
supports cancellation and retry, and downloads completed videos.

## Mode mapping

- AI photos and Reddit/gameplay → `../Storyteller/main.py`
- Real images and historical documentary → `../HistoicalEventExplainer/main.py`
- Stock explainer and AI avatar → visible as planned modes until dedicated
  generation workers are implemented
