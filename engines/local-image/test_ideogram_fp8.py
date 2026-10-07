import torch
from diffusers import DiffusionPipeline

model_id = "ideogram-ai/ideogram-4-fp8"

pipe = DiffusionPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16
)

pipe = pipe.to("cuda")

prompt = "Astronaut in a jungle, cold color palette, muted colors, detailed, 8k"
image = pipe(prompt).images[0]
image.save("out.png")

print("Bitti: out.png kaydedildi")

