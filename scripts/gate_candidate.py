#!/usr/bin/env python3
"""Fail-closed static release gate for Westcott scene candidates.

This does NOT verify external source truth, voice naturalness, or user approval.
It binds the source receipt to the exact draft bytes and runs the canonical
static scene validator. Only submissions routed through this script are gated.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS = ROOT / "automation" / "submissions"
VALIDATOR = ROOT / "skills" / "p004-chat-suite" / "scene-orchestrator" / "tools" / "validate_scene.py"
REQUIRED_SOURCES = ("github_rules", "google_docs", "notion_corrections", "identity_roster")
SCENES = {"morning", "afternoon", "evening", "general"}


def check_one(manifest_path: Path) -> list[str]:
    errors = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{manifest_path}: missing/invalid manifest: {exc}"]

    draft = manifest_path.parent / "draft.txt"
    if not draft.is_file():
        return [f"{manifest_path}: draft.txt is missing"]
    draft_bytes = draft.read_bytes()
    if not draft_bytes.strip():
        errors.append("draft.txt is empty")
    digest = hashlib.sha256(draft_bytes).hexdigest()
    if manifest.get("draft_sha256") != digest:
        errors.append("draft_sha256 mismatch: receipt is not bound to this exact text")

    if manifest.get("task_mode") != "WESTCOTT_SCENE":
        errors.append("task_mode must be WESTCOTT_SCENE")
    scene = manifest.get("scene")
    if scene not in SCENES:
        errors.append(f"invalid/missing scene: {scene!r}")
    if manifest.get("release_status") != "CANDIDATE":
        errors.append("release_status must be CANDIDATE; this script cannot authorize publication")
    if not isinstance(manifest.get("activity"), bool):
        errors.append("activity must be a boolean")
    sources = manifest.get("source_receipts")
    if not isinstance(sources, dict):
        sources = {}
        errors.append("source_receipts must be a map")
    for key in REQUIRED_SOURCES:
        src = sources.get(key)
        if not isinstance(src, dict) or src.get("status") != "READ" or not src.get("reference"):
            errors.append(f"source_receipts.{key} needs READ and a nonempty reference")
    if not isinstance(manifest.get("story_date"), str) or len(manifest["story_date"]) != 10:
        errors.append("story_date must be YYYY-MM-DD")

    # Run canonical static checks for every scene; do not silently drop --scene.
    if scene in SCENES and draft_bytes.strip():
        cmd = [sys.executable, str(VALIDATOR), str(draft), "--scene", scene, "--json"]
        if manifest.get("activity") is True:
            cmd.append("--activity")
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        try:
            report = json.loads(result.stdout)
            for issue in report.get("issues", []):
                if issue.get("severity") == "blocker":
                    errors.append(f"static blocker {issue['code']}: {issue['detail']}")
            if result.returncode and not any(x.startswith("static blocker") for x in errors):
                errors.append(f"static validator returned {result.returncode}")
        except ValueError:
            errors.append(f"static validator could not run: {result.stderr[:400]}")

    return [f"{manifest_path.relative_to(ROOT)}: {x}" for x in errors]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true", help="scan all candidate bundles")
    parser.add_argument("--manifest", type=Path, help="check one JSON manifest")
    args = parser.parse_args()
    if args.check_all == bool(args.manifest):
        parser.error("select exactly one of --check-all or --manifest")
    if args.check_all:
        manifests = sorted(SUBMISSIONS.glob("*/manifest.json")) if SUBMISSIONS.is_dir() else []
    else:
        manifests = [args.manifest.resolve()]
    errors = []
    for path in manifests:
        errors.extend(check_one(path))
    if errors:
        for item in errors:
            print("FAIL:", item)
        return 2
    print(f"STATIC_GATE_PASS: {len(manifests)} bundle(s); external facts/voice/user approval NOT VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
