# RESURRECT 64 SPRITE PROFILE — 64×64

## CANONICAL PALETTE

**Palette:** Resurrect 64  
**Creator:** Kerrie Lake  
**Allowed transparent value:** `#00000000` only

| ID | Hex |
|---|---|
| R64-00 | `#2e222f` |
| R64-01 | `#3e3546` |
| R64-02 | `#625565` |
| R64-03 | `#966c6c` |
| R64-04 | `#ab947a` |
| R64-05 | `#694f62` |
| R64-06 | `#7f708a` |
| R64-07 | `#9babb2` |
| R64-08 | `#c7dcd0` |
| R64-09 | `#ffffff` |
| R64-10 | `#6e2727` |
| R64-11 | `#b33831` |
| R64-12 | `#ea4f36` |
| R64-13 | `#f57d4a` |
| R64-14 | `#ae2334` |
| R64-15 | `#e83b3b` |
| R64-16 | `#fb6b1d` |
| R64-17 | `#f79617` |
| R64-18 | `#f9c22b` |
| R64-19 | `#7a3045` |
| R64-20 | `#9e4539` |
| R64-21 | `#cd683d` |
| R64-22 | `#e6904e` |
| R64-23 | `#fbb954` |
| R64-24 | `#4c3e24` |
| R64-25 | `#676633` |
| R64-26 | `#a2a947` |
| R64-27 | `#d5e04b` |
| R64-28 | `#fbff86` |
| R64-29 | `#165a4c` |
| R64-30 | `#239063` |
| R64-31 | `#1ebc73` |
| R64-32 | `#91db69` |
| R64-33 | `#cddf6c` |
| R64-34 | `#313638` |
| R64-35 | `#374e4a` |
| R64-36 | `#547e64` |
| R64-37 | `#92a984` |
| R64-38 | `#b2ba90` |
| R64-39 | `#0b5e65` |
| R64-40 | `#0b8a8f` |
| R64-41 | `#0eaf9b` |
| R64-42 | `#30e1b9` |
| R64-43 | `#8ff8e2` |
| R64-44 | `#323353` |
| R64-45 | `#484a77` |
| R64-46 | `#4d65b4` |
| R64-47 | `#4d9be6` |
| R64-48 | `#8fd3ff` |
| R64-49 | `#45293f` |
| R64-50 | `#6b3e75` |
| R64-51 | `#905ea9` |
| R64-52 | `#a884f3` |
| R64-53 | `#eaaded` |
| R64-54 | `#753c54` |
| R64-55 | `#a24b6f` |
| R64-56 | `#cf657f` |
| R64-57 | `#ed8099` |
| R64-58 | `#831c5d` |
| R64-59 | `#c32454` |
| R64-60 | `#f04f78` |
| R64-61 | `#f68181` |
| R64-62 | `#fca790` |
| R64-63 | `#fdcbb0` |


## SIZE PROFILE

- Canvas MUST be exactly `64×64`.
- Unique opaque color count MUST be `12` to `22` inclusive.
- Major material ramp depth MUST be `3` or `4` colors.
- Minor material ramp depth MUST be `1` or `2` colors.
- Exterior contour thickness MUST be `1` pixel.
- Dithering is prohibited.
- `R64-09` usage MUST NOT exceed `8` opaque pixels.
- The occupied subject bounding box height MUST be `48` to `60` pixels inclusive unless the asset specification explicitly defines a non-upright subject.
- The largest single highlight cluster MUST NOT exceed `4` connected pixels.
- The sprite MUST contain at least `3` distinct value levels across the full figure.
- The sprite MUST contain at least `1` clear separation edge between body and primary equipment if primary equipment is present.
- Face detail MUST use at most `6` opaque pixels excluding hairline.
- Fine texture clusters MUST NOT exceed `2×2` unless the cluster describes a major form edge.


## APPROVED RAMP FAMILIES

Use only the IDs listed in one family for one local material ramp. A ramp MAY omit interior steps. A ramp MUST preserve order from dark to light.

| Family ID | Palette IDs |
|---|---|
| OUTLINE-WARM | R64-00, R64-01, R64-02 |
| OUTLINE-COOL | R64-34, R64-44, R64-45 |
| OUTLINE-VIOLET | R64-49, R64-50 |
| METAL-IRON | R64-34, R64-35, R64-07, R64-08, R64-09 |
| METAL-BLUE | R64-44, R64-45, R64-07, R64-08, R64-09 |
| LEATHER-BROWN | R64-24, R64-20, R64-21, R64-22, R64-23 |
| LEATHER-RED | R64-10, R64-11, R64-12, R64-13 |
| WOOD | R64-24, R64-20, R64-04, R64-22, R64-23 |
| CLOTH-RED | R64-10, R64-14, R64-15, R64-13 |
| CLOTH-ORANGE | R64-20, R64-21, R64-22, R64-23 |
| CLOTH-YELLOW | R64-25, R64-26, R64-27, R64-28 |
| CLOTH-OLIVE | R64-24, R64-25, R64-26, R64-27 |
| CLOTH-GREEN | R64-29, R64-30, R64-31, R64-32, R64-33 |
| CLOTH-SAGE | R64-35, R64-36, R64-37, R64-38 |
| CLOTH-TEAL | R64-39, R64-40, R64-41, R64-42, R64-43 |
| CLOTH-BLUE | R64-44, R64-45, R64-46, R64-47, R64-48 |
| CLOTH-VIOLET | R64-49, R64-50, R64-51, R64-52, R64-53 |
| CLOTH-ROSE | R64-54, R64-55, R64-56, R64-57 |
| CLOTH-MAGENTA | R64-58, R64-59, R64-60, R64-61, R64-62 |
| SKIN-DARK | R64-19, R64-20, R64-21, R64-22, R64-23 |
| SKIN-MEDIUM | R64-03, R64-04, R64-21, R64-22, R64-62 |
| SKIN-LIGHT | R64-03, R64-04, R64-61, R64-62, R64-63 |
| SKIN-COOL | R64-05, R64-03, R64-54, R64-61, R64-62 |
| BONE | R64-24, R64-04, R64-08, R64-09 |
| MAGIC-TEAL | R64-39, R64-40, R64-41, R64-42, R64-43 |
| MAGIC-BLUE | R64-44, R64-46, R64-47, R64-48, R64-09 |
| MAGIC-VIOLET | R64-49, R64-50, R64-51, R64-52, R64-53 |
| MAGIC-ROSE | R64-54, R64-55, R64-56, R64-57, R64-63 |
| BLOOD | R64-10, R64-14, R64-15 |
| NEUTRAL-COOL | R64-01, R64-05, R64-06, R64-07, R64-08, R64-09 |
| WARM-GOLD | R64-20, R64-21, R64-16, R64-17, R64-18 |
| FIRE | R64-10, R64-14, R64-16, R64-17, R64-18 |


## GLOBAL RULES

1. Output MUST be pixel art.
2. Every opaque pixel MUST match exactly one canonical palette RGB value.
3. Alpha MUST be `0` or `255` only.
4. Background MUST be fully transparent.
5. Cast shadows MUST NOT be baked into the sprite.
6. Blur, glow filters, gradients, soft brushes, subpixel anti-aliasing, and non-integer resampling are prohibited.
7. Review scale MUST be integer nearest-neighbor.
8. Silhouette, pose, facing, and gameplay-critical equipment MUST read at native size.
9. Large contiguous clusters are required. Random noise is prohibited.
10. The sprite MUST NOT be a downscaled painting.
11. The sprite MUST NOT be cropped by the canvas edge.
12. The same entity across multiple frames MUST preserve the same RGB assignments for the same materials.
13. New colors in later frames are allowed only for newly visible materials or explicit effects.
14. Quantization to the canonical palette is mandatory.
15. Cluster cleanup after quantization is mandatory.

## MATERIAL-RAMP RULES

1. Each major material MUST use one approved family.
2. A major material MUST NOT exceed the size-profile ramp limit.
3. A minor material MUST NOT exceed the size-profile ramp limit.
4. A material MAY borrow one darker contour color from an approved outline family.
5. A material MUST NOT mix unrelated bright families.
6. Skin MUST use one approved skin family.
7. Metal MUST use one approved metal family.
8. Magic MUST use one approved magic family.
9. `R64-09` MUST be used only for the brightest focal highlights.

## LINE RULES

1. Exterior contour thickness MUST follow the size profile.
2. Interior separation lines MUST be 1 pixel thick.
3. Interior outlines MUST be used only to separate overlapping forms or clarify form breaks.
4. Full sticker-style uniform border treatment is prohibited unless an asset specification explicitly requires it.

## TEXTURE RULES

1. Texture MUST be cluster-based.
2. Checkerboard dithering MUST follow the size profile.
3. Texture MUST NOT replace form shading.
4. Single-pixel noise clusters of size 1 are prohibited unless they are intentional eyes, spark points, studs, or equivalent focal details.

## VALIDATION RULES

Reject the sprite if any condition is true:

- wrong dimensions;
- any opaque RGB value is outside the canonical palette;
- any alpha value is not `0` or `255`;
- unique opaque color count is outside the size-profile limits;
- anti-aliasing is present;
- blur, gradient, or soft-edge artifacts are present;
- subject is cropped;
- background is not fully transparent;
- silhouette fails at native size;
- same-entity palette drift exists across frames.


## OUTPUT CHECKLIST

- [ ] Dimensions match the size profile.
- [ ] Background is fully transparent.
- [ ] Alpha is binary only.
- [ ] Opaque RGB values belong to canonical Resurrect 64 only.
- [ ] Unique opaque color count is within the size-profile range.
- [ ] Major material ramp depth complies.
- [ ] Minor material ramp depth complies.
- [ ] Outline thickness complies.
- [ ] Dithering complies.
- [ ] `R64-09` usage complies.
- [ ] Subject bounding box complies.
- [ ] Subject is not cropped.
- [ ] Silhouette reads at 1×.
- [ ] Equipment separation reads at 1×.
- [ ] No anti-aliasing exists.
- [ ] No blur or gradient artifacts exist.
- [ ] Same-entity RGB assignments are stable across frames.

