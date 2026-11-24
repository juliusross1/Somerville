"""Fast, export-only letters + naryunion proofing subset.

Passed directly to ``glyphs export --script`` by build.sh --bigoperators-only.
Only the CLI's in-memory font is modified; this script never saves it. Excluded
glyphs are removed from that font before export, so Glyphs does not process them.
Component helpers remain available with their original export flags. Space and .notdef
are retained as font infrastructure. Numbers and unrelated symbols are omitted.
"""

from pathlib import Path
import os
import re
import runpy
from time import perf_counter


PROOF_SYMBOL_FAMILIES = {
    "equal", "plus", "minus",
    "union", "intersection", "naryintersection",
    "nAryUnionOperatorWithPlus", "nAryUnionOperatorWithDot",
    "summation", "product", "coproduct", "nAryTimesOperator",
    "nAryCircledPlusOperator", "nAryCircledDotOperator", "nAryCircledTimesOperator",
    "nArySquareUnionOperator", "nArySquareIntersectionOperator",
}


def feature_is_active(feature):
    # GlyphsApp exposes active as a property and disabled as an ObjC method;
    # glyphsLib exposes disabled as a Boolean instead.
    if hasattr(feature, "active"):
        return bool(feature.active)
    return not feature.disabled


def set_feature_active(feature, active):
    if hasattr(feature, "active"):
        feature.active = active
    else:
        feature.disabled = not active


def prune_substitutions(code, exporting):
    """Keep complete simple substitution rules; reject complex feature code.

    Somerville's manual features use single substitutions and alternate lists.
    Dropping an entire rule avoids mismatching parallel substitution classes.
    Complex lookups (notably accent ccmp) are disabled in this proofing subset.
    """
    code = re.sub(r"#[^\n]*", "", code)
    kept = []
    for statement in code.split(";"):
        statement = statement.strip()
        if not statement:
            continue
        match = re.fullmatch(
            r"sub\s+([\w.\-]+)\s+(by\s+[\w.\-]+|from\s+\[[\w.\-\s]+\])",
            statement,
        )
        if match is None:
            return ""
        names = re.findall(r"[\w.\-]+", statement)
        if all(name in exporting for name in names if name not in {"sub", "by", "from"}):
            kept.append(statement + ";")
    return "\n".join(kept)


def subset_for_naryunion(font, exclude=False, letters=True):
    started = perf_counter()
    glyphs = {glyph.name: glyph for glyph in font.glyphs}
    if "naryunion" not in glyphs:
        raise ValueError("Naryunion prefilter requires the naryunion glyph.")
    families = {"naryunion"}
    if letters:
        families.update(PROOF_SYMBOL_FAMILIES)
        # Retain the small square forms too if added to the source later.
        families.update(g.name for g in glyphs.values()
                        if g.unicode in {"2293", "2294"})
    keep = {
        name for name, glyph in glyphs.items()
        if glyph.export and (
            (letters and glyph.category in {"Letter", "Number"}) or name in {"space", ".notdef"}
            or name.split(".", 1)[0] in families
        )
    }
    if "naryunion" not in keep:
        raise ValueError("naryunion is not enabled for export in the source.")

    # Walk only retained glyphs, never the thousands of discarded symbol layers.
    # Visit each glyph once, including nested/smart components and backup layers.
    pending = list(keep)
    while pending:
        name = pending.pop()
        for layer in glyphs[name].layers:
            for component in layer.components:
                dependency = component.componentName
                if dependency not in glyphs:
                    raise ValueError("Missing component %s in %s" % (dependency, name))
                if dependency not in keep:
                    keep.add(dependency)
                    pending.append(dependency)

    disabled = 0
    excluded = glyphs.keys() - keep
    if not exclude:
        # Changing export flags in the Glyphs CLI triggers Bugsnag messages.
        # Only change them when the excluded glyphs will stay in the font.
        for name in excluded:
            if glyphs[name].export:
                glyphs[name].export = False
                disabled += 1
    exporting = {name for name in keep if glyphs[name].export}

    active_features = []
    for feature in font.features:
        if not feature_is_active(feature) or feature.name == "aalt":
            continue
        if feature.name == "kern" and feature.automatic:
            # Glyphs generates kerning from the exporting glyph set.
            continue
        code = prune_substitutions(feature.code, exporting)
        feature.automatic = False
        feature.code = code
        set_feature_active(feature, bool(code))
        if code:
            active_features.append(feature.name)
    for feature in font.features:
        if feature.name == "aalt" and feature_is_active(feature):
            feature.code = "\n".join("feature %s;" % tag for tag in active_features)
            feature.automatic = False
            set_feature_active(feature, bool(feature.code))

    removed = 0
    if exclude:
        # export=False alone still leaves thousands of glyphs for Glyphs'
        # variable-export preparation. Remove them from the CLI font instead.
        # Every foreground component dependency is already in keep.
        font.disableUpdateInterface()
        try:
            for name in excluded:
                del font.glyphs[name]
                removed += 1
        finally:
            font.enableUpdateInterface()

    elapsed = perf_counter() - started
    print("Naryunion prefilter: %d exporting glyphs; disabled %d; "
          "%d retained glyphs including component helpers; removed %d; "
          "%.3f seconds (not saved)."
          % (len(exporting), disabled, len(keep), removed, elapsed), flush=True)
    return {"exporting": exporting, "retained": keep, "removed": removed, "seconds": elapsed}


# Glyphs CLI executes --script without __file__ and with a non-main __name__.
if __name__ == "__main__" or "__file__" not in globals():
    from GlyphsApp import Glyphs

    for font in Glyphs.fonts:
        subset_for_naryunion(font, exclude=True,
                            letters=os.environ.get("SOMERVILLE_UNION_ONLY") != "1")
    # Keep the callback target alive for the complete CLI export.
    math_bootstrap = runpy.run_path(str(
        Path.home() / "Developer/Glyphs-MATH-Plugin/glyphs-cli-bootstrap.py"
    ))
