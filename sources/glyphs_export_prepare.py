"""Prepare the in-memory export font, then initialize the MATH plug-in.

Used by build.sh as the Glyphs CLI --script. Neither step saves the source.
"""

from pathlib import Path
import runpy

from GlyphsApp import Glyphs


# CLI --script does not supply __file__. The saved font package lives beside
# these scripts in sources/; glyphs run does supply __file__.
script_path = globals().get('__file__')
source_dir = (Path(script_path).resolve().parent if script_path else
              Path(Glyphs.fonts[0].filepath).resolve().parent)

prefilter = runpy.run_path(
    str(source_dir / 'arrows_prefilter.py'),
    run_name='__main__',
)

# Retain the returned namespace so the plug-in callback stays alive through
# export, just as when its bootstrap is run directly by the CLI.
math_bootstrap = runpy.run_path(str(
    Path.home() / 'Developer/Glyphs-MATH-Plugin/glyphs-cli-bootstrap.py'
))
