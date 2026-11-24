#!/usr/bin/env python3
"""Install or restore the Somerville LuaMetaTeX sized-operator SSTY patch."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


SOURCE_ROOT = Path("tex/texmf-context/source/luametatex")
SOURCE_FILES = tuple(Path("source/tex") / name for name in ("texfont.c", "texfont.h", "texmlist.c"))
ENGINE = Path("tex/texmf-osx-arm64/bin/luametatex")
FILES = tuple(SOURCE_ROOT / file for file in SOURCE_FILES) + (ENGINE,)
PATCH = Path(__file__).resolve().with_name("context-sized-operator-ssty.patch")


def same_files(left, right):
    return all((left / file).read_bytes() == (right / file).read_bytes() for file in FILES)


def snapshot(context, state, staged_source, staged_engine):
    with tempfile.TemporaryDirectory(dir=context, prefix=".ssty-backup-") as saving:
        bundle = Path(saving) / "snapshot"
        check = Path(saving) / "check"
        for file in FILES:
            original = bundle / "original" / file
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(context / file, original)
        for file in SOURCE_FILES:
            (check / file).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundle / "original" / SOURCE_ROOT / file, check / file)
        subprocess.run(["patch", "--batch", "-p1", "-i", str(PATCH)], cwd=check, check=True)
        for file in SOURCE_FILES:
            if (check / file).read_bytes() != (staged_source / file).read_bytes():
                raise ValueError(f"Staged source does not match the patch: {file}")
        if not os.access(staged_engine, os.X_OK):
            raise ValueError(f"Staged engine is not executable: {staged_engine}")
        for file in FILES:
            patched = bundle / "patched" / file
            patched.parent.mkdir(parents=True, exist_ok=True)
            candidate = staged_engine if file == ENGINE else check / file.relative_to(SOURCE_ROOT)
            shutil.copy2(candidate, patched)
        bundle.rename(state)


def replace_file(source, target):
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        candidate = Path(temporary) / target.name
        shutil.copy2(source, candidate)
        os.replace(candidate, target)


def install_files(context, before, after):
    changed = []
    try:
        for file in FILES:
            if (context / file).read_bytes() != (before / file).read_bytes():
                raise ValueError(f"File changed during installation: {context / file}")
            changed.append(file)
            replace_file(after / file, context / file)
    except BaseException:
        for file in reversed(changed):
            replace_file(before / file, context / file)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("apply", "undo", "status"))
    parser.add_argument("--context", type=Path, default=Path.home() / "context")
    parser.add_argument("--staged-source", type=Path)
    parser.add_argument("--staged-engine", type=Path)
    args = parser.parse_args()
    context = args.context.expanduser().resolve()
    state = context / ".somerville-sized-operator-ssty"
    if not state.exists():
        if args.action != "apply":
            parser.exit(message=f"No patch backup found at {state}\n")
        if not args.staged_source or not args.staged_engine:
            parser.error("First apply requires --staged-source and --staged-engine.")
        snapshot(context, state, args.staged_source.resolve(), args.staged_engine.resolve())

    original = state / "original"
    patched = state / "patched"
    if same_files(context, original):
        status = "undone"
    elif same_files(context, patched):
        status = "applied"
    else:
        parser.exit(1, f"Live files differ from both saved versions. Backups are at {state}\n")

    if args.action == "apply" and status == "undone":
        install_files(context, original, patched)
        status = "applied"
    elif args.action == "undo" and status == "applied":
        install_files(context, patched, original)
        status = "undone"
    print(f"Sized-operator SSTY patch {status}. Backups: {state}")


if __name__ == "__main__":
    main()
