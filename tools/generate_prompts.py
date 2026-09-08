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


BODY_TYPES = {
    "quadruped": {
        "keywords": ["quadruped", "hooves", "four legs"],
        "creatures": ["Boar", "Wolf", "Dire Wolf", "Worg", "Lion", "Tiger",
                       "Panther", "Bear", "Brown Bear", "Polar Bear", "Deer",
                       "Elk", "Mastiff", "Hyena", "Jackal", "Weasel", "Cat",
                       "Rat", "Mammoth", "Elephant", "Rhinoceros", "Camel",
                       "Draft Horse", "Riding Horse", "Warhorse", "Mule",
                       "Hippopotamus", "Saber-Toothed Tiger", "Hell Hound",
                       "Blink Dog", "Giant Boar", "Giant Hyena", "Giant Rat",
                       "Giant Weasel", "Giant Lizard"],
        "facing": "Three-quarter front-right view. Body oriented diagonally, head turned slightly toward viewer. Front legs visible, hind legs partially behind.",
        "idle_hint": "Standing alert on all fours, ears up, weight evenly distributed.",
    },
    "serpentine": {
        "keywords": ["serpent", "snake", "worm", "eel"],
        "creatures": ["Constrictor Snake", "Giant Constrictor Snake",
                       "Flying Snake", "Giant Venomous Snake", "Purple Worm",
                       "Behir", "Remorhaz"],
        "facing": "Three-quarter front-right view. Body coiled or S-curved, head raised and facing viewer.",
        "idle_hint": "Coiled with head raised, alert and watchful.",
    },
    "avian": {
        "keywords": ["wings", "flying", "bird"],
        "creatures": ["Eagle", "Giant Eagle", "Hawk", "Blood Hawk", "Raven",
                       "Giant Vulture", "Owl", "Bat", "Roc", "Griffon",
                       "Hippogriff", "Pseudodragon", "Pteranodon", "Wyvern",
                       "Cockatrice", "Harpy", "Axe Beak"],
        "facing": "Three-quarter front-right view. Wings partially spread or folded at sides. Talons/feet visible below.",
        "idle_hint": "Perched or standing with wings folded, head alert.",
    },
    "dragon": {
        "keywords": ["dragon"],
        "creatures": [],
        "facing": "Three-quarter front-right view. Wings partially spread, long neck curved toward viewer. Tail trailing behind. Forelimbs and hind legs visible.",
        "idle_hint": "Rearing slightly with wings half-spread, head raised, imposing and alert.",
    },
    "amorphous": {
        "keywords": ["amorphous", "ooze", "blob"],
        "creatures": ["Gelatinous Cube", "Ochre Jelly", "Gray Ooze",
                       "Black Pudding", "Shambling Mound"],
        "facing": "Three-quarter front-right view. Shapeless mass with a vaguely defined front face.",
        "idle_hint": "Quivering mass at rest, pseudopods retracted.",
    },
    "aquatic": {
        "keywords": ["fish", "shark", "whale", "seahorse", "octopus"],
        "creatures": ["Octopus", "Giant Octopus", "Giant Seahorse", "Seahorse",
                       "Hunter Shark", "Giant Shark", "Reef Shark", "Killer Whale",
                       "Piranha", "Giant Crocodile", "Crocodile", "Giant Frog",
                       "Giant Toad", "Frog", "Aboleth", "Kraken", "Dragon Turtle",
                       "Merfolk Skirmisher", "Merrow", "Sahuagin Warrior"],
        "facing": "Three-quarter front-right view. Body angled as if swimming or hovering, fins/tentacles visible.",
        "idle_hint": "Floating or hovering in a neutral swimming pose.",
    },
    "arachnid": {
        "keywords": ["spider", "eight legs", "scorpion"],
        "creatures": ["Spider", "Giant Spider", "Phase Spider", "Scorpion",
                       "Giant Scorpion", "Ettercap", "Drider"],
        "facing": "Three-quarter front-right view. Multiple legs splayed outward, body low to ground, front pair of legs raised slightly.",
        "idle_hint": "Crouched low, legs splayed, pedipalps or pincers forward.",
    },
    "swarm": {
        "keywords": ["swarm"],
        "creatures": [],
        "facing": "Three-quarter view. Clustered mass of tiny creatures forming a loose cloud or mound shape.",
        "idle_hint": "Swirling cluster of tiny creatures, loosely cohesive.",
    },
    "plant": {
        "keywords": ["plant body", "tree"],
        "creatures": ["Treant", "Awakened Tree", "Awakened Shrub",
                       "Shambling Mound", "Violet Fungus"],
        "facing": "Three-quarter front-right view. Trunk or main body facing viewer, branches/limbs spread naturally.",
        "idle_hint": "Standing rooted, branches slightly swaying, ancient and still.",
    },
    "insectoid": {
        "keywords": ["insect", "beetle", "wasp", "centipede", "ant"],
        "creatures": ["Giant Centipede", "Giant Fire Beetle", "Giant Wasp",
                       "Stirge", "Ankheg", "Rust Monster"],
        "facing": "Three-quarter front-right view. Segmented body visible, legs splayed, antennae forward.",
        "idle_hint": "Crouched or standing, antennae twitching, legs poised.",
    },
}

ARMED_HUMANOID_FACING = (
    "Three-quarter front-right view. Body angled slightly right. "
    "Weapon arm (right) visible; shield arm (left) partially occluded."
)
UNARMED_HUMANOID_FACING = (
    "Three-quarter front-right view. Body angled slightly right, "
    "arms at sides or in a natural resting position."
)
ELEMENTAL_FACING = (
    "Three-quarter front-right view. Swirling elemental form "
    "with a vaguely humanoid shape, no distinct limbs needed."
)


def classify_body_type(spec: dict) -> str:
    name = spec.get("entity_name", "")
    descriptors = " ".join(spec.get("visual_descriptors", [])).lower()
    creature_type = spec.get("creature_type", "")

    if "swarm" in name.lower():
        return "swarm"

    for btype, info in BODY_TYPES.items():
        if name in info["creatures"]:
            return btype

    if "dragon" in name.lower() and "Dragon" in creature_type:
        return "dragon"

    for btype, info in BODY_TYPES.items():
        for kw in info["keywords"]:
            if kw in descriptors:
                return btype

    if "Ooze" in creature_type:
        return "amorphous"
    if "Plant" in creature_type:
        return "plant"
    if "Elemental" in creature_type:
        return "elemental"

    return "humanoid"


def get_facing_description(spec: dict) -> str:
    body_type = classify_body_type(spec)

    if body_type in BODY_TYPES:
        return BODY_TYPES[body_type]["facing"]

    if body_type == "elemental":
        return ELEMENTAL_FACING

    has_weapon = "weapon" in spec.get("material_assignments", {})
    has_shield = "shield" in spec.get("material_assignments", {})
    equipment = spec.get("typical_equipment") or []

    if has_weapon or has_shield or any(
        e in equipment for e in [
            "longsword", "greatsword", "scimitar", "mace", "dagger",
            "spear", "greataxe", "shield", "staff", "wand",
            "longbow", "shortbow", "crossbow",
        ]
    ):
        return ARMED_HUMANOID_FACING

    return UNARMED_HUMANOID_FACING


def get_idle_hint(spec: dict) -> str | None:
    body_type = classify_body_type(spec)
    if body_type in BODY_TYPES:
        return BODY_TYPES[body_type]["idle_hint"]
    if body_type == "elemental":
        return "Hovering or swirling in place, elemental energy contained."
    return None


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
    else:
        lines.append("Equipment: none — this creature does not carry weapons or tools.")
    lines.append("")

    lines.append("== POSE ==")
    if frame_info and frame_info.get("pose_hint"):
        idle_override = get_idle_hint(spec) if frame == "idle" else None
        if idle_override:
            lines.append(f"Frame: {frame} — {idle_override}")
        else:
            lines.append(f"Frame: {frame} — {frame_info['pose_hint']}")
    facing = get_facing_description(spec)
    lines.append(f"Facing: {facing}")
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
