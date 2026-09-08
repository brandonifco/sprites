# Sprite File Naming Convention

## Pattern

```
assets/sprites/{profile}/{entity_slug}_{frame}.png
```

All PNGs live directly under the size-tier directory. No subdirectories within a tier.

## Entity Slug

Lowercase, underscores only, derived from the entity's canonical name.

### Monsters

Use the full SRD stat-block name. Each variant is its own entity.

| SRD Name | Slug |
|---|---|
| Goblin Warrior | `goblin_warrior` |
| Goblin Boss | `goblin_boss` |
| Adult Red Dragon | `adult_red_dragon` |
| Animated Flying Sword | `animated_flying_sword` |
| Troll Limb | `troll_limb` |

### Player Characters

Pattern: `{class}_{species}_{variant}`

- **class**: SRD class name (e.g., `fighter`, `cleric`, `rogue`)
- **species**: SRD species name (e.g., `human`, `elf`, `dwarf`, `dragonborn`)
- **variant**: short tag for visual differentiation (e.g., `f`, `m`, `a`, `b` or descriptive like `dark`, `light`)

| Description | Slug |
|---|---|
| Female human fighter | `fighter_human_f` |
| Male dwarf cleric | `cleric_dwarf_m` |
| Elf rogue variant A | `rogue_elf_a` |

## Frame Suffix

From the entity's `frame_sets` definition in the profile JSON:

| Entity Type | Mandatory Frames | Optional |
|---|---|---|
| Monster | `idle`, `attack`, `death` | — |
| Player | `idle`, `attack`, `hit`, `death`, `cast` | — |

## Complete Examples

```
assets/sprites/64x64/goblin_warrior_idle.png
assets/sprites/64x64/goblin_warrior_attack.png
assets/sprites/64x64/goblin_warrior_death.png
assets/sprites/64x64/fighter_human_f_idle.png
assets/sprites/64x64/fighter_human_f_attack.png
assets/sprites/64x64/fighter_human_f_hit.png
assets/sprites/64x64/fighter_human_f_death.png
assets/sprites/64x64/fighter_human_f_cast.png
assets/sprites/128x128/adult_red_dragon_idle.png
assets/sprites/192x192/ancient_gold_dragon_attack.png
```

## Slug Rules

1. Only lowercase ASCII letters, digits, and underscores.
2. No leading or trailing underscores.
3. No consecutive underscores.
4. The slug MUST be stable across all frames of the same entity.
5. The frame suffix MUST be the final `_`-delimited segment before `.png`.

## Multi-Frame Consistency

The validator groups files by entity slug (everything before the last `_` segment). All files sharing a slug are treated as the same entity and are subject to Global Rules 12–13 (same RGB assignments for same materials across frames).
