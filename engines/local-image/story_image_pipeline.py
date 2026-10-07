import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import subprocess
import sys
import time

import requests
import torch
from diffusers import StableDiffusionPipeline

from diffusers import StableDiffusionPipeline
from diffusers import DiffusionPipeline


OLLAMA_URL = "http://localhost:11434/api/generate"



def unload_ollama_model(ollama_model: str) -> None:
    """
    Storyboard bittikten sonra Ollama modelini GPU/RAM'den boşaltmaya çalışır.
    Bu, SD 1.5 için VRAM açar.
    """
    print(f"\n[INFO] Ollama modeli boşaltılıyor: {ollama_model}")

    try:
        requests.post(
            OLLAMA_URL,
            json={
                "model": ollama_model,
                "prompt": "",
                "stream": False,
                "keep_alive": "0s"
            },
            timeout=60
        )
    except Exception as e:
        print(f"[WARN] Ollama API unload denenemedi: {e}")

    try:
        subprocess.run(
            ["ollama", "stop", ollama_model],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        print(f"[WARN] ollama stop çalışmadı: {e}")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    time.sleep(2)


STORY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "main_character": {"type": "string"},
        "visual_style": {"type": "string"},
        "negative_prompt": {"type": "string"},
        "frames": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "frame": {"type": "integer"},
                    "scene_goal": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "voiceover": {"type": "string"},
                    "camera_motion": {"type": "string"}
                },
                "required": [
                    "frame",
                    "scene_goal",
                    "image_prompt",
                    "voiceover",
                    "camera_motion"
                ]
            }
        }
    },
    "required": [
        "title",
        "main_character",
        "visual_style",
        "negative_prompt",
        "frames"
    ]
}


def extract_json(text: str) -> Dict[str, Any]:
    """
    Ollama bazen düzgün JSON döndürür, bazen başına/sonuna ekstra karakter koyabilir.
    Bu fonksiyon JSON'u daha dayanıklı parse eder.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Model JSON döndürmedi.")

    return json.loads(match.group(0))


def ask_ollama_for_storyboard(
    idea: str,
    ollama_model: str,
    width: int,
    height: int
) -> Dict[str, Any]:
    system_prompt = f"""
You are a professional short-form storytelling video prompt engineer.

The user will describe a video idea.
Your job is to create exactly 5 image-generation prompts for Stable Diffusion 1.5.

Rules:
- Output ONLY valid JSON.
- The JSON must match the provided schema.
- Create exactly 5 frames.
- Keep the same main character across all frames.
- Repeat the same character identity, clothing, age, hair, and visual style in every image_prompt.
- Make prompts in English because Stable Diffusion 1.5 understands English better.
- Avoid text, logos, watermarks, graphic violence, explicit sexual content, gore, self-harm, and unsafe content.
- Each image_prompt must be cinematic and detailed.
- Target resolution is {width}x{height}.
- Good SD 1.5 style keywords: cinematic, realistic lighting, soft shadows, film still, detailed, 35mm photography.
- Do not mention frame numbers inside the image prompt.
"""

    user_prompt = f"""
Video idea:
{idea}

Return a 5-frame visual storytelling plan as JSON.

JSON schema:
{json.dumps(STORY_SCHEMA, ensure_ascii=False)}
"""

    payload = {
        "model": ollama_model,
        "prompt": user_prompt,
        "system": system_prompt,
        "format": STORY_SCHEMA,
        "stream": True,
        "keep_alive": "0s",
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 4096
        }
    }

    print("\n========== OLLAMA LIVE OUTPUT ==========\n")

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        stream=True,
        timeout=300
    )
    response.raise_for_status()

    full_text = ""

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue

        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            continue

        token = chunk.get("response", "")

        if token:
            print(token, end="", flush=True)
            full_text += token

        if chunk.get("done", False):
            break

    print("\n\n========== OLLAMA OUTPUT END ==========\n")

    plan = extract_json(full_text)

    if "frames" not in plan or len(plan["frames"]) != 5:
        raise ValueError(
            "Model 5 frame üretmedi. Gelen çıktı:\n"
            + json.dumps(plan, indent=2, ensure_ascii=False)
        )

    return plan


def load_sd15(sd_model: str) -> DiffusionPipeline:
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    pipe = DiffusionPipeline.from_pretrained(
        sd_model,
        torch_dtype=dtype,
        use_safetensors=True
    )

    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
        pipe.enable_attention_slicing()
    else:
        pipe = pipe.to("cpu")

    try:
        pipe.enable_xformers_memory_efficient_attention()
        print("[OK] xFormers memory efficient attention aktif.")
    except Exception:
        print("[INFO] xFormers yok, attention slicing ile devam ediliyor.")

    return pipe

def generate_images(
    pipe: StableDiffusionPipeline,
    plan: Dict[str, Any],
    out_dir: Path,
    width: int,
    height: int,
    steps: int,
    guidance: float,
    seed: int
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    plan_path = out_dir / "story_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    negative_prompt = plan.get(
        "negative_prompt",
        "blurry, low quality, worst quality, deformed face, bad anatomy, extra fingers, watermark, text, logo"
    )

    generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu").manual_seed(seed)

    frames: List[Dict[str, Any]] = plan["frames"]

    for item in frames:
        frame_no = int(item["frame"])
        prompt = item["image_prompt"].strip()

        print(f"\n[FRAME {frame_no}]")
        print(prompt[:300] + ("..." if len(prompt) > 300 else ""))

        image = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=generator
        ).images[0]

        image_path = out_dir / f"frame_{frame_no:02d}.png"
        image.save(image_path)
        print(f"[OK] Kaydedildi: {image_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--idea", type=str, required=True, help="Video fikrin")
    parser.add_argument("--ollama-model", type=str, default="llama3.1:8b", help="Ollama model adı")
    parser.add_argument("--sd-model", type=str, default="stable-diffusion-v1-5/stable-diffusion-v1-5")
    parser.add_argument("--out", type=str, default="outputs/story_001")
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--guidance", type=float, default=7.5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_dir = Path(args.out)

    print("[1/3] Ollama ile 5 frame storyboard oluşturuluyor...")
    plan = ask_ollama_for_storyboard(
        idea=args.idea,
        ollama_model=args.ollama_model,
        width=args.width,
        height=args.height
    )

    unload_ollama_model(args.ollama_model)

    print("\n[STORY TITLE]", plan.get("title", "Untitled"))
    print("[MAIN CHARACTER]", plan.get("main_character", ""))
    print("\n[2/3] SD 1.5 yükleniyor...")
    pipe = load_sd15(args.sd_model)

    print("\n[3/3] Görseller üretiliyor...")
    generate_images(
        pipe=pipe,
        plan=plan,
        out_dir=out_dir,
        width=args.width,
        height=args.height,
        steps=args.steps,
        guidance=args.guidance,
        seed=args.seed
    )

    print(f"\nBitti kanki. Çıktılar burada: {out_dir}")


if __name__ == "__main__":
    main()
