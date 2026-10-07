import os
import torch
from diffusers import Ideogram4Pipeline

model_id = "ideogram-ai/ideogram-4-nf4-diffusers"

pipe = Ideogram4Pipeline.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    token=os.environ.get("HF_TOKEN", True),
)

pipe.enable_attention_slicing()
pipe.enable_model_cpu_offload()

prompt = "Astronaut in a jungle, cold color palette, muted colors, detailed, 8k"

image = pipe(
    prompt,
    height=1024,
    width=1024,
    num_inference_steps=24,
).images[0]

image.save("out.png")
print("Bitti: out.png kaydedildi")

