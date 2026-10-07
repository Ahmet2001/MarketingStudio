# TopicExplainer

Create researched vertical explainer videos from a factual topic. The default visual
pipeline searches for authentic documentary and archival media instead of generic
stock photography.

For example:

```bash
python main.py \
  "The 2001 financial crisis in Turkey" \
  --language English \
  --duration 45 \
  --scenes 7 \
  --skip-cover
```

## What the pipeline does

1. Gemini plans complementary research queries.
2. DDGS searches the web and extracts a compact source brief.
3. Gemini writes a question → context → cause → evidence → consequence explainer.
4. Every scene receives an explicit authentic-photo requirement and two to four
   event-, person-, place-, date-, or artifact-specific media queries.
5. Openverse and Wikimedia Commons are searched together for freely
   licensed/public-domain candidates. Results are interleaved so one weak provider
   cannot dominate the candidate set. Obvious illustrations, maps, logos, synthetic
   images, non-commercial licenses, and no-derivatives licenses are filtered out.
   If an exact archive phrase returns nothing, the search removes over-specific
   years and generic terms while preserving named people, institutions, places,
   and local-language spellings.
6. Gemini vision inspects the candidate pixels and metadata. It rejects generic,
   wrong-era, wrong-location, or potentially synthetic imagery and labels the
   chosen file as `exact_event`, `actual_subject`, `period_context`, or
   `primary_source`.
7. ElevenLabs creates narration. FFmpeg adds a zero-cost title card, fitted photos,
   gentle crossfades, date/time/location labels, a scene-progress indicator, and
   word-emphasis captions.
8. Optional background music is looped, faded, and automatically ducked beneath
   narration.

Each run saves:

- `research.json` — queries, sources, snippets, and extracted research text.
- `explainer.json` — narration and visual-evidence plan.
- `real_photos.json` — file URLs, creator, license, selection score, explanation,
  and depiction type for every scene.
- `real_photo_credits.txt` — ready-to-review credit lines.
- `subtitles.srt` — portable plain subtitles.
- `overlays.ass` — styled title, metadata, timeline, and animated captions.
- The scene images, audio, intermediate clips, and final MP4.

## Setup

Requires Python 3.12+, FFmpeg, and FFprobe.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Configure:

```dotenv
GEMINI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
WIKIMEDIA_USER_AGENT=TopicExplainer/1.0 (you@example.com)
```

`WIKIMEDIA_USER_AGENT` should identify your application and provide a way to
contact you. Wikimedia Commons does not require an API key.

`REPLICATE_API_TOKEN` is not needed for the built-in FFmpeg title card. It is
required only with `--generate-cover` or `--visual-source generated`.

## Useful options

```text
--skip-research
--research-results NUMBER
--research-pages NUMBER
--research-region REGION
--visual-source real|generated
--real-photo-results NUMBER
--real-photo-candidates NUMBER
--real-photo-min-match SCORE
--generate-cover
--music PATH
--music-volume 0.12
--force-render
--voice-id ID
--api-attempts NUMBER
```

The separate Replicate poster is disabled by default. The in-video FFmpeg title
card is always included and has no model cost.

Use `--force-render` when resuming an older run so cached scene clips are rebuilt
with the latest framing and transition style:

```bash
python main.py \
  --resume-run outputs/20260726_192548 \
  --force-render \
  --music /path/to/licensed-music.mp3
```

If no candidate meets `--real-photo-min-match`, the run stops with a clear scene
error instead of silently substituting generic stock footage. Lowering the threshold
is possible, but reviewing the queries and selected file pages is safer.

If a run stops after `explainer.json` has been created, resume it without paying for
research and script generation again:

```bash
python main.py \
  --resume-run outputs/20260726_183704 \
  --skip-cover
```

## Licensing

Wikimedia Commons files have individual licenses. Before publishing, review every
source page and the generated `real_photo_credits.txt`, then satisfy attribution,
license-linking, share-alike, personality-rights, and other applicable conditions.
The generated manifest is assistance, not legal advice.

## Tests

```bash
python -m unittest discover -s tests -v
```
