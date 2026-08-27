#!/usr/bin/env python3
"""Compare the no-smart export baseline with baseline plus `_smart.minus`."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import statistics
import tempfile

from profile_smart_component_families import (
    DEFAULT_METADATA,
    DEFAULT_SOURCE,
    Profiler,
    read_glyph_records,
    smart_dependencies,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = "_smart.minus"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--app", default="4.0.1")
    parser.add_argument("--glyphs", default=shutil.which("glyphs") or "glyphs")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    args = parser.parse_args()
    args.source = args.source.resolve()
    args.metadata = args.metadata.resolve()

    records = read_glyph_records(args.source)
    smart_bases, dependencies = smart_dependencies(records)
    target = args.target
    if target not in smart_bases:
        raise SystemExit(f"Smart base not found: {target}")

    baseline = {name for name, values in dependencies.items() if not values}
    required_smart_bases = set(dependencies[target])
    selected = baseline | {
        name
        for name, values in dependencies.items()
        if values and values.issubset(required_smart_bases)
    }
    added = sorted(selected - baseline)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_slug = target.removeprefix("_smart.").replace(".", "-")
    results = ROOT / "profiling_results" / f"smart-{target_slug}-{timestamp}"
    results.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="mayfair-smart-minus-") as temporary:
        profiler = Profiler(
            args, records, dependencies, results, Path(temporary)
        )
        rows = []
        for repetition in range(1, args.repetitions + 1):
            rows.append(profiler.run("focused", "baseline", repetition, baseline, 0))
            rows.append(
                profiler.run(
                    "focused",
                    f"baseline_plus_{target}",
                    repetition,
                    selected,
                    len(required_smart_bases),
                )
            )

    grouped = {
        target: [
            float(row["elapsed_seconds"])
            for row in rows
            if row["target"] == target and row["status"] == "ok"
        ]
        for target_name in ("baseline", f"baseline_plus_{target}")
        for target in (target_name,)
    }
    medians = {key: statistics.median(values) for key, values in grouped.items()}
    summary = {
        "baselineGlyphCount": len(baseline),
        "selectedGlyphCount": len(selected),
        "requiredSmartBases": sorted(required_smart_bases),
        "glyphsAdded": added,
        "times": grouped,
        "medians": medians,
        "medianDifferenceSeconds": (
            medians[f"baseline_plus_{target}"] - medians["baseline"]
        ),
    }
    (results / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    print(f"Results: {results}")


if __name__ == "__main__":
    main()
