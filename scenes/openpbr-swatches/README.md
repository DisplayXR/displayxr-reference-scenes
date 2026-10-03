# OpenPBR material swatches (planned)

Every official OpenPBR example material on the standard shader ball, one material
per scene:

- 83 materials from the OpenPBR spec repository and 10 from MaterialX, both Apache-2.0;
- the ball is the usd-wg StandardShaderBall, CC-BY 4.0.

A single object at a time is the format a 3D panel shows best. Coat depth,
fuzz and transmission read through parallax.

**Blocked on:** the example documents declare `colorspace="acescg"`. The
DisplayXR loader and converter have to convert ACEScg colour inputs to linear
Rec.709 first, or every swatch shifts hue. Details in [scene.json](scene.json).
