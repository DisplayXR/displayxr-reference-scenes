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
REPO=$(python3 -c "import json;print(json.load(open('$SCENE'))['source']['repo'])")
TAG=$(python3 -c "import json;print(json.load(open('$SCENE'))['source']['tag'])")
COMMIT=$(python3 -c "import json;print(json.load(open('$SCENE'))['source']['commit'])")
CONV=$(python3 -c "import json;print([p for p in json.load(open('$SCENE'))['packs'] if p['format']=='glb'][0]['converter_commit'])")
WORK="$OUT/work"; mkdir -p "$WORK"
UPSTREAM="$WORK/OpenPBRShaderPlayground"

if [ ! -d "$UPSTREAM" ]; then
    echo "==> upstream $TAG (~2 GB)"
    git clone -q --depth 1 --branch "$TAG" "$REPO.git" "$UPSTREAM"
fi
# The pack, its NOTICE and MODIFICATIONS.md all say they were built from source.commit: a tag
# that upstream moved, or a work directory reused from another build, must not pass for it.
# Checked after a fresh clone AND on a reused directory.
HEAD_COMMIT=$(git -C "$UPSTREAM" rev-parse --verify -q HEAD || true)
if [ "$HEAD_COMMIT" != "$COMMIT" ]; then
    echo "error: $UPSTREAM is at '${HEAD_COMMIT:-no commit}', but $SCENE pins source.commit $COMMIT (tag $TAG)." >&2
    echo "       Upstream moved the tag, or the work directory is stale: remove it and re-run, or update the pin deliberately." >&2
    exit 1
fi
echo "==> upstream at pinned commit ${COMMIT:0:12}"
SRC="$UPSTREAM/ShdrPlygrnd"

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
