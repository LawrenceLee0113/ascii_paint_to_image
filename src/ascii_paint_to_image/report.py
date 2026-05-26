from html import escape
from pathlib import Path
from typing import Iterable

from ascii_paint_to_image.controlnet import ControlNetResult


def write_controlnet_report(
    run_dir: Path,
    title: str,
    outline_path: Path,
    results: Iterable[ControlNetResult],
    base_model: str,
    controlnet_model: str,
    device: str,
) -> Path:
    report_path = run_dir / "controlnet_report.html"
    outline_ref = _relative_ref(report_path, outline_path)
    cards = []
    for result in results:
        experiment = result.experiment
        image_ref = _relative_ref(report_path, result.image_path)
        cards.append(
            "\n".join(
                [
                    '<article class="card">',
                    f"<h2>{escape(experiment.name)}</h2>",
                    '<div class="pair">',
                    f'<figure><img src="{escape(outline_ref)}" alt="input outline"><figcaption>outline.png</figcaption></figure>',
                    f'<figure><img src="{escape(image_ref)}" alt="{escape(experiment.name)} output"><figcaption>{escape(result.image_path.name)}</figcaption></figure>',
                    "</div>",
                    f"<p>{escape(experiment.prompt)}</p>",
                    '<dl>',
                    f"<dt>seed</dt><dd>{experiment.seed}</dd>",
                    f"<dt>steps</dt><dd>{experiment.steps}</dd>",
                    f"<dt>guidance</dt><dd>{experiment.guidance_scale}</dd>",
                    f"<dt>control</dt><dd>{experiment.controlnet_conditioning_scale}</dd>",
                    "</dl>",
                    "</article>",
                ]
            )
        )

    html = "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(title)}</title>",
            "<style>",
            "body{margin:0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#f7f7f4;color:#1e1f21}",
            "header{padding:28px 32px 18px;border-bottom:1px solid #d8d8d0;background:#ffffff}",
            "h1{margin:0 0 10px;font-size:28px;font-weight:700}",
            ".meta{display:flex;flex-wrap:wrap;gap:10px 18px;color:#575a5f;font-size:13px}",
            "main{padding:24px 32px;display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px}",
            ".card{background:#fff;border:1px solid #deded7;border-radius:8px;padding:16px}",
            "h2{font-size:17px;margin:0 0 12px}",
            ".pair{display:grid;grid-template-columns:1fr 1fr;gap:10px}",
            "figure{margin:0}",
            "img{display:block;width:100%;aspect-ratio:1/1;object-fit:contain;background:#ecece6;border:1px solid #ddd}",
            "figcaption{font-size:12px;color:#62666c;margin-top:5px;overflow-wrap:anywhere}",
            "p{font-size:13px;line-height:1.45}",
            "dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 10px;font-size:12px;color:#4d5157}",
            "dt{font-weight:700}",
            "@media(max-width:700px){main{padding:16px;grid-template-columns:1fr}.pair{grid-template-columns:1fr}}",
            "</style>",
            "</head>",
            "<body>",
            "<header>",
            f"<h1>{escape(title)}</h1>",
            '<div class="meta">',
            f"<span>base: {escape(base_model)}</span>",
            f"<span>controlnet: {escape(controlnet_model)}</span>",
            f"<span>device: {escape(device)}</span>",
            "</div>",
            "</header>",
            "<main>",
            "\n".join(cards),
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    report_path.write_text(html)
    return report_path


def _relative_ref(from_path: Path, target_path: Path) -> str:
    return str(target_path.resolve().relative_to(from_path.resolve().parent))
