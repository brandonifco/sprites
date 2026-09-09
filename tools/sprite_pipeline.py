#!/usr/bin/env python3
"""
Sprite generation pipeline orchestrator.

Automates the full workflow:
  1. Generate prompt from asset spec
  2. Invoke Codex CLI to generate image (uses ChatGPT Pro subscription)
  3. Normalize to Resurrect 64 palette
  4. Validate against profile rules
  5. Deploy passing sprites to assets/

Codex uses whatever model is in ~/.codex/config.toml (Luna medium by default).
No API key needed — authenticates via ChatGPT session.

Supports batch mode: generates 2 sprites per Codex session to halve rate
limit consumption. Retries fall back to single generation.

Usage:
  python3 tools/sprite_pipeline.py goblin_warrior skeleton troll
  python3 tools/sprite_pipeline.py --all --skip-existing
  python3 tools/sprite_pipeline.py --all-frames adult_red_dragon
  python3 tools/sprite_pipeline.py --dry-run goblin_warrior
  python3 tools/sprite_pipeline.py --no-batch goblin_warrior skeleton
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROFILES_PATH = Path("art/sprite-palettes/resurrect64_sprite_profiles.json")
SPECS_DIR = Path("art/asset-specs")
STAGING_RAW = Path("staging/raw")
STAGING_NORM = Path("staging/normalized")
ASSETS_DIR = Path("assets/sprites")

BATCH_SIZE = 2


@dataclass
class Result:
    entity: str
    frame: str
    profile: str
    status: str
    message: str = ""
    attempts: int = 0


def load_spec(slug: str) -> dict | None:
    path = SPECS_DIR / f"{slug}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def is_valid(sprite_path: Path, profile: str) -> bool:
    if not sprite_path.exists():
        return False
    r = subprocess.run(
        [sys.executable, "tools/validate_resurrect64_sprites.py",
         "--config", str(PROFILES_PATH), "--profile", profile, str(sprite_path)],
        capture_output=True,
    )
    return r.returncode == 0


def generate_prompt(spec_path: Path, frame: str) -> str | None:
    r = subprocess.run(
        [sys.executable, "tools/generate_prompts.py",
         "--config", str(PROFILES_PATH), "--frame", frame, str(spec_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None
    lines = r.stdout.strip().split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith("Create a ")), 0)
    return "\n".join(lines[start:]).strip()


def codex_generate(prompt: str, output: Path) -> tuple[bool, str]:
    sys.path.insert(0, str(Path("tools").resolve()))
    from codex_generate import generate_image
    return generate_image(prompt, output)


def codex_generate_batch(items: list[tuple[str, Path]]) -> list[tuple[bool, str]]:
    sys.path.insert(0, str(Path("tools").resolve()))
    from codex_generate import generate_images_batch
    return generate_images_batch(items, timeout=300)


def normalize(raw: Path, out: Path, profile: str) -> tuple[bool, list[str]]:
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [sys.executable, "tools/normalize_resurrect64_sprite.py",
         "--config", str(PROFILES_PATH), "--profile", profile,
         str(raw), str(out)],
        capture_output=True, text=True,
    )
    msgs = [l.strip() for l in (r.stdout + r.stderr).split("\n") if l.strip()]
    return r.returncode == 0, msgs


def validate(sprite: Path, profile: str) -> tuple[bool, list[str]]:
    r = subprocess.run(
        [sys.executable, "tools/validate_resurrect64_sprites.py",
         "--config", str(PROFILES_PATH), "--profile", profile, str(sprite)],
        capture_output=True, text=True,
    )
    msgs = [l.strip() for l in (r.stdout + r.stderr).split("\n") if l.strip()]
    return r.returncode == 0, msgs


def normalize_and_validate(slug, frame, profile, raw, norm):
    """Normalize a raw image and validate it. Returns (passed, Result_or_None)."""
    ok, msgs = normalize(raw, norm, profile)
    for m in msgs:
        print(f"    {m}")
    if not ok:
        return False, None

    ok, msgs = validate(norm, profile)
    for m in msgs:
        print(f"    {m}")
    if ok:
        final = ASSETS_DIR / profile / f"{slug}_{frame}.png"
        final.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(norm, final)
        print(f"    Deployed: {final}")
        return True, Result(slug, frame, profile, "pass", str(final), 1)
    return False, None


def process_single(slug: str, frame: str, max_attempts: int = 3,
                   skip_existing: bool = True, dry_run: bool = False) -> Result:
    """Process a single entity with single-sprite Codex calls (used for retries)."""
    spec = load_spec(slug)
    if not spec:
        return Result(slug, frame, "", "fail", f"no spec: {SPECS_DIR / f'{slug}.json'}")

    profile = spec["canvas_profile"]
    filename = f"{slug}_{frame}.png"
    final = ASSETS_DIR / profile / filename

    if skip_existing and is_valid(final, profile):
        return Result(slug, frame, profile, "skip", "already valid")

    prompt = generate_prompt(SPECS_DIR / f"{slug}.json", frame)
    if not prompt:
        return Result(slug, frame, profile, "fail", "prompt generation failed")

    if dry_run:
        out = STAGING_RAW / f"{slug}_{frame}_prompt.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prompt, encoding="utf-8")
        return Result(slug, frame, profile, "skip", f"dry run — {out}")

    raw = STAGING_RAW / filename
    norm = STAGING_NORM / filename

    for attempt in range(1, max_attempts + 1):
        tag = f"[{attempt}/{max_attempts}]"
        print(f"\n  {tag} Codex generating {filename}...")

        ok, msg = codex_generate(prompt, raw)
        if not ok:
            print(f"    FAILED: {msg}")
            continue
        print(f"    Image saved")

        passed, result = normalize_and_validate(slug, frame, profile, raw, norm)
        if passed:
            return result

    return Result(slug, frame, profile, "fail", "exhausted attempts", max_attempts)


def process_batch(jobs: list[tuple[str, str, dict]], skip_existing: bool = True,
                  max_attempts: int = 3, dry_run: bool = False) -> list[Result]:
    """Process a batch of (slug, frame, spec) with batched Codex calls.

    First attempt uses batch generation (2 per Codex session).
    Failed sprites retry individually.
    """
    results = []
    pending = []

    for slug, frame, spec in jobs:
        profile = spec["canvas_profile"]
        filename = f"{slug}_{frame}.png"
        final = ASSETS_DIR / profile / filename

        if skip_existing and is_valid(final, profile):
            results.append(Result(slug, frame, profile, "skip", "already valid"))
            print(f"  -> SKIP: already valid")
            continue

        prompt = generate_prompt(SPECS_DIR / f"{slug}.json", frame)
        if not prompt:
            results.append(Result(slug, frame, profile, "fail", "prompt generation failed"))
            print(f"  -> FAIL: prompt generation failed")
            continue

        if dry_run:
            out = STAGING_RAW / f"{slug}_{frame}_prompt.txt"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(prompt, encoding="utf-8")
            results.append(Result(slug, frame, profile, "skip", f"dry run — {out}"))
            continue

        pending.append((slug, frame, profile, prompt))

    # Batch generate in pairs
    i = 0
    while i < len(pending):
        chunk = pending[i:i + BATCH_SIZE]
        items = [(p[3], STAGING_RAW / f"{p[0]}_{p[1]}.png") for p in chunk]

        names = ", ".join(f"{p[0]}_{p[1]}.png" for p in chunk)
        print(f"\n  [batch] Codex generating {names}...")

        gen_results = codex_generate_batch(items)

        for j, (slug, frame, profile, prompt) in enumerate(chunk):
            ok, msg = gen_results[j]
            filename = f"{slug}_{frame}.png"
            raw = STAGING_RAW / filename
            norm = STAGING_NORM / filename

            if not ok:
                print(f"    {filename}: FAILED — {msg}")
                # Retry individually
                print(f"    Retrying {filename} individually...")
                r = process_single(slug, frame, max_attempts - 1, False, False)
                results.append(r)
                continue

            print(f"    {filename}: Image saved")
            passed, result = normalize_and_validate(slug, frame, profile, raw, norm)
            if passed:
                results.append(result)
            else:
                # Retry individually
                print(f"    Retrying {filename} individually...")
                r = process_single(slug, frame, max_attempts - 1, False, False)
                results.append(r)

        i += BATCH_SIZE

    return results


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Sprite generation pipeline.")
    parser.add_argument("entities", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--all-frames", action="store_true")
    parser.add_argument("--frames", nargs="+")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-skip", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--no-batch", action="store_true",
                        help="Disable batch generation (1 sprite per Codex call)")
    args = parser.parse_args()

    if args.all:
        entities = sorted(p.stem for p in SPECS_DIR.iterdir() if p.suffix == ".json")
    elif args.entities:
        entities = args.entities
    else:
        parser.error("provide entity slugs or --all")
        return 1

    skip = not args.no_skip

    # Build job list
    all_jobs = []
    for slug in entities:
        spec = load_spec(slug)
        if not spec:
            print(f"\nSKIP {slug}: no spec")
            continue

        if args.all_frames:
            frames = [f["frame"] for f in spec.get("frames", [])]
        elif args.frames:
            frames = args.frames
        else:
            frames = ["idle"]

        for frame in frames:
            print(f"\n{'='*50}")
            print(f"{slug} / {frame} ({spec['canvas_profile']})")
            print(f"{'='*50}")
            all_jobs.append((slug, frame, spec))

    if args.no_batch:
        results = []
        for slug, frame, spec in all_jobs:
            r = process_single(slug, frame, args.max_attempts, skip, args.dry_run)
            results.append(r)
            print(f"  -> {r.status.upper()}: {r.message}")
    else:
        results = process_batch(all_jobs, skip, args.max_attempts, args.dry_run)

    passed = [r for r in results if r.status == "pass"]
    skipped = [r for r in results if r.status == "skip"]
    failed = [r for r in results if r.status == "fail"]

    print(f"\n{'='*50}")
    print(f"DONE: {len(passed)} pass, {len(skipped)} skip, {len(failed)} fail")
    if failed:
        for r in failed:
            print(f"  FAIL: {r.entity}_{r.frame} — {r.message}")

    return 1 if failed and not passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
