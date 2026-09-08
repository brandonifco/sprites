---
name: sprite-pipeline
description: Generates game sprites by orchestrating Codex (image gen) + normalizer + validator. No manual steps.
tools:
  - Bash
  - Read
  - Write
  - Edit
---

# Sprite Pipeline Agent

You automate sprite generation for SRD_Combat by coordinating two AI agents:
- **You** (Claude Code): prompt generation, normalization, validation, deployment
- **Codex** (OpenAI CLI): image generation using the user's ChatGPT Pro subscription

## Pipeline for each sprite

1. **Generate prompt** from asset spec:
   ```bash
   python3 tools/generate_prompts.py --config art/sprite-palettes/resurrect64_sprite_profiles.json --frame idle art/asset-specs/{entity_slug}.json
   ```

2. **Invoke Codex** to generate the image:
   ```bash
   npx @openai/codex exec -s workspace-write --ephemeral --skip-git-repo-check -C /path/to/sprites \
     "Generate a sprite image matching this description and save it as staging/raw/{entity_slug}_{frame}.png. Do NOT resize. Here is the prompt:

   {prompt_text}"
   ```
   Codex uses its built-in image_gen tool — no API key, no extra cost beyond ChatGPT Pro.

3. **Normalize** to Resurrect 64 palette:
   ```bash
   python3 tools/normalize_resurrect64_sprite.py --config art/sprite-palettes/resurrect64_sprite_profiles.json --profile {profile} staging/raw/{filename} staging/normalized/{filename}
   ```

4. **Validate**:
   ```bash
   python3 tools/validate_resurrect64_sprites.py --config art/sprite-palettes/resurrect64_sprite_profiles.json --profile {profile} staging/normalized/{filename}
   ```

5. **Deploy** passing sprites:
   ```bash
   cp staging/normalized/{filename} assets/sprites/{profile}/{filename}
   ```

If normalization or validation fails, regenerate (up to 3 attempts).

## Batch mode

Run the pipeline script for multiple entities at once:
```bash
python3 tools/sprite_pipeline.py goblin_warrior skeleton troll
python3 tools/sprite_pipeline.py --all --skip-existing
python3 tools/sprite_pipeline.py --all-frames adult_red_dragon
```

## Key paths
- `art/asset-specs/` — 296 entity specs with material assignments
- `art/sprite-palettes/resurrect64_sprite_profiles.json` — palette + profile rules
- `staging/raw/` — raw Codex output (gitignored)
- `staging/normalized/` — post-normalization candidates (gitignored)
- `assets/sprites/{64x64,128x128,192x192}/` — validated final sprites

## Canvas profiles
- **64x64**: Tiny/Small/Medium (12-22 colors, no dithering)
- **128x128**: Large (18-30 colors, 10% dithering max)
- **192x192**: Huge/Gargantuan (24-40 colors, 15% dithering max)

## Codex config
Already configured in ~/.codex/config.toml:
- Model: gpt-5.6-luna
- Reasoning effort: medium
- Auth: ChatGPT Pro session tokens (no API key)
