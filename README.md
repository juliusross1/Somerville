**Playfair Math**

This records the steps taken to create a math font to pair with Playfair. The hope is that these notes may also help with other font pairings in the future. Not all the steps need to be done in the order they appear here.

*Step 1: Select a font to pair*

Things to consider include glyph coverage, existing italic and bold styles, and possible optical sizing. Existing mathematical glyphs, such as plus and minus, may also be helpful. Check the font license to make sure you can reuse it, and confirm that there is not already an existing math-font pairing available.


*Step 2: Math Constants Table*
Install the Math OpenType plugin (version made by JR link). Go to Edit -> Edit Math Constants. The three-dot menu has a drop-down item for "Guess all Masters". It will make reasonable guesses for many constants. One exception may be DisplayOperatorMinHeight, which you can edit yourself or leave as zero and return to later.

Add this to the Languages feature:

```
languagesystem math dflt;
```

*Step 3: Export Instances*

Export instances at each master coordinate. It is also useful to export several intermediate instances.

*Step 4: The MathConstants Tool*
Download and use the MathConstants tool. You will need to edit `axes-config` with the coordinates of the masters and list the fonts you want to test with. Run `server.py --help` for more help. This tool will save the math constants, which you can then insert into your Glyphs file (add more detail on how to do this).

*Step 5: Insert the math constants*

Add the saved math constants back into the Glyphs source, then re-export the font and check the result.
