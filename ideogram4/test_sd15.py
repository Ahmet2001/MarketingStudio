import torch
from diffusers import StableDiffusionPipeline

model_id = "stable-diffusion-v1-5/stable-diffusion-v1-5"

pipe = StableDiffusionPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    safety_checker=None
)

pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

prompt = "a 17-year-old Turkish male student, short dark hair, frustrated expression, wearing a black hoodie, casual pants, slim build, sitting back in his chair after a problem with his project, hands on his head, messy desk, error visible on laptop screen, feeling disappointed, dramatic low light, cinematic, detailed, storytelling, emotional, realistic lighting, soft shadows, highly detailed, film still, 35mm photography"

image = pipe(
    prompt,
    height=512,
    width=512,
    num_inference_steps=25,
    guidance_scale=7.5
).images[0]

image.save("sd17_out.png")
print("Bitti: sd15_out.png")

