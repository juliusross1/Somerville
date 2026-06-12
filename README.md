**PlayFair Math**

I will record here the steps that I take in making a math font for playfair

Select a font.  Good things to think about are Glyph coverage (italics and bold are helpful), and maybe also optical sizing.  Make sure this is not an existing math font

Install the Math Opentype Plugin.  Go to Edit->Edit Math constants.  The three dots will have a drop down for "Guess all Masters".    It will make reasonable guesses for these constants for many of them (one exception may be  DisplayOperatorMinHeight) which you can edit yourself or leave as zero and go back to later.

Export instances.  You want instances at each master coordinate and it is useful to have several in between for the next step

