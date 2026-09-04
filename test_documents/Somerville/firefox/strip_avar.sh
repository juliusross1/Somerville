#!/bin/sh
set -eu

input=${1:-SomervilleVF-withMathtable.ttf}
output=${2:-$input}

if ! command -v ttx >/dev/null 2>&1; then
  echo "Error: FontTools ttx is not installed or not on PATH." >&2
  exit 1
fi

if [ ! -f "$input" ]; then
  echo "Error: input font not found: $input" >&2
  exit 1
fi

if [ "$input" != "$output" ] && [ -e "$output" ]; then
  echo "Error: output already exists: $output" >&2
  exit 1
fi

if ! ttx -l "$input" 2>/dev/null | grep -q '^[[:space:]]*avar[[:space:]]'; then
  echo "Error: input font does not contain an avar table: $input" >&2
  exit 1
fi

ttx_command=$(command -v ttx)
fonttools_python=$(sed -n '1s/^#!//p' "$ttx_command")

if [ ! -x "$fonttools_python" ]; then
  echo "Error: could not locate the Python interpreter used by ttx." >&2
  exit 1
fi

output_directory=$(dirname "$output")
temporary_output=$(mktemp "$output_directory/.strip-avar.XXXXXX.ttf")
trap 'rm -f "$temporary_output"' EXIT HUP INT TERM

# Lazy loading lets FontTools copy untouched binary tables directly. This is
# important for fonts containing tables that cannot safely round-trip via XML.
"$fonttools_python" - "$input" "$temporary_output" <<'PY'
import sys
from fontTools.ttLib import TTFont

input_path, output_path = sys.argv[1:]
font = TTFont(input_path, lazy=True, recalcTimestamp=False)

if "avar" not in font:
    raise SystemExit(f"Error: input font does not contain an avar table: {input_path}")

del font["avar"]
font.save(output_path, reorderTables=False)
font.close()

result = TTFont(output_path, lazy=True)
if "avar" in result:
    raise SystemExit("Error: avar is still present in the generated font.")
result.close()
PY

mv "$temporary_output" "$output"

if [ "$input" = "$output" ]; then
  echo "Updated $output in place without an avar table."
else
  echo "Created $output without an avar table."
fi
