#!/usr/bin/env python3
# Copyright 2026, The DisplayXR Project and its contributors
# SPDX-License-Identifier: CC0-1.0
"""
Generate the 3D-display test scenes (glTF binary, CC0).

These test the DISPLAY path (stereo/multiview geometry, the zero-disparity
plane, edges, crosstalk), not materials. Every scene is authored so a viewer
using the DisplayXR framing rule (AABB centre on the ZDP; height filled to 80%)
maps it the same way on any landscape panel:

    scene: 1.4 wide x 1.0 tall x <= 1.0 deep, centred on the origin
    -> the HEIGHT cap binds whenever aspect >= ~1.74 (hypot(1.4, depth) / 0.8 / 1.25)
    -> 1 display height (vH) = 1.0 / 0.8 = 1.25 scene units
    -> a surface at z = d * 1.25 sits d display heights in front of the glass
       (+z = out of the glass, toward the viewer)

So depth labels are exact in display heights. On a narrower (portrait) panel
the width cap binds instead; run the model viewer with `--vh 1.25` to pin the
mapping. Scenes:

  depth_ladder.glb    9 checker tiles, each labelled with its depth in vH,
                      from +0.40 (in front) to -0.40 (behind), in 0.10 steps.
  window_box.glb      an open-fronted grid box: its opening is the frame at the
                      ZDP, its back wall 0.40 vH behind. Straight grid lines
                      must stay straight and the box must stay put as the
                      viewer moves: a Kooima / view-rig correctness check.
  edge_violation.glb  bars crossing the top and bottom frame edges at depths
                      from +0.40 to -0.40 vH. Run with `--vh 1.0` so the frame
                      edges ARE the display edges: a bar in FRONT of the glass
                      cut by the edge is a stereo window violation; one behind
                      is not.
  crosstalk_bars.glb  thin emissive white bars over a black backdrop at depths
                      from +0.40 to -0.40 vH. Ghosting (a faint double of each
                      bar) grows with |depth|; the 0.00 bar must show none.

Deterministic: the same script writes byte-identical files (no timestamps,
fixed PNG encoding). Only numpy is needed.

Usage: make_display_tests.py <out-dir>
"""
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

VH = 1.25            # scene units per display height (see the docstring)
FRAME_W, FRAME_H = 1.4, 1.0
DEPTHS = [0.40, 0.30, 0.20, 0.10, 0.00, -0.10, -0.20, -0.30, -0.40]  # in vH

# ------------------------------------------------------------ 5x7 bitmap font
# Hand-drawn, so the labels carry no font licence. Rows top to bottom.
GLYPHS = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "v": ["00000", "00000", "10001", "10001", "10001", "01010", "00100"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    " ": ["00000"] * 7,
}


def label(text):
    """Text -> 7-row bool mask, 1 px between glyphs."""
    cols = []
    for ch in text:
        g = np.array([[c == "1" for c in row] for row in GLYPHS[ch]])
        cols += [g, np.zeros((7, 1), bool)]
    return np.concatenate(cols[:-1], 1)


def depth_text(d):
    return ("+" if d > 0 else "-" if d < 0 else " ") + f"{abs(d):.2f}vH"


def png(rgb):
    """uint8 HxWx3 -> PNG bytes, fixed encoding (deterministic)."""
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def tile_texture(text, size=256, checks=8):
    """Fine checker (fusion needs texture) with a label band across the middle."""
    y, x = np.mgrid[0:size, 0:size]
    chk = ((x * checks // size + y * checks // size) % 2).astype(np.float32)
    img = np.stack([0.55 + 0.25 * chk] * 3, -1)
    m = label(text)
    s = max(1, (size - 24) // m.shape[1])
    m = np.kron(m, np.ones((s, s), bool))
    y0, x0 = (size - m.shape[0]) // 2, (size - m.shape[1]) // 2
    band = img[y0 - 6:y0 + m.shape[0] + 6, x0 - 6:x0 + m.shape[1] + 6]
    band[:] = 1.0
    img[y0:y0 + m.shape[0], x0:x0 + m.shape[1]][m] = 0.0
    return (img * 255 + 0.5).astype(np.uint8)


def grid_texture(size=256, lines=8, width=3):
    y, x = np.mgrid[0:size, 0:size]
    on = ((x % (size // lines)) < width) | ((y % (size // lines)) < width)
    img = np.where(on[..., None], 0.95, 0.35) * np.ones(3)
    return (img * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------ glTF writer
class Glb:
    def __init__(self, generator_note):
        self.bin = bytearray()
        self.g = {"asset": {"version": "2.0", "generator": "displayxr-reference-scenes make_display_tests.py",
                            "copyright": "CC0-1.0 - The DisplayXR Project", "extras": {"note": generator_note}},
                  "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "materials": [],
                  "accessors": [], "bufferViews": [], "buffers": [], "textures": [], "images": [],
                  "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]}
        self.mat_cache = {}

    def _view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin += b"\x00"
        v = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target:
            v["target"] = target
        self.bin += data
        self.g["bufferViews"].append(v)
        return len(self.g["bufferViews"]) - 1

    def _acc(self, arr, typ, target):
        comp = 5125 if arr.dtype == np.uint32 else 5126
        a = {"bufferView": self._view(arr.tobytes(), target), "componentType": comp,
             "count": len(arr), "type": typ}
        if typ == "VEC3" and comp == 5126:
            a["min"] = arr.min(0).tolist()
            a["max"] = arr.max(0).tolist()
        self.g["accessors"].append(a)
        return len(self.g["accessors"]) - 1

    def texture(self, rgb):
        self.g["images"].append({"bufferView": self._view(png(rgb)), "mimeType": "image/png"})
        self.g["textures"].append({"sampler": 0, "source": len(self.g["images"]) - 1})
        return len(self.g["textures"]) - 1

    def material(self, name, color=(0.8, 0.8, 0.8), tex=None, emissive=None, rough=0.9, double=False):
        key = (name, color, tex, emissive, rough, double)
        if key in self.mat_cache:
            return self.mat_cache[key]
        pbr = {"baseColorFactor": list(color) + [1.0], "metallicFactor": 0.0, "roughnessFactor": rough}
        if tex is not None:
            pbr["baseColorTexture"] = {"index": tex}
        m = {"name": name, "pbrMetallicRoughness": pbr, "doubleSided": double}
        if emissive is not None:
            m["emissiveFactor"] = list(emissive)
            if tex is not None:   # a self-lit label: the text must stay in the emission
                m["emissiveTexture"] = {"index": tex}
        self.g["materials"].append(m)
        self.mat_cache[key] = len(self.g["materials"]) - 1
        return self.mat_cache[key]

    def mesh(self, name, pos, nrm, uv, idx, mat):
        prim = {"attributes": {"POSITION": self._acc(pos.astype(np.float32), "VEC3", 34962),
                               "NORMAL": self._acc(nrm.astype(np.float32), "VEC3", 34962),
                               "TEXCOORD_0": self._acc(uv.astype(np.float32), "VEC2", 34962)},
                "indices": self._acc(idx.astype(np.uint32).ravel(), "SCALAR", 34963), "material": mat}
        self.g["meshes"].append({"name": name, "primitives": [prim]})
        self.g["nodes"].append({"name": name, "mesh": len(self.g["meshes"]) - 1})
        self.g["scenes"][0]["nodes"].append(len(self.g["nodes"]) - 1)

    def write(self, path):
        for k in ("textures", "images"):
            if not self.g[k]:
                del self.g[k]
        if "textures" not in self.g:
            del self.g["samplers"]
        while len(self.bin) % 4:
            self.bin += b"\x00"
        self.g["buffers"] = [{"byteLength": len(self.bin)}]
        js = json.dumps(self.g, separators=(",", ":"), sort_keys=True).encode()
        js += b" " * ((4 - len(js) % 4) % 4)
        out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(self.bin))
        out += struct.pack("<II", len(js), 0x4E4F534A) + js
        out += struct.pack("<II", len(self.bin), 0x004E4942) + bytes(self.bin)
        Path(path).write_bytes(out)


def quad(center, u, v, uv_repeat=(1, 1)):
    """Rectangle spanning center +/- u/2, +/- v/2; normal = u x v."""
    c, u, v = (np.asarray(a, float) for a in (center, u, v))
    p = np.array([c - u / 2 - v / 2, c + u / 2 - v / 2, c + u / 2 + v / 2, c - u / 2 + v / 2])
    n = np.cross(u, v)
    n /= np.linalg.norm(n)
    ru, rv = uv_repeat
    t = np.array([[0, rv], [ru, rv], [ru, 0], [0, 0]], float)
    return p, np.tile(n, (4, 1)), t, np.array([[0, 1, 2], [0, 2, 3]])


def box(center, size):
    """Axis-aligned box as 6 outward quads."""
    c, s = np.asarray(center, float), np.asarray(size, float) / 2
    faces = []
    for ax in range(3):
        for sign in (1, -1):
            n = np.zeros(3); n[ax] = sign
            u = np.zeros(3); u[(ax + 1) % 3] = 2 * s[(ax + 1) % 3]
            v = np.zeros(3); v[(ax + 2) % 3] = 2 * s[(ax + 2) % 3]
            if sign < 0:
                u = -u
            faces.append(quad(c + n * s, u, v))
    return merge(faces)


def merge(parts):
    P, N, T, I, off = [], [], [], [], 0
    for p, n, t, i in parts:
        P.append(p); N.append(n); T.append(t); I.append(i + off); off += len(p)
    return np.concatenate(P), np.concatenate(N), np.concatenate(T), np.concatenate(I)


def frame(g, z=0.0, bar=0.02):
    """Thin border marking the ZDP frame (1.4 x 1.0): defines the scene's AABB."""
    m = g.material("frame", (0.9, 0.9, 0.9), rough=0.6)
    w, h = FRAME_W, FRAME_H
    parts = [box((0, h / 2 - bar / 2, z), (w, bar, bar)), box((0, -h / 2 + bar / 2, z), (w, bar, bar)),
             box((w / 2 - bar / 2, 0, z), (bar, h, bar)), box((-w / 2 + bar / 2, 0, z), (bar, h, bar))]
    g.mesh("zdp_frame", *merge(parts), m)


def depth_extent_guard(g, margin=0.0):
    """Invisible-in-practice slivers pinning the AABB depth to exactly +/-0.4 vH,
    so the AABB centre (which the viewer puts on the ZDP) is z = 0 whatever the
    scene's own content spans. `margin` widens it to cover content that pokes a
    little past +/-0.40 vH (a bar's thickness), keeping the extremes symmetric."""
    m = g.material("guard", (0.9, 0.9, 0.9), rough=0.6)   # the frame's own colour
    z = 0.40 * VH + margin
    parts = [box((-FRAME_W / 2 + 0.002, -FRAME_H / 2 + 0.002, s * (z - 0.002)), (0.004, 0.004, 0.004)) for s in (1, -1)]
    g.mesh("depth_guard", *merge(parts), m)


# ------------------------------------------------------------ scenes
def depth_ladder(out):
    g = Glb("Depth ladder: tile depths in display heights (vH); 1 vH = 1.25 units. See make_display_tests.py.")
    frame(g)
    depth_extent_guard(g)
    tw, th, gap = 0.40, 0.27, 0.05
    for k, d in enumerate(DEPTHS):
        r, c = divmod(k, 3)
        x = (c - 1) * (tw + gap)
        y = (1 - r) * (th + gap)
        mat = g.material(f"tile_{depth_text(d).strip()}", (1, 1, 1), tex=g.texture(tile_texture(depth_text(d))))
        g.mesh(f"tile_{depth_text(d).strip()}", *quad((x, y, d * VH), (tw, 0, 0), (0, th, 0)), mat)
    g.write(out / "depth_ladder.glb")


def window_box(out):
    g = Glb("Window box: opening = ZDP frame, back wall 0.40 vH behind. Lines must stay straight under head motion.")
    frame(g)
    depth_extent_guard(g)
    w, h, d = FRAME_W, FRAME_H, 0.40 * VH
    tex = g.texture(grid_texture())
    m = g.material("grid", (1, 1, 1), tex=tex, double=True)
    rep_w, rep_h, rep_d = w / 0.25, h / 0.25, d / 0.25
    parts = [quad((0, 0, -d), (w, 0, 0), (0, h, 0), (rep_w, rep_h)),               # back
             quad((0, -h / 2, -d / 2), (w, 0, 0), (0, 0, -d), (rep_w, rep_d)),     # floor
             quad((0, h / 2, -d / 2), (w, 0, 0), (0, 0, d), (rep_w, rep_d)),       # ceiling
             quad((-w / 2, 0, -d / 2), (0, 0, -d), (0, h, 0), (rep_d, rep_h)),     # left
             quad((w / 2, 0, -d / 2), (0, 0, d), (0, h, 0), (rep_d, rep_h))]       # right
    g.mesh("box_walls", *merge(parts), m)
    # one cube floating at +0.20 vH, one resting on the floor at -0.20 vH
    g.mesh("cube_front", *box((-0.3, 0.1, 0.20 * VH), (0.12, 0.12, 0.12)), g.material("red", (0.8, 0.15, 0.1), rough=0.5))
    g.mesh("cube_back", *box((0.3, -h / 2 + 0.06, -0.20 * VH), (0.12, 0.12, 0.12)), g.material("blue", (0.1, 0.25, 0.8), rough=0.5))
    g.write(out / "window_box.glb")


def edge_violation(out):
    g = Glb("Edge violation: bars cross the top/bottom frame edges; run with --vh 1.0 so those ARE the display edges.")
    frame(g)
    depth_extent_guard(g, margin=0.0151)   # bar half-thickness 0.01 + label offset
    n = len(DEPTHS)
    span = FRAME_W - 0.16
    for k, d in enumerate(DEPTHS):
        x = -span / 2 + span * k / (n - 1)
        hue = (0.85, 0.2, 0.15) if d > 0 else (0.2, 0.75, 0.25) if d < 0 else (0.85, 0.85, 0.85)
        m = g.material(f"bar_{depth_text(d).strip()}", hue, rough=0.5)
        # vertical bar spanning the full frame height: cut by BOTH edges
        g.mesh(f"bar_{depth_text(d).strip()}", *box((x, 0, d * VH), (0.06, FRAME_H - 0.002, 0.02)), m)
        lt = g.texture(tile_texture(depth_text(d), size=128, checks=1))
        g.mesh(f"label_{depth_text(d).strip()}", *quad((x, 0, d * VH + 0.0101), (0.15, 0, 0), (0, 0.15, 0)),
               g.material(f"label_{depth_text(d).strip()}", (1, 1, 1), tex=lt))
    g.write(out / "edge_violation.glb")


def crosstalk_bars(out):
    g = Glb("Crosstalk: white emissive bars over black; ghosting grows with |depth|, none at 0.00 vH.")
    depth_extent_guard(g)
    # black backdrop at the back of the volume: uniform, so its own disparity is invisible
    g.mesh("backdrop", *quad((0, 0, -0.40 * VH), (FRAME_W, 0, 0), (0, FRAME_H, 0)),
           g.material("black", (0.0, 0.0, 0.0), rough=1.0))
    n = len(DEPTHS)
    span = FRAME_W - 0.2
    white = g.material("emissive_white", (0.0, 0.0, 0.0), emissive=(1.0, 1.0, 1.0), rough=1.0)
    for k, d in enumerate(DEPTHS):
        x = -span / 2 + span * k / (n - 1)
        z = max(d * VH, -0.40 * VH + 0.01)
        g.mesh(f"bar_{depth_text(d).strip()}", *quad((x, 0.08, z), (0.012, 0, 0), (0, 0.7, 0)), white)
        lt = g.texture(tile_texture(depth_text(d), size=128, checks=1))
        g.mesh(f"label_{depth_text(d).strip()}", *quad((x, -0.4, z), (0.15, 0, 0), (0, 0.15, 0)),
               g.material(f"label_{depth_text(d).strip()}", (0.0, 0.0, 0.0), tex=lt, emissive=(1.0, 1.0, 1.0)))
    g.write(out / "crosstalk_bars.glb")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for f in (depth_ladder, window_box, edge_violation, crosstalk_bars):
        f(out)
        print("wrote", out / (f.__name__ + ".glb"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
