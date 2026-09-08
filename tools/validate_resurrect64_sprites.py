#!/usr/bin/env python3
from __future__ import annotations

import argparse
import colorsys
import json
import sys
from collections import deque
from pathlib import Path

from PIL import Image


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_luminance(r: int, g: int, b: int) -> float:
    return 0.2126 * (r / 255.0) + 0.7152 * (g / 255.0) + 0.0722 * (b / 255.0)


def infer_profile(path: Path, profiles: dict) -> str | None:
    parts = {p.lower() for p in path.parts}
    matches = [name for name in profiles if name.lower() in parts]
    if len(matches) == 1:
        return matches[0]
    return None


def connected_cluster_max(coords: set[tuple[int, int]]) -> int:
    remaining = set(coords)
    best = 0
    while remaining:
        start = remaining.pop()
        q = deque([start])
        size = 1
        while q:
            x, y = q.popleft()
            for n in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if n in remaining:
                    remaining.remove(n)
                    q.append(n)
                    size += 1
        best = max(best, size)
    return best


def count_value_levels(
    opaque_rgb: set[tuple[int, int, int]], num_buckets: int = 8
) -> int:
    if not opaque_rgb:
        return 0
    occupied = set()
    for r, g, b in opaque_rgb:
        lum = rgb_to_luminance(r, g, b)
        bucket = min(int(lum * num_buckets), num_buckets - 1)
        occupied.add(bucket)
    return len(occupied)


def estimate_dither_fraction(
    img: Image.Image, opaque_coords: set[tuple[int, int]]
) -> float:
    if not opaque_coords:
        return 0.0
    px = img.load()
    w, h = img.size
    checker_count = 0
    for x, y in opaque_coords:
        r, g, b, _ = px[x, y]
        neighbors_differ = 0
        neighbor_count = 0
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) in opaque_coords:
                nr, ng, nb, _ = px[nx, ny]
                neighbor_count += 1
                if (nr, ng, nb) != (r, g, b):
                    neighbors_differ += 1
        if neighbor_count >= 2 and neighbors_differ == neighbor_count:
            checker_count += 1
    return checker_count / len(opaque_coords)


def validate_palette_coverage(cfg: dict) -> list[str]:
    errors: list[str] = []
    if not cfg.get("ci", {}).get("invariants", {}).get(
        "every_palette_color_in_at_least_one_family", False
    ):
        return errors
    palette_ids = {c["id"] for c in cfg["palette"]["colors"]}
    used = set()
    for ids in cfg["ramp_families"].values():
        used.update(ids)
    orphans = sorted(palette_ids - used, key=lambda x: int(x.split("-")[1]))
    if orphans:
        errors.append(
            f"palette coverage invariant violated: {', '.join(orphans)} "
            f"not in any ramp family"
        )
    return errors


def validate_png(path: Path, profile_name: str, cfg: dict) -> list[str]:
    errors: list[str] = []
    profile = cfg["profiles"][profile_name]
    allowed = {hex_to_rgb(c["hex"]) for c in cfg["palette"]["colors"]}
    white = hex_to_rgb(
        next(c["hex"] for c in cfg["palette"]["colors"] if c["id"] == "R64-09")
    )
    allowed_alpha = set(cfg["palette"]["allowed_alpha_values"])

    try:
        img = Image.open(path).convert("RGBA")
    except Exception as e:
        return [f"cannot open PNG: {e}"]

    if img.size != (profile["width"], profile["height"]):
        errors.append(
            f"dimensions {img.size[0]}x{img.size[1]} "
            f"!= {profile['width']}x{profile['height']}"
        )

    opaque_rgb: set[tuple[int, int, int]] = set()
    opaque_coords: set[tuple[int, int]] = set()
    white_coords: set[tuple[int, int]] = set()
    bad_alpha = 0
    bad_palette = set()

    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a not in allowed_alpha:
                bad_alpha += 1
            if a == 255:
                rgb = (r, g, b)
                opaque_rgb.add(rgb)
                opaque_coords.add((x, y))
                if rgb not in allowed:
                    bad_palette.add(rgb)
                if rgb == white:
                    white_coords.add((x, y))

    if bad_alpha:
        errors.append(f"{bad_alpha} pixel(s) have non-binary alpha")
    if bad_palette:
        vals = ", ".join(
            f"#{r:02x}{g:02x}{b:02x}" for r, g, b in sorted(bad_palette)
        )
        errors.append(f"opaque colors outside Resurrect 64: {vals}")

    color_rule = profile["unique_opaque_colors"]
    ncolors = len(opaque_rgb)
    if not (color_rule["min"] <= ncolors <= color_rule["max"]):
        errors.append(
            f"{ncolors} unique opaque colors outside allowed range "
            f"{color_rule['min']}..{color_rule['max']}"
        )

    if not opaque_coords:
        errors.append("sprite contains no opaque pixels")
        return errors

    xs = [x for x, _ in opaque_coords]
    ys = [y for _, y in opaque_coords]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    bbox_h = maxy - miny + 1
    bbox_rule = profile["occupied_bbox_height_px"]
    if not (bbox_rule["min"] <= bbox_h <= bbox_rule["max"]):
        errors.append(
            f"occupied bounding-box height {bbox_h}px outside allowed range "
            f"{bbox_rule['min']}..{bbox_rule['max']}px"
        )

    if not profile.get("opaque_edge_contact_allowed", False):
        touching = [
            (x, y)
            for x, y in opaque_coords
            if x in (0, img.width - 1) or y in (0, img.height - 1)
        ]
        if touching:
            errors.append(f"{len(touching)} opaque pixel(s) touch canvas edge")

    white_count = len(white_coords)
    white_max = profile["r64_09_white_pixels_max"]
    if white_count > white_max:
        errors.append(
            f"R64-09 white usage {white_count} exceeds maximum {white_max}"
        )

    if white_coords:
        cluster = connected_cluster_max(white_coords)
        cluster_max = profile["largest_white_connected_cluster_max"]
        if cluster > cluster_max:
            errors.append(
                f"largest connected R64-09 cluster is {cluster} pixels; "
                f"maximum is {cluster_max}"
            )

    min_levels = profile.get("minimum_distinct_palette_value_levels", 0)
    if min_levels > 0:
        actual_levels = count_value_levels(opaque_rgb)
        if actual_levels < min_levels:
            errors.append(
                f"only {actual_levels} distinct value levels; "
                f"minimum is {min_levels}"
            )

    dither_cfg = profile.get("dithering", {})
    max_frac = dither_cfg.get("max_opaque_fraction", 1.0)
    if max_frac < 1.0:
        actual_frac = estimate_dither_fraction(img, opaque_coords)
        if actual_frac > max_frac:
            errors.append(
                f"estimated dithering fraction {actual_frac:.1%} exceeds "
                f"maximum {max_frac:.0%}"
            )
    if not dither_cfg.get("allowed", True):
        actual_frac = estimate_dither_fraction(img, opaque_coords)
        if actual_frac > 0.005:
            errors.append(
                f"dithering detected ({actual_frac:.1%}) but prohibited "
                f"for this profile"
            )

    return errors


def collect_pngs(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.png") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Resurrect 64 sprite PNGs."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--profile", choices=["64x64", "128x128", "192x192"])
    parser.add_argument("--check-invariants", action="store_true")
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args()

    cfg = load_config(args.config)
    profiles = cfg["profiles"]

    if args.check_invariants:
        inv_errors = validate_palette_coverage(cfg)
        if inv_errors:
            for e in inv_errors:
                fail(e)
            return 1
        print("PASS palette coverage invariant")

    files = list(args.files)
    if args.root:
        files.extend(collect_pngs(args.root))
    files = sorted(set(files))

    if not files and not args.check_invariants:
        fail("no PNG files found")
        return 2

    if not files:
        return 0

    failures = 0
    checked = 0

    for path in files:
        if path.suffix.lower() != ".png":
            continue

        profile = args.profile or infer_profile(path, profiles)
        if profile is None:
            fail(
                f"{path}: cannot infer profile; "
                f"place file under 64x64/128x128/192x192 or pass --profile"
            )
            failures += 1
            continue

        checked += 1
        errors = validate_png(path, profile, cfg)
        if errors:
            failures += 1
            print(f"FAIL {path} [{profile}]")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"PASS {path} [{profile}]")

    if checked == 0 and not args.check_invariants:
        fail("no PNG files checked")
        return 2

    print(
        f"\nChecked: {checked}  Failed: {failures}  "
        f"Passed: {checked - failures}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
