#MenuTitle: Add center Anchor to Same Path on All Layers

# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, GSAnchor, Message

def rect_values(bounds):

	"""
	Return x, y, width, height from either tuple-style or NSRect-style bounds.
	"""
	try:
		# Tuple style: ((x, y), (w, h))
		(x, y), (w, h) = bounds
		return x, y, w, h
	except Exception:
		# NSRect style
		return bounds.origin.x, bounds.origin.y, bounds.size.width, bounds.size.height

font = Glyphs.font

if not font or not font.selectedLayers:

	Message("No layer selected", "Please select a path in a glyph layer first.")

else:

	selLayer = font.selectedLayers[0]
	glyph = selLayer.parent
	# Find selected paths on the current layer
	selectedPaths = [p for p in selLayer.paths if p.selected]
	if len(selectedPaths) == 0:
		Message("No path selected", "Please select one path in the current layer.")
	elif len(selectedPaths) > 1:
		Message("Too many paths selected", "Please select exactly one path.")
	else:
		selectedPath = selectedPaths[0]
		pathIndex = list(selLayer.paths).index(selectedPath)
		Glyphs.clearLog()
		print("Glyph:", glyph.name)
		print("Selected layer:", selLayer.name)
		print("Selected path index:", pathIndex)
		print("Adding/updating anchor: center")
		font.disableUpdateInterface()
		glyph.beginUndo()
		try:
			for layer in glyph.layers:
				if len(layer.paths) <= pathIndex:
					print("Skipping layer %s: does not have path index %s" % (layer.name, pathIndex))
					continue
				path = layer.paths[pathIndex]
				x, y, width, height = rect_values(path.bounds)
				centerX = x + width / 2.0
				centerY = y + height / 2.0
				layer.beginChanges()
				try:
					existingAnchor = layer.anchors["center"]
					if existingAnchor:
						existingAnchor.position = (centerX, centerY)
						print("Updated center anchor in layer %s: (%s, %s)" % (layer.name, centerX, centerY))
					else:
						newAnchor = GSAnchor("center", (centerX, centerY))
						layer.anchors.append(newAnchor)
						print("Added center anchor in layer %s: (%s, %s)" % (layer.name, centerX, centerY))
				except Exception as e:
					print("Could not process layer %s: %s" % (layer.name, e))
				finally:
					layer.endChanges()
		finally:
			glyph.endUndo()
			font.enableUpdateInterface()
		print("Done.")