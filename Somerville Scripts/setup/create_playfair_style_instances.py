#MenuTitle: Create Playfair-Style Somerville Instances
# -*- coding: utf-8 -*-

"""
Create or update Somerville's static instances using the instance matrix from
Playfair-2_2-Roman.glyphspackage.

The script creates 12 optical sizes x 3 widths x 7 weights (252 instances).
The first three design coordinates and the style names match Playfair. The
internal STYA/STYB values follow SomervilleA's Axis Mappings 2 (avar2) outputs,
with their hidden external coordinates set to the mapping inputs STYA=5 and
STYB=5. Math Weight is min(Weight + 300, 900).

Existing static instances with matching names are updated. Missing instances
are appended. Variable instances and unrelated static instances are preserved.
"""

from GlyphsApp import Glyphs, GSInstance


# (name, opsz design, opsz external, STYA design, STYB design)
OPTICAL_SIZES = (
    ("Micro", 5, 5, 5, 5),
    ("Minuscule", 200, 6, 112, 50),
    ("Miniature", 325, 7, 221, 114),
    ("Caption", 400, 8, 278, 165),
    ("Regular", 550, 12, 375, 246),
    ("SubHeading", 640, 16, 519, 384),
    ("Trumpet", 700, 21, 585, 451),
    ("Headline", 800, 32, 700, 575),
    ("Display", 900, 48, 818, 711),
    ("Titling", 980, 72, 916, 830),
    ("Hairline", 1020, 96, 966, 893),
    ("Needlepoint", 1200, 1200, 1150, 1100),
)

WIDTHS = (
    ("SemiCondensed", 95, 88),
    ("", 100, 100),
    ("SemiExpanded", 113, 113),
)

WEIGHTS = (
    ("SemiLight", 360),
    ("", 400),
    ("Medium", 475),
    ("SemiBold", 550),
    ("Bold", 650),
    ("ExtraBold", 750),
    ("Black", 900),
)

FIXED_COORDINATES = {
    "STYA": 5,
    "STYB": 5,
    "ARHD": 100,
    "ARLN": 100,
    "INSL": 0,
}

REQUIRED_TAGS = ("opsz", "wdth", "wght", "STYA", "STYB", "MGHT", "ARHD", "ARLN", "INSL")


def safe_value(value):
    if callable(value):
        try:
            return value()
        except Exception:
            return None
    return value


def axis_tag(axis):
    for attribute_name in ("tag", "axisTag"):
        value = safe_value(getattr(axis, attribute_name, None))
        if value:
            return str(value)
    return ""


def is_static(instance):
    # Glyphs uses type 0 for static and type 1 for variable instances.
    return int(safe_value(getattr(instance, "type", 0)) or 0) == 0


def style_name(optical_name, width_name, weight_name):
    return " ".join(part for part in (optical_name, width_name, weight_name) if part)


def set_internal_axis_values(instance, axes_by_tag, values_by_tag):
    """Set and verify each internal coordinate by its Glyphs axis ID."""
    for tag in REQUIRED_TAGS:
        axis = axes_by_tag[tag]
        value = values_by_tag[tag]
        setter = getattr(instance, "setAxisInternalValueValue_forId_", None)
        if callable(setter):
            setter(value, axis.axisId)
        else:
            instance.internalAxesValues[axis.axisId] = value

    for tag in ("STYA", "STYB"):
        axis = axes_by_tag[tag]
        expected = values_by_tag[tag]
        getter = getattr(instance, "axisInternalValueValueForId_", None)
        if callable(getter):
            actual = getter(axis.axisId)
        else:
            actual = instance.internalAxesValues[axis.axisId]
        if abs(float(actual) - float(expected)) > 0.000001:
            raise RuntimeError(
                "%s: %s (%s) read back as %s; expected %s"
                % (instance.name, axis.name, tag, actual, expected)
            )


def set_external_axis_values(instance, font, opsz_external, width_external, weight, math_weight):
    """Set all external coordinates, including avar2's hidden-axis inputs."""
    locations_by_tag = {
        "opsz": opsz_external,
        "wdth": width_external,
        "wght": weight,
        "MGHT": math_weight,
    }
    for tag, value in FIXED_COORDINATES.items():
        locations_by_tag[tag] = value

    external_values = instance.externalAxesValues
    for axis in font.axes:
        tag = axis_tag(axis)
        external_values[axis.axisId] = locations_by_tag[tag]


def main():
    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Create Playfair-Style Somerville Instances")
    print("")

    font = Glyphs.font
    if font is None:
        raise RuntimeError("No font is open.")

    axes_by_tag = {}
    for axis in font.axes:
        tag = axis_tag(axis)
        if tag:
            axes_by_tag[tag] = axis

    missing = [tag for tag in REQUIRED_TAGS if tag not in axes_by_tag]
    if missing:
        raise RuntimeError("The font is missing required axes: %s" % ", ".join(missing))

    existing_by_name = {
        instance.name: instance
        for instance in font.instances
        if is_static(instance)
    }

    created = 0
    updated = 0
    font.disableUpdateInterface()
    try:
        for optical_name, opsz, opsz_external, stya, styb in OPTICAL_SIZES:
            for width_name, width, width_external in WIDTHS:
                for weight_name, weight in WEIGHTS:
                    name = style_name(optical_name, width_name, weight_name)
                    math_weight = min(weight + 300, 900)
                    instance = existing_by_name.get(name)
                    if instance is None:
                        action = "ADD"
                        instance = GSInstance()
                        instance.name = name
                        font.instances.append(instance)
                        existing_by_name[name] = instance
                        created += 1
                    else:
                        action = "SET"
                        updated += 1

                    values_by_tag = {
                        "opsz": opsz,
                        "wdth": width,
                        "wght": weight,
                        "MGHT": math_weight,
                    }
                    values_by_tag.update(FIXED_COORDINATES)
                    values_by_tag["STYA"] = stya
                    values_by_tag["STYB"] = styb
                    # Glyphs 4 stores the user-facing coordinate separately
                    # from the internal design-space coordinate. Set external
                    # values first because avar2 may recalculate internal axes.
                    set_external_axis_values(
                        instance,
                        font,
                        opsz_external,
                        width_external,
                        weight,
                        math_weight,
                    )

                    # Apply the intended design coordinates last, after avar2
                    # has reacted to changes in the user-facing coordinates.
                    set_internal_axis_values(instance, axes_by_tag, values_by_tag)

                    # Match Playfair's Regular/Bold style-link pairs.
                    if weight_name == "Bold":
                        instance.isBold = True
                        instance.linkStyle = style_name(optical_name, width_name, "")
                    else:
                        instance.isBold = False
                        instance.linkStyle = ""

                    print("%s: %s" % (action, name))
    finally:
        font.enableUpdateInterface()

    print("")
    print("Done: created %d and updated %d instances." % (created, updated))
    print("The expected Playfair-style matrix contains 252 static instances.")


main()
