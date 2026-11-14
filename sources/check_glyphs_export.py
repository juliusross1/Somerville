"""Reject failed Glyphs exports even when the CLI exits with status zero."""

import json
from pathlib import Path
import sys


def check_export(report_path, expected_font):
    reports = []
    for line_number, line in enumerate(report_path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            report = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("Invalid export report on line %i: %s" % (line_number, error)) from error
        if not isinstance(report, dict):
            raise ValueError("Export report on line %i is not an object." % line_number)
        reports.append(report)
    if not reports:
        raise ValueError("Glyphs produced no instance export reports.")

    failures = []
    exported_paths = set()
    for report in reports:
        instance = report.get("instanceName") or "Unnamed instance"
        errors = report.get("errors") or []
        if errors:
            failures.append("%s: %i export error(s)." % (instance, len(errors)))
            for error in errors:
                if isinstance(error, dict):
                    detail = error.get("description") or error.get("title") or str(error)
                else:
                    detail = str(error)
                failures.append("  " + detail)
        output = report.get("exportFilePath")
        if not isinstance(output, str) or not output:
            failures.append("%s: no exported font file was reported." % instance)
        else:
            path = Path(output).expanduser().resolve()
            if not path.is_file() or path.stat().st_size == 0:
                failures.append("%s: exported font is missing or empty: %s" % (instance, path))
            exported_paths.add(path)

    expected_font = expected_font.expanduser().resolve()
    if expected_font not in exported_paths:
        failures.append("Expected font was not successfully reported: %s" % expected_font)
    if failures:
        raise ValueError("\n".join(failures))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: check_glyphs_export.py REPORT.jsonl EXPECTED_FONT.ttf")
    try:
        check_export(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError) as error:
        print("Glyphs export failed validation:\n%s" % error, file=sys.stderr)
        sys.exit(1)
