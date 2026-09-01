#MenuTitle: ✂ Cut All Layers at Y Value
# -*- coding: utf-8 -*-

__doc__ = """
Cut all paths in all layers of the selected glyph at a user-specified horizontal y-value.
Uses one long horizontal cut per layer, rather than per-path bounds.
"""

from GlyphsApp import Glyphs, Message
import vanilla


def rect_values(bounds):
	try:
		# Tuple style: ((x, y), (w, h))
		(x, y), (w, h) = bounds
		return x, y, w, h
	except Exception:
		# NSRect style
		return bounds.origin.x, bounds.origin.y, bounds.size.width, bounds.size.height


class CutAllLayersAtY:

	def __init__(self):
		self.font = Glyphs.font

		if not self.font or not self.font.selectedLayers:
			Message("No glyph selected", "Please select a glyph first.")
			return

		self.selLayer = self.font.selectedLayers[0]
		self.glyph = self.selLayer.parent

		default_y = 0
		if self.selLayer.paths:
			x, y, w, h = rect_values(self.selLayer.bounds)
			default_y = y + h / 2.0

		self.w = vanilla.FloatingWindow(
			(320, 130),
			"Cut All Layers at Y"
		)

		self.w.text = vanilla.TextBox(
			(15, 18, -15, 20),
			"Horizontal cut y-value:"
		)

		self.w.yValue = vanilla.EditText(
			(15, 42, -15, 24),
			str(round(default_y, 2))
		)

		self.w.runButton = vanilla.Button(
			(15, 82, -15, 24),
			"Cut All Layers",
			callback=self.cutCallback
		)

		self.w.setDefaultButton(self.w.runButton)
		self.w.open()
		self.w.makeKey()

	def cutCallback(self, sender):
		try:
			cut_y = float(self.w.yValue.get())
		except Exception:
			Message("Invalid y-value", "Please enter a number, for example 350 or 412.5.")
			return

		Glyphs.clearLog()

		print("Cutting glyph: %s" % self.glyph.name)
		print("Horizontal cut at y = %s" % cut_y)

		self.font.disableUpdateInterface()
		self.glyph.beginUndo()

		try:
			for layer in self.glyph.layers:
				if not layer.paths:
					print("Skipping layer %s: no paths" % layer.name)
					continue

				# Use the full layer bounds, not individual path bounds.
				x, y, width, height = rect_values(layer.bounds)

				# Skip if the layer does not cross the cut height.
				if not (y <= cut_y <= y + height):
					print("Skipping layer %s: layer bounds do not cross y=%s" % (layer.name, cut_y))
					continue

				# Make the cut line deliberately much wider than the glyph.
				# This avoids the “only halfway” problem after paths have been split.
				padding = max(1000, width * 2)
				x1 = x - padding
				x2 = x + width + padding

				layer.beginChanges()
				try:
					layer.cutBetweenPoints(
						(x1, cut_y),
						(x2, cut_y)
					)
					print("Cut layer %s from x=%s to x=%s at y=%s" % (layer.name, x1, x2, cut_y))

				except Exception as e:
					print("Could not cut layer %s: %s" % (layer.name, e))

				finally:
					layer.endChanges()

		finally:
			self.glyph.endUndo()
			self.font.enableUpdateInterface()

		print("Done.")
		self.w.close()


CutAllLayersAtY()