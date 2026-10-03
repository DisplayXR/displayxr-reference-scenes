#!/usr/bin/env python3
# Copyright 2026, The DisplayXR Project and its contributors
# SPDX-License-Identifier: Apache-2.0
"""
Build a slim, natively loadable copy of an OpenUSD + MaterialX scene.

The ASWF OpenPBR Shader Playground ships ~2.1 GB of 4096-px, mostly LZW-TIFF
maps. A DisplayXR panel needs a fraction of that, so this copies the scene's
layers unchanged and re-encodes only its TEXTURES:

  * every texture the scene references -- MaterialX `file` inputs (all UDIM
    tiles of a <UDIM> pattern) and asset paths authored in USD text layers
    (overrides can swap a node's file) -- and nothing else;
  * colour maps (MaterialX colorspace srgb_tx) -> JPEG, quality --jpeg;
    data maps (normals, masks, roughness, metalness) -> lossless 8-bit PNG,
    where JPEG blocks would read as bumps or roughness noise;
  * longest edge capped at --max-size;
  * the references in .mtlx / .usda text rewritten to the new names.

Binary layers (.usd crate files: geometry, cameras, lights) are copied as-is.
It writes MODIFICATIONS.md describing exactly what changed, which the ASWF
Digital Assets License requires of a redistribution.

Usage:
    build_usd_slim.py <src-scene-dir> <out-dir> [--max-size 1024] [--jpeg 90]

Needs: numpy pillow tifffile imagecodecs  (imagecodecs: LZW / Deflate TIFF)
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TEX_EXT = (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".exr")
# A texture path inside a .mtlx value="..." or a USD @...@ asset path.
PATH_RE = re.compile(r'([A-Za-z0-9_./\\<>-]+?\.(?:tif|tiff|png|jpg|jpeg|exr))', re.I)


def load(path):
    if path.suffix.lower() in (".tif", ".tiff"):
        import tifffile
        a = tifffile.imread(str(path))
    else:
        a = np.asarray(Image.open(path))
    if a.dtype == np.uint16:
        a = (a.astype(np.float32) / 257.0).round().clip(0, 255).astype(np.uint8)
    elif a.dtype != np.uint8:
        a = (np.clip(a.astype(np.float32), 0, 1) * 255 + 0.5).astype(np.uint8)
    if a.ndim == 3 and a.shape[2] > 4:
        a = a[..., :4]
    return a


def resize(a, max_size):
    h, w = a.shape[:2]
    s = min(1.0, max_size / max(h, w))
    if s >= 1.0:
        return a
    im = Image.fromarray(a)
    return np.asarray(im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--max-size", type=int, default=1024)
    ap.add_argument("--jpeg", type=int, default=90)
    a = ap.parse_args()
    src, out = Path(a.src).resolve(), Path(a.out).resolve()
    if out.exists():
        shutil.rmtree(out)

    text_files = [p for p in src.rglob("*") if p.suffix.lower() in (".mtlx", ".usda")]
    # colourspace per referenced texture pattern, from the MaterialX inputs
    srgb_patterns = set()
    for p in text_files:
        if p.suffix.lower() != ".mtlx":
            continue
        # Quoted values may contain '>' -- MaterialX writes `<UDIM>` inside them.
        for m in re.finditer(r'<input\b(?:[^>"]|"[^"]*")*>', p.read_text(errors="replace")):
            if 'name="file"' not in m.group(0):
                continue
            tag = m.group(0)
            cs = re.search(r'colorspace="([^"]+)"', tag)
            val = re.search(r'value="([^"]+)"', tag)
            if val and cs and cs.group(1).lower().startswith("srgb"):
                srgb_patterns.add((p.parent / val.group(1)).as_posix())

    # every referenced texture, resolved against the referencing file's folder
    referenced = {}   # resolved source file -> (is_colour, pattern string as authored)
    for p in text_files:
        for m in PATH_RE.finditer(p.read_text(errors="replace")):
            rel = m.group(1)
            pattern = (p.parent / rel).as_posix()
            colour = pattern in srgb_patterns
            if "<UDIM>" in rel:
                base = Path(pattern)
                pre, post = base.name.split("<UDIM>")
                for f in base.parent.glob(pre + "[0-9][0-9][0-9][0-9]" + post):
                    referenced[f.resolve()] = colour
            else:
                f = Path(os.path.normpath(pattern))
                if f.exists():
                    referenced[f.resolve()] = colour

    # copy everything except textures; re-encode referenced textures
    renamed = {}   # old file name -> new file name (per directory, names are unique)
    stats = {"colour": 0, "data": 0, "skipped": [], "in_bytes": 0, "out_bytes": 0}
    for f in src.rglob("*"):
        if f.is_dir():
            continue
        rel = f.relative_to(src)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if f.suffix.lower() not in TEX_EXT:
            shutil.copy2(f, dst)
            continue
        if f.resolve() not in referenced:
            continue   # unreferenced texture: dropped
        colour = referenced[f.resolve()]
        try:
            img = resize(load(f), a.max_size)
        except Exception as e:  # noqa: BLE001 -- keep the original, say so
            shutil.copy2(f, dst)
            stats["skipped"].append(f"{rel} ({e})")
            continue
        stats["in_bytes"] += f.stat().st_size
        if colour and (img.ndim == 2 or img.shape[2] == 3):
            new = dst.with_suffix(".jpg")
            Image.fromarray(img).save(new, "JPEG", quality=a.jpeg, optimize=True)
            stats["colour"] += 1
        else:
            new = dst.with_suffix(".png")
            Image.fromarray(img).save(new, "PNG", optimize=True)
            stats["data"] += 1
        stats["out_bytes"] += new.stat().st_size
        renamed[f.name] = new.name

    # rewrite references in text layers; a <UDIM> pattern follows its tiles
    def rewrite(m):
        rel = m.group(1)
        name = Path(rel.replace("\\", "/")).name
        probe = name.replace("<UDIM>", "1001")
        tile_new = renamed.get(probe)
        if tile_new is None and "<UDIM>" in name:
            pre = name.split("<UDIM>")[0]
            tile_new = next((v for k, v in renamed.items() if k.startswith(pre)), None)
        if tile_new is None:
            tile_new = renamed.get(name)
        if tile_new is None:
            return rel
        return rel[: len(rel) - len(Path(rel).suffix)] + Path(tile_new).suffix
    for p in out.rglob("*"):
        if p.suffix.lower() in (".mtlx", ".usda"):
            t = p.read_text(errors="replace")
            p.write_text(PATH_RE.sub(rewrite, t))

    mb = lambda b: f"{b / 1e6:.0f} MB"
    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    (out / "MODIFICATIONS.md").write_text(f"""# Modifications from the original

This is a modified redistribution, produced by DisplayXR's
`scripts/build_usd_slim.py` (displayxr-reference-scenes). The scene's USD
layers, MaterialX documents and geometry are unchanged except as listed:

- Every referenced texture was re-encoded with its longest edge capped at
  {a.max_size} px: {stats['colour']} colour maps (MaterialX colorspace srgb_tx)
  as JPEG at quality {a.jpeg}, {stats['data']} data maps as lossless 8-bit PNG
  (16-bit sources reduced to 8 bit). {mb(stats['in_bytes'])} of source textures
  became {mb(stats['out_bytes'])}.
- Texture references in the `.mtlx` and `.usda` text layers were renamed to
  the new file extensions. No other content of those layers changed.
- Textures the scene does not reference were omitted.
{''.join(f'- Not re-encoded (copied as-is): {s}{chr(10)}' for s in stats['skipped'])}
Package size: {mb(total)}.
""")
    print(f"{stats['colour']} colour + {stats['data']} data textures; "
          f"{mb(stats['in_bytes'])} -> {mb(stats['out_bytes'])}; package {mb(total)}; "
          f"{len(stats['skipped'])} skipped")


if __name__ == "__main__":
    sys.exit(main())
