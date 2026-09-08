#!/usr/bin/env python3
"""
Auto-generate asset specifications for all SRD entities.

Reads the entity index and sprite profiles, infers ramp family
assignments based on creature type, visual descriptors, and equipment,
then writes one JSON spec per entity into art/asset-specs/.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def name_to_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug


def base_creature_type(creature_type: str) -> str:
    return creature_type.split("(")[0].strip()


DRAGON_COLOR_RAMPS = {
    "red": "LEATHER-RED",
    "blue": "CLOTH-BLUE",
    "green": "CLOTH-GREEN",
    "black": "CLOTH-OLIVE",
    "white": "NEUTRAL-COOL",
    "gold": "WARM-GOLD",
    "silver": "METAL-IRON",
    "bronze": "WARM-GOLD",
    "copper": "LEATHER-BROWN",
    "brass": "WARM-GOLD",
}

ELEMENTAL_RAMPS = {
    "fire": "FIRE",
    "air": "NEUTRAL-COOL",
    "water": "CLOTH-TEAL",
    "earth": "LEATHER-BROWN",
    "ice": "CLOTH-BLUE",
    "magma": "FIRE",
    "mud": "LEATHER-BROWN",
    "smoke": "NEUTRAL-COOL",
    "steam": "NEUTRAL-COOL",
    "dust": "CLOTH-SAGE",
}

EQUIPMENT_RAMPS = {
    "longsword": "METAL-IRON",
    "greatsword": "METAL-IRON",
    "scimitar": "METAL-IRON",
    "dagger": "METAL-IRON",
    "mace": "METAL-IRON",
    "spear": "WOOD",
    "javelin": "WOOD",
    "greataxe": "METAL-IRON",
    "crossbow": "WOOD",
    "longbow": "WOOD",
    "shortbow": "WOOD",
    "staff": "WOOD",
    "wand": "WOOD",
    "shield": "METAL-IRON",
    "plate armor": "METAL-IRON",
    "chain mail": "METAL-IRON",
    "scale mail": "METAL-IRON",
    "leather armor": "LEATHER-BROWN",
    "hide armor": "LEATHER-BROWN",
}

CLASS_DEFAULTS = {
    "Barbarian": {
        "body": "SKIN-MEDIUM",
        "clothing": "LEATHER-BROWN",
        "weapon": "METAL-IRON",
    },
    "Bard": {
        "body": "SKIN-LIGHT",
        "clothing": "CLOTH-VIOLET",
        "weapon": "WOOD",
        "accent": "WARM-GOLD",
    },
    "Cleric": {
        "body": "SKIN-MEDIUM",
        "armor": "METAL-IRON",
        "clothing": "CLOTH-RED",
        "weapon": "METAL-IRON",
    },
    "Druid": {
        "body": "SKIN-MEDIUM",
        "clothing": "CLOTH-GREEN",
        "weapon": "WOOD",
        "accent": "CLOTH-SAGE",
    },
    "Fighter": {
        "body": "SKIN-MEDIUM",
        "armor": "METAL-IRON",
        "weapon": "METAL-IRON",
        "clothing": "CLOTH-RED",
    },
    "Monk": {
        "body": "SKIN-MEDIUM",
        "clothing": "CLOTH-ORANGE",
        "accent": "CLOTH-SAGE",
    },
    "Paladin": {
        "body": "SKIN-LIGHT",
        "armor": "METAL-IRON",
        "weapon": "METAL-IRON",
        "clothing": "CLOTH-BLUE",
        "accent": "WARM-GOLD",
    },
    "Ranger": {
        "body": "SKIN-MEDIUM",
        "armor": "LEATHER-BROWN",
        "weapon": "WOOD",
        "clothing": "CLOTH-GREEN",
    },
    "Rogue": {
        "body": "SKIN-MEDIUM",
        "armor": "LEATHER-BROWN",
        "weapon": "METAL-IRON",
        "clothing": "CLOTH-OLIVE",
    },
    "Sorcerer": {
        "body": "SKIN-LIGHT",
        "clothing": "CLOTH-MAGENTA",
        "weapon": "WOOD",
        "accent": "MAGIC-VIOLET",
    },
    "Warlock": {
        "body": "SKIN-COOL",
        "clothing": "CLOTH-VIOLET",
        "weapon": "WOOD",
        "accent": "MAGIC-TEAL",
    },
    "Wizard": {
        "body": "SKIN-LIGHT",
        "clothing": "CLOTH-BLUE",
        "weapon": "WOOD",
        "accent": "MAGIC-BLUE",
    },
}

POSE_HINTS = {
    "monster": {
        "idle": "Standing alert in a neutral ready stance, weight balanced.",
        "attack": "Mid-strike with primary attack, body lunging forward.",
        "death": "Collapsing or fallen, body limp and defeated.",
    },
    "player": {
        "idle": "Standing alert in a neutral ready stance, weapon at side.",
        "attack": "Mid-swing or thrust with primary weapon.",
        "hit": "Recoiling from a blow, body flinching backward.",
        "death": "Collapsing or fallen, body limp and defeated.",
        "cast": "Channeling magic, free hand raised with energy gathering.",
    },
}


def determine_outline(entity: dict, cfg: dict) -> str:
    defaults = cfg.get("outline_family_defaults", {})
    overrides = defaults.get("overrides", {})
    ct = base_creature_type(entity.get("creature_type", ""))
    name_lower = entity["name"].lower()

    for rule in overrides.values():
        for keyword in rule.get("keywords", []):
            if keyword in name_lower:
                return rule["family"]
        for ctype in rule.get("creature_types", []):
            if ctype == ct:
                return rule["family"]

    return defaults.get("default", "OUTLINE-WARM")


def infer_body_material(entity: dict) -> str:
    ct = base_creature_type(entity.get("creature_type", ""))
    name_lower = entity["name"].lower()
    descriptors = " ".join(entity.get("visual_descriptors", [])).lower()

    if ct == "Dragon":
        for color, ramp in DRAGON_COLOR_RAMPS.items():
            if color in name_lower:
                return ramp
        return "CLOTH-GREEN"

    if ct == "Undead":
        if "skeleton" in name_lower or "exposed bones" in descriptors:
            return "BONE"
        if "ghost" in name_lower or "specter" in name_lower or "translucent" in descriptors:
            return "NEUTRAL-COOL"
        if "zombie" in name_lower or "rotting" in descriptors:
            return "SKIN-COOL"
        if "vampire" in name_lower:
            return "SKIN-LIGHT"
        if "lich" in name_lower or "mummy" in name_lower:
            return "BONE"
        if "wraith" in name_lower or "wight" in name_lower:
            return "NEUTRAL-COOL"
        return "BONE"

    if ct == "Elemental":
        for key, ramp in ELEMENTAL_RAMPS.items():
            if key in name_lower:
                return ramp
        return "NEUTRAL-COOL"

    if ct == "Fiend":
        if "devil" in name_lower or "pit" in name_lower:
            return "LEATHER-RED"
        if "demon" in name_lower:
            return "SKIN-DARK"
        if "succubus" in name_lower or "incubus" in name_lower:
            return "SKIN-COOL"
        return "SKIN-DARK"

    if ct == "Celestial":
        return "SKIN-LIGHT"

    if ct == "Fey":
        if "goblin" in descriptors or "goblinoid" in descriptors:
            return "SKIN-DARK"
        if "hag" in name_lower:
            return "SKIN-COOL"
        return "SKIN-LIGHT"

    if ct == "Aberration":
        if "beholder" in name_lower:
            return "SKIN-COOL"
        return "SKIN-COOL"

    if ct == "Giant":
        if "frost" in name_lower or "ice" in name_lower:
            return "SKIN-COOL"
        if "fire" in name_lower:
            return "SKIN-DARK"
        if "stone" in name_lower:
            return "NEUTRAL-COOL"
        if "storm" in name_lower:
            return "SKIN-MEDIUM"
        if "cloud" in name_lower:
            return "SKIN-LIGHT"
        return "SKIN-MEDIUM"

    if ct == "Construct":
        if "golem" in name_lower:
            if "iron" in name_lower:
                return "METAL-IRON"
            if "stone" in name_lower:
                return "NEUTRAL-COOL"
            if "clay" in name_lower:
                return "LEATHER-BROWN"
            if "flesh" in name_lower:
                return "SKIN-COOL"
            return "METAL-IRON"
        if "animated" in name_lower:
            return "METAL-IRON"
        return "METAL-IRON"

    if ct == "Plant":
        return "CLOTH-GREEN"

    if ct == "Ooze":
        if "black" in name_lower:
            return "CLOTH-OLIVE"
        if "gray" in name_lower or "grey" in name_lower:
            return "NEUTRAL-COOL"
        return "CLOTH-SAGE"

    if ct == "Beast" or ct.startswith("Swarm"):
        if "fur" in descriptors:
            return "LEATHER-BROWN"
        if any(d in descriptors for d in ["scales", "reptile", "serpent", "snake"]):
            return "CLOTH-GREEN"
        if "spider" in name_lower or "scorpion" in name_lower or "insect" in name_lower:
            return "LEATHER-BROWN"
        if any(w in name_lower for w in ["shark", "octopus", "seahorse", "fish", "crocodile"]):
            return "CLOTH-SAGE"
        if any(w in name_lower for w in ["bat", "raven", "vulture", "hawk", "eagle", "owl"]):
            return "LEATHER-BROWN"
        return "LEATHER-BROWN"

    if ct == "Monstrosity":
        if "basilisk" in name_lower or "cockatrice" in name_lower:
            return "CLOTH-GREEN"
        if "minotaur" in name_lower:
            return "SKIN-DARK"
        if "medusa" in name_lower:
            return "SKIN-COOL"
        if "roper" in name_lower:
            return "NEUTRAL-COOL"
        if "manticore" in name_lower or "chimera" in name_lower:
            return "LEATHER-BROWN"
        if "hydra" in name_lower:
            return "CLOTH-GREEN"
        if "griffon" in name_lower or "hippogriff" in name_lower:
            return "LEATHER-BROWN"
        return "SKIN-MEDIUM"

    if ct == "Humanoid":
        return "SKIN-MEDIUM"

    return "SKIN-MEDIUM"


def infer_accent_material(entity: dict) -> str | None:
    ct = base_creature_type(entity.get("creature_type", ""))
    name_lower = entity["name"].lower()
    descriptors = " ".join(entity.get("visual_descriptors", [])).lower()

    if ct == "Dragon":
        return "WARM-GOLD"
    if ct == "Celestial":
        return "WARM-GOLD"
    if ct == "Fiend":
        return "FIRE"
    if ct == "Undead":
        if "lich" in name_lower:
            return "MAGIC-VIOLET"
        return None
    if ct == "Elemental":
        return None
    if "wings" in descriptors:
        return "LEATHER-BROWN"
    if "humanoid" in ct.lower():
        return "CLOTH-RED"
    return None


def infer_equipment_materials(entity: dict) -> dict[str, str]:
    materials: dict[str, str] = {}
    equipment = entity.get("typical_equipment") or []

    has_weapon = False
    has_armor = False
    has_shield = False

    for item in equipment:
        ramp = EQUIPMENT_RAMPS.get(item)
        if ramp is None:
            continue
        if "armor" in item or "mail" in item:
            materials["armor"] = ramp
            has_armor = True
        elif item == "shield":
            materials["shield"] = ramp
            has_shield = True
        elif item in ("staff", "wand"):
            materials["weapon"] = ramp
            has_weapon = True
        elif item in ("longbow", "shortbow", "crossbow"):
            materials["weapon"] = ramp
            has_weapon = True
        else:
            if not has_weapon:
                materials["weapon"] = ramp
                has_weapon = True

    return materials


def infer_eye_material(entity: dict) -> str | None:
    ct = base_creature_type(entity.get("creature_type", ""))
    name_lower = entity["name"].lower()

    if ct == "Undead":
        if "skeleton" in name_lower:
            return None
        return "FIRE"
    if ct == "Fiend":
        return "FIRE"
    if ct == "Dragon":
        return "WARM-GOLD"
    if ct == "Construct":
        return "MAGIC-BLUE"
    if ct == "Aberration":
        return "MAGIC-VIOLET"
    if ct == "Celestial":
        return "MAGIC-BLUE"
    return None


def build_material_assignments(entity: dict) -> dict[str, str]:
    materials: dict[str, str] = {}

    materials["body"] = infer_body_material(entity)

    equip_materials = infer_equipment_materials(entity)
    materials.update(equip_materials)

    accent = infer_accent_material(entity)
    if accent and accent != materials.get("body"):
        materials["accent"] = accent

    eyes = infer_eye_material(entity)
    if eyes:
        materials["eyes"] = eyes

    descriptors = " ".join(entity.get("visual_descriptors", [])).lower()
    ct = base_creature_type(entity.get("creature_type", ""))
    if "wings" in descriptors:
        if ct == "Dragon":
            materials["wings"] = materials["body"]
        elif ct == "Fiend":
            materials["wings"] = "LEATHER-RED"
        elif ct == "Celestial":
            materials["wings"] = "NEUTRAL-COOL"
        else:
            materials["wings"] = "LEATHER-BROWN"

    return materials


def build_frames(entity: dict, slug: str) -> list[dict]:
    entity_type = entity["type"]
    frame_list = (
        ["idle", "attack", "hit", "death", "cast"]
        if entity_type == "player"
        else ["idle", "attack", "death"]
    )

    hints = POSE_HINTS.get(entity_type, POSE_HINTS["monster"])
    frames = []
    for frame in frame_list:
        entry: dict = {
            "frame": frame,
            "filename": f"{slug}_{frame}.png",
            "pose_hint": hints.get(frame, ""),
        }
        if frame == "death":
            ct = base_creature_type(entity.get("creature_type", ""))
            if ct not in ("Construct", "Elemental", "Ooze", "Plant"):
                entry["material_overrides"] = {"blood": "BLOOD"}
        frames.append(entry)
    return frames


def generate_notes(entity: dict) -> str:
    ct = base_creature_type(entity.get("creature_type", ""))
    name = entity["name"]
    size = entity.get("dnd_size", "Medium")
    descriptors = entity.get("visual_descriptors", [])

    size_type = f"{size.lower()} {ct.lower()}"
    unique = [d for d in descriptors if not d.startswith(size_type)]
    parts = [f"{size} {ct.lower()}"]
    if unique:
        parts.append(", ".join(unique))

    name_lower = name.lower()
    if ct == "Dragon":
        for color in DRAGON_COLOR_RAMPS:
            if color in name_lower:
                parts.append(f"Dominant {color} coloration throughout scales and wings")
                break
        if "wyrmling" in name_lower:
            parts.append("Smaller proportions, less imposing than adult")
        elif "young" in name_lower:
            parts.append("Moderate size, developing features")
        elif "adult" in name_lower:
            parts.append("Full size with prominent horns and wingspan")
        elif "ancient" in name_lower:
            parts.append("Massive, weathered, ancient and imposing")

    if "swarm" in name_lower:
        parts.append("Render as a clustered mass of tiny creatures, not a single individual")

    if ct == "Ooze":
        parts.append("Amorphous, bloblike form with no distinct limbs")

    if ct == "Elemental":
        for elem in ("fire", "water", "air", "earth"):
            if elem in name_lower:
                parts.append(f"Body composed entirely of {elem}")
                break

    return ". ".join(parts) + "."


def generate_monster_spec(entity: dict, cfg: dict) -> dict:
    slug = name_to_slug(entity["name"])
    outline = determine_outline(entity, cfg)
    materials = build_material_assignments(entity)
    frames = build_frames(entity, slug)

    spec: dict = {
        "spec_version": 1,
        "entity_name": entity["name"],
        "entity_slug": slug,
        "entity_type": "monster",
        "canvas_profile": entity["canvas_profile"],
        "dnd_size": entity.get("dnd_size", "Medium"),
        "creature_type": entity.get("creature_type", ""),
        "cr": entity.get("cr"),
        "outline_family": outline,
        "material_assignments": materials,
        "frames": frames,
        "visual_descriptors": entity.get("visual_descriptors", []),
        "typical_equipment": entity.get("typical_equipment"),
        "generation_notes": generate_notes(entity),
    }
    return spec


def generate_player_spec(
    entity: dict, species: str, variant: str, cfg: dict
) -> dict:
    cls = entity["name"]
    slug = f"{name_to_slug(cls)}_{name_to_slug(species)}_{variant}"
    outline = "OUTLINE-WARM"

    materials = dict(CLASS_DEFAULTS.get(cls, {"body": "SKIN-MEDIUM"}))
    if species in ("Tiefling",):
        materials["body"] = "SKIN-COOL"
        materials["accent"] = materials.get("accent", "FIRE")
    elif species in ("Orc", "Half-Orc", "Goliath"):
        materials["body"] = "SKIN-DARK"
    elif species in ("Elf", "Half-Elf", "Aasimar"):
        materials["body"] = "SKIN-LIGHT"
    elif species == "Dragonborn":
        materials["body"] = "CLOTH-GREEN"
    elif species in ("Dwarf", "Gnome", "Halfling"):
        materials["body"] = "SKIN-MEDIUM"

    frames = build_frames(entity, slug)

    spec: dict = {
        "spec_version": 1,
        "entity_name": cls,
        "entity_slug": slug,
        "entity_type": "player",
        "canvas_profile": "64x64",
        "dnd_size": "Medium",
        "creature_type": "Humanoid",
        "cr": None,
        "outline_family": outline,
        "material_assignments": materials,
        "frames": frames,
        "visual_descriptors": ["medium humanoid", species.lower()],
        "typical_equipment": None,
        "generation_notes": f"{cls} ({species}, variant {variant}). Medium humanoid in class-appropriate gear.",
        "player_species": species,
        "player_variant": variant,
    }
    return spec


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate asset specifications for all SRD entities."
    )
    parser.add_argument(
        "--index", type=Path,
        default=Path("reference/srd_entity_index.json"),
        help="Path to the entity index JSON.",
    )
    parser.add_argument(
        "--config", type=Path,
        default=Path("art/sprite-palettes/resurrect64_sprite_profiles.json"),
        help="Path to the sprite profiles JSON.",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path,
        default=Path("art/asset-specs"),
        help="Output directory for spec files.",
    )
    parser.add_argument(
        "--player-variant", default="a",
        help="Default variant tag for player specs.",
    )
    parser.add_argument(
        "--player-species", nargs="*",
        help="Generate only these species for players (default: Human).",
    )
    args = parser.parse_args()

    index = load_json(args.index)
    cfg = load_json(args.config)

    valid_ramps = set(cfg.get("ramp_families", {}).keys())

    args.output_dir.mkdir(parents=True, exist_ok=True)

    entities = index["entities"]
    monster_count = 0
    player_count = 0
    warnings = []

    for entity in entities:
        if entity["type"] == "monster":
            spec = generate_monster_spec(entity, cfg)

            for mat_name, ramp in spec["material_assignments"].items():
                if ramp not in valid_ramps:
                    warnings.append(
                        f"{entity['name']}: material '{mat_name}' uses "
                        f"unknown ramp '{ramp}'"
                    )

            out = args.output_dir / f"{spec['entity_slug']}.json"
            with out.open("w", encoding="utf-8") as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
                f.write("\n")
            monster_count += 1

        elif entity["type"] == "player":
            species_list = args.player_species or ["Human"]
            variant = args.player_variant

            for species in species_list:
                if species not in (entity.get("available_species") or []):
                    continue
                spec = generate_player_spec(entity, species, variant, cfg)

                for mat_name, ramp in spec["material_assignments"].items():
                    if ramp not in valid_ramps:
                        warnings.append(
                            f"{entity['name']} ({species}): material "
                            f"'{mat_name}' uses unknown ramp '{ramp}'"
                        )

                out = args.output_dir / f"{spec['entity_slug']}.json"
                with out.open("w", encoding="utf-8") as f:
                    json.dump(spec, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                player_count += 1

    if warnings:
        print("WARNINGS:", file=sys.stderr)
        for w in warnings:
            print(f"  {w}", file=sys.stderr)

    print(f"Generated {monster_count} monster specs + {player_count} player specs")
    print(f"Output: {args.output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
