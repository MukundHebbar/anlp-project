"""Fail-closed evidence checks for the prospective semantic-recovery endpoint.

These validate recorded assertions, not the truth of a model's mathematics.
Independent review remains required for every counted recovery.
"""
import json
from .reconstruct import is_grounded_success, validate_source_recovery, stable_hash


LEAK_FLAGS = ('direct_question_copy', 'premise_target_bundle_exposed', 'complete_solution_exposed')


def check_student_readiness(run, index, evidence):
    gate=run.get('metadata',{}).get('student_readiness')
    if gate is None:
        return  # Historical protocols retain their original behavior.
    if gate.get('status')!='ready':
        raise ValueError('Frozen diagnostic is not ready: disclosure/copy reviews are pending')
    if gate.get('approved_evidence_hashes',{}).get(str(index))!=stable_hash(evidence):
        raise ValueError('Student input differs from the reviewed frozen evidence')


def verify_response_bindings(response_key, response, evaluation, semantic, source):
    """Reject legacy/unbound or stale records rather than invent their provenance."""
    try:
        evidence_hash=stable_hash(response['public_evidence'])
        index=response['source_index']
        return bool(
            evaluation['response_key']==semantic['response_key']==response_key
            and evaluation['source_index']==semantic['source_index']==index
            and response['evidence_hash']==evaluation['evidence_hash']==evidence_hash
            and evaluation['response_output_hash']==stable_hash(response['output'])
            and semantic['candidate_question_hash']==stable_hash(response['output']['question'])
            and semantic['source_question_hash']==stable_hash(source['question']))
    except (KeyError,TypeError):
        return False


def public_disclosure_text(answer, bank, scope):
    """Exact rendered public fields plus decoded sentence values, no source data."""
    label='PUBLIC FINAL ANSWER' if scope=='source_disclosure' else 'FINAL ANSWER'
    payload={'role_cue_id':bank.get('role_cue_id'),
             'clues':[{'id':c['id'],'sentence':c['sentence']} for c in bank['clues']]}
    return (f'{label}: {answer}\nPUBLIC OBSERVATIONS:\n'+json.dumps(payload,ensure_ascii=False,indent=2)
            +'\n'+'\n'.join(c['sentence'] for c in bank['clues']))


def validate_strict_disclosure(value, public_text, scope):
    if value.get('scope') != scope:
        raise ValueError('Wrong disclosure review scope')
    if value.get('status') not in {'ACCEPT','REJECT','NEEDS_REVIEW'}:
        raise ValueError('Invalid disclosure decision')
    if any(type(value.get(key)) not in (bool,type(None)) for key in LEAK_FLAGS):
        raise ValueError('Leak flags must be Boolean or explicit null')
    if any(key not in value for key in LEAK_FLAGS):
        raise ValueError('Missing leak flag')
    quotes=value.get('public_quotes')
    if not isinstance(quotes,list) or not quotes:
        raise ValueError('Disclosure review needs exact public evidence')
    if any(not isinstance(q,str) or not q.strip() or q not in public_text for q in quotes):
        raise ValueError('Disclosure review quotes hidden or nonexistent text')
    for key in ('missing_essential_element','inference_required','reason'):
        if not isinstance(value.get(key),str) or not value[key].strip():
            raise ValueError(f'Missing disclosure explanation: {key}')
    if value['status']=='ACCEPT' and any(value[k] is not False for k in LEAK_FLAGS):
        raise ValueError('Acceptance contradicts leak flags or unresolved flags')
    if value['status']=='REJECT' and not any(value[k] is True for k in LEAK_FLAGS):
        raise ValueError('Rejection needs an identified disclosure defect; otherwise review')
    return value


def recovery_gate(grounding, semantic, evidence):
    """Only verified, non-leaking, semantically recovered cases count.

Evidence fields refer to the same hashed exact input/response. The assembler
must establish that binding; this function cannot infer it from prose.
"""
    reasons=[]
    if not is_grounded_success(grounding): reasons.append('not_grounded')
    if grounding.get('score') not in {3,4} or grounding.get('justification') not in {'sufficient','minor_omission'}:
        reasons.append('sound_verification_unverified')
    n=evidence.get('displayed_clue_count')
    checks=grounding.get('clue_checks',[])
    indices=[c.get('index') for c in checks if isinstance(c,dict)] if isinstance(checks,list) else []
    if (type(n) is not int or n<1 or len(indices)!=n
        or any(type(i) is not int for i in indices) or set(indices)!=set(range(1,n+1))):
        reasons.append('complete_clue_coverage_unverified')
    try:
        validate_source_recovery(semantic,strict=True)
        if semantic.get('source_recovery')!=2: reasons.append('not_same_source_question')
    except (ValueError,TypeError,AttributeError):
        reasons.append('semantic_record_invalid_or_missing')
    for field in ('source_supported','public_disclosure_passed','source_disclosure_passed',
                  'copy_challenge_reviewed_no_direct_recovery','independent_math_review_passed',
                  'independent_semantic_review_passed','exact_record_binding_verified'):
        if evidence.get(field) is not True: reasons.append(field+'_unverified')
    return {'confirmed_grounded_semantic_recovery':not reasons,'reasons':reasons}


def validate_copy_challenge(value, public_text):
    """Validate attribution, without pretending it proves semantic coverage."""
    if value.get('status') not in {'direct_candidate','no_direct_reconstruction','needs_review'}:
        raise ValueError('Invalid copy-challenge status')
    if not isinstance(value.get('reason'),str) or not value['reason'].strip():
        raise ValueError('Copy challenge lacks a reason')
    alignments=value.get('alignments')
    if not isinstance(alignments,list):raise ValueError('Copy challenge lacks alignments')
    question=value.get('question')
    if value['status']!='direct_candidate':
        if question is not None or alignments:
            raise ValueError('A non-candidate must not supply a question or alignments')
        return value
    if not isinstance(question,str) or not question.strip() or not alignments:
        raise ValueError('Direct copy candidate needs a question and alignments')
    for a in alignments:
        if not isinstance(a,dict):raise ValueError('Invalid copy alignment')
        for field,target in [('question_span',question),('public_quote',public_text)]:
            s=a.get(field)
            if not isinstance(s,str) or not s.strip() or s not in target:
                raise ValueError('Copy alignment cites absent text')
        if a.get('operation') not in {'copy','paraphrase','rename','reorder','grammatical_assembly'}:
            raise ValueError('Unpermitted copy transformation')
    return value


def normalize_non_candidate_copy_annotations(value, public_text):
    """Drop only verified public-fragment annotations when no question was emitted.

    The caller must preserve the raw response and this normalization's provenance.
    Never change a verdict, discard a proposed question, or repair invented quotes.
    """
    if value.get('status') != 'no_direct_reconstruction' or value.get('question') is not None:
        raise ValueError('Recovery requires an unchanged no-candidate verdict and null question')
    annotations = value.get('alignments')
    if not isinstance(annotations, list) or not annotations:
        raise ValueError('No explanatory annotations to normalize')
    for annotation in annotations:
        if not isinstance(annotation, dict) or annotation.get('operation') != 'copy':
            raise ValueError('Only exact-copy fragment annotations can be normalized')
        for field in ('question_span', 'public_quote'):
            text = annotation.get(field)
            if not isinstance(text, str) or not text.strip() or text not in public_text:
                raise ValueError('Annotation contains non-public text')
    return validate_copy_challenge({**value, 'alignments': []}, public_text)


def confirmation_recovery_count(source_indices, rows):
    """Count the prospective 5/25 endpoint, never authorize overall release.

    The caller supplies the previously frozen source-family manifest. Each row
    contains the actual source/response/judgments and independently assembled
    review evidence. This checks record bindings, not reviewers' mathematics or
    the manifest's historical freeze time. Missing rows remain in the denominator.
    """
    if (len(source_indices) != 25
            or any(type(i) is not int for i in source_indices)
            or len(set(source_indices)) != 25):
        raise ValueError('Confirmation requires exactly 25 distinct source-family IDs')
    by_source = {}
    for row in rows:
        index = row.get('source_index')
        if type(index) is not int or index not in source_indices:
            raise ValueError('Response outside the frozen confirmation manifest')
        if index in by_source:
            raise ValueError('Multiple primary rows for one source family')
        by_source[index] = row

    outcomes = []
    for index in source_indices:
        row = by_source.get(index)
        if row is None:
            outcomes.append({'source_index': index, 'counted': False,
                             'reasons': ['missing_primary_record']})
            continue
        response = row.get('response') or {}
        evaluation = row.get('evaluation') or {}
        semantic = row.get('semantic') or {}
        evidence = dict(row.get('evidence') or {})
        # Never trust a caller's pre-filled binding assertion.
        evidence['exact_record_binding_verified'] = verify_response_bindings(
            row.get('response_key'), response, evaluation, semantic,
            row.get('source') or {})
        result = recovery_gate(evaluation.get('output') or {},
                               semantic.get('output') or {}, evidence)
        reasons = result['reasons']
        if not isinstance(row.get('response_key'), str) or not row['response_key']:
            reasons.append('missing_response_key')
        seed = response.get('sampling', {}).get('seed')
        if type(seed) is not int or seed != 0:
            reasons.append('not_primary_seed_0')
        if response.get('source_index') != index:
            reasons.append('manifest_response_source_mismatch')
        outcomes.append({'source_index': index, 'counted': not reasons,
                         'reasons': reasons})
    count = sum(row['counted'] for row in outcomes)
    return {'confirmed_successes': count, 'preselected_families': 25,
            'minimum_required': 5, 'recovery_count_gate_passed': count >= 5,
            'overall_release_assessed': False, 'outcomes': outcomes}
