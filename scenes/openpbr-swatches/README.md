# OpenPBR material swatches

Every official OpenPBR reference material on the standard shader ball, one
material per scene:

- 83 materials from the OpenPBR repository's `examples/`;
- 2 more from MaterialX's `Examples/OpenPbr` (`honey`, `lightbulb`; its other
  8 duplicate OpenPBR file names);
- the ball is the usd-wg StandardShaderBall (CC BY 4.0).

A single object at a time is what a 3D panel shows best. Coat depth, fuzz and
transmission read through parallax.

**Format.** The pack is plain USD + MaterialX. It holds the upstream files
unchanged, plus one wrapper per material (`swatches/<name>.usda`). The
wrapper sublayers the ball, references the `.mtlx` and binds it to the
ball's outer surface. `swatches/INDEX.tsv` maps swatch → document → material.
Open any wrapper in an OpenPBR-aware USD viewer. In the DisplayXR model
viewer, the version that understands MaterialX colour spaces is listed in
[scene.json](scene.json).

**Colour.** The example documents are authored in ACEScg. A loader that
ignores `colorspace="acescg"` renders every swatch with shifted hues.

**Build:** `scripts/build_swatches.sh <out>` (pinned sources, ~25 MB download).
Known divergences are listed in [scene.json](scene.json).
