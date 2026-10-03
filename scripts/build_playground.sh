#!/usr/bin/env bash
# Copyright 2026, The DisplayXR Project and its contributors
# SPDX-License-Identifier: Apache-2.0
#
# Build the OpenPBR Shader Playground packs from the PINNED upstream release:
#   <out>/openpbr-shader-playground-usd.zip   (scripts/build_usd_slim.py)
#   <out>/openpbr-shader-playground.glb       (the model viewer's converter,
#                                              pinned in scene.json)
# Each pack carries the licence, the notice and MODIFICATIONS.md.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(mkdir -p "${1:-out}" && cd "${1:-out}" && pwd)"
SCENE="$HERE/scenes/openpbr-shader-playground/scene.json"
TAG=$(python3 -c "import json;print(json.load(open('$SCENE'))['source']['tag'])")
CONV=$(python3 -c "import json;print([p for p in json.load(open('$SCENE'))['packs'] if p['format']=='glb'][0]['converter_commit'])")
WORK="$OUT/work"; mkdir -p "$WORK"

if [ ! -d "$WORK/OpenPBRShaderPlayground" ]; then
    echo "==> upstream $TAG (~2 GB)"
    git clone -q --depth 1 --branch "$TAG" \
        https://github.com/DigitalProductionExampleLibrary/OpenPBRShaderPlayground.git \
        "$WORK/OpenPBRShaderPlayground"
fi
SRC="$WORK/OpenPBRShaderPlayground/ShdrPlygrnd"

echo "==> USD pack"
rm -rf "$WORK/usd"; mkdir -p "$WORK/usd"
python3 "$HERE/scripts/build_usd_slim.py" "$SRC" "$WORK/usd/ShdrPlygrnd"
cp "$WORK/usd/ShdrPlygrnd/MODIFICATIONS.md" "$WORK/usd/"
cp "$HERE/LICENSES/ASWF-DAL-1.1_OpenPBR-Shader-Playground.txt" "$WORK/usd/LICENSE.txt"
cp "$HERE/scenes/openpbr-shader-playground/NOTICE.md" "$WORK/usd/"
(cd "$WORK/usd" && rm -f "$OUT/openpbr-shader-playground-usd.zip" &&
    zip -qr "$OUT/openpbr-shader-playground-usd.zip" .)

echo "==> glTF pack (converter @ $CONV)"
curl -sfL "https://raw.githubusercontent.com/DisplayXR/displayxr-demo-modelviewer/$CONV/scripts/openpbr_mtlx_to_gltf.py" \
    -o "$WORK/openpbr_mtlx_to_gltf.py"
python3 "$WORK/openpbr_mtlx_to_gltf.py" "$SRC/ShdrPlygrnd_OpenPBR.usda" "$WORK/glb" \
    --groups /World --jpeg-quality 90 --decimate bubbles=0.2,bubblesMasonJar=0.2,OJ=0.4
mv "$WORK/glb/World.glb" "$OUT/openpbr-shader-playground.glb"

(cd "$OUT" && shasum -a 256 openpbr-shader-playground-usd.zip openpbr-shader-playground.glb > SHA256SUMS)
ls -la "$OUT"
