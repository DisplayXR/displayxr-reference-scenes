#!/usr/bin/env bash
# Copyright 2026, The DisplayXR Project and its contributors
# SPDX-License-Identifier: Apache-2.0
#
# Build the OpenPBR swatch pack from the PINNED upstream commits in
# scenes/openpbr-swatches/scene.json:
#   <out>/openpbr-swatches-usd.zip   (scripts/build_swatches.py)
# The pack carries both licences, the notice and MODIFICATIONS.md.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(mkdir -p "${1:-out}" && cd "${1:-out}" && pwd)"
SCENE="$HERE/scenes/openpbr-swatches/scene.json"
WORK="$OUT/work-swatches"; mkdir -p "$WORK"

# repo-url commit sparse-path, one line per pinned source
python3 - "$SCENE" > "$WORK/sources.txt" <<'PY'
import json, sys
for s in json.load(open(sys.argv[1]))["sources"]:
    print(s["repo"], s["commit"], s["path"])
PY

fetch() {   # <repo-url> <commit> <path> -> $WORK/<repo-name>
    local url=$1 commit=$2 path=$3 dir="$WORK/$(basename "$1")"
    if [ ! -d "$dir/.git" ]; then
        git init -q "$dir"
        git -C "$dir" remote add origin "$url"
        git -C "$dir" config core.sparseCheckout true
    fi
    echo "$path" > "$dir/.git/info/sparse-checkout"
    git -C "$dir" fetch -q --depth 1 --filter=blob:none origin "$commit"
    git -C "$dir" checkout -q FETCH_HEAD
    echo "$dir/$path"
}

MTLX_ARGS=()
BALL=""
while read -r url commit path; do
    echo "==> $(basename "$url") @ ${commit:0:12} ($path)"
    dir=$(fetch "$url" "$commit" "$path")
    case "$path" in
        *StandardShaderBall*) BALL="$dir" ;;
        *) MTLX_ARGS+=(--mtlx "$dir") ;;
    esac
done < "$WORK/sources.txt"
[ -n "$BALL" ] || { echo "no StandardShaderBall source in $SCENE" >&2; exit 1; }

echo "==> swatches"
rm -rf "$WORK/pack"
python3 "$HERE/scripts/build_swatches.py" "$WORK/pack/openpbr-swatches" --ball "$BALL" "${MTLX_ARGS[@]}"
cp "$WORK/pack/openpbr-swatches/MODIFICATIONS.md" "$WORK/pack/"
cp "$HERE/LICENSES/Apache-2.0.txt" "$WORK/pack/LICENSE-Apache-2.0.txt"
cp "$HERE/LICENSES/CC-BY-4.0.txt" "$WORK/pack/LICENSE-CC-BY-4.0.txt"
cp "$HERE/scenes/openpbr-swatches/NOTICE.md" "$WORK/pack/"
(cd "$WORK/pack" && rm -f "$OUT/openpbr-swatches-usd.zip" && zip -qr "$OUT/openpbr-swatches-usd.zip" .)
(cd "$OUT" && shasum -a 256 openpbr-swatches-usd.zip >> SHA256SUMS)
ls -la "$OUT/openpbr-swatches-usd.zip"
