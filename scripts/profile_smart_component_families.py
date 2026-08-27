#!/usr/bin/env python3
"""Profile Glyphs variable export time by smart-component dependency family.

All test packages are built in a temporary directory. The source packages are
read-only. Results and export logs are written incrementally to a timestamped
directory under ``profiling_results`` so an interrupted run remains useful.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "sources" / "MayfairGlyphs4.glyphspackage"
DEFAULT_METADATA = ROOT / "sources" / "MayfairAonly.glyphspackage"
NAME_PATTERN = re.compile(r"^glyphname = (.+);$", re.MULTILINE)
REFERENCE_PATTERN = re.compile(r"^ref = (.+);$", re.MULTILINE)
SMART_AXES_PATTERN = re.compile(r"^partsSettings = \($", re.MULTILINE)
ERROR_PATTERN = re.compile(r"(?:\[\d+\]\s+Error:|Failed exporting instance|Traceback)")


def decode_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    return value


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return slug[:100] or "unnamed"


def read_glyph_records(source: Path) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for glyph_path in sorted((source / "glyphs").glob("*.glyph")):
        text = glyph_path.read_text(encoding="utf-8")
        name_match = NAME_PATTERN.search(text)
        if name_match is None:
            raise RuntimeError(f"Could not determine glyph name for {glyph_path}")
        glyph_name = decode_value(name_match.group(1))
        if glyph_name in records:
            raise RuntimeError(f"Duplicate glyph name: {glyph_name}")
        records[glyph_name] = {
            "path": glyph_path,
            "references": {
                decode_value(match.group(1))
                for match in REFERENCE_PATTERN.finditer(text)
            },
            "smart_base": SMART_AXES_PATTERN.search(text) is not None,
        }
    return records


def smart_dependencies(
    records: dict[str, dict[str, object]],
) -> tuple[set[str], dict[str, frozenset[str]]]:
    smart_bases = {
        name for name, record in records.items() if bool(record["smart_base"])
    }
    dependencies: dict[str, set[str]] = {
        name: {name} if name in smart_bases else set() for name in records
    }

    changed = True
    while changed:
        changed = False
        for glyph_name, record in records.items():
            combined = set(dependencies[glyph_name])
            for reference in record["references"]:  # type: ignore[union-attr]
                combined.update(dependencies.get(reference, ()))
            if combined != dependencies[glyph_name]:
                dependencies[glyph_name] = combined
                changed = True

    return smart_bases, {
        name: frozenset(values) for name, values in dependencies.items()
    }


class UnionFind:
    def __init__(self, items: set[str]):
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, first: str, second: str) -> None:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


def smart_families(
    smart_bases: set[str], dependencies: dict[str, frozenset[str]]
) -> list[set[str]]:
    union_find = UnionFind(smart_bases)
    for values in dependencies.values():
        ordered = sorted(values)
        for other in ordered[1:]:
            union_find.union(ordered[0], other)

    grouped: dict[str, set[str]] = {}
    for smart_base in smart_bases:
        grouped.setdefault(union_find.find(smart_base), set()).add(smart_base)
    return sorted(grouped.values(), key=lambda family: (-len(family), sorted(family)))


def filter_order(source_order: Path, destination_order: Path, selected: set[str]) -> None:
    output: list[str] = []
    for line in source_order.read_text(encoding="utf-8").splitlines(keepends=True):
        token = line.strip().rstrip(",")
        if token in ("(", ")") or decode_value(token) in selected:
            output.append(line)
    destination_order.write_text("".join(output), encoding="utf-8")


def link_or_copy(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def build_test_package(
    package_path: Path,
    metadata_source: Path,
    source: Path,
    records: dict[str, dict[str, object]],
    selected: set[str],
) -> None:
    if package_path.exists():
        shutil.rmtree(package_path)
    shutil.copytree(metadata_source, package_path)
    shutil.rmtree(package_path / "glyphs")
    (package_path / "glyphs").mkdir()

    for glyph_name in selected:
        record = records[glyph_name]
        glyph_path = record["path"]
        link_or_copy(glyph_path, package_path / "glyphs" / glyph_path.name)  # type: ignore[union-attr]
    filter_order(source / "order.plist", package_path / "order.plist", selected)


def font_file_from_output(output_directory: Path) -> Path | None:
    candidates = sorted(
        list(output_directory.glob("*.ttf")) + list(output_directory.glob("*.otf")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


class Profiler:
    def __init__(
        self,
        args: argparse.Namespace,
        records: dict[str, dict[str, object]],
        dependencies: dict[str, frozenset[str]],
        results_directory: Path,
        temporary_directory: Path,
    ):
        self.args = args
        self.records = records
        self.dependencies = dependencies
        self.results_directory = results_directory
        self.logs_directory = results_directory / "logs"
        self.logs_directory.mkdir(parents=True)
        self.package_path = temporary_directory / "MayfairProfile.glyphspackage"
        self.output_directory = temporary_directory / "output"
        self.output_directory.mkdir()
        self.csv_path = results_directory / "timings.csv"
        self.rows: list[dict[str, object]] = []
        self.run_number = 0
        with self.csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames())
            writer.writeheader()

    @staticmethod
    def fieldnames() -> list[str]:
        return [
            "run_number",
            "kind",
            "target",
            "repeat",
            "glyph_count",
            "smart_base_count",
            "elapsed_seconds",
            "status",
            "font_size",
            "log_file",
        ]

    def run(
        self,
        kind: str,
        target: str,
        repeat: int,
        selected: set[str],
        smart_base_count: int,
    ) -> dict[str, object]:
        self.run_number += 1
        print(
            f"[{self.run_number}] {kind}: {target} "
            f"({len(selected)} glyphs, {smart_base_count} smart bases)",
            flush=True,
        )
        build_test_package(
            self.package_path,
            self.args.metadata,
            self.args.source,
            self.records,
            selected,
        )
        for font_path in self.output_directory.glob("*"):
            if font_path.is_file():
                font_path.unlink()

        command = [
            self.args.glyphs,
            "export",
            "--app",
            self.args.app,
            "--plugins",
            "",
            "--format",
            "tt",
            "--output",
            str(self.output_directory),
            str(self.package_path),
            "--quiet",
        ]
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=self.args.timeout,
        )
        elapsed = time.perf_counter() - started
        output = completed.stdout or ""
        failed = completed.returncode != 0 or ERROR_PATTERN.search(output) is not None
        status = "failed" if failed else "ok"
        font_path = font_file_from_output(self.output_directory)
        font_size = font_path.stat().st_size if font_path is not None else ""
        log_name = f"{self.run_number:03d}_{kind}_{safe_slug(target)}_r{repeat}.log"
        (self.logs_directory / log_name).write_text(
            "$ " + " ".join(command) + "\n\n" + output,
            encoding="utf-8",
        )
        row: dict[str, object] = {
            "run_number": self.run_number,
            "kind": kind,
            "target": target,
            "repeat": repeat,
            "glyph_count": len(selected),
            "smart_base_count": smart_base_count,
            "elapsed_seconds": round(elapsed, 3),
            "status": status,
            "font_size": font_size,
            "log_file": str(Path("logs") / log_name),
        }
        self.rows.append(row)
        with self.csv_path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames())
            writer.writerow(row)
        print(f"    {elapsed:.3f} seconds, {status}", flush=True)
        return row


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--app", default="4.0.1")
    parser.add_argument("--glyphs", default=shutil.which("glyphs") or "glyphs")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--top", type=int, default=5, help="Slowest bases to repeat")
    parser.add_argument("--analyze-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.source = args.source.resolve()
    args.metadata = args.metadata.resolve()
    for path in (args.source, args.metadata):
        if not path.is_dir():
            raise SystemExit(f"Package not found: {path}")

    records = read_glyph_records(args.source)
    smart_bases, dependencies = smart_dependencies(records)
    families = smart_families(smart_bases, dependencies)
    no_smart = {name for name, values in dependencies.items() if not values}
    smart_closure = set(records) - no_smart

    print(f"Source glyphs: {len(records)}")
    print(f"Smart-component bases: {len(smart_bases)}")
    print(f"Smart dependency closure: {len(smart_closure)}")
    print(f"Independent smart families: {len(families)}")
    print("Family sizes (bases): " + ", ".join(str(len(family)) for family in families))
    if args.analyze_only:
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results_directory = ROOT / "profiling_results" / f"smart-components-{timestamp}"
    results_directory.mkdir(parents=True)
    analysis = {
        "source": str(args.source),
        "metadata": str(args.metadata),
        "sourceGlyphCount": len(records),
        "smartBaseCount": len(smart_bases),
        "smartClosureCount": len(smart_closure),
        "families": [sorted(family) for family in families],
    }
    (results_directory / "analysis.json").write_text(
        json.dumps(analysis, indent=2) + "\n", encoding="utf-8"
    )

    with tempfile.TemporaryDirectory(prefix="mayfair-smart-profile-") as temporary:
        profiler = Profiler(
            args,
            records,
            dependencies,
            results_directory,
            Path(temporary),
        )
        all_glyphs = set(records)
        profiler.run("control", "no_smart", 1, no_smart, 0)
        profiler.run("control", "no_smart", 2, no_smart, 0)
        profiler.run("control", "all_glyphs", 1, all_glyphs, len(smart_bases))

        for index, family in enumerate(families, 1):
            if len(family) == 1:
                continue
            family_glyphs = {
                name
                for name, values in dependencies.items()
                if values and values.issubset(family)
            }
            label = f"family_{index:02d}_" + "+".join(sorted(family))
            profiler.run(
                "family",
                label,
                1,
                no_smart | family_glyphs,
                len(family),
            )

        base_rows = []
        for smart_base in sorted(smart_bases):
            exclusive_glyphs = {
                name
                for name, values in dependencies.items()
                if values == frozenset((smart_base,))
            }
            row = profiler.run(
                "base",
                smart_base,
                1,
                no_smart | exclusive_glyphs,
                1,
            )
            base_rows.append((smart_base, exclusive_glyphs, row))

        successful = [
            item for item in base_rows if item[2]["status"] == "ok"
        ]
        successful.sort(
            key=lambda item: float(item[2]["elapsed_seconds"]), reverse=True
        )
        for smart_base, exclusive_glyphs, _row in successful[: args.top]:
            for repeat in (2, 3):
                profiler.run(
                    "base_repeat",
                    smart_base,
                    repeat,
                    no_smart | exclusive_glyphs,
                    1,
                )

        summary: dict[str, object] = dict(analysis)
        summary["runs"] = profiler.rows
        grouped: dict[str, list[float]] = {}
        for row in profiler.rows:
            if row["status"] != "ok":
                continue
            key = f"{row['kind']}:{row['target']}"
            grouped.setdefault(key, []).append(float(row["elapsed_seconds"]))
        summary["medians"] = {
            key: round(median(values), 3) for key, values in grouped.items()
        }
        (results_directory / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )

    print(f"Results: {results_directory}")


if __name__ == "__main__":
    main()
