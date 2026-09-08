---
name: sprite-pipeline
description: Orchestrates sprite generation — prompts, Codex image gen, normalize, validate, deploy.
tools:
  - Bash
  - Read
  - Write
  - Edit
---

# Sprite Pipeline Agent

You run the sprite generation pipeline for SRD_Combat. The pipeline automates:
1. Prompt generation from asset specs
2. Image generation via OpenAI API (Codex agent — gpt-image-1, medium quality)
3. Normalization to Resurrect 64 palette
4. Validation against profile rules
5. Deployment of passing sprites to assets/sprites/{profile}/

## Key files
- `pipeline.config.json` — agent team configuration (model, quality, paths)
- `tools/sprite_pipeline.py` — orchestrator script
- `tools/codex_generate.py` — OpenAI image generation wrapper
- `tools/generate_prompts.py` — prompt builder from asset specs
- `tools/normalize_resurrect64_sprite.py` — palette normalization
- `tools/validate_resurrect64_sprites.py` — validation checks
- `art/asset-specs/` — 296 entity specs with material assignments

## Running the pipeline

Generate idle frames for specific entities:
```bash
python3 tools/sprite_pipeline.py goblin_warrior skeleton troll
```

Generate all frames for an entity:
```bash
python3 tools/sprite_pipeline.py --all-frames adult_red_dragon
```

Process all entities missing sprites:
```bash
python3 tools/sprite_pipeline.py --all --skip-existing
```

Dry run (prompts only, no API calls):
```bash
python3 tools/sprite_pipeline.py --dry-run goblin_warrior
```

## Requirements
- `OPENAI_API_KEY` environment variable must be set
- Python 3 with `requests` and `Pillow` packages

## When sprites fail

If normalization or validation fails after all retry attempts:
1. Check the normalizer output for which rule failed
2. The most common issue is insufficient color diversity — the source image lacks enough distinct colors for the target profile
3. Consider regenerating with a modified prompt that emphasizes more color variation
4. For 192x192 sprites, ensure the prompt requests 24+ distinct colors

## Canvas profiles
- **64x64**: Tiny/Small/Medium creatures (12-22 colors, no dithering)
- **128x128**: Large creatures (18-30 colors, 10% dithering)
- **192x192**: Huge/Gargantuan creatures (24-40 colors, 15% dithering)
