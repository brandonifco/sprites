#!/usr/bin/env python3
"""
Extract structured entity data from SRD 5.2.1 raw text.

Parses monster stat blocks into a JSON index with name, size, CR,
creature type, alignment, and canvas profile mapping.

The SRD raw text is a PDF-to-text dump with column interleaving,
so this parser uses the size/type line and CR line as anchors.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SIZE_TYPE_RE = re.compile(
    r"^(Tiny|Small|Medium|Large|Huge|Gargantuan)"
    r"(?: or (Small|Medium|Large))?"
    r"\s+(.+?),\s+(.+)$"
)

CR_RE = re.compile(
    r"^CR\s+([\d/]+|None)\s*\(XP\s+([\d,]+)"
)

CREATURE_SIZE_MAP = {
    "Tiny": "64x64",
    "Small": "64x64",
    "Medium": "64x64",
    "Large": "128x128",
    "Huge": "192x192",
    "Gargantuan": "192x192",
}

PLAYER_CLASSES = [
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter",
    "Monk", "Paladin", "Ranger", "Rogue", "Sorcerer",
    "Warlock", "Wizard",
]

SRD_SPECIES = [
    "Human", "Elf", "Dwarf", "Halfling", "Gnome",
    "Half-Elf", "Half-Orc", "Tiefling", "Dragonborn", "Orc",
    "Aasimar", "Goliath",
]

CR_CORRECTIONS = {
    "Troll": "5",
    "Skeleton": "1/4",
    "Goblin Boss": "2",
    "Bandit": "1/8",
    "Chimera": "6",
    "Cockatrice": "1/2",
    "Crawling Claw": "0",
    "Cultist": "1/8",
    "Earth Elemental": "5",
    "Efreeti": "11",
    "Flesh Golem": "5",
    "Violet Fungus": "1/4",
    "Ghast": "2",
    "Gladiator": "5",
    "Gold Dragon Wyrmling": "3",
    "Hell Hound": "3",
    "Hill Giant": "5",
    "Homunculus": "0",
    "Incubus": "4",
    "Magma Mephit": "1/2",
    "Roper": "5",
    "Silver Dragon Wyrmling": "3",
    "Stirge": "1/8",
    "White Dragon Wyrmling": "2",
    "Young White Dragon": "6",
    "Ancient White Dragon": "20",
    "Adult Blue Dragon": "16",
    "Adult Copper Dragon": "14",
    "Ankylosaurus": "3",
    "Boar": "1/4",
    "Dire Wolf": "1",
    "Flying Snake": "1/8",
    "Giant Crocodile": "5",
    "Giant Octopus": "1",
    "Giant Shark": "5",
    "Giant Seahorse": "1/2",
    "Giant Vulture": "1",
    "Jackal": "0",
    "Lizard": "0",
    "Mule": "1/8",
    "Panther": "1/4",
    "Pteranodon": "1/4",
    "Scorpion": "0",
    "Swarm of Insects": "1/2",
    "Swarm of Bats": "1/4",
    "Tyrannosaurus Rex": "8",
    "Triceratops": "5",
    "Warrior Infantry": "1/2",
    "Tough": "1/2",
    "Wraith": "5",
}

NAME_BLACKLIST = {
    "Vampires", "Skeletons", "Zombies", "Bugbears",
}

SIZE_CORRECTIONS = {
    "Hill Giant": "Huge",
}

EQUIPMENT_HINTS = {
    "sword": ["longsword"],
    "scimitar": ["scimitar"],
    "greataxe": ["greataxe"],
    "greatsword": ["greatsword"],
    "mace": ["mace"],
    "dagger": ["dagger"],
    "spear": ["spear"],
    "javelin": ["javelin"],
    "crossbow": ["crossbow"],
    "longbow": ["longbow"],
    "shortbow": ["shortbow"],
    "shield": ["shield"],
    "plate": ["plate armor"],
    "chain": ["chain mail"],
    "scale": ["scale mail"],
    "leather": ["leather armor"],
    "hide": ["hide armor"],
    "staff": ["staff"],
    "wand": ["wand"],
    "claw": [],
    "bite": [],
    "tail": [],
    "tentacle": [],
}


def extract_equipment_from_actions(text: str) -> list[str]:
    equipment = []
    text_lower = text.lower()
    for keyword, items in EQUIPMENT_HINTS.items():
        if keyword in text_lower:
            equipment.extend(items)
    return sorted(set(equipment))


def extract_visual_descriptors(
    name: str, creature_type: str, size: str, actions_text: str
) -> list[str]:
    descriptors = []
    descriptors.append(f"{size.lower()} {creature_type.lower()}")

    name_lower = name.lower()
    type_lower = creature_type.lower()

    if "dragon" in name_lower:
        for color in ["red", "blue", "green", "black", "white",
                       "gold", "silver", "bronze", "copper", "brass"]:
            if color in name_lower:
                descriptors.append(f"{color} scales")
                break
        if "dragon" in type_lower:
            descriptors.append("wings")
            descriptors.append("claws")
            descriptors.append("tail")
    if "undead" in type_lower:
        descriptors.append("undead")
    if "fiend" in type_lower:
        descriptors.append("fiendish")
    if "celestial" in type_lower:
        descriptors.append("radiant")
    if "elemental" in type_lower:
        descriptors.append("elemental form")
    if "construct" in type_lower:
        descriptors.append("constructed body")
    if "plant" in type_lower:
        descriptors.append("plant body")
    if "ooze" in type_lower:
        descriptors.append("amorphous")
    if "goblinoid" in type_lower:
        descriptors.append("goblinoid")
    if "humanoid" in type_lower:
        descriptors.append("humanoid")

    if "skeleton" in name_lower:
        descriptors.append("exposed bones")
    if "zombie" in name_lower:
        descriptors.append("rotting flesh")
    if "ghost" in name_lower or "specter" in name_lower:
        descriptors.append("translucent")
    if "spider" in name_lower:
        descriptors.append("eight legs")
    if "wolf" in name_lower or "worg" in name_lower:
        descriptors.append("quadruped")
        descriptors.append("fur")
    if "bear" in name_lower:
        descriptors.append("quadruped")
        descriptors.append("fur")
    if "horse" in name_lower or "warhorse" in name_lower:
        descriptors.append("quadruped")
        descriptors.append("hooves")
    if "giant" in name_lower and "humanoid" not in type_lower:
        descriptors.append("massive frame")

    actions_lower = actions_text.lower()
    if "bite" in actions_lower and "bite" not in " ".join(descriptors):
        descriptors.append("fangs/bite")
    if "claw" in actions_lower:
        descriptors.append("claws")
    if "tail" in actions_lower and "tail" not in " ".join(descriptors):
        descriptors.append("tail")

    return list(dict.fromkeys(descriptors))


def parse_monsters(lines: list[str]) -> list[dict]:
    monsters_start = None
    for i, line in enumerate(lines):
        if line.strip() == "Monsters A–Z":
            monsters_start = i
            break
    if monsters_start is None:
        for i, line in enumerate(lines):
            if "Monsters A" in line and "Z" in line:
                monsters_start = i
                break
    if monsters_start is None:
        print("WARNING: Could not find Monsters A-Z section", file=sys.stderr)
        return []

    entities = []
    i = monsters_start + 1

    while i < len(lines):
        line = lines[i].strip()

        size_match = SIZE_TYPE_RE.match(line)
        if not size_match:
            i += 1
            continue

        size = size_match.group(1)
        alt_size = size_match.group(2)
        creature_type = size_match.group(3).strip()
        alignment = size_match.group(4).strip()

        name_candidates = []
        for j in range(max(0, i - 20), i):
            candidate = lines[j].strip()
            if candidate and not candidate.startswith("System Reference"):
                if not re.match(r"^\d+$", candidate):
                    if not SIZE_TYPE_RE.match(candidate):
                        if len(candidate) < 80 and not candidate.startswith("CR "):
                            name_candidates.append(candidate)

        name = name_candidates[-1] if name_candidates else f"Unknown_{i}"

        junk_prefixes = [
            "Traits", "Actions", "Legendary", "Reactions", "Bonus",
            "MOD SAVE", "Str ", "Dex ", "Con ", "Int ", "Wis ", "Cha ",
            "Skills ", "Senses ", "Languages ", "AC ", "HP ", "Speed ",
            "Initiative", "damage", "feet", "attack", "spell",
            "At Will", "1/Day", "2/Day", "3/Day", "Recharge",
            "The ", "A ", "If ", "When ", "While ", "Each ",
        ]
        junk_substrings = [
            "Saving Throw", "Attack Roll", "Hit:", "reach",
            "damage", "condition", "within", "creature",
        ]

        filtered = []
        for c in name_candidates:
            if any(c.startswith(p) for p in junk_prefixes):
                continue
            if any(s in c for s in junk_substrings):
                continue
            if len(c) > 50:
                continue
            if re.match(r"^[A-Z][a-z]+(\s[A-Z][a-z]+)*(\s\([^)]+\))?$", c):
                filtered.append(c)

        name = filtered[-1] if filtered else (
            name_candidates[-1] if name_candidates else None
        )
        if name is None:
            i += 1
            continue
        if any(name.startswith(p) for p in junk_prefixes):
            i += 1
            continue
        if len(name) > 60:
            i += 1
            continue

        cr = None
        xp = None
        actions_text = ""

        next_monster = len(lines)
        for j in range(i + 3, min(i + 150, len(lines))):
            if SIZE_TYPE_RE.match(lines[j].strip()):
                next_monster = j
                break

        for j in range(i + 1, min(next_monster, len(lines))):
            l = lines[j].strip()
            cr_match = CR_RE.match(l)
            if cr_match:
                cr = cr_match.group(1)
                xp = cr_match.group(2).replace(",", "")
                break

        for j in range(i + 1, min(next_monster, len(lines))):
            actions_text += " " + lines[j].strip()

        equipment = extract_equipment_from_actions(actions_text)
        visual = extract_visual_descriptors(name, creature_type, size, actions_text)

        canvas = CREATURE_SIZE_MAP.get(size, "64x64")
        if alt_size:
            pass

        if cr is None and name in CR_CORRECTIONS:
            cr = CR_CORRECTIONS[name]

        if "." in name or len(name.split()) > 6 or name in NAME_BLACKLIST:
            i += 1
            continue

        if name in SIZE_CORRECTIONS:
            size = SIZE_CORRECTIONS[name]
            canvas = CREATURE_SIZE_MAP.get(size, canvas)

        entity = {
            "name": name,
            "type": "monster",
            "dnd_size": size,
            "canvas_profile": canvas,
            "creature_type": creature_type,
            "alignment": alignment,
            "cr": cr,
            "xp": int(xp) if xp and xp.isdigit() else None,
            "visual_descriptors": visual,
            "typical_equipment": equipment if equipment else None,
        }

        if name not in [e["name"] for e in entities]:
            entities.append(entity)

        i += 1

    return entities


def build_player_templates() -> list[dict]:
    templates = []
    for cls in PLAYER_CLASSES:
        templates.append({
            "name": cls,
            "type": "player",
            "dnd_size": "Medium",
            "canvas_profile": "64x64",
            "creature_type": "Humanoid",
            "alignment": "Any",
            "cr": None,
            "xp": None,
            "visual_descriptors": ["medium humanoid"],
            "typical_equipment": None,
            "available_species": SRD_SPECIES,
        })
    return templates


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract SRD entities into structured JSON."
    )
    parser.add_argument(
        "srd_path", type=Path, help="Path to SRD_raw.txt"
    )
    parser.add_argument(
        "--config", type=Path,
        help="Sprite profiles JSON (for creature_size_mapping)"
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        default=Path("reference/srd_entity_index.json"),
    )
    args = parser.parse_args()

    text = args.srd_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    monsters = parse_monsters(lines)
    players = build_player_templates()

    index = {
        "schema_version": 1,
        "srd_version": "5.2.1",
        "creature_size_mapping": CREATURE_SIZE_MAP,
        "entities": players + monsters,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")

    monster_count = len(monsters)
    player_count = len(players)
    sizes = {}
    for e in monsters:
        s = e["dnd_size"]
        sizes[s] = sizes.get(s, 0) + 1

    print(f"Extracted {monster_count} monsters + {player_count} player templates")
    print(f"Size breakdown: {sizes}")
    print(f"Written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
