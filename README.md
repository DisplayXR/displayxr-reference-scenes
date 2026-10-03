# DisplayXR reference scenes

Scenes for **demonstrating and validating** open-standard 3D content on 3D
displays: OpenUSD, MaterialX / OpenPBR and glTF, rendered through
[DisplayXR](https://github.com/DisplayXR/displayxr-runtime), the OpenXR runtime
for glasses-free 3D displays.

Each scene says what it exercises, where it came from (pinned), and the
licence it is under. Everything here is for technology demonstration,
development and benchmarking.

## Scenes

| Scene | Kind | Status | Licence |
|---|---|---|---|
| [OpenPBR Shader Playground](scenes/openpbr-shader-playground/) | OpenUSD + MaterialX OpenPBR, lights, cameras | packs on releases | ASWF Digital Assets License v1.1 |
| [DisplayXR material tests](scenes/displayxr-material-tests/) | glTF `KHR_materials_*` sweeps | in repo | CC0-1.0 |
| [OpenPBR material swatches](scenes/openpbr-swatches/) | 93 OpenPBR example materials on the standard shader ball | planned | Apache-2.0 + CC-BY-4.0 |
| [Khronos glTF showcases](index/khronos-gltf-sample-assets.json) | 11 glTF extension showcases | **index only**: fetched from upstream at a pinned commit | per model: CC0-1.0 / CC-BY-4.0 |

## Licensing

**Two layers, kept apart:**

- **Scripts, manifests and docs:** [Apache-2.0](LICENSE).
- **Each scene's content:** its own licence, stated in its `scene.json`, with the full text in [`LICENSES/`](LICENSES/) and attributions in [NOTICE.md](NOTICE.md). Nothing here changes a third-party asset's licence.

**Index entries are never copied.** A Khronos showcase is fetched from its own
repository and keeps its upstream licence and attribution.

**Redistributed scenes** (the OpenPBR Shader Playground packs) carry the licence
text, the copyright notice and `MODIFICATIONS.md` inside every pack. That
licence permits use **solely** for education, training, research,
software/hardware development, benchmarking and product demonstration. It does
not allow implying endorsement by the copyright holder, and it requires the
copyright notice on any published image.

## Layout

```
scenes/<id>/scene.json   manifest: what it exercises, source pin, licence, packs
scenes/<id>/README.md    what the scene shows and how to open it
scenes/<id>/NOTICE.md    licence obligations (redistributed scenes)
index/*.json             upstream-hosted scenes, by pinned commit
scripts/                 pack builders + the manifest validator
LICENSES/                full licence texts
```

`scripts/validate.py` runs on every PR. It checks that every scene declares a
licence, a pinned source and an existing licence file, and that no binary file
is committed for an index-only source.

## Building packs

```
pip install usd-core numpy pillow tifffile imagecodecs fast-simplification
scripts/build_playground.sh out/
```

Packs are published as GitHub release assets by the `build-packs` workflow.
