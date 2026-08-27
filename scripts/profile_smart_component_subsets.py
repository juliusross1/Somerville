#!/usr/bin/env python3
"""Profile dependency-complete subsets of the expensive smart-component families.

The arrow family is tested exhaustively. The larger math family is explored
with all pairs plus forward-addition and backward-elimination searches. Every
temporary package contains all glyphs with no smart dependencies and only the
glyphs whose complete smart-base dependency set fits inside the tested subset.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import itertools
import json
from pathlib import Path
import random
import shutil
import tempfile

from profile_smart_component_families import (
    DEFAULT_METADATA,
    DEFAULT_SOURCE,
    Profiler,
    read_glyph_records,
    smart_dependencies,
    smart_families,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEEDS = ("_smart.integral", "_smart.Arrow.mid")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--app", default="4.0.1")
    parser.add_argument("--glyphs", default=shutil.which("glyphs") or "glyphs")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--seed", action="append", dest="seeds")
    parser.add_argument("--checkpoint-every", type=int, default=40)
    parser.add_argument("--repeat-top", type=int, default=8)
    parser.add_argument("--random-seed", type=int, default=20260827)
    parser.add_argument("--analyze-only", action="store_true")
    return parser.parse_args()


def family_for_seed(families: list[set[str]], seed: str) -> set[str]:
    for family in families:
        if seed in family:
            return family
    raise RuntimeError(f"No smart-component family contains {seed}")


def subset_label(family_label: str, subset: frozenset[str]) -> str:
    return family_label + "__" + "+".join(sorted(subset))


class SubsetRunner:
    def __init__(
        self,
        profiler: Profiler,
        dependencies: dict[str, frozenset[str]],
        no_smart: set[str],
        checkpoint_every: int,
    ):
        self.profiler = profiler
        self.dependencies = dependencies
        self.no_smart = no_smart
        self.checkpoint_every = checkpoint_every
        self.cache: dict[tuple[str, frozenset[str]], dict[str, object]] = {}
        self.subset_rows: list[dict[str, object]] = []
        self.subset_run_count = 0
        self.checkpoint_count = 0

    def selected_glyphs(self, subset: frozenset[str]) -> set[str]:
        return self.no_smart | {
            name
            for name, values in self.dependencies.items()
            if values and values.issubset(subset)
        }

    def checkpoint(self) -> None:
        self.checkpoint_count += 1
        self.profiler.run(
            "checkpoint",
            f"no_smart_{self.checkpoint_count:02d}",
            1,
            self.no_smart,
            0,
        )

    def run_subset(
        self,
        family_label: str,
        subset: frozenset[str],
        search: str,
        force: bool = False,
        repeat: int = 1,
    ) -> dict[str, object]:
        key = (family_label, subset)
        if not force and key in self.cache:
            return self.cache[key]
        if (
            self.subset_run_count
            and self.subset_run_count % self.checkpoint_every == 0
        ):
            self.checkpoint()
        row = self.profiler.run(
            search,
            subset_label(family_label, subset),
            repeat,
            self.selected_glyphs(subset),
            len(subset),
        )
        row["family_label"] = family_label
        row["subset"] = sorted(subset)
        self.subset_rows.append(row)
        self.subset_run_count += 1
        if not force:
            self.cache[key] = row
        return row


def elapsed(row: dict[str, object]) -> float:
    if row["status"] != "ok":
        return float("-inf")
    return float(row["elapsed_seconds"])


def run_exhaustive(
    runner: SubsetRunner,
    family_label: str,
    family: set[str],
    randomizer: random.Random,
) -> None:
    subsets = []
    ordered = sorted(family)
    for size in range(1, len(ordered)):
        subsets.extend(frozenset(values) for values in itertools.combinations(ordered, size))
    randomizer.shuffle(subsets)
    for subset in subsets:
        runner.run_subset(family_label, subset, "exhaustive")


def run_all_pairs(
    runner: SubsetRunner,
    family_label: str,
    family: set[str],
    randomizer: random.Random,
) -> None:
    subsets = [
        frozenset(values) for values in itertools.combinations(sorted(family), 2)
    ]
    randomizer.shuffle(subsets)
    for subset in subsets:
        runner.run_subset(family_label, subset, "pair")


def run_forward_search(
    runner: SubsetRunner, family_label: str, family: set[str]
) -> list[dict[str, object]]:
    current = frozenset()
    path = []
    while current != frozenset(family):
        candidates = []
        for smart_base in sorted(family - set(current)):
            subset = current | frozenset((smart_base,))
            row = runner.run_subset(family_label, subset, "forward")
            candidates.append((elapsed(row), smart_base, subset, row))
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        _score, chosen_base, current, chosen_row = candidates[0]
        path.append(
            {
                "added": chosen_base,
                "subset": sorted(current),
                "elapsed_seconds": chosen_row["elapsed_seconds"],
            }
        )
        print(f"FORWARD chose {chosen_base}: {chosen_row['elapsed_seconds']} seconds")
    return path


def run_backward_search(
    runner: SubsetRunner, family_label: str, family: set[str]
) -> list[dict[str, object]]:
    current = frozenset(family)
    path = []
    while current:
        candidates = []
        for smart_base in sorted(current):
            subset = current - frozenset((smart_base,))
            if subset:
                row = runner.run_subset(family_label, subset, "backward")
            else:
                row = {
                    "elapsed_seconds": 0.0,
                    "status": "ok",
                }
            candidates.append((elapsed(row), smart_base, subset, row))
        candidates.sort(key=lambda item: (item[0], item[1]))
        _score, removed_base, current, chosen_row = candidates[0]
        path.append(
            {
                "removed": removed_base,
                "subset": sorted(current),
                "elapsed_seconds": chosen_row["elapsed_seconds"],
            }
        )
        print(f"BACKWARD removed {removed_base}: {chosen_row['elapsed_seconds']} seconds")
    return path


def append_subset_metadata_csv(results_directory: Path, rows: list[dict[str, object]]) -> None:
    path = results_directory / "subsets.csv"
    fieldnames = [
        "run_number",
        "family_label",
        "kind",
        "repeat",
        "smart_base_count",
        "glyph_count",
        "elapsed_seconds",
        "status",
        "subset",
        "log_file",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: "+".join(row[key]) if key == "subset" else row.get(key, "")
                    for key in fieldnames
                }
            )


def main() -> None:
    args = parse_args()
    args.source = args.source.resolve()
    args.metadata = args.metadata.resolve()
    records = read_glyph_records(args.source)
    smart_bases, dependencies = smart_dependencies(records)
    families = smart_families(smart_bases, dependencies)
    no_smart = {name for name, values in dependencies.items() if not values}
    seeds = args.seeds or list(DEFAULT_SEEDS)
    selected_families = []
    seen = set()
    for seed in seeds:
        family = family_for_seed(families, seed)
        key = frozenset(family)
        if key in seen:
            continue
        seen.add(key)
        selected_families.append((seed, family))

    print(f"Source glyphs: {len(records)}")
    print(f"No-smart baseline glyphs: {len(no_smart)}")
    for seed, family in selected_families:
        print(f"Selected family {seed}: {len(family)} bases")
        print("  " + ", ".join(sorted(family)))
    if args.analyze_only:
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results_directory = ROOT / "profiling_results" / f"smart-subsets-{timestamp}"
    results_directory.mkdir(parents=True)
    randomizer = random.Random(args.random_seed)
    search_paths: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="mayfair-smart-subsets-") as temporary:
        profiler = Profiler(
            args,
            records,
            dependencies,
            results_directory,
            Path(temporary),
        )
        runner = SubsetRunner(
            profiler, dependencies, no_smart, args.checkpoint_every
        )
        runner.checkpoint()

        for seed, family in selected_families:
            family_label = "arrow" if "Arrow" in seed else "math"
            full = frozenset(family)
            runner.run_subset(family_label, full, "full_family", force=True, repeat=1)
            runner.run_subset(family_label, full, "full_family", force=True, repeat=2)

            if len(family) <= 8:
                run_exhaustive(runner, family_label, family, randomizer)
            else:
                run_all_pairs(runner, family_label, family, randomizer)
                search_paths[f"{family_label}_forward"] = run_forward_search(
                    runner, family_label, family
                )
                search_paths[f"{family_label}_backward"] = run_backward_search(
                    runner, family_label, family
                )

        ranked = sorted(
            (
                (elapsed(row), row)
                for row in runner.subset_rows
                if row["status"] == "ok" and row["kind"] != "full_family"
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        repeated_keys = set()
        for _score, row in ranked:
            key = (row["family_label"], frozenset(row["subset"]))
            if key in repeated_keys:
                continue
            repeated_keys.add(key)
            if len(repeated_keys) > args.repeat_top:
                break
            for repeat in (2, 3):
                runner.run_subset(
                    row["family_label"],
                    frozenset(row["subset"]),
                    "slow_repeat",
                    force=True,
                    repeat=repeat,
                )

        runner.checkpoint()
        append_subset_metadata_csv(results_directory, runner.subset_rows)
        summary = {
            "source": str(args.source),
            "metadata": str(args.metadata),
            "sourceGlyphCount": len(records),
            "noSmartGlyphCount": len(no_smart),
            "families": {
                seed: sorted(family) for seed, family in selected_families
            },
            "searchPaths": search_paths,
            "subsetRuns": runner.subset_rows,
        }
        (results_directory / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )

    print(f"Results: {results_directory}")


if __name__ == "__main__":
    main()
