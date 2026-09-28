import sys,json
from pathlib import Path
from math import factorial
sys.path.insert(0,'src')
from anlp_project.reconstruct import stable_hash,atomic_write_json
root=Path('artifacts/reconstruct/target-example-w')
run=json.loads((root/'run.json').read_text())
notes={
0:(True,'Defining quadrature condition and first moment; answer and second moment determine absolute sum only.','The answer gives (alpha-beta)^2=4/3. Together with sum of squares8/3 this gives (alpha+beta)^2=4, hence either sign. Original positive sum is not identified.'),
13:(True,'Dividend/product operation.','Unit domain is supported; requested remainder retained, but no product operation is specified.'),
46:(True,'Three column heights.','Within positive unordered integer partitions of8 into3 heights, multinomial560 uniquely selects2,3,3. This is an inverse constraint search, not verbatim question copying. Leakage audits still required.'),
62:(True,'Exact function and center, global singularity structure.','One negative Laurent term alone does not force infinite outer radius; a regular part may have finite singularities.'),
87:(False,'Original small-o limit hypothesis and differentiability-neighborhood target.','Assignments near1/n alone do not imply f(x)/x^2 tends to0: elsewhere, including negative x, values remain unconstrained. Public local observations are true, but private recoverability explanation overstates them.'),
80:(True,'Specific components and curve.','Potential nearly complete-solution exposure: both partial derivatives and zero Green integrand already provide the zero-integral argument. Missing original functions cannot automatically excuse full proof exposure.'),
96:(True,'Nested integrals and g hypotheses.','Potential nearly complete-solution exposure: F(x)~x^8/12 and sin(F(x))/x^8 leave only sin(u)/u. Must not admit merely because inner definitions are withheld.'),
118:(True,'Associated-value formula (k^2-1)/8.','Target odd integer retained but undefined associated relation allows many replacements. Original asks a witness; do not silently impose positivity or uniqueness.'),
129:(True,'Word length.','Converter claims length12 identifiable; exact modular recurrence also gives1392 at lengths35,307,etc. Valid original reconstruction may still be possible, but uniqueness is false without a bound. No post-hoc length cap will be added.'),
137:(True,'Maximal-planarity and original equal degree groups3,4,5.','Answer n=6 and handshaking yield e=12, but do not force the missing maximal-planar relation. Degree-sum4n is weaker than the original degree distribution; many graphs satisfy it.')}
rows=[]
for key,bank in run['banks'].items():
 i=bank['source_index']
 if i not in notes:continue
 target,missing,note=notes[i]
 clues=bank['output']['clues']
 rows.append(dict(source_index=i,bank_key=key,bank_output_hash=stable_hash(bank['output']),explicit_target_role=target,clue_count=len(clues),public_clue_word_count=sum(len(c['sentence'].split()) for c in clues),withheld_elements=missing,note=note))
parts=[(a,b,8-a-b) for a in range(1,7) for b in range(a,8-a) if b<=8-a-b]
v=[1]*7;hits=[]
for n in range(1,10001):
 if sum(v)%2008==1392:hits.append(n)
 v=[((v[d-1] if d else 0)+(v[d+1] if d<6 else 0))%2008 for d in range(7)]
result=dict(stage='Before W audits and student generation; initial10 banks only, two technical retries pending',reviewer='assistant analytic review, not independent human gold',notes_are_hypotheses_not_gate_overrides=True,rows=rows,checks={'46_positive_unordered_partitions':[{'heights':p,'count':factorial(8)//(factorial(p[0])*factorial(p[1])*factorial(p[2]))} for p in parts],'129_length_search_max':10000,'129_first_matching_lengths':hits[:12],'129_uniqueness_claim_refuted':True},policy='No manual per-source clue edits; preserve unknown/ambiguous cases and all12 coverage denominator. Audit exact public input jointly with final answer.')
assert not (root/'preaudit-content-review.json').exists()
atomic_write_json(root/'preaudit-content-review.json',result)
print('Saved10 exact-bank annotations and two finite computation checks')
