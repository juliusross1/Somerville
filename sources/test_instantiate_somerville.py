"""CLI checks for static mathematics and portable Playfair fontspec configurations."""

import contextlib
import io
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest

from fontTools.misc.roundTools import otRound
from fontTools.pens.basePen import NullPen
from fontTools.ttLib import TTFont
from fontTools.varLib.varStore import VarStoreInstancer

import insertavar2tables


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'instantiate_somerville.py'
sys.path.insert(0, str(ROOT))
import instantiate_somerville


class MathOnlyInstantiationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_directory = tempfile.TemporaryDirectory()
        cls.fixture = Path(cls.fixture_directory.name) / 'math-vf.ttf'
        with contextlib.redirect_stdout(io.StringIO()):
            insertavar2tables.insert_avar2_tables(
                ROOT / 'fonts/SomervilleMath/SomervilleMathVF.ttf', output=cls.fixture)

    @classmethod
    def tearDownClass(cls):
        cls.fixture_directory.cleanup()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cwd = Path(self.directory.name)
        self.input = self.cwd / 'SomervilleMathVF.ttf'
        shutil.copyfile(self.fixture, self.input)
        # Coordinate/config tests can reuse Roman outlines for both text faces.
        # The LuaLaTeX integration check uses the actual Roman and Italic VFs.
        for name in ('PlayfairRomanVF.ttf', 'PlayfairItalicVF.ttf'):
            shutil.copyfile(ROOT / 'fonts/Playfair/PlayfairRomanVF.ttf', self.cwd / name)
        self.input_names = {'SomervilleMathVF.ttf', 'PlayfairRomanVF.ttf', 'PlayfairItalicVF.ttf'}

    def run_script(self, *arguments, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=self.cwd,
                                text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def assert_static_math(self, path):
        with TTFont(path) as font:
            font.ensureDecompiled()
            self.assertIn('MATH', font)
            self.assertNotIn('BASE', font)
            for tag in ('fvar', 'gvar', 'avar'):
                self.assertNotIn(tag, font)

    def test_default_export_only_creates_math_font(self):
        before = self.input.read_bytes()
        result = self.run_script('-o', 'Custom', '--validate')
        self.assert_static_math(self.cwd / 'SomervilleMathCustom.ttf')
        self.assertEqual({p.name for p in self.cwd.iterdir()},
                         self.input_names | {'SomervilleMathCustom.ttf', 'SomervilleCustom.fontspec'})
        self.assertEqual(self.input.read_bytes(), before)
        self.assertNotIn('Playfair', result.stdout + result.stderr)

    def test_named_instance_and_math_variation_resolution(self):
        self.run_script('--instance', 'somerville-caption-bold', 'MGHT=75', 'INSL=100',
                        '-o', 'CaptionBold', '--output-dir', 'output', '--validate')
        output = self.cwd / 'output/SomervilleMathCaptionBold.ttf'
        self.assert_static_math(output)
        with TTFont(self.input) as source, TTFont(output) as target:
            instance = next(i for i in source['fvar'].instances
                            if source['name'].getDebugName(i.subfamilyNameID) == 'Caption Bold')
            coordinates = {**instance.coordinates, 'MGHT': 75, 'INSL': 100}
            store = VarStoreInstancer(source['GDEF'].table.VarStore, source['fvar'].axes,
                                     source.normalizeLocation(coordinates))
            constants = source['MATH'].table.MathConstants
            checked = 0
            for field, value in vars(constants).items():
                device = getattr(value, 'DeviceTable', None)
                if device is not None and device.DeltaFormat == 0x8000:
                    index = (device.StartSize << 16) | device.EndSize
                    expected = otRound(value.Value + store[index])
                    actual = getattr(target['MATH'].table.MathConstants, field)
                    # AxisLimits (used by the outline instancer) and
                    # normalizeLocation quantize avar coordinates differently;
                    # a value at a rounding boundary can differ by one unit.
                    self.assertAlmostEqual(actual.Value, expected, delta=1, msg=field)
                    self.assertIsNone(actual.DeviceTable, field)
                    checked += 1
            self.assertGreater(checked, 0)
        self.assertEqual({p.name for p in output.parent.iterdir()}, {output.name, 'SomervilleCaptionBold.fontspec'})

    def test_batch_prefix_and_allinstances(self):
        # Keep the real variation/MATH data, with two named instances to make
        # exercising the all-instances path quick.
        with TTFont(self.input) as font:
            font['fvar'].instances = [i for i in font['fvar'].instances
                if font['name'].getDebugName(i.subfamilyNameID) in ('Regular', 'Caption Bold')]
            font.save(self.input)
        self.run_script('--allinstances', '-o', 'Custom', '--output-dir', 'batch', '--validate')
        outputs = list((self.cwd / 'batch').iterdir())
        self.assertEqual({p.name for p in outputs}, {'SomervilleMathCustomRegular.ttf', 'SomervilleMathCustomCaptionBold.ttf',
                          'SomervilleCustomRegular.fontspec', 'SomervilleCustomCaptionBold.fontspec'})
        for path in outputs:
            if path.suffix == '.ttf':
                self.assert_static_math(path)

    def test_allinstances_without_output_name_uses_standard_names(self):
        with TTFont(self.input) as font:
            font['fvar'].instances = [i for i in font['fvar'].instances
                if font['name'].getDebugName(i.subfamilyNameID) in ('Regular', 'Caption Bold')]
            font.save(self.input)
        self.run_script('--allinstances', '--output-dir', 'standard', '--validate')
        self.assertEqual({p.name for p in (self.cwd / 'standard').iterdir()},
                         {'SomervilleMathRegular.ttf', 'SomervilleRegular.fontspec',
                          'SomervilleMathCaptionBold.ttf', 'SomervilleCaptionBold.fontspec'})

    def test_fontspec_is_portable_and_configures_all_faces_and_math(self):
        self.run_script('--instance', 'somerville-regular', '-o', 'Custom')
        content = (self.cwd / 'SomervilleCustom.fontspec').read_text()
        self.assertIn(r'\defaultfontfeatures[SomervilleCustom]', content)
        for shape in ('Upright', 'Italic', 'Bold', 'BoldItalic'):
            self.assertIn(f'{shape}Font=', content)
            self.assertIn(f'{shape}Features={{RawAxis=', content)
        self.assertIn(r'\setmathfont{SomervilleMathCustom.ttf}', content)
        self.assertIn('UprightFeatures={RawAxis={opsz=12,wdth=100,wght=400}}', content)
        self.assertIn('BoldFeatures={RawAxis={opsz=12,wdth=100,wght=650}}', content)
        self.assertNotIn(str(self.cwd), content)

    @unittest.skipUnless(shutil.which('lualatex'), 'LuaLaTeX is not installed')
    def test_lualatex_text_faces_apply_the_requested_variations(self):
        self.run_script('--instance', 'somerville-regular')
        with TTFont(self.input) as math, TTFont(self.cwd / 'PlayfairRomanVF.ttf') as text:
            coordinates = instantiate_somerville.resolve_coordinates(math, [])
            location = instantiate_somerville.normalized_coordinates(math, coordinates)
            checks = []
            for shape in ('Upright', 'Italic', 'Bold', 'BoldItalic'):
                axes = instantiate_somerville.matching_text_coordinates(
                    text, location, bold=shape in ('Bold', 'BoldItalic'))
                glyphs = text.getGlyphSet(location=axes)
                widths = []
                for c in 'Theo':
                    glyph = glyphs[text.getBestCmap()[ord(c)]]
                    # gvar phantom points update advances while drawing.
                    glyph.draw(NullPen())
                    widths.append(f'[{ord(c)}]={glyph.width}')
                checks.append(f"['{shape}']={{{','.join(widths)}}}")
            units_per_em = text['head'].unitsPerEm
        (self.cwd / 'check-font.lua').write_text(
            'local expected={' + ','.join(checks) + '}\n'
            f'local units_per_em={units_per_em}\n' + '''
function check_face(shape)
  local f=font.getfont(font.current())
  assert(f.name:find('mode=harf',1,true), shape..' must use HarfBuzz')
  for unicode,width in pairs(expected[shape]) do
    local actual=f.characters[unicode].width * units_per_em / f.size
    assert(math.abs(actual-width) <= 1,
      shape..' wrong variation at '..unicode..': '..actual..' versus '..width)
  end
  texio.write_nl('MATCHED-FACE '..shape)
end
''', encoding='utf-8')
        (self.cwd / 'check-font.tex').write_text(r'''
\documentclass{article}
\usepackage{unicode-math}
\setmainfont{SomervilleRegular}
\directlua{dofile('check-font.lua')}
\begin{document}
\directlua{check_face('Upright')} Text.
\textit{\directlua{check_face('Italic')} Italic.}
\textbf{\directlua{check_face('Bold')} Bold.}
\textbf{\textit{\directlua{check_face('BoldItalic')} Bold italic.}}
\(x^2+\symbf{ABC}+\symit{xyz}\)
\newcommand\checkmathalphabet[2]{%
  \setbox0=\hbox{$#1{ooo}$}\setbox1=\hbox{$#2{ooo}$}%
  \ifdim\wd0=\wd1\else\errmessage{Math alphabet must use SomervilleMath}\fi}
\checkmathalphabet{\mathrm}{\symup}
\checkmathalphabet{\mathit}{\symit}
\checkmathalphabet{\mathbf}{\symbf}
\end{document}
''', encoding='utf-8')
        # Keep font caches inside the test directory, including in sandboxes.
        cache = self.cwd / 'tex-cache'
        cache.mkdir()
        environment = {**os.environ, 'TEXMFCACHE': str(cache), 'TEXMFVAR': str(cache)}
        result = subprocess.run(
            ['lualatex', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error',
             'check-font.tex'], cwd=self.cwd, env=environment, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for shape in ('Upright', 'Italic', 'Bold', 'BoldItalic'):
            self.assertIn('MATCHED-FACE ' + shape, result.stdout)

    def test_text_mapping_uses_internal_math_weight_and_each_avar(self):
        with TTFont(self.input) as math, TTFont(self.cwd / 'PlayfairRomanVF.ttf') as text:
            coordinates = instantiate_somerville.resolve_coordinates(math, [])
            location = instantiate_somerville.normalized_coordinates(math, coordinates)
            upright = instantiate_somerville.matching_text_coordinates(text, location)
            bold = instantiate_somerville.matching_text_coordinates(text, location, bold=True)
            self.assertAlmostEqual(upright['wght'], 400, delta=0.03)
            # At internal wght 400, MGHT=50 means internal 600, which is
            # approximately user wght 650 in Playfair, not user wght 50 or 600.
            self.assertAlmostEqual(bold['wght'], 650, delta=0.03)
            for strength in (0, 25, 50, 75, 100):
                coordinates.update(wdth=113, wght=700, MGHT=strength)
                location = instantiate_somerville.normalized_coordinates(math, coordinates)
                mapped = instantiate_somerville.matching_text_coordinates(text, location, bold=True)
                actual = text.normalizeLocation(mapped)
                for tag, source in [('wdth', 'wdth'), ('opsz', 'opsz'), ('wght', 'MGHT')]:
                    self.assertAlmostEqual(actual.get(tag, 0), location[source], delta=2/16384)
                self.assertAlmostEqual(mapped['wdth'], 112.5, delta=0.03)
                if strength == 0:
                    self.assertEqual(mapped['wght'], 360)

    def test_existing_fontspec_is_protected_before_math_export(self):
        setup = self.cwd / 'SomervilleCustom.fontspec'
        setup.write_text('keep me')
        self.run_script('--instance', 'somerville-regular', '-o', 'Custom', success=False)
        self.assertEqual(setup.read_text(), 'keep me')
        self.assertFalse((self.cwd / 'SomervilleMathCustom.ttf').exists())
        self.run_script('--instance', 'somerville-regular', '-o', 'Custom', '--overwrite')
        self.assertIn(r'\defaultfontfeatures', setup.read_text())

    def test_playfair_location_can_be_overridden_and_is_read_only(self):
        directory = self.cwd / 'text-inputs'
        directory.mkdir()
        for name in ('PlayfairRomanVF.ttf', 'PlayfairItalicVF.ttf'):
            shutil.move(self.cwd / name, directory / name)
        before = {p.name: p.read_bytes() for p in directory.iterdir()}
        self.run_script('--instance', 'somerville-regular', '-o', 'Custom', success=False)
        self.assertFalse((self.cwd / 'SomervilleMathCustom.ttf').exists())
        self.run_script('--instance', 'somerville-regular', '-o', 'Custom',
                        '--playfair-dir', str(directory))
        self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir()})

    def test_listing_and_invalid_batch_do_not_create_fonts(self):
        result = self.run_script('--list-instances')
        self.assertIn('somerville-caption-bold', result.stdout)
        self.assertNotIn('Caption Bold', result.stdout)
        self.run_script('--instance', 'somerville-regular', 'not-an-instance', '--output-dir', 'bad', success=False)
        self.assertEqual({p.name for p in self.cwd.iterdir()}, self.input_names)

    def test_guide_names_aliases_and_listing(self):
        result = self.run_script('--list-instances')
        listed = result.stdout.splitlines()[1:]
        with TTFont(self.input) as font:
            entries = instantiate_somerville.named_instances(font)
            self.assertEqual(len(listed), len(entries))
            self.assertEqual(len(set(listed)), len(listed))
            for listed_name, (_, aliases, _) in zip(listed, entries):
                self.assertRegex(listed_name, r'^somerville-[a-z]+(?:-[a-z]+)*$')
                self.assertIn(listed_name, aliases)
            regular = instantiate_somerville.instance_coordinates(font, 'somerville-regular')
            self.assertEqual(instantiate_somerville.instance_coordinates(font, 'somerville'), regular)
            caption = instantiate_somerville.instance_coordinates(font, 'somerville-caption-bold')
            for alias in ('SOMERVILLE-CAPTION-BOLD', 'caption-bold', 'Caption Bold'):
                self.assertEqual(instantiate_somerville.instance_coordinates(font, alias), caption)

    def test_list_axes_reports_ranges_names_and_aliases_without_writing(self):
        result = self.run_script('--list-axes', '--output-dir', 'unused')
        self.assertIn('Math Weight (MGHT): 0..100 (font default 50)', result.stdout)
        self.assertIn('Arrow Head (ARHD): 100..200', result.stdout)
        self.assertRegex(result.stdout, r'Heavier\s+= 75')
        self.assertRegex(result.stdout, r'Large\s+= 200 \(alias of Largest\)')
        self.assertNotIn('STYA', result.stdout)
        self.assertNotIn('STYB', result.stdout)
        self.assertEqual({p.name for p in self.cwd.iterdir()}, self.input_names)

    def test_list_axes_uses_input_font_ranges_and_omits_invalid_choices(self):
        with TTFont(self.input) as font:
            axis = next(a for a in font['fvar'].axes if a.axisTag == 'ARHD')
            axis.maxValue = 150
            font.save(self.input)
        result = self.run_script('--list-axes')
        self.assertIn('Arrow Head (ARHD): 100..150', result.stdout)
        self.assertRegex(result.stdout, r'Larger\s+= 150')
        self.assertNotIn('Largest', result.stdout)
        self.assertNotIn('alias of', result.stdout)

    def test_list_axes_rejects_axis_assignments_and_instance_selection(self):
        result = self.run_script('--list-axes', 'wght=700', success=False)
        self.assertIn('Axis assignments cannot be combined with --list-axes', result.stderr)
        self.run_script('--list-axes', '--instance', 'somerville-regular', success=False)
        self.assertEqual({p.name for p in self.cwd.iterdir()}, self.input_names)

    def test_unmodified_instance_uses_canonical_filename_without_prefix(self):
        self.run_script('--instance', 'somerville-caption-bold', '--validate')
        self.assert_static_math(self.cwd / 'SomervilleMathCaptionBold.ttf')
        self.assertEqual({p.name for p in self.cwd.iterdir()},
                         self.input_names | {'SomervilleMathCaptionBold.ttf', 'SomervilleCaptionBold.fontspec'})

    def test_custom_exports_require_output_prefix_before_writing(self):
        for arguments in ((), ('wght=700',),
                          ('--instance', 'somerville-regular', 'MGHT=75'),
                          ('MGHT=75', '--instance', 'somerville-regular'),
                          ('--instance', 'somerville-regular', 'Arrow Head=Large'),
                          ('--allinstances', 'MGHT=75')):
            with self.subTest(arguments=arguments):
                result = self.run_script(*arguments, '--output-dir', 'forbidden', success=False)
                self.assertIn('-o is required', result.stderr)
                self.assertEqual({p.name for p in self.cwd.iterdir()}, self.input_names)

    def test_named_axis_values_can_be_mixed_with_numbers(self):
        with TTFont(self.input) as font:
            coordinates = instantiate_somerville.resolve_coordinates(font, [
                'Width=SemiCondensed', 'Weight=ExtraBold', 'Math Weight=None',
                'Optical Size=SubHeading', 'Arrow Length=Long', 'Arrow Head=lArGe',
                'Integral Slant=semi-slanted',
            ])
            for tag, value in {'wdth': 88, 'wght': 800, 'MGHT': 0, 'opsz': 16,
                               'ARLN': 150, 'ARHD': 200, 'INSL': 50}.items():
                self.assertEqual(coordinates[tag], value)
            mixed = instantiate_somerville.resolve_coordinates(font,
                ['wght=700', 'MGHT=Heavier', 'opsz=Micro', 'Arrow Head=Largest'])
            self.assertEqual((mixed['wght'], mixed['MGHT'], mixed['opsz'], mixed['ARHD']),
                             (700, 75, 5, 200))

    def test_unknown_names_and_duplicate_axes_are_rejected(self):
        result = self.run_script('Arrow Head=unknown', '-o', 'Bad', success=False)
        self.assertIn('Unknown value', result.stderr)
        self.assertIn('Largest', result.stderr)
        self.run_script('Weight=Bold', 'wght=400', '-o', 'Bad', success=False)
        self.assertEqual({p.name for p in self.cwd.iterdir()}, self.input_names)

    def test_documented_custom_commands_work(self):
        commands = []
        lines = iter(instantiate_somerville.__doc__.splitlines())
        for line in lines:
            command = line.strip()
            if not command.startswith('python3 instantiate_somerville.py '):
                continue
            while command.endswith('\\'):
                command = command[:-1] + next(lines).strip()
            if ' -o ' in command:
                commands.append(shlex.split(command)[2:])
        self.assertGreaterEqual(len(commands), 3)
        for command in commands:
            self.run_script(*command, '--validate')
        for name in ('SomervilleMathCustom.ttf', 'SomervilleMathCustomTwo.ttf', 'SomervilleMathCustomThree.ttf', 'SomervilleMathCustomFour.ttf'):
            self.assert_static_math(self.cwd / name)

    def test_alias_duplicates_are_rejected_before_export(self):
        result = self.run_script('--instance', 'somerville-regular', 'Regular', success=False)
        self.assertIn('Duplicate instances', result.stderr)
        self.assertEqual({p.name for p in self.cwd.iterdir()}, self.input_names)

    def test_existing_output_requires_overwrite(self):
        output = self.cwd / 'SomervilleMathCustom.ttf'
        output.write_bytes(b'keep me')
        self.run_script('-o', 'Custom', success=False)
        self.assertEqual(output.read_bytes(), b'keep me')
        self.run_script('-o', 'Custom', '--overwrite', '--validate')
        self.assert_static_math(output)

    def test_input_hardlink_cannot_be_overwritten(self):
        before = self.input.read_bytes()
        os.link(self.input, self.cwd / 'SomervilleMathCustom.ttf')
        result = self.run_script('-o', 'Custom', '--overwrite', success=False)
        self.assertIn('replace an input font', result.stderr)
        self.assertEqual(self.input.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
