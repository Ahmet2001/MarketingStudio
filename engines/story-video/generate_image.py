import os
from pathlib import Path

import replicate

from api_retry import RetryPolicy, call_with_retry


TEXT = "MIDNIGHT STORIES"
RETRY_POLICY = RetryPolicy()

prompt = f"""
Create a cinematic vertical poster for a storytelling channel.

The exact text "{TEXT}" must appear at the center of the image.
Spell the text exactly as written.
Large, clean, bold typography.
Dark mysterious city at night in the background.
Cinematic lighting, blue fog, dramatic atmosphere.
Professional YouTube Shorts poster design.
No additional text, no watermark, no logo.
"""

output = call_with_retry(
    lambda: replicate.run(
        "ideogram-ai/ideogram-v3-turbo",
        input={
            "prompt": prompt,
            "aspect_ratio": "9:16",

            # Metni modelin değiştirme ihtimalini azaltır
            "magic_prompt_option": "Off",
        },
    ),
    label="Replicate poster generation",
    policy=RETRY_POLICY,
)

output_path = Path("poster_with_text.png")

# Ideogram tek FileOutput döndürür.
# Bazı modeller liste döndürdüğü için ikisini de destekliyoruz.
file_output = output[0] if isinstance(output, list) else output

image_bytes = call_with_retry(
    file_output.read,
    label="Replicate poster download",
    policy=RETRY_POLICY,
)
if not image_bytes:
    raise RuntimeError("Replicate returned an empty poster image.")
output_path.write_bytes(image_bytes)

print(f"Görsel kaydedildi: {output_path.resolve()}")

try:
    print(f"Görsel URL'si: {file_output.url()}")
except (AttributeError, TypeError):
    pass
