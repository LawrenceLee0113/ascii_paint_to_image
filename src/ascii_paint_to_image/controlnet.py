import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


DEFAULT_CONTROLNET_BASE_MODEL = "runwayml/stable-diffusion-v1-5"
DEFAULT_CONTROLNET_MODEL = "lllyasviel/control_v11p_sd15_scribble"


@dataclass(frozen=True)
class ControlNetExperiment:
    name: str
    prompt: str
    negative_prompt: str
    seed: int
    steps: int
    guidance_scale: float
    controlnet_conditioning_scale: float

    def slug(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        return slug or "experiment"


@dataclass(frozen=True)
class ControlNetResult:
    experiment: ControlNetExperiment
    image_path: Path


def default_controlnet_experiments() -> List[ControlNetExperiment]:
    negative = (
        "low quality, blurry, distorted, extra limbs, text, watermark, logo, "
        "cropped, noisy, malformed"
    )
    return [
        ControlNetExperiment(
            name="photo-object",
            prompt="a photorealistic small sculptural object matching the sketch outline, studio lighting, detailed material texture",
            negative_prompt=negative,
            seed=3101,
            steps=16,
            guidance_scale=7.0,
            controlnet_conditioning_scale=0.85,
        ),
        ControlNetExperiment(
            name="product-render",
            prompt="a clean product design render following the sketch silhouette, white background, soft shadows, precise edges",
            negative_prompt=negative,
            seed=3102,
            steps=16,
            guidance_scale=7.5,
            controlnet_conditioning_scale=0.9,
        ),
        ControlNetExperiment(
            name="watercolor",
            prompt="a watercolor illustration following the sketch structure, layered translucent pigment, handmade paper texture",
            negative_prompt=negative,
            seed=3103,
            steps=16,
            guidance_scale=7.0,
            controlnet_conditioning_scale=0.75,
        ),
        ControlNetExperiment(
            name="iconic-poster",
            prompt="a bold graphic poster image matching the sketch composition, high contrast, screen printed shapes, crisp silhouette",
            negative_prompt=negative,
            seed=3104,
            steps=16,
            guidance_scale=8.0,
            controlnet_conditioning_scale=0.8,
        ),
        ControlNetExperiment(
            name="abstract-material",
            prompt="an abstract polished material study guided by the sketch outline, ceramic, glass, brushed metal, dramatic light",
            negative_prompt=negative,
            seed=3105,
            steps=16,
            guidance_scale=7.0,
            controlnet_conditioning_scale=0.7,
        ),
    ]


def select_torch_device(requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    try:
        import torch
    except Exception:
        return "cpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def run_controlnet_experiments(
    outline_path: Path,
    output_dir: Path,
    experiments: Iterable[ControlNetExperiment],
    base_model: str = DEFAULT_CONTROLNET_BASE_MODEL,
    controlnet_model: str = DEFAULT_CONTROLNET_MODEL,
    device: str = "auto",
    width: int = 512,
    height: int = 512,
) -> List[ControlNetResult]:
    try:
        import torch
        from diffusers import ControlNetModel, StableDiffusionControlNetPipeline, UniPCMultistepScheduler
        from PIL import Image
    except Exception as exc:
        raise RuntimeError(
            "ControlNet inference requires diffusers, transformers, accelerate, torch, and pillow. "
            "Install them before running --controlnet-demo."
        ) from exc

    resolved_device = select_torch_device(device)
    torch_dtype = torch.float16 if resolved_device == "cuda" else torch.float32
    load_kwargs = {"torch_dtype": torch_dtype, "use_safetensors": True}
    if resolved_device in ("mps", "cuda"):
        load_kwargs["variant"] = "fp16"
    controlnet = ControlNetModel.from_pretrained(controlnet_model, **load_kwargs)
    pipeline = StableDiffusionControlNetPipeline.from_pretrained(
        base_model,
        controlnet=controlnet,
        **load_kwargs,
        safety_checker=None,
        requires_safety_checker=False,
    )
    pipeline.scheduler = UniPCMultistepScheduler.from_config(pipeline.scheduler.config)
    pipeline = pipeline.to(resolved_device)
    pipeline.enable_attention_slicing()
    pipeline.vae.enable_slicing()

    control_image = Image.open(outline_path).convert("RGB").resize((width, height))
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[ControlNetResult] = []
    for experiment in experiments:
        generator = torch.Generator(device="cpu").manual_seed(experiment.seed)
        image = pipeline(
            prompt=experiment.prompt,
            negative_prompt=experiment.negative_prompt,
            image=control_image,
            num_inference_steps=experiment.steps,
            guidance_scale=experiment.guidance_scale,
            controlnet_conditioning_scale=experiment.controlnet_conditioning_scale,
            generator=generator,
            width=width,
            height=height,
        ).images[0]
        image_path = output_dir / f"{experiment.slug()}.png"
        image.save(image_path)
        results.append(ControlNetResult(experiment=experiment, image_path=image_path))
    return results
