# Storyteller

Generate narrated vertical story videos from a single topic.

The pipeline:

1. Loads one niche profile that defines the audience, creator persona, tone, hooks,
   research angles, script rules, and topics to avoid.
2. Asks Gemini to select the factual research focus and create several concise
   search queries, then searches them individually with DuckDuckGo and extracts
   readable text from selected result pages. If DuckDuckGo returns no results,
   DDGS automatically tries its available search engines for the same query.
3. Creates a niche-aware, research-grounded script and detailed scene prompts with
   Gemini. Each scene has a retention purpose and one literal visual anchor, while
   the script follows a clear hook → context → escalation → turning point → payoff
   structure.
4. Generates coherent scene images through Replicate, or selects a gameplay clip
   when video game mode is enabled.
5. Produces scene narration with ElevenLabs. Video game mode also requests exact
   character timestamps for synchronized word highlighting.
6. Builds a normalized narration master.
7. Renders animated 9:16 scene clips, captions, and optional music with FFmpeg.
8. Exports a captioned 1080×1920 MP4.

API operations include retry handling for throttling, timeouts, connection failures,
and transient server errors.

## Requirements

- Python 3.12+
- FFmpeg and FFprobe
- Gemini and ElevenLabs API keys
- A Replicate key for generated images (not required in video game mode)

On Ubuntu or Debian:

```bash
sudo apt install ffmpeg
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Add your API keys to `.env`:

```dotenv
GEMINI_API_KEY=your_key
REPLICATE_API_TOKEN=your_token
ELEVENLABS_API_KEY=your_key
```

Never commit `.env`; it is excluded by `.gitignore`.

## Usage

```bash
python main.py \
  "A taxi driver receives a passenger request from an abandoned town" \
  --language English \
  --duration 20 \
  --scenes 4
```

Generated files are saved under `outputs/<timestamp>/`.

### Video game mode

Video game mode replaces generated scene images with gameplay, crops the source to
the center of a 9:16 frame, removes its original audio, and renders it at 60 fps.
Subtitles appear in the middle of the screen in compact groups of up to four words.
The currently spoken word uses a smooth scale animation and yellow highlight.

The downloaded Minecraft parkour clips are the default gameplay library, so this
command is ready to use:

```bash
python main.py \
  "Why some habits are so difficult to break" \
  --video-game-mode \
  --speaking-style serious \
  --skip-research \
  --duration 45 \
  --scenes 7
```

You can supply one video or a directory of videos. Directory selection and the
starting point are deterministic for the chosen `--seed`:

```bash
python main.py \
  "The rise and fall of a forgotten company" \
  --video-game-mode \
  --gameplay-video /path/to/gameplay-clips \
  --seed 2026
```

This mode requires Gemini and ElevenLabs keys but does not require a Replicate key.
It saves the chosen source and start time in `gameplay.json` and the editable
animated subtitle track in `subtitles.ass`.

### Narration style and speed

Narration is slightly slower by default. Choose a delivery profile with
`--speaking-style`:

```text
mysterious  Quiet, suspenseful, and intimate
excited     Energetic and enthusiastic without rushing
sad         Gentle, reflective, and emotionally heavy
angry       Intense, urgent, and controlled
serious     Authoritative, focused, and deliberate (default)
```

For example:

```bash
python main.py \
  "A man receives a voicemail from his own phone number" \
  --video-game-mode \
  --speaking-style mysterious \
  --speech-speed 0.82 \
  --skip-research
```

Every profile uses a speed below `1.0`. `--speech-speed` can override it with a
value from `0.7` to `1.2`; lower values speak more slowly. Each run records the
effective controls in `speech_settings.json`.

### Replicate character styles

Generated-image mode can enforce a recurring character direction with
`--character-style`:

```text
auto            Choose the best subject for the story (default)
life-sim        Original stylized 3D everyday-life character and world
animal          Consistent expressive animal protagonist
horror          Original unsettling, non-graphic horror character
animated-human  Original feature-animation-style human protagonist
```

`sims` is accepted as a convenient alias for `life-sim`, but the prompt creates an
original unbranded world rather than copying recognizable characters, icons, UI, or
assets.

Examples:

```bash
python main.py \
  "A new neighbor behaves strangely every night" \
  --character-style life-sim \
  --speaking-style mysterious \
  --skip-research

python main.py \
  "A stray cat discovers why everyone left the village" \
  --character-style animal \
  --speaking-style sad \
  --skip-research

python main.py \
  "The creature in the hallway only moves when the lights are off" \
  --character-style horror \
  --speaking-style mysterious \
  --skip-research
```

The selection controls Gemini's character bible and scene prompts, then adds a
mandatory style direction to every Replicate image request. Each run records it in
`visual_settings.json`. This option is ignored by video game mode because that mode
does not generate Replicate images.

The default niche is `general-storytelling`. Choose one of the 15 built-in
profiles:

```bash
python main.py --list-niches

python main.py \
  "Why the Roman road network lasted so long" \
  --niche history \
  --language English \
  --duration 30 \
  --scenes 5
```

To bring your own niche, copy and edit `niches/custom.example.json`, then pass
its path:

```bash
python main.py \
  "The legend behind an abandoned station" \
  --niche niches/custom.example.json
```

Every run saves the exact loaded profile as `niche_profile.json` and the search
focus, Gemini-selected queries, source URLs, snippets, and extracted text as
`research.json`. A query with no results is skipped immediately and the next query
is tried after DuckDuckGo and the automatic fallback are exhausted. Each source
records which search backend found it. Web research is enabled by default; use
`--skip-research` for fictional topics or offline runs.

Scene images are generated from the exact narration displayed during that scene,
its mandatory visual anchor, and its detailed shot direction. Each scene is limited
to one visually coherent story beat so its compact caption chunks continue to match
the image on screen. Scene images use `black-forest-labs/flux-schnell` by default;
the separate title cover continues to use Ideogram for reliable title typography.

Factual explainers and authentic documentary-photo sourcing now live in the
separate `TopicExplainer` project.

Useful options:

```text
--niche BUILTIN_ID_OR_JSON_PATH
--list-niches
--skip-research
--research-results NUMBER
--research-pages NUMBER
--research-region REGION
--music PATH
--skip-cover
--video-game-mode
--gameplay-video FILE_OR_DIRECTORY
--image-model MODEL
--character-style auto|life-sim|animal|horror|animated-human
--voice-id ID
--speaking-style mysterious|excited|sad|angry|serious
--speech-speed 0.7-1.2
--seed NUMBER
--api-attempts NUMBER
--retry-base-delay SECONDS
--retry-max-delay SECONDS
```

## Tests

```bash
python -m unittest discover -s tests -v
```
