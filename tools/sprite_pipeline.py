#!/usr/bin/env python3
"""
Sprite generation pipeline orchestrator.

Automates the full workflow:
  1. Generate prompt from asset spec
  2. Call OpenAI API to generate image (Codex agent)
  3. Normalize to Resurrect 64 palette
  4. Validate against profile rules
  5. Deploy passing sprites to assets/

Usage:
  # Generate idle frames for specific entities
  python3 tools/sprite_pipeline.py goblin_warrior skeleton troll

  # Generate all frames for an entity
  python3 tools/sprite_pipeline.py --all-frames adult_red_dragon

  # Process everything that doesn't have a passing sprite yet
  python3 tools/sprite_pipeline.py --all --skip-existing

  # Dry run — generate prompts only, no API calls
  python3 tools/sprite_pipeline.py --dry-run goblin_warrior
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    config_path: Path
    specs_dir: Path
    staging_raw_dir: Path
    staging_normalized_dir: Path
    assets_dir: Path
    default_frames: list[str]
    skip_existing: bool
    max_generation_attempts: int
    codex_model: str
    codex_quality: str
    codex_size: str
    codex_max_retries: int
    codex_retry_delay: float
    codex_api_base: str

    @classmethod
    def from_file(cls, path: Path) -> "PipelineConfig":
        raw = json.loads(path.read_text(encoding="utf-8"))
        p = raw["pipeline"]
        c = raw["codex"]
        return cls(
            config_path=Path(p["config_path"]),
            specs_dir=Path(p["specs_dir"]),
            staging_raw_dir=Path(p["staging_raw_dir"]),
            staging_normalized_dir=Path(p["staging_normalized_dir"]),
            assets_dir=Path(p["assets_dir"]),
            default_frames=p.get("default_frames", ["idle"]),
            skip_existing=p.get("skip_existing", True),
            max_generation_attempts=p.get("max_generation_attempts", 3),
            codex_model=c.get("model", "gpt-image-1"),
            codex_quality=c.get("quality", "medium"),
            codex_size=c.get("size", "1024x1024"),
            codex_max_retries=c.get("max_retries", 3),
            codex_retry_delay=c.get("retry_delay_seconds", 5.0),
            codex_api_base=c.get("api_base", "https://api.openai.com/v1"),
        )


@dataclass
class SpriteResult:
    entity_slug: str
    frame: str
    profile: str
    status: str  # "pass", "fail_generate", "fail_normalize", "fail_validate", "skipped"
    message: str = ""
    attempts: int = 0


def load_spec(specs_dir: Path, entity_slug: str) -> dict | None:
    path = specs_dir / f"{entity_slug}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sprite_exists_and_valid(
    assets_dir: Path, profile: str, filename: str, config_path: Path
) -> bool:
    sprite_path = assets_dir / profile / filename
    if not sprite_path.exists():
        return False
    result = subprocess.run(
        [
            sys.executable, "tools/validate_resurrect64_sprites.py",
            "--config", str(config_path),
            "--profile", profile,
            str(sprite_path),
        ],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def generate_prompt(spec_path: Path, config_path: Path, frame: str) -> str | None:
    result = subprocess.run(
        [
            sys.executable, "tools/generate_prompts.py",
            "--config", str(config_path),
            "--frame", frame,
            str(spec_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    lines = result.stdout.strip().split("\n")
    prompt_lines = []
    in_prompt = False
    for line in lines:
        if line.startswith("=") and not in_prompt:
            in_prompt = True
            continue
        if in_prompt:
            prompt_lines.append(line)
    return "\n".join(prompt_lines).strip() if prompt_lines else result.stdout.strip()


def run_codex_generate(
    prompt: str,
    output_path: Path,
    cfg: PipelineConfig,
) -> tuple[bool, str]:
    sys.path.insert(0, str(Path("tools").resolve()))
    from codex_generate import generate_image

    return generate_image(
        prompt,
        output_path,
        api_base=cfg.codex_api_base,
        model=cfg.codex_model,
        quality=cfg.codex_quality,
        size=cfg.codex_size,
        max_retries=cfg.codex_max_retries,
        retry_delay=cfg.codex_retry_delay,
    )


def run_normalize(
    raw_path: Path,
    output_path: Path,
    profile: str,
    config_path: Path,
) -> tuple[bool, list[str]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            sys.executable, "tools/normalize_resurrect64_sprite.py",
            "--config", str(config_path),
            "--profile", profile,
            str(raw_path),
            str(output_path),
        ],
        capture_output=True, text=True,
    )
    messages = [
        line.strip()
        for line in (result.stdout + result.stderr).strip().split("\n")
        if line.strip()
    ]
    return result.returncode == 0, messages


def run_validate(
    sprite_path: Path,
    profile: str,
    config_path: Path,
) -> tuple[bool, list[str]]:
    result = subprocess.run(
        [
            sys.executable, "tools/validate_resurrect64_sprites.py",
            "--config", str(config_path),
            "--profile", profile,
            str(sprite_path),
        ],
        capture_output=True, text=True,
    )
    messages = [
        line.strip()
        for line in (result.stdout + result.stderr).strip().split("\n")
        if line.strip()
    ]
    return result.returncode == 0, messages


def process_sprite(
    entity_slug: str,
    frame: str,
    cfg: PipelineConfig,
    dry_run: bool = False,
) -> SpriteResult:
    spec = load_spec(cfg.specs_dir, entity_slug)
    if spec is None:
        return SpriteResult(entity_slug, frame, "", "fail_generate",
                            f"no asset spec found: {cfg.specs_dir / f'{entity_slug}.json'}")

    profile = spec["canvas_profile"]
    filename = f"{entity_slug}_{frame}.png"

    if cfg.skip_existing and sprite_exists_and_valid(
        cfg.assets_dir, profile, filename, cfg.config_path
    ):
        return SpriteResult(entity_slug, frame, profile, "skipped",
                            "already exists and passes validation")

    spec_path = cfg.specs_dir / f"{entity_slug}.json"
    prompt = generate_prompt(spec_path, cfg.config_path, frame)
    if prompt is None:
        return SpriteResult(entity_slug, frame, profile, "fail_generate",
                            "prompt generation failed")

    if dry_run:
        prompt_out = cfg.staging_raw_dir / f"{entity_slug}_{frame}_prompt.txt"
        prompt_out.parent.mkdir(parents=True, exist_ok=True)
        prompt_out.write_text(prompt, encoding="utf-8")
        return SpriteResult(entity_slug, frame, profile, "skipped",
                            f"dry run — prompt saved to {prompt_out}")

    raw_path = cfg.staging_raw_dir / filename
    norm_path = cfg.staging_normalized_dir / filename
    final_path = cfg.assets_dir / profile / filename

    for attempt in range(1, cfg.max_generation_attempts + 1):
        print(f"\n  [{attempt}/{cfg.max_generation_attempts}] Generating {filename}...")

        ok, msg = run_codex_generate(prompt, raw_path, cfg)
        if not ok:
            print(f"    Codex: FAILED — {msg}")
            if attempt < cfg.max_generation_attempts:
                time.sleep(cfg.codex_retry_delay)
            continue
        print(f"    Codex: image generated")

        ok, messages = run_normalize(raw_path, norm_path, profile, cfg.config_path)
        for m in messages:
            print(f"    Normalize: {m}")
        if not ok:
            if attempt < cfg.max_generation_attempts:
                continue
            return SpriteResult(entity_slug, frame, profile, "fail_normalize",
                                "; ".join(messages), attempt)

        ok, messages = run_validate(norm_path, profile, cfg.config_path)
        for m in messages:
            print(f"    Validate: {m}")
        if ok:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(norm_path, final_path)
            print(f"    Deployed to {final_path}")
            return SpriteResult(entity_slug, frame, profile, "pass",
                                str(final_path), attempt)

        if attempt < cfg.max_generation_attempts:
            continue
        return SpriteResult(entity_slug, frame, profile, "fail_validate",
                            "; ".join(messages), attempt)

    return SpriteResult(entity_slug, frame, profile, "fail_generate",
                        "exhausted all attempts", cfg.max_generation_attempts)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Sprite generation pipeline orchestrator."
    )
    parser.add_argument(
        "entities", nargs="*",
        help="Entity slugs to process (e.g. goblin_warrior troll).",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Process all entities in the asset specs directory.",
    )
    parser.add_argument(
        "--all-frames", action="store_true",
        help="Generate all frames (idle, attack, death, etc.), not just idle.",
    )
    parser.add_argument(
        "--frames", nargs="+",
        help="Specific frames to generate (default: from config).",
    )
    parser.add_argument(
        "--skip-existing", action="store_true", default=None,
        help="Skip entities that already have passing sprites.",
    )
    parser.add_argument(
        "--no-skip-existing", action="store_true",
        help="Regenerate even if a passing sprite exists.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate prompts only, no API calls.",
    )
    parser.add_argument(
        "--pipeline-config", type=Path, default=Path("pipeline.config.json"),
        help="Path to pipeline configuration file.",
    )
    args = parser.parse_args()

    if not args.pipeline_config.exists():
        print(f"ERROR: config not found: {args.pipeline_config}")
        return 1

    cfg = PipelineConfig.from_file(args.pipeline_config)

    if args.skip_existing is not None:
        cfg.skip_existing = True
    if args.no_skip_existing:
        cfg.skip_existing = False

    if args.all:
        entities = sorted(
            p.stem for p in cfg.specs_dir.iterdir()
            if p.suffix == ".json"
        )
    elif args.entities:
        entities = args.entities
    else:
        parser.error("provide entity slugs or --all")
        return 1

    results: list[SpriteResult] = []

    for entity_slug in entities:
        spec = load_spec(cfg.specs_dir, entity_slug)
        if spec is None:
            print(f"\n{'='*60}")
            print(f"SKIP {entity_slug}: no asset spec found")
            results.append(SpriteResult(entity_slug, "", "", "fail_generate",
                                        "no asset spec"))
            continue

        if args.all_frames:
            frames = [f["frame"] for f in spec.get("frames", [])]
        elif args.frames:
            frames = args.frames
        else:
            frames = cfg.default_frames

        for frame in frames:
            print(f"\n{'='*60}")
            print(f"PROCESSING: {entity_slug} / {frame} ({spec['canvas_profile']})")
            print(f"{'='*60}")

            result = process_sprite(entity_slug, frame, cfg, dry_run=args.dry_run)
            results.append(result)

            status_icon = {
                "pass": "PASS",
                "skipped": "SKIP",
                "fail_generate": "FAIL(gen)",
                "fail_normalize": "FAIL(norm)",
                "fail_validate": "FAIL(val)",
            }.get(result.status, "???")
            print(f"  Result: {status_icon} — {result.message}")

    print(f"\n{'='*60}")
    print("PIPELINE SUMMARY")
    print(f"{'='*60}")

    passed = [r for r in results if r.status == "pass"]
    skipped = [r for r in results if r.status == "skipped"]
    failed = [r for r in results if r.status.startswith("fail")]

    print(f"  Passed:  {len(passed)}")
    print(f"  Skipped: {len(skipped)}")
    print(f"  Failed:  {len(failed)}")

    if passed:
        print(f"\n  Deployed sprites:")
        for r in passed:
            print(f"    {r.entity_slug}_{r.frame}.png -> {r.message} (attempt {r.attempts})")

    if failed:
        print(f"\n  Failures:")
        for r in failed:
            print(f"    {r.entity_slug}_{r.frame}: {r.status} — {r.message}")

    return 1 if failed and not passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
