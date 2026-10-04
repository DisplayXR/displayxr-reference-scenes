# OpenPBR material swatches: notice

The pack published for this scene combines three upstream works. **None of
them is modified.** Each swatch is a small wrapper layer, written by
`scripts/build_swatches.py`, that binds one example material to the ball
using USD opinions. The pack's `MODIFICATIONS.md` lists exactly which files
it includes and what the wrappers override.

- **OpenPBR example materials**
  ([AcademySoftwareFoundation/OpenPBR](https://github.com/AcademySoftwareFoundation/OpenPBR)
  `examples/`). Apache License 2.0, Copyright Contributors to the OpenPBR
  Project.
- **MaterialX OpenPBR examples**
  ([AcademySoftwareFoundation/MaterialX](https://github.com/AcademySoftwareFoundation/MaterialX)
  `resources/Materials/Examples/OpenPbr/`). Apache License 2.0, Copyright
  Contributors to the MaterialX Project. Where a file name also exists in the
  OpenPBR repository, the OpenPBR copy is used.
- **StandardShaderBall**
  ([usd-wg/assets](https://github.com/usd-wg/assets)
  `full_assets/StandardShaderBall/`). Creative Commons Attribution 4.0
  International, usd-wg/assets contributors. Its own `LICENCE` and
  `README.md` travel unchanged inside the pack. Per that README, the ball was
  built from scratch, *inspired by* Thomas Anagnostou's "Simball" (released
  under CC BY-SA). No Simball content is included.

Licences: `LICENSE-Apache-2.0.txt` and `LICENSE-CC-BY-4.0.txt` in the pack;
`LICENSES/` in this repository. Exact upstream commits:
[scene.json](scene.json).

No endorsement by the Academy Software Foundation, the OpenPBR or MaterialX
projects, or the usd-wg contributors is implied.
