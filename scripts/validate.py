#!/usr/bin/env python3
# Copyright 2026, The DisplayXR Project and its contributors
# SPDX-License-Identifier: Apache-2.0
"""Validate scene manifests and index files. Exit 1 on any problem.

Rules (they are what keep the licensing honest):
  * every scenes/<id>/scene.json has id == folder, a status, a licence block
    whose `file` (or every entry of `files`) exists, and either a source pinned
    to a commit, a list of sources each pinned to a commit, or (for content
    generated HERE) a `generator` script that exists in this repository;
  * a redistributed third-party scene has a NOTICE.md;
  * files a scene lists exist; packs are NOT committed (release assets only);
  * index files pin a commit, are marked redistributed:false, and every entry
    carries a licence; nothing from an index is committed here.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []
def err(msg): errors.append(msg)

for sj in sorted((ROOT / "scenes").glob("*/scene.json")):
    d = json.loads(sj.read_text())
    sid = sj.parent.name
    where = f"scenes/{sid}"
    if d.get("id") != sid: err(f"{where}: id '{d.get('id')}' != folder")
    if d.get("status") not in ("available", "planned"): err(f"{where}: status must be available|planned")
    if not (sj.parent / "README.md").exists(): err(f"{where}: missing README.md")
    if d.get("status") == "planned":
        if not d.get("sources") and not d.get("source"): err(f"{where}: planned scene must name its sources")
        continue
    lic = d.get("license") or {}
    lic_files = lic.get("files") or ([lic["file"]] if lic.get("file") else [])
    if not lic.get("spdx") or not lic_files: err(f"{where}: license.spdx and license.file(s) required")
    for f in lic_files:
        if not (ROOT / f).exists(): err(f"{where}: license file {f} missing")
    srcs = d.get("sources") or [d.get("source") or {}]
    for src in srcs:
        if src.get("generator"):
            if "displayxr-reference-scenes" not in src.get("repo", ""):
                err(f"{where}: a generator source must be this repository")
            elif not (ROOT / src["generator"]).exists():
                err(f"{where}: generator {src['generator']} missing")
        elif len(src.get("commit", "")) != 40:
            err(f"{where}: source {src.get('repo', '?')} must be pinned to a full 40-char commit")
    src = srcs[0]
    third_party = not lic.get("spdx", "").startswith("CC0") or "displayxr" not in src.get("repo", "").lower()
    if d.get("redistributed") and third_party and not (sj.parent / "NOTICE.md").exists():
        err(f"{where}: redistributed third-party scene needs NOTICE.md")
    for f in d.get("files", []):
        if not (sj.parent / f).exists(): err(f"{where}: listed file {f} missing")
    for p in d.get("packs", []):
        if list(ROOT.rglob(p["file"])): err(f"{where}: pack {p['file']} is committed (packs are release assets)")

for ix in sorted((ROOT / "index").glob("*.json")):
    d = json.loads(ix.read_text())
    where = f"index/{ix.name}"
    if len(d.get("commit", "")) != 40: err(f"{where}: commit must be a full 40-char sha")
    if d.get("redistributed") is not False: err(f"{where}: must declare redistributed: false")
    for m in d.get("models", []):
        if not m.get("licenses"): err(f"{where}: {m.get('name')} has no licence")
        name = m.get("name", "")
        hits = [p for p in ROOT.rglob(f"{name}.*") if p.suffix in (".glb", ".gltf", ".bin")]
        if hits: err(f"{where}: {name} is index-only but committed at {hits[0].relative_to(ROOT)}")

if errors:
    print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
print(f"ok: {len(list((ROOT/'scenes').glob('*/scene.json')))} scenes, "
      f"{len(list((ROOT/'index').glob('*.json')))} index file(s)")
