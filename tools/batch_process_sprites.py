#!/usr/bin/env python3
"""
Batch-process AI-generated images into validated sprite candidates.

Reads raw images from an input directory, runs each through the
normalizer, then validates the result. Produces a summary report.

Expected input naming: {entity_slug}_{frame}.{ext}
  e.g. goblin_warrior_idle.png, skeleton_attack.webp

Accepts PNG, JPEG, WebP — any format Pillow can open.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def find_images(input_dir: Path) -> list[Path]:
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
    images = []
    for p in sorted(input_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in exts:
            images.append(p)
    return images


def infer_profile(slug: str, specs_dir: Path) -> str | None:
    spec_path = None
    parts = slug.rsplit("_", 1)
    if len(parts) == 2:
        entity_slug = parts[0]
        spec_path = specs_dir / f"{entity_slug}.json"

    if spec_path and spec_path.exists():
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        return spec.get("canvas_profile")
    return None


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch-process AI-generated images into validated sprites."
    )
    parser.add_argument(
        "input_dir", type=Path,
        help="Directory containing raw AI-generated images.",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path,
        default=Path("assets/sprites"),
        help="Base output directory for processed sprites.",
    )
    parser.add_argument(
        "--specs-dir", type=Path,
        default=Path("art/asset-specs"),
        help="Asset specs directory (for profile inference).",
    )
    parser.add_argument(
        "--config", type=Path,
        default=Path("art/sprite-palettes/resurrect64_sprite_profiles.json"),
    )
    parser.add_argument(
        "--profile", choices=["64x64", "128x128", "192x192"],
        help="Force a specific profile (overrides auto-detection).",
    )
    parser.add_argument(
        "--keep-rejects", action="store_true",
        help="Keep images that fail validation in a rejects/ subdirectory.",
    )
    args = parser.parse_args()

    images = find_images(args.input_dir)
    if not images:
        print(f"No images found in {args.input_dir}", file=sys.stderr)
        return 1

    print(f"Found {len(images)} image(s) to process\n")

    normalizer = Path("tools/normalize_resurrect64_sprite.py")
    validator = Path("tools/validate_resurrect64_sprites.py")

    if not normalizer.exists() or not validator.exists():
        print("ERROR: normalizer or validator script not found", file=sys.stderr)
        return 1

    results = {"passed": [], "failed": [], "error": []}
    reject_dir = args.input_dir / "rejects"

    for img_path in images:
        stem = img_path.stem
        print(f"--- {stem} ---")

        profile = args.profile or infer_profile(stem, args.specs_dir)
        if profile is None:
            print(f"  SKIP: cannot determine profile for '{stem}'")
            print(f"        Name should be {{entity_slug}}_{{frame}}.ext")
            results["error"].append(stem)
            continue

        tier_dir = args.output_dir / profile
        tier_dir.mkdir(parents=True, exist_ok=True)
        out_path = tier_dir / f"{stem}.png"

        norm_cmd = [
            sys.executable, str(normalizer),
            str(img_path), str(out_path),
            "--config", str(args.config),
            "--profile", profile,
        ]
        print(f"  Normalizing ({profile})...")
        result = subprocess.run(
            norm_cmd, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  NORMALIZE FAILED:")
            for line in result.stderr.strip().split("\n"):
                print(f"    {line}")
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    print(f"    {line}")
            results["error"].append(stem)
            continue

        for line in result.stdout.strip().split("\n"):
            if line.strip():
                print(f"    {line}")

        val_cmd = [
            sys.executable, str(validator),
            "--config", str(args.config),
            "--profile", profile,
            str(out_path),
        ]
        print(f"  Validating...")
        result = subprocess.run(
            val_cmd, capture_output=True, text=True
        )

        stdout = result.stdout.strip()
        if "PASS" in stdout and result.returncode == 0:
            print(f"  PASS")
            results["passed"].append(stem)
        else:
            print(f"  FAIL:")
            for line in stdout.split("\n"):
                print(f"    {line}")
            results["failed"].append(stem)
            if args.keep_rejects:
                reject_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(out_path), str(reject_dir / f"{stem}.png"))
                print(f"  Moved to rejects/")

    print(f"\n{'='*40}")
    print(f"RESULTS")
    print(f"  Passed:  {len(results['passed'])}")
    print(f"  Failed:  {len(results['failed'])}")
    print(f"  Errors:  {len(results['error'])}")

    if results["passed"]:
        print(f"\nPassed sprites in: {args.output_dir}/")
    if results["failed"]:
        print(f"\nFailed (need touch-up):")
        for s in results["failed"]:
            print(f"  {s}")
    if results["error"]:
        print(f"\nCould not process:")
        for s in results["error"]:
            print(f"  {s}")

    return 0 if not results["failed"] and not results["error"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
