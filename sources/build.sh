#!/bin/zsh
usage() {
  printf '%s\n' 'Usage: sources/build.sh [--bigoperators-only | --union-only]' \
    '  --bigoperators-only  Export letters, numerals, = + minus, round/square union/intersection' \
    '                   and their n-ary forms, n-ary union with plus and dot, summation, product, coproduct,' \
    '                   bigoplus, bigodot, bigotimes, and bigtimes,' \
    '                   with variants and components, including naryunion.ssty1 and .ssty2.' \
    '  --union-only      Export naryunion variants and components, without letters.' \
    '                   Exclude other glyphs in memory; never save the source.'
}

bigoperators_only=0
union_only=0
for option in "$@"; do
  case "$option" in
    --bigoperators-only|--big-operators-only) bigoperators_only=1 ;;
    --union-only) bigoperators_only=1; union_only=1 ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done
export SOMERVILLE_UNION_ONLY="$union_only"

. "$HOME/.zprofile"
set -e

source_dir="$(CDPATH= cd "$(dirname "$0")" && pwd -P)"
export_script="$HOME/Developer/Glyphs-MATH-Plugin/glyphs-cli-bootstrap.py"
context_options=()
if (( bigoperators_only )); then
  export_script="$source_dir/naryunion_prefilter.py"
  context_options=(--mode=bigoperators-only)
fi
export_report="$(mktemp "${TMPDIR:-/tmp}/somerville-export.XXXXXX")"
trap 'rm -f -- "$export_report"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Keep an interruptible launcher in the terminal's foreground process group.
# Each command and its workers run in a separate, cancellable process group.
run_step() {
  python3 "$source_dir/run_cancellable.py" "$@"
}

run_step glyphs export \
  --plugins "$HOME/Developer/Glyphs-MATH-Plugin/MATHPlugin.glyphsPlugin" \
  --script "$export_script" \
  --config "$HOME/Documents/Somerville/sources/somerville-vf-export.json" \
  --format tt \
  --json-output "$export_report" \
  --output "$HOME/Documents/fontoutputs" || {
    export_status=$?
    printf '%s\n' "Glyphs export failed (exit status $export_status); stopping build." >&2
    exit "$export_status"
  }

# Per-instance export failures can still return process status zero.
run_step python3 "$source_dir/check_glyphs_export.py" \
  "$export_report" "$HOME/Documents/fontoutputs/SomervilleMathVF.ttf" || {
    printf '%s\n' "Stopping build; ConTeXt and Skim were not run." >&2
    exit 1
  }

# Add automatic script-axis mappings in place before ConTeXt loads the font.
run_step "$source_dir/venv/bin/python" "$source_dir/insertavar2tables.py" \
  "$HOME/Documents/fontoutputs/SomervilleMathVF.ttf" || {
    printf '%s\n' "avar v2 conversion failed; ConTeXt and Skim were not run." >&2
    exit 1
  }

if (( bigoperators_only )); then
  run_step "$source_dir/venv/bin/python" "$source_dir/fix_variable_font_bounds.py" \
    "$HOME/Documents/fontoutputs/SomervilleMathVF.ttf"
fi

cd "$HOME/Documents/Somerville/test_documents/Somerville/context"

# ~/Documents/Somerville/sources/venv/bin/python ~/Documents/Somerville/instantiate_somerville.py \
#  -i ~/Documents/fontoutputs/SomervilleMathVF.ttf \
#  --instance somerville-regular \
#  --output-dir ~/Documents/fontoutputs \
#  --overwrite

#run_step context sommerville-guide.tex
#run_step open -a Skim sommerville-guide.pdf

run_step context "${context_options[@]}" somerville-letter-test.tex
run_step open -a Skim somerville-letter-test.pdf

#run_step context somerville-integral-test.tex
#run_step open -a Skim somerville-integral-test.pdf

#context somerville-sample.tex
#open -a Skim somerville-sample.pdf
