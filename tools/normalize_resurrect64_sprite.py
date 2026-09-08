#!/usr/bin/env python3
"""
Resurrect 64 Sprite Normalization Pipeline

Converts an AI-generated intermediate image into a spec-compliant candidate.

Pipeline stages:
  1. Resize to target canvas (nearest-neighbor only)
  2. Binary alpha normalization (threshold to 0 or 255)
  3. Exact Resurrect 64 palette quantization (nearest RGB)
  4. Anti-alias / soft-edge removal (eliminate semi-transparent fringes)
  5. Cluster cleanup (remove isolated single-pixel noise)
  6. Color count enforcement (reduce to profile limits if needed)
  7. Validation pass (reject if automated correction cannot produce a
     compliant asset)

Output is a CANDIDATE, not a master. Only after external validation
succeeds does an asset become an accepted master.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, deque
from pathlib import Path

from PIL import Image


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def color_distance_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def build_palette_lut(
    palette_rgb: list[tuple[int, int, int]],
) -> dict[tuple[int, int, int], tuple[int, int, int]]:
    lut: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for rgb in palette_rgb:
        lut[rgb] = rgb
    return lut


def nearest_palette_color(
    rgb: tuple[int, int, int],
    palette_rgb: list[tuple[int, int, int]],
    lut: dict[tuple[int, int, int], tuple[int, int, int]],
) -> tuple[int, int, int]:
    if rgb in lut:
        return lut[rgb]
    best = palette_rgb[0]
    best_dist = color_distance_sq(rgb, best)
    for c in palette_rgb[1:]:
        d = color_distance_sq(rgb, c)
        if d < best_dist:
            best_dist = d
            best = c
    lut[rgb] = best
    return best


def flood_fill_label(
    opaque: dict[tuple[int, int], tuple[int, int, int]],
) -> dict[tuple[int, int], int]:
    labels: dict[tuple[int, int], int] = {}
    label_id = 0
    remaining = set(opaque.keys())
    while remaining:
        start = remaining.pop()
        label_id += 1
        labels[start] = label_id
        q = deque([start])
        color = opaque[start]
        while q:
            x, y = q.popleft()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if (nx, ny) in remaining and opaque[(nx, ny)] == color:
                    remaining.discard((nx, ny))
                    labels[(nx, ny)] = label_id
                    q.append((nx, ny))
    return labels


def cluster_sizes(
    labels: dict[tuple[int, int], int],
) -> dict[int, int]:
    sizes: Counter[int] = Counter()
    for lid in labels.values():
        sizes[lid] += 1
    return dict(sizes)


def get_neighbor_colors(
    x: int,
    y: int,
    opaque: dict[tuple[int, int], tuple[int, int, int]],
) -> list[tuple[int, int, int]]:
    colors = []
    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if (nx, ny) in opaque:
            colors.append(opaque[(nx, ny)])
    return colors


def normalize_sprite(
    input_path: Path,
    output_path: Path,
    profile_name: str,
    cfg: dict,
    alpha_threshold: int = 128,
    min_cluster_size: int = 2,
    max_color_reduce_passes: int = 10,
) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    profile = cfg["profiles"][profile_name]
    target_w = profile["width"]
    target_h = profile["height"]

    palette_rgb = [hex_to_rgb(c["hex"]) for c in cfg["palette"]["colors"]]
    white_rgb = hex_to_rgb(
        next(c["hex"] for c in cfg["palette"]["colors"] if c["id"] == "R64-09")
    )
    lut = build_palette_lut(palette_rgb)

    try:
        img = Image.open(input_path).convert("RGBA")
    except Exception as e:
        return False, [f"cannot open image: {e}"]

    # --- Stage 1: Resize to target canvas ---
    if img.size != (target_w, target_h):
        warnings.append(
            f"resized {img.size[0]}x{img.size[1]} -> {target_w}x{target_h} "
            f"(nearest-neighbor)"
        )
        img = img.resize((target_w, target_h), Image.NEAREST)

    px = img.load()

    # --- Stage 2: Binary alpha normalization ---
    alpha_fixed = 0
    for y in range(target_h):
        for x in range(target_w):
            r, g, b, a = px[x, y]
            if a != 0 and a != 255:
                new_a = 255 if a >= alpha_threshold else 0
                px[x, y] = (r, g, b, new_a)
                alpha_fixed += 1
    if alpha_fixed:
        warnings.append(f"binary alpha: normalized {alpha_fixed} pixels")

    # --- Stage 3: Anti-alias / fringe removal ---
    # Remove opaque pixels on the silhouette edge that are very close to
    # transparent neighbors' implied background (low-saturation, high-value
    # fringes typical of AA).
    fringe_removed = 0
    changed = True
    while changed:
        changed = False
        for y in range(target_h):
            for x in range(target_w):
                r, g, b, a = px[x, y]
                if a != 255:
                    continue
                has_transparent_neighbor = False
                opaque_neighbors = 0
                for nx, ny in (
                    (x - 1, y),
                    (x + 1, y),
                    (x, y - 1),
                    (x, y + 1),
                ):
                    if 0 <= nx < target_w and 0 <= ny < target_h:
                        if px[nx, ny][3] == 0:
                            has_transparent_neighbor = True
                        else:
                            opaque_neighbors += 1
                    else:
                        has_transparent_neighbor = True
                if has_transparent_neighbor and opaque_neighbors <= 1:
                    nearest = nearest_palette_color((r, g, b), palette_rgb, lut)
                    dist = color_distance_sq((r, g, b), nearest)
                    if dist > 3000:
                        px[x, y] = (0, 0, 0, 0)
                        fringe_removed += 1
                        changed = True
    if fringe_removed:
        warnings.append(f"fringe removal: cleared {fringe_removed} pixels")

    # --- Stage 4: Palette quantization ---
    quant_changed = 0
    for y in range(target_h):
        for x in range(target_w):
            r, g, b, a = px[x, y]
            if a == 0:
                px[x, y] = (0, 0, 0, 0)
                continue
            rgb = (r, g, b)
            nearest = nearest_palette_color(rgb, palette_rgb, lut)
            if nearest != rgb:
                quant_changed += 1
                px[x, y] = (*nearest, 255)
    if quant_changed:
        warnings.append(f"palette quantization: remapped {quant_changed} pixels")

    # --- Stage 5: Cluster cleanup ---
    opaque: dict[tuple[int, int], tuple[int, int, int]] = {}
    for y in range(target_h):
        for x in range(target_w):
            r, g, b, a = px[x, y]
            if a == 255:
                opaque[(x, y)] = (r, g, b)

    labels = flood_fill_label(opaque)
    sizes = cluster_sizes(labels)
    label_to_color: dict[int, tuple[int, int, int]] = {}
    for pos, lid in labels.items():
        label_to_color[lid] = opaque[pos]

    clusters_merged = 0
    for lid, size in sizes.items():
        if size >= min_cluster_size:
            continue
        color = label_to_color[lid]
        pixels = [pos for pos, l in labels.items() if l == lid]
        for pos in pixels:
            neighbors = get_neighbor_colors(pos[0], pos[1], opaque)
            neighbors = [c for c in neighbors if c != color]
            if neighbors:
                most_common = Counter(neighbors).most_common(1)[0][0]
                opaque[pos] = most_common
                px[pos[0], pos[1]] = (*most_common, 255)
                clusters_merged += 1
            else:
                px[pos[0], pos[1]] = (0, 0, 0, 0)
                del opaque[pos]
                clusters_merged += 1
    if clusters_merged:
        warnings.append(f"cluster cleanup: fixed {clusters_merged} pixels")

    # --- Stage 5b: Dithering cleanup (for no-dither profiles) ---
    dither_cfg = profile.get("dithering", {})
    if not dither_cfg.get("allowed", True):
        dither_fixed = 0
        for y in range(target_h):
            for x in range(target_w):
                if (x, y) not in opaque:
                    continue
                color = opaque[(x, y)]
                neighbors = []
                for nx, ny in (
                    (x - 1, y),
                    (x + 1, y),
                    (x, y - 1),
                    (x, y + 1),
                ):
                    if (nx, ny) in opaque:
                        neighbors.append(opaque[(nx, ny)])
                if len(neighbors) >= 2 and all(n != color for n in neighbors):
                    most_common = Counter(neighbors).most_common(1)[0][0]
                    opaque[(x, y)] = most_common
                    px[x, y] = (*most_common, 255)
                    dither_fixed += 1
        if dither_fixed:
            warnings.append(f"dither cleanup: smoothed {dither_fixed} pixels")

    # --- Stage 6: Color count enforcement ---
    color_rule = profile["unique_opaque_colors"]
    for _ in range(max_color_reduce_passes):
        unique = set(opaque.values())
        if len(unique) <= color_rule["max"]:
            break
        color_counts = Counter(opaque.values())
        rarest = color_counts.most_common()[-1][0]
        for pos in list(opaque.keys()):
            if opaque[pos] == rarest:
                neighbors = get_neighbor_colors(pos[0], pos[1], opaque)
                neighbors = [c for c in neighbors if c != rarest]
                if neighbors:
                    replacement = Counter(neighbors).most_common(1)[0][0]
                else:
                    best = None
                    best_d = float("inf")
                    for c in palette_rgb:
                        if c != rarest and c in color_counts:
                            d = color_distance_sq(rarest, c)
                            if d < best_d:
                                best_d = d
                                best = c
                    replacement = best or palette_rgb[0]
                opaque[pos] = replacement
                px[pos[0], pos[1]] = (*replacement, 255)
    else:
        unique = set(opaque.values())
        if len(unique) > color_rule["max"]:
            warnings.append(
                f"color reduction incomplete: {len(unique)} unique colors "
                f"(max {color_rule['max']}) after {max_color_reduce_passes} "
                f"passes"
            )

    final_unique = len(set(opaque.values()))
    if final_unique < color_rule["min"]:
        return False, [
            f"REJECT: only {final_unique} unique colors after normalization; "
            f"minimum is {color_rule['min']} — source image lacks sufficient "
            f"color variation for this profile"
        ]

    # --- Stage 7: Edge contact check ---
    if not profile.get("opaque_edge_contact_allowed", False):
        edge_cleared = 0
        for x, y in list(opaque.keys()):
            if x in (0, target_w - 1) or y in (0, target_h - 1):
                px[x, y] = (0, 0, 0, 0)
                del opaque[x, y]
                edge_cleared += 1
        if edge_cleared:
            warnings.append(f"edge contact: cleared {edge_cleared} edge pixels")

    # --- Stage 8: R64-09 white cap ---
    white_max = profile["r64_09_white_pixels_max"]
    white_positions = [pos for pos, c in opaque.items() if c == white_rgb]
    if len(white_positions) > white_max:
        excess = sorted(white_positions, key=lambda p: (p[1], p[0]))[white_max:]
        best_alt = None
        best_d = float("inf")
        for c in palette_rgb:
            if c != white_rgb:
                d = color_distance_sq(white_rgb, c)
                if d < best_d:
                    best_d = d
                    best = c
        for pos in excess:
            neighbors = get_neighbor_colors(pos[0], pos[1], opaque)
            neighbors = [c for c in neighbors if c != white_rgb]
            if neighbors:
                replacement = Counter(neighbors).most_common(1)[0][0]
            else:
                replacement = best
            opaque[pos] = replacement
            px[pos[0], pos[1]] = (*replacement, 255)
        warnings.append(
            f"R64-09 cap: downgraded {len(excess)} white pixels "
            f"(limit {white_max})"
        )

    # --- Final bbox check ---
    if opaque:
        ys = [y for _, y in opaque]
        bbox_h = max(ys) - min(ys) + 1
        bbox_rule = profile["occupied_bbox_height_px"]
        if not (bbox_rule["min"] <= bbox_h <= bbox_rule["max"]):
            return False, [
                f"REJECT: occupied bounding-box height {bbox_h}px outside "
                f"allowed range {bbox_rule['min']}..{bbox_rule['max']}px — "
                f"source image composition incompatible with this profile"
            ]
    else:
        return False, ["REJECT: no opaque pixels remain after normalization"]

    img.save(output_path, "PNG")
    warnings.append(f"candidate saved to {output_path}")
    return True, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize an AI-generated image into a Resurrect 64 "
            "sprite candidate."
        )
    )
    parser.add_argument("input", type=Path, help="Source image (any format PIL reads)")
    parser.add_argument("output", type=Path, help="Output PNG path (candidate)")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--profile",
        choices=["64x64", "128x128", "192x192"],
        required=True,
    )
    parser.add_argument(
        "--alpha-threshold",
        type=int,
        default=128,
        help="Alpha threshold for binary normalization (default: 128)",
    )
    parser.add_argument(
        "--min-cluster",
        type=int,
        default=2,
        help="Minimum cluster size; smaller clusters are merged (default: 2)",
    )
    args = parser.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))

    ok, messages = normalize_sprite(
        args.input,
        args.output,
        args.profile,
        cfg,
        alpha_threshold=args.alpha_threshold,
        min_cluster_size=args.min_cluster,
    )

    for msg in messages:
        prefix = "  " if not msg.startswith("REJECT") else ""
        print(f"{prefix}{msg}")

    if ok:
        print(f"\nCANDIDATE generated. Run validator to promote to master.")
        return 0
    else:
        print(f"\nREJECTED. Automated correction cannot produce a compliant asset.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
