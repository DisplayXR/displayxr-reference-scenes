# OpenPBR Shader Playground

The ASWF reference scene for the OpenPBR surface model: a child's arts-and-crafts
room with 61 OpenPBR materials authored in MaterialX and composed in OpenUSD,
lit by area and sphere lights and framed by eight render cameras. It is the
most complete open-standards production scene we know of, which makes it the
headline test of "author in open standards, view on any 3D display".

| Pack | Format | Size | Opens in |
|---|---|---|---|
| `openpbr-shader-playground-usd.zip` | OpenUSD + MaterialX (textures re-encoded, ≤1024 px) | ~130 MB | DisplayXR model viewer, natively |
| `openpbr-shader-playground.glb` | glTF 2.0 + `KHR_materials_*` + `KHR_lights_punctual` | ~145 MB | DisplayXR model viewer, other glTF viewers (draft extensions vary) |

Packs are release assets, not files in this repository. Build them yourself with
[`scripts/build_playground.sh`](../../scripts/build_playground.sh).

**What it exercises:** MaterialX node-graph evaluation, USD composition
(sublayers, payload, `.mtlx` references, and the layer that overrides 23 of the
54 looks), scene lights with shadow maps, render cameras, GeomSubset materials,
UDIM tiles, and transmission, subsurface, coat, fuzz and emission.

**Try it:** open `ShdrPlygrnd/ShdrPlygrnd_OpenPBR.usda` in the model viewer.
On macOS, `DXR_MODELVIEWER_CAMERA=renderCam_CU_planeTOP` starts at the
published top-down still's viewpoint.

**Known divergences from the published Arnold renders:** see `known_divergences`
in [scene.json](scene.json).

Licensing: [NOTICE.md](NOTICE.md).
