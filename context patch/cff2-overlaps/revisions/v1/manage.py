#!/usr/bin/env python3
"""Install/undo the CFF2 overlap patch, preserving existing local ConTeXt changes."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
STATE = PACKAGE / "active-install.json"
SOURCE_FILES = ("font-cff.lmt", "font-shp.lmt")
SUPPORT_FILES = ("font-cff-overlaps.lua", "font-cff-overlaps.py", "font-cff-overlaps-config.json")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def format_directory(tree):
    matches = list((tree / "texmf-cache").glob("luametatex-cache/context/*/formats/luametatex/cont-en.fmt"))
    require(len(matches) == 1, "Expected one English LuaMetaTeX format in this tree's texmf-cache.")
    return matches[0].parent


def restore(manifest):
    for entry in reversed(manifest["files"]):
        dest = Path(entry["path"])
        if entry["backup"] is None:
            if dest.exists():
                dest.unlink()
        else:
            shutil.copy2(entry["backup"], dest)


def record_new_formats(manifest, fmtdir):
    known = {entry["path"] for entry in manifest["files"]}
    for path in sorted(fmtdir.glob("cont-en.*")):
        if path.is_file() and str(path) not in known:
            manifest["files"].append({"path": str(path), "backup": None, "before_sha256": None})


def snapshot_after(manifest):
    for entry in manifest["files"]:
        path = Path(entry["path"])
        entry["after_sha256"] = digest(path) if path.exists() else None


def apply(args):
    require(not STATE.exists(), "An installation is already recorded. Run status or undo first.")
    tree = args.context_tree.resolve()
    base = tree / "texmf-context/tex/context/base/mkxl"
    python = args.python.absolute()
    require(python.is_file(), f"Python interpreter missing: {python}")
    subprocess.run([str(python), "-c", "import pathops; print('pathops', pathops.__version__)"], check=True)
    for name in SOURCE_FILES:
        require(digest(base / name) == digest(PACKAGE / "original" / name),
                f"Baseline mismatch: {base / name}. Refusing to overwrite local changes.")
    for name in SUPPORT_FILES:
        require(not (base / name).exists(), f"Support file already exists: {base / name}")
    for name in SOURCE_FILES:
        require((PACKAGE / "patched" / name).is_file(), f"Patched source missing: {name}")
    for name in SUPPORT_FILES[:2]:
        require((PACKAGE / name).is_file(), f"Support file missing: {name}")
    fmtdir = format_directory(tree)
    executable = tree / "texmf-osx-arm64/bin/context"
    require(executable.is_file(), f"Context executable missing: {executable}")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = PACKAGE / "backups" / stamp
    backup.mkdir(parents=True)
    manifest = {"context_tree": str(tree), "backup": str(backup), "files": [],
                "python": str(python), "status": "applying"}
    paths = [base / n for n in SOURCE_FILES + SUPPORT_FILES]
    paths += sorted(fmtdir.glob("cont-en.*"))
    for index, path in enumerate(paths):
        entry = {"path": str(path), "backup": None, "before_sha256": None}
        if path.exists():
            copy = backup / f"{index:02d}-{path.name}"
            shutil.copy2(path, copy)
            entry.update(backup=str(copy), before_sha256=digest(copy))
        manifest["files"].append(entry)
    save_json(STATE, manifest)
    try:
        for name in SOURCE_FILES:
            shutil.copy2(PACKAGE / "patched" / name, base / name)
        for name in SUPPORT_FILES[:2]:
            shutil.copy2(PACKAGE / name, base / name)
        save_json(base / SUPPORT_FILES[2], {"python": str(python)})
        env = dict(os.environ)
        env["PATH"] = str(executable.parent) + os.pathsep + env.get("PATH", "")
        formatfile = fmtdir / "cont-en.fmt"
        before_format = (formatfile.stat().st_mtime_ns, digest(formatfile))
        try:
            with (backup / "format-build.log").open("w") as log:
                subprocess.run([str(executable), "--make", "en"], cwd=backup, env=env,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
        finally:
            # Failed format builds can create new companions too.
            record_new_formats(manifest, fmtdir)
        require(formatfile.is_file(), "English format build did not produce the expected format.")
        require((formatfile.stat().st_mtime_ns, digest(formatfile)) != before_format,
                "Format build did not update this tree's expected English format; refusing an inactive patch.")
        snapshot_after(manifest)
        manifest["status"] = "applied"
        save_json(STATE, manifest)
        save_json(backup / "manifest.json", manifest)
    except BaseException:
        record_new_formats(manifest, fmtdir)
        snapshot_after(manifest)
        manifest["status"] = "rollback-incomplete"
        save_json(STATE, manifest)
        save_json(backup / "manifest.json", manifest)
        restore(manifest)
        manifest["status"] = "rolled-back-after-error"
        save_json(backup / "manifest.json", manifest)
        STATE.unlink()
        raise
    print(f"Applied CFF2 overlap conversion only. Backup: {backup}")
    print(f'Undo: python3 "{PACKAGE / "manage.py"}" undo')


def undo(args):
    require(STATE.exists(), "No active installation is recorded.")
    manifest = json.loads(STATE.read_text())
    allowed = ("applied", "undoing", "undo-incomplete", "rollback-incomplete")
    require(manifest["status"] in allowed, "Incomplete installation recorded; inspect its backup before recovery.")
    recovering = manifest["status"] != "applied"
    for entry in manifest["files"]:
        path = Path(entry["path"])
        # A rebuilt format can represent unrelated later changes: do not overwrite it.
        current = digest(path) if path.exists() else None
        expected = {entry["after_sha256"]}
        if recovering:
            expected.add(entry["before_sha256"])
        require(current in expected, f"Changed since application: {path}. Refusing to overwrite it.")
        if entry["backup"]:
            require(digest(entry["backup"]) == entry["before_sha256"], f"Backup checksum mismatch: {entry['backup']}")
    manifest["status"] = "undoing"
    save_json(STATE, manifest)
    try:
        restore(manifest)
    except BaseException:
        manifest["status"] = "undo-incomplete"
        save_json(STATE, manifest)
        save_json(Path(manifest["backup"]) / "manifest.json", manifest)
        raise
    manifest["status"] = "undone"
    save_json(Path(manifest["backup"]) / "manifest.json", manifest)
    STATE.unlink()
    print("Restored the exact previous source files and English format; removed the patch's support files.")


def status(args):
    if not STATE.exists():
        print("Not applied (no active installation record).")
        return
    manifest = json.loads(STATE.read_text())
    print(f"Status: {manifest['status']}\nTree: {manifest['context_tree']}\nBackup: {manifest['backup']}")
    for entry in manifest["files"]:
        path = Path(entry["path"])
        current = digest(path) if path.exists() else None
        print(f"{'matches' if current == entry.get('after_sha256') else 'CHANGED'}: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("apply", "undo", "status"))
    parser.add_argument("--context-tree", type=Path, default=Path("/Users/juliusross/context/tex"))
    parser.add_argument("--python", type=Path, default=PACKAGE.parents[1] / "sources/venv/bin/python")
    args = parser.parse_args()
    try:
        {"apply": apply, "undo": undo, "status": status}[args.command](args)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
