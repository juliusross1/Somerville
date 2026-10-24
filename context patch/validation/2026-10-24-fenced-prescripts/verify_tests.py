from pathlib import Path
import json
root=Path(__file__).parent
def rows(name):
 out={}
 for line in (root/name).read_text().splitlines():
  if line.startswith('RESULT '):
   p=line.split();out[p[1]]={'width':int(p[2]),'kerns':[int(x) for x in p[3].split(',')] if len(p)>3 else []}
 return out
old=rows('old-console.log');new=rows('new-console.log');zero=rows('zero-console.log');positive=rows('positive-console.log');assembly=rows('assembly-console.log')
assert len(old)==len(new)==len(zero)==len(positive)==128
for key in old:
 if key.startswith('off-') or key=='on-glyph':assert old[key]==new[key],key
for fence in ['parenthesis','bracket','brace']:
 for size in [1,5,10,20]:
  prefix=f'on-{fence}-{size}-'
  for case,expect in [('upper',[-333270]),('lower',[-31740]),('both',[-333270,-31740]),('multi',[-380880,-126960])]:
   assert new[prefix+case]['kerns']==expect,(prefix+case,new[prefix+case],expect)
  assert zero[prefix+'multi']['kerns']==[]
  assert positive[prefix+'multi']['kerns']==[380880,126960]
  assert zero[prefix+'upper']['kerns']==[47610]
  assert zero[prefix+'lower']['kerns']==[95220]
assert new['on-invisible']==old['on-invisible']
assert new['on-nested']['kerns']==[-380880,-126960]
assert new['on-scriptstyle']['kerns']==[-248651,-21202]
for fence in ['parenthesis','bracket','brace']:
 assert assembly['assembly-'+fence]['kerns']==[-471600,-157200]
report={'comparative_cases':128,'disabled_cases_unchanged':64,'zero_corner_cases':128,'positive_corner_cases':128,'assembly_document_cases':len(assembly),'single_glyph_unchanged':True,'independent_corner_and_script_contribution_assertions':'passed','multi_character_delimiter_only':'passed','invisible_left_fence':'passed','nested_fences':'passed','script_style_scaling':'passed','assembled_parenthesis_bracket_brace':'passed'}
(root/'validation-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
