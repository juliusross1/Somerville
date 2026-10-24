from pathlib import Path
import shutil
p=Path('/tmp/somerville-fenced-prescripts/tests')
shutil.copy2('/Users/juliusross/Documents/Somerville/test_documents/Somerville/context/somerville.lfg',p/'somerville.lfg')
(p/'probe-on.lfg').write_text('return {name="probe-on",mathematics={tweaks={aftercopying={{tweak="setoptions",set={"separateprescriptkerns"}}}}}}\n')
(p/'probe-off.lfg').write_text('''mathematics.tweaks.probeoff = function(target)
 local code=tex.mathcontrolcodes
 local control=(tex.get("mathfontcontrol") & (~code.separateprescriptkerns)) | code.usefontcontrol
 target.mathcontrol=control; target.properties.mathcontrol=control
end
return {name="probe-off",mathematics={tweaks={aftercopying={{tweak="probeoff"}}}}}
''')
s=''
for mode in ['on','off']:
 s+=rf'''\definefontfeature[{mode}][goodies={{somerville,probe-{mode}}}]
\starttypescript[math][probe-{mode}]
\definefontsynonym[MathRoman][file:FenceProbe.ttf][features={{math\mathsizesuffix,mathextra,{mode}}}]
\stoptypescript
\definetypeface[probe-{mode}][rm][serif][modern][default]
\definetypeface[probe-{mode}][mm][math][probe-{mode}][default]
'''
s+=r'''\setupbodyfont[probe-on,12pt]
\startluacode
userdata.probe = function(label)
 local kerns={}
 local function walk(head)
  for n in node.traverse(head) do
   if node.type(n.id)=='kern' and n.subtype==11 then kerns[#kerns+1]=n.kern end
   if n.list then walk(n.list) end
  end
 end
 walk(tex.box[0].list)
 texio.write_nl('term and log','RESULT '..label..' '..tostring(tex.box[0].width)..' '..table.concat(kerns,','))
end
\stopluacode
\def\Probe#1#2{\setbox0=\hbox{\m{#2}}\ctxlua{userdata.probe("#1")}\dontleavehmode\box0\par}
\starttext
'''
for mode in ['off','on']:
 s+=rf'\switchtobodyfont[probe-{mode},12pt]'+'\n'
 for size in [1,5,10,20]:
  for fence in ['parenthesis','bracket','brace']:
   base=rf'\fenced[{fence}][size={size}]{{x}}'
   for kind,suffix in [('upper',r'^^^{\rm M}'),('lower',r'___{\rm M}'),('both',r'___{\rm M}^^^{\rm M}'),('multi',r'___{\rm MM}^^^{\rm MM}'),('posts',r'_{\rm M}^{\rm M}___{\rm M}^^^{\rm M}')]:
    s+=rf'\Probe{{{mode}-{fence}-{size}-{kind}}}{{{base}{suffix}}}'+'\n'
 for label,expr in [('glyph',r'M___{\rm M}^^^{\rm M}'),('nested',r'\fenced[parenthesis][size=20]{\fenced[brace][size=5]{x}}___{\rm MM}^^^{\rm MM}'),('invisible',r'\left.\fenced[parenthesis][size=20]{x}\right)___{\rm MM}^^^{\rm MM}'),('scriptstyle',r'\scriptstyle\fenced[parenthesis][size=20]{x}___{\rm M}^^^{\rm M}')]:
  s+=rf'\Probe{{{mode}-{label}}}{{{expr}}}'+'\n'
s+=r'\stoptext'+'\n'
(p/'fence-tests.tex').write_text(s)
