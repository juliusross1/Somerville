# MenuTitle: Copy MATH hAssembly to All Master Layers
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
from Foundation import NSMutableDictionary, NSMutableArray


OUTER_KEY = "com.nagwa.MATHPlugin.variants"
ASSEMBLY_KEY = "hAssembly"


def keys_for_dictionary(dictionary):
    if dictionary is None:
        return []

    try:
        return list(dictionary.keys())
    except Exception:
        pass

    try:
        return list(dictionary.allKeys())
    except Exception:
        return []


def get_value(dictionary, key):
    if dictionary is None:
        return None

    try:
        return dictionary[key]
    except Exception:
        pass

    try:
        return dictionary.objectForKey_(key)
    except Exception:
        return None


def set_value(dictionary, key, value):
    try:
        dictionary[key] = value
        return True, "dictionary[key] = value"
    except Exception as first_error:
        try:
            dictionary.setObject_forKey_(value, key)
            return True, "setObject_forKey_"
        except Exception as second_error:
            return False, (
                "Python assignment failed: %s; Cocoa assignment failed: %s"
                % (first_error, second_error)
            )


def mutable_copy(value):
    """
    Make a mutable copy where possible.

    This is important because the plugin data contains nested Cocoa arrays
    and dictionaries rather than ordinary Python lists and dictionaries.
    """
    if value is None:
        return None

    try:
        return value.mutableCopy()
    except Exception:
        pass

    try:
        return value.copy()
    except Exception:
        return value


def describe_dictionary(dictionary, indent="    "):
    if dictionary is None:
        print(indent + "(None)")
        return

    keys = keys_for_dictionary(dictionary)

    if not keys:
        print(indent + "(no keys)")
        return

    for key in keys:
        value = get_value(dictionary, key)
        print("%s%r:" % (indent, str(key)))
        print("%s    %r" % (indent, value))


font = Glyphs.font

if font is None:
    print("ERROR: No font is open.")

elif not font.selectedLayers:
    print("ERROR: No layer is selected.")

else:
    source_layer = font.selectedLayers[0]
    glyph = source_layer.parent

    print("=" * 100)
    print("Glyph:", glyph.name)
    print("Source layer:", source_layer.name)
    print("Source layer ID:", source_layer.layerId)
    print("Associated master ID:", source_layer.associatedMasterId)
    print("=" * 100)

    print("\nSOURCE TOP-LEVEL USER DATA")
    print("-" * 100)
    describe_dictionary(source_layer.userData)

    source_variants = get_value(source_layer.userData, OUTER_KEY)

    print("\nSOURCE PLUGIN DATA")
    print("-" * 100)
    print("Outer key:", repr(OUTER_KEY))
    print("Plugin data object:", repr(source_variants))
    print("Plugin data type:", type(source_variants))
    print("Plugin data contents:")
    describe_dictionary(source_variants)

    source_assembly = get_value(source_variants, ASSEMBLY_KEY)

    print("\nSOURCE hAssembly")
    print("-" * 100)
    print("Nested key:", repr(ASSEMBLY_KEY))
    print("Value:", repr(source_assembly))
    print("Value type:", type(source_assembly))

    if source_variants is None:
        print()
        print("ERROR: The source layer has no data under:")
        print("   ", repr(OUTER_KEY))

    elif source_assembly is None:
        print()
        print("ERROR: The plugin dictionary has no hAssembly entry.")
        print("Available nested keys:")
        for key in keys_for_dictionary(source_variants):
            print("   ", repr(str(key)))

    else:
        print("\nCOPYING TO MASTER LAYERS")
        print("=" * 100)

        copied_count = 0
        skipped_count = 0
        failed_count = 0

        font.disableUpdateInterface()

        try:
            for index, layer in enumerate(glyph.layers):
                print()
                print("-" * 100)
                print("Layer index:", index)
                print("Layer name:", layer.name)
                print("Layer ID:", layer.layerId)
                print("Associated master ID:", layer.associatedMasterId)

                is_master_layer = (
                    layer.layerId == layer.associatedMasterId
                )

                print("Is master layer:", is_master_layer)

                if not is_master_layer:
                    print("Action: skipped; not a master layer.")
                    skipped_count += 1
                    continue

                if layer.layerId == source_layer.layerId:
                    print("Action: skipped; this is the source layer.")
                    skipped_count += 1
                    continue

                print("Destination top-level userData before:")
                describe_dictionary(layer.userData)

                destination_variants = get_value(
                    layer.userData,
                    OUTER_KEY
                )

                print("Destination plugin data before:")
                describe_dictionary(destination_variants)

                old_assembly = get_value(
                    destination_variants,
                    ASSEMBLY_KEY
                )

                print("Previous hAssembly:", repr(old_assembly))

                # If the destination has no plugin dictionary, create one.
                if destination_variants is None:
                    print(
                        "No destination plugin dictionary exists; "
                        "creating one."
                    )

                    destination_variants = NSMutableDictionary.dictionary()

                    success, method = set_value(
                        layer.userData,
                        OUTER_KEY,
                        destination_variants
                    )

                    print("Outer-dictionary write result:", success)
                    print("Outer-dictionary write method:", method)

                    if not success:
                        print("Action: FAILED to create plugin dictionary.")
                        failed_count += 1
                        continue

                    # Re-read the dictionary actually stored by Glyphs.
                    destination_variants = get_value(
                        layer.userData,
                        OUTER_KEY
                    )

                # Copy the hAssembly structure.
                assembly_copy = mutable_copy(source_assembly)

                success, method = set_value(
                    destination_variants,
                    ASSEMBLY_KEY,
                    assembly_copy
                )

                print("hAssembly write result:", success)
                print("hAssembly write method:", method)

                if not success:
                    print("Action: FAILED to write hAssembly.")
                    failed_count += 1
                    continue

                # Re-read everything from the layer for verification.
                verified_variants = get_value(
                    layer.userData,
                    OUTER_KEY
                )

                verified_assembly = get_value(
                    verified_variants,
                    ASSEMBLY_KEY
                )

                print("Destination plugin data after:")
                describe_dictionary(verified_variants)

                print(
                    "Verified hAssembly:",
                    repr(verified_assembly)
                )

                if verified_assembly is None:
                    print("Action: FAILED verification.")
                    failed_count += 1
                else:
                    try:
                        item_count = len(verified_assembly)
                    except Exception:
                        item_count = "unknown"

                    print("Verified assembly item count:", item_count)
                    print("Action: copied successfully.")
                    copied_count += 1

        finally:
            font.enableUpdateInterface()

        print()
        print("=" * 100)
        print("SUMMARY")
        print("-" * 100)
        print("Glyph:", glyph.name)
        print("Source layer:", source_layer.name)
        print("Master layers updated:", copied_count)
        print("Layers skipped:", skipped_count)
        print("Failures:", failed_count)
        print("=" * 100)