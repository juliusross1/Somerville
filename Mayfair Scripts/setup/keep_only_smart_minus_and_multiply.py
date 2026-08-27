#MenuTitle: Keep Only Smart Minus and Multiply
# -*- coding: utf-8 -*-

"""Keep two smart bases, their users, and all required component dependencies.

The operation affects only the currently open font and does not save it. The
script presents the complete keep/delete counts and asks for confirmation
before changing the font.
"""

from AppKit import NSAlert, NSAlertFirstButtonReturn
from GlyphsApp import Glyphs, Message


ROOT_GLYPHS = ("_smart.minus", "_smart.multiply")


def component_name(component):
    """Return a component's referenced glyph name across Glyphs API versions."""
    try:
        if component.componentName:
            return str(component.componentName)
    except Exception:
        pass
    try:
        if component.name:
            return str(component.name)
    except Exception:
        pass
    try:
        if component.component and component.component.name:
            return str(component.component.name)
    except Exception:
        pass
    return None


def direct_dependencies(glyph):
    names = set()
    for layer in glyph.layers:
        try:
            components = layer.components
        except Exception:
            components = []
        for component in components:
            name = component_name(component)
            if name:
                names.add(name)
    return names


def dependency_closure(font, roots):
    keep = set()
    missing = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name in keep:
            continue
        glyph = font.glyphs[name]
        if glyph is None:
            missing.add(name)
            continue
        keep.add(name)
        for dependency in direct_dependencies(glyph):
            if dependency not in keep:
                pending.append(dependency)
    return keep, missing


def related_glyph_closure(font, roots):
    """Find roots, dependencies, and every direct or transitive component user."""
    # First follow only the reverse component graph outward from the requested
    # roots. Incidental dependencies are deliberately not added to this set,
    # because doing so would retain unrelated users of common components.
    users = set(roots)
    changed = True
    while changed:
        changed = False
        for glyph in font.glyphs:
            if glyph.name in users:
                continue
            if direct_dependencies(glyph).intersection(users):
                users.add(glyph.name)
                changed = True

    # Only after the complete user tree is known, add the components required
    # to keep those glyphs structurally valid. Do not expand users from these.
    return dependency_closure(font, users)


def confirmed(font, keep, delete_names):
    alert = NSAlert.alloc().init()
    alert.setMessageText_("Keep only smart minus and multiply?")
    alert.setInformativeText_(
        "Font: %s\n\nKeep %i glyphs and delete %i glyphs. "
        "The font will not be saved automatically."
        % (
            font.familyName or "Untitled",
            len(keep),
            len(delete_names),
        )
    )
    alert.addButtonWithTitle_("Delete Other Glyphs")
    alert.addButtonWithTitle_("Cancel")
    return alert.runModal() == NSAlertFirstButtonReturn


font = Glyphs.font
if font is None:
    Message("No Font Open", "Open a font and run the script again.")
else:
    keep, missing = related_glyph_closure(font, ROOT_GLYPHS)
    if missing:
        Message(
            "Required Glyphs Missing",
            "No glyphs were deleted. Missing: %s" % ", ".join(sorted(missing)),
        )
    else:
        delete_names = [glyph.name for glyph in font.glyphs if glyph.name not in keep]
        print("Keep Only Smart Minus and Multiply")
        print("Keeping %i glyphs: %s" % (len(keep), ", ".join(sorted(keep))))
        print("Deleting %i glyphs" % len(delete_names))
        if delete_names and confirmed(font, keep, delete_names):
            font.disableUpdateInterface()
            try:
                for name in delete_names:
                    if font.glyphs[name] is not None:
                        del font.glyphs[name]
            finally:
                font.enableUpdateInterface()
            remaining = [name for name in delete_names if font.glyphs[name] is not None]
            if remaining:
                Message(
                    "Deletion Incomplete",
                    "%i glyphs could not be deleted. See the Macro window."
                    % len(remaining),
                )
                print("Glyphs not deleted: %s" % ", ".join(remaining))
            else:
                Message(
                    "Glyphs Deleted",
                    "Kept %i glyphs and deleted %i. The font has not been saved."
                    % (len(keep), len(delete_names)),
                )
        elif not delete_names:
            Message("Nothing to Delete", "The font already contains only the required glyphs.")
