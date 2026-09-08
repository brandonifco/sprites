#!/usr/bin/env python3
"""
Generate image-generation prompts from asset specs.

Reads an asset spec JSON and the sprite profiles to produce a
self-contained prompt optimized for AI image generation. The prompt
includes palette color descriptions, material guidance, and pose.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


RAMP_DESCRIPTIONS = {
    "OUTLINE-WARM": "near-black warm purple-brown",
    "OUTLINE-COOL": "dark blue-gray to charcoal",
    "OUTLINE-VIOLET": "deep plum to dark purple",
    "METAL-IRON": "dark steel gray → silver-white highlights",
    "METAL-BLUE": "dark navy → silver-white highlights",
    "LEATHER-BROWN": "dark brown → warm tan → pale gold",
    "LEATHER-RED": "deep maroon → crimson → bright orange-red",
    "WOOD": "dark walnut brown → tan → pale gold",
    "CLOTH-RED": "deep crimson → scarlet → bright red-orange",
    "CLOTH-ORANGE": "rust → burnt orange → warm peach",
    "CLOTH-YELLOW": "olive-gold → lime-yellow → bright yellow",
    "CLOTH-OLIVE": "dark brown → olive → yellow-green",
    "CLOTH-GREEN": "deep forest green → emerald → bright green → yellow-green",
    "CLOTH-SAGE": "dark teal-gray → muted green → sage → pale sage",
    "CLOTH-TEAL": "deep teal → cyan → bright aqua → pale mint",
    "CLOTH-BLUE": "dark navy → medium blue → sky blue → pale blue",
    "CLOTH-VIOLET": "deep purple → medium purple → lavender → pale lilac",
    "CLOTH-ROSE": "deep mauve → rose → pink → pale pink",
    "CLOTH-MAGENTA": "deep magenta → hot pink → coral → salmon",
    "SKIN-DARK": "deep mahogany → warm brown → tan → peach",
    "SKIN-MEDIUM": "dusty rose-brown → tan → warm peach → salmon",
    "SKIN-LIGHT": "dusty rose → tan → pink → peach → pale cream",
    "SKIN-COOL": "cool plum-gray → dusty rose → pink → salmon",
    "BONE": "dark brown → tan → pale cream → white",
    "MAGIC-TEAL": "deep teal → cyan → bright aqua → pale mint",
    "MAGIC-BLUE": "dark navy → blue → sky blue → pale blue → white glow",
    "MAGIC-VIOLET": "deep purple → medium purple → lavender → pale lilac",
    "MAGIC-ROSE": "deep mauve → rose → pink → pale cream glow",
    "BLOOD": "dark crimson → deep red → bright red",
    "NEUTRAL-COOL": "dark gray-purple → cool gray → silver → pale blue-white",
    "WARM-GOLD": "rust → orange → amber → golden yellow",
    "FIRE": "deep crimson → red → orange → amber → golden yellow",
}


def build_prompt(spec: dict, cfg: dict, frame: str = "idle") -> str:
    profile = cfg["profiles"][spec["canvas_profile"]]
    w, h = profile["width"], profile["height"]
    conventions = cfg.get("rendering_conventions", {})

    frame_info = None
    for f in spec.get("frames", []):
        if f["frame"] == frame:
            frame_info = f
            break

    lines = []

    lines.append(f"Create a {w}x{w} pixel art sprite on a TRANSPARENT background.")
    lines.append("")

    lines.append("== SUBJECT ==")
    lines.append(f"{spec['entity_name']}: {spec.get('generation_notes', '')}")
    if spec.get("visual_descriptors"):
        lines.append(f"Visual features: {', '.join(spec['visual_descriptors'])}")
    if spec.get("typical_equipment"):
        lines.append(f"Equipment: {', '.join(spec['typical_equipment'])}")
    lines.append("")

    lines.append("== POSE ==")
    if frame_info and frame_info.get("pose_hint"):
        lines.append(f"Frame: {frame} — {frame_info['pose_hint']}")
    lines.append(f"Facing: {conventions.get('facing_description', 'Three-quarter front-right view.')}")
    lines.append(f"Lighting: {conventions.get('light_description', 'Upper-left light source.')}")
    lines.append("")

    lines.append("== PIXEL ART STYLE RULES ==")
    lines.append(f"- Exactly {w}x{h} pixels, transparent background (PNG with alpha)")
    lines.append("- Classic pixel art: NO anti-aliasing, NO sub-pixel rendering, NO gradients")
    lines.append("- Every opaque pixel must be a single flat color from the palette below")
    lines.append("- Binary alpha only: each pixel is fully opaque (255) or fully transparent (0)")
    lines.append(f"- 1-pixel dark outline around the entire sprite exterior")
    bbox = profile["occupied_bbox_height_px"]
    lines.append(f"- Sprite height should fill {bbox['min']}-{bbox['max']}px of the {h}px canvas")
    lines.append("- No opaque pixels touching the canvas edge (1px margin all around)")
    colors = profile["unique_opaque_colors"]
    lines.append(f"- Use {colors['min']}-{colors['max']} unique colors total")
    if not profile.get("dithering", {}).get("allowed", True):
        lines.append("- NO dithering or checkerboard patterns")
    else:
        frac = profile.get("dithering", {}).get("max_opaque_fraction", 0)
        if frac > 0:
            lines.append(f"- Dithering allowed sparingly (max {frac:.0%} of opaque pixels), rough materials only")
    lines.append("")

    lines.append("== COLOR PALETTE — USE ONLY THESE COLORS ==")
    lines.append(f"Outline: {RAMP_DESCRIPTIONS.get(spec['outline_family'], spec['outline_family'])}")
    lines.append("")
    lines.append("Material colors (use the described color ramp for each body part):")

    mats = dict(spec.get("material_assignments", {}))
    if frame_info and frame_info.get("material_overrides"):
        mats.update(frame_info["material_overrides"])

    for mat_name, ramp in mats.items():
        desc = RAMP_DESCRIPTIONS.get(ramp, ramp)
        lines.append(f"  • {mat_name}: {desc}")

    lines.append("")
    lines.append("Each material region should show 2-4 distinct value steps from the ramp:")
    lines.append("darkest on lower-right edges (shadow), lightest on upper-left (highlight).")
    lines.append("")
    lines.append("== IMPORTANT ==")
    lines.append("This must look like a retro game sprite — chunky, readable pixels with")
    lines.append("clear silhouette. Think SNES/GBA era pixel art. No smooth gradients,")
    lines.append("no blurring, no soft edges. Every pixel is intentional.")

    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate image-generation prompts from asset specs."
    )
    parser.add_argument(
        "specs", nargs="+", type=Path,
        help="Asset spec JSON file(s).",
    )
    parser.add_argument(
        "--config", type=Path,
        default=Path("art/sprite-palettes/resurrect64_sprite_profiles.json"),
    )
    parser.add_argument(
        "--frame", default="idle",
        help="Which frame to generate prompt for (default: idle).",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path,
        help="Write prompts as .txt files to this directory.",
    )
    parser.add_argument(
        "--all-frames", action="store_true",
        help="Generate prompts for all frames of each entity.",
    )
    args = parser.parse_args()

    cfg = load_json(args.config)

    for spec_path in args.specs:
        spec = load_json(spec_path)
        frames = [args.frame]
        if args.all_frames:
            frames = [f["frame"] for f in spec.get("frames", [])]

        for frame in frames:
            prompt = build_prompt(spec, cfg, frame)

            if args.output_dir:
                args.output_dir.mkdir(parents=True, exist_ok=True)
                slug = spec["entity_slug"]
                out = args.output_dir / f"{slug}_{frame}_prompt.txt"
                out.write_text(prompt, encoding="utf-8")
                print(f"Wrote {out}")
            else:
                print(f"{'='*60}")
                print(f"PROMPT: {spec['entity_name']} — {frame}")
                print(f"{'='*60}")
                print(prompt)
                print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
