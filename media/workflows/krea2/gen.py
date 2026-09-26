#!/usr/bin/env python3
"""Generate the generic Krea-2 Turbo text-to-image workflow set.

Writes, into this directory: twelve workflow pairs — model in {fp8, int8}
crossed with lora_count in 0..5 — plus README.md. Each pair is a UI-format
workflow (``krea2_<model>_lora<n>.json``, drag onto the ComfyUI canvas or
copy into the server's user workflows directory) and the matching
API-format prompt body (``krea2_<model>_lora<n>.api.json``, the body for
``POST /prompt``). The pipeline mirrors ComfyUI's shipped
``image_krea2_turbo_t2i.json`` template minus its prompt-enhancement stage
(see README.md). Regenerate with: python3 gen.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUT_DIR = Path(__file__).parent

# A fixed seed keeps the twelve files byte-comparable except for the bits
# that actually vary (model, LoRA count). The UI's "randomize" widget still
# re-rolls it on every queue from the editor.
SEED = 424242424242
MAX_LORAS = 5

MODEL_FILES = {
    "fp8": "krea2_turbo_fp8_scaled.safetensors",
    "int8": "krea2_turbo_int8_convrot.safetensors",
}
CLIP_NAME = "qwen3vl_4b_bf16.safetensors"
VAE_NAME = "qwen_image_vae.safetensors"

# name -> trigger word, in slot-fill order (Comfy-Org/Krea-2/loras).
LORAS: list[tuple[str, str]] = [
    ("krea2_darkbrush", "monochrome ink wash style"),
    ("krea2_dotmatrix", "monochrome stippling style"),
    ("krea2_kidsdrawing", "naive expressive sketch style"),
    ("krea2_neondrip", "textured abstract style"),
    ("krea2_rainywindow", "rainy window style"),
    ("krea2_retroanime", "purple retro anime style"),
    ("krea2_softwatercolor", "art deco watercolor style"),
    ("krea2_sunsetblur", "ethereal motion blur style"),
    ("krea2_vintagetarot", "vintage tarot style"),
]

BASE_PROMPT = (
    "A photograph of a red bicycle leaning against a sunlit brick wall, "
    "morning light, shallow depth of field"
)

# Column layout: loaders | loras | conditioning | sampler | decode/save | note.
GAP = 60
COL_LOADERS_X = 0
COL_LORAS_X = COL_LOADERS_X + 315 + GAP
COL_COND_X = COL_LORAS_X + 315 + GAP
COL_SAMPLER_X = COL_COND_X + 400 + GAP
COL_DECODE_X = COL_SAMPLER_X + 315 + GAP
COL_NOTE_X = COL_DECODE_X + 315 + GAP


def lora_strength(slot: int) -> float:
    return 0.8 if slot == 0 else 0.6


class Builder:
    """Assembles one workflow's UI graph and its matching API prompt."""

    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        self.links: list[list[Any]] = []
        self.api: dict[str, Any] = {}
        self._col_y: dict[int, int] = {}
        self._next_link = 1
        self._next_id = 1

    def _y_for(self, x: int, height: int) -> int:
        y = self._col_y.get(x, 0)
        self._col_y[x] = y + height + GAP
        return y

    def add(
        self,
        node_type: str,
        x: int,
        size: tuple[int, int],
        inputs: list[tuple[str, str]],
        outputs: list[tuple[str, str]],
        widgets_values: list[Any],
        api_inputs: dict[str, Any] | None,
        title: str | None = None,
    ) -> int:
        node_id = self._next_id
        self._next_id += 1
        y = self._y_for(x, size[1])
        node: dict[str, Any] = {
            "id": node_id,
            "type": node_type,
            "pos": [x, y],
            "size": list(size),
            "flags": {},
            "order": len(self.nodes),
            "mode": 0,
            "inputs": [{"name": n, "type": t, "link": None} for n, t in inputs],
            "outputs": [
                {"name": n, "type": t, "links": [], "slot_index": i}
                for i, (n, t) in enumerate(outputs)
            ],
            "properties": {"Node name for S&R": node_type},
            "widgets_values": widgets_values,
        }
        if title:
            node["title"] = title
        self.nodes.append(node)
        if api_inputs is not None:
            self.api[str(node_id)] = {"class_type": node_type, "inputs": api_inputs}
        return node_id

    def link(
        self, src_id: int, src_slot: int, dst_id: int, dst_slot: int, ltype: str
    ) -> None:
        link_id = self._next_link
        self._next_link += 1
        for n in self.nodes:
            if n["id"] == src_id:
                n["outputs"][src_slot]["links"].append(link_id)
            if n["id"] == dst_id:
                n["inputs"][dst_slot]["link"] = link_id
        self.links.append([link_id, src_id, src_slot, dst_id, dst_slot, ltype])


def build_variant(
    model_key: str, n_loras: int
) -> tuple[dict[str, Any], dict[str, Any], str]:
    b = Builder()
    variant = f"{model_key}_lora{n_loras}"
    enabled = LORAS[:n_loras]

    unet_id = b.add(
        "UNETLoader",
        COL_LOADERS_X,
        (315, 100),
        inputs=[],
        outputs=[("MODEL", "MODEL")],
        widgets_values=[MODEL_FILES[model_key], "default"],
        api_inputs={"unet_name": MODEL_FILES[model_key], "weight_dtype": "default"},
    )

    model_src = unet_id
    for slot, (lora_name, _trigger) in enumerate(enabled):
        strength = lora_strength(slot)
        lora_file = f"{lora_name}.safetensors"
        lora_id = b.add(
            "LoraLoaderModelOnly",
            COL_LORAS_X,
            (315, 106),
            inputs=[("model", "MODEL")],
            outputs=[("MODEL", "MODEL")],
            widgets_values=[lora_file, strength],
            api_inputs={
                "model": [str(model_src), 0],
                "lora_name": lora_file,
                "strength_model": strength,
            },
        )
        b.link(model_src, 0, lora_id, 0, "MODEL")
        model_src = lora_id

    clip_id = b.add(
        "CLIPLoader",
        COL_LOADERS_X,
        (315, 130),
        inputs=[],
        outputs=[("CLIP", "CLIP")],
        widgets_values=[CLIP_NAME, "krea2", "default"],
        api_inputs={"clip_name": CLIP_NAME, "type": "krea2", "device": "default"},
    )

    prompt = BASE_PROMPT + "".join(f", {trigger}" for _, trigger in enabled)

    pos_id = b.add(
        "CLIPTextEncode",
        COL_COND_X,
        (400, 200),
        inputs=[("clip", "CLIP")],
        outputs=[("CONDITIONING", "CONDITIONING")],
        widgets_values=[prompt],
        api_inputs={"text": prompt, "clip": [str(clip_id), 0]},
    )
    b.link(clip_id, 0, pos_id, 0, "CLIP")

    neg_id = b.add(
        "ConditioningZeroOut",
        COL_COND_X,
        (225, 80),
        inputs=[("conditioning", "CONDITIONING")],
        outputs=[("CONDITIONING", "CONDITIONING")],
        widgets_values=[],
        api_inputs={"conditioning": [str(pos_id), 0]},
    )
    b.link(pos_id, 0, neg_id, 0, "CONDITIONING")

    latent_id = b.add(
        "EmptyLatentImage",
        COL_COND_X,
        (315, 130),
        inputs=[],
        outputs=[("LATENT", "LATENT")],
        widgets_values=[1024, 1024, 1],
        api_inputs={"width": 1024, "height": 1024, "batch_size": 1},
    )

    ksampler_id = b.add(
        "KSampler",
        COL_SAMPLER_X,
        (315, 262),
        inputs=[
            ("model", "MODEL"),
            ("positive", "CONDITIONING"),
            ("negative", "CONDITIONING"),
            ("latent_image", "LATENT"),
        ],
        outputs=[("LATENT", "LATENT")],
        widgets_values=[SEED, "randomize", 8, 1, "euler", "simple", 1],
        api_inputs={
            "seed": SEED,
            "steps": 8,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1,
            "model": [str(model_src), 0],
            "positive": [str(pos_id), 0],
            "negative": [str(neg_id), 0],
            "latent_image": [str(latent_id), 0],
        },
    )
    b.link(model_src, 0, ksampler_id, 0, "MODEL")
    b.link(pos_id, 0, ksampler_id, 1, "CONDITIONING")
    b.link(neg_id, 0, ksampler_id, 2, "CONDITIONING")
    b.link(latent_id, 0, ksampler_id, 3, "LATENT")

    vae_loader_id = b.add(
        "VAELoader",
        COL_LOADERS_X,
        (315, 80),
        inputs=[],
        outputs=[("VAE", "VAE")],
        widgets_values=[VAE_NAME],
        api_inputs={"vae_name": VAE_NAME},
    )

    decode_id = b.add(
        "VAEDecode",
        COL_DECODE_X,
        (225, 80),
        inputs=[("samples", "LATENT"), ("vae", "VAE")],
        outputs=[("IMAGE", "IMAGE")],
        widgets_values=[],
        api_inputs={"samples": [str(ksampler_id), 0], "vae": [str(vae_loader_id), 0]},
    )
    b.link(ksampler_id, 0, decode_id, 0, "LATENT")
    b.link(vae_loader_id, 0, decode_id, 1, "VAE")

    save_prefix = f"krea2/{variant}"
    save_id = b.add(
        "SaveImage",
        COL_DECODE_X,
        (315, 120),
        inputs=[("images", "IMAGE")],
        outputs=[],
        widgets_values=[save_prefix],
        api_inputs={"images": [str(decode_id), 0], "filename_prefix": save_prefix},
    )
    b.link(decode_id, 0, save_id, 0, "IMAGE")

    note_lines = [
        f"## krea2_{variant}",
        "",
        f"- diffusion_models/{MODEL_FILES[model_key]}",
        f"- text_encoders/{CLIP_NAME}",
        f"- vae/{VAE_NAME}",
    ]
    if enabled:
        note_lines.append("")
        note_lines.append("LoRA slots (loras/, model-only, chained in order):")
        for slot, (lora_name, trigger) in enumerate(enabled):
            note_lines.append(
                f"{slot + 1}. `{lora_name}.safetensors` — trigger `{trigger}`, "
                f"strength {lora_strength(slot)}"
            )
        if n_loras > 1:
            note_lines.append("")
            note_lines.append(
                "Stacked styles fight each other — retune strengths per pair."
            )
    note_lines.append("")
    note_lines.append(
        "Source: https://huggingface.co/Comfy-Org/Krea-2 "
        "(diffusion_models/, text_encoders/, vae/, loras/)."
    )
    b.add(
        "MarkdownNote",
        COL_NOTE_X,
        (420, 420),
        inputs=[],
        outputs=[],
        widgets_values=["\n".join(note_lines)],
        api_inputs=None,
        title="Krea-2 Turbo notes",
    )

    ui = {
        "last_node_id": b._next_id - 1,
        "last_link_id": b._next_link - 1,
        "nodes": b.nodes,
        "links": b.links,
        "groups": [],
        "config": {},
        "extra": {},
        "version": 0.4,
    }
    return ui, b.api, variant


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


LORA_TABLE_ROWS = "\n".join(f"| `{name}` | `{trigger}` |" for name, trigger in LORAS)

README_TEMPLATE = """\
# Krea-2 Turbo text-to-image workflows

Generic ComfyUI workflows for the **Krea-2 Turbo** text-to-image pipeline:
twelve variants, `fp8`/`int8` crossed with 0-5 model-only style LoRAs, each
as a UI file and an API file. Generated by `gen.py`; regenerate with
`python3 gen.py` (stdlib only, no deps) and commit the JSON alongside it.

The pipeline mirrors ComfyUI 0.34.5's shipped
`image_krea2_turbo_t2i.json` template minus its prompt-enhancement stage
(no `TextGenerate`/Qwen prompt refiner, no enable/disable switches) — these
files run the fixed pipeline straight: `UNETLoader` to 0-5 chained
`LoraLoaderModelOnly` to `KSampler`, `CLIPLoader` to `CLIPTextEncode` to
`ConditioningZeroOut` for the negative, `EmptyLatentImage` at 1024x1024,
`VAELoader`/`VAEDecode`/`SaveImage`. No `ModelSampling` node, no
`FluxGuidance` — Krea-2 Turbo needs neither.

## Files

- `krea2_<model>_lora<n>.json` — UI format. Drag onto the ComfyUI canvas at
  http://127.0.0.1:8188, or copy into
  `/var/lib/comfyui/user/default/workflows/` as root and reload.
- `krea2_<model>_lora<n>.api.json` — API format, the body for `POST
  /prompt`:

  ```
  curl -s -X POST http://127.0.0.1:8188/prompt \\
    -H 'Content-Type: application/json' \\
    -d "{{\\"prompt\\": $(cat krea2_fp8_lora0.api.json), \\"client_id\\": \\"gen\\"}}"
  ```

## Models

From https://huggingface.co/Comfy-Org/Krea-2:

| slot | file | goes under |
|---|---|---|
| UNET (fp8) | `diffusion_models/{fp8}` | `models/diffusion_models/` |
| UNET (int8) | `diffusion_models/{int8}` | `models/diffusion_models/` (path unconfirmed — not in the shipped template's own model list; check the repo's file listing before fetching) |
| text encoder | `text_encoders/{clip}` | `models/text_encoders/` |
| VAE | `vae/{vae}` | `models/vae/` |
| LoRAs | `loras/<name>.safetensors` | `models/loras/` |

On `core` the models directory is
`/var/lib/comfyui/models/{{diffusion_models,text_encoders,vae,loras}}`,
owned by user `comfyui`. The service's broker allows no egress, so every
fetch happens by hand, off the running service.

## LoRA slots

Style LoRAs are model-only (`LoraLoaderModelOnly`), chained in order, slot
1 at strength 0.8 and each further slot at 0.6 — stacked styles fight each
other, retune per pair. Trigger words are appended to the prompt in slot
order.

| LoRA | trigger word |
|---|---|
{lora_table}

## Validation

Every file was checked against the running 0.34.5 server's
`/object_info`: node types exist, required inputs match, and enum widgets
(`weight_dtype`, `type`, `device`, `sampler_name`, `scheduler`) are valid
members. Every `.api.json` was POSTed to `/prompt` with empty model
folders: each fails validation with `value_not_in_list` only, on
`unet_name`/`clip_name`/`vae_name`/`lora_name` — nothing is ever queued.
`MarkdownNote` is a frontend-only virtual node (absent from
`/object_info`); it is UI-only and omitted from the API files.
"""


def build_readme() -> str:
    return README_TEMPLATE.format(
        fp8=MODEL_FILES["fp8"],
        int8=MODEL_FILES["int8"],
        clip=CLIP_NAME,
        vae=VAE_NAME,
        lora_table=LORA_TABLE_ROWS,
    )


def main() -> None:
    for model_key in MODEL_FILES:
        for n_loras in range(MAX_LORAS + 1):
            ui, api, variant = build_variant(model_key, n_loras)
            write_json(OUT_DIR / f"krea2_{variant}.json", ui)
            write_json(OUT_DIR / f"krea2_{variant}.api.json", api)
    (OUT_DIR / "README.md").write_text(build_readme())


if __name__ == "__main__":
    main()
