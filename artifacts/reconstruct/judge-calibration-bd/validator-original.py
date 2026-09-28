"""Fail closed on malformed or contradictory PC judge certificates.

These checks enforce evidence structure, not mathematical truth.
"""


def validate_judgment(out, role, *, question, response=None, clue_count=0):
    if role not in ('fidelity', 'validity'):
        raise ValueError('Unknown judge role')
    if out.get('status') not in ('scored', 'needs_review'):
        raise ValueError('Invalid status')
    fields = (('premise_fidelity', 'target_fidelity') if role == 'fidelity'
              else ('evidence_integration', 'mathematical_validity'))
    for field in fields:
        value = out.get(field, {}).get('score', 'missing')
        if value is not None and (type(value) is not int or not 0 <= value <= 4):
            raise ValueError('Invalid score: ' + field)
        if value is None and out['status'] == 'scored':
            raise ValueError('Unresolved dimension marked scored')
    certificate = out.get('verification_certificate', {})
    required = (('source_target', 'candidate_target', 'premise_comparison', 'target_comparison')
                if role == 'fidelity' else
                ('requested_quantity', 'independent_check', 'response_check'))
    for field in required:
        if not isinstance(certificate.get(field), str) or not certificate[field].strip():
            raise ValueError('Missing certificate: ' + field)

    def boolean(value):
        if value is not None and type(value) is not bool:
            raise ValueError('Invalid Boolean label')
        if value is None and out['status'] == 'scored':
            raise ValueError('Unresolved label marked scored')

    if role == 'fidelity':
        for field in ('semantic_equivalent', 'answer_in_premise'):
            boolean(out.get(field, 'missing'))
        if out['semantic_equivalent'] is True and any(out[f]['score'] != 4 for f in fields):
            raise ValueError('Equivalence contradicts dimensions')
        if all(out[f]['score'] == 4 for f in fields) and out['semantic_equivalent'] is False:
            raise ValueError('Full fidelity contradicts non-equivalence')
        return out

    checks = out['evidence_integration'].get('clue_checks', [])
    indices = [c.get('index') for c in checks]
    if (any(type(i) is not int for i in indices)
            or sorted(indices) != list(range(1, clue_count + 1))):
        raise ValueError('Incomplete/duplicate clue checks')
    for check in checks:
        if check.get('verdict') not in ('grounded', 'partial', 'unsupported', 'contradicted', 'uncertain'):
            raise ValueError('Invalid clue verdict')
        if not isinstance(check.get('reason'), str) or not check['reason'].strip():
            raise ValueError('Missing clue reason')
    math = out['mathematical_validity']
    flags = ('question_well_posed', 'supplied_answer_correct', 'verification_sound')
    for field in flags:
        boolean(math.get(field, 'missing'))
    if math['score'] in (3, 4) and any(math[f] is not True for f in flags):
        raise ValueError('High mathematical score contradicts verification')
    strings = []
    def collect(value):
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
    collect(response or {'question': question})
    for check in math.get('checks', []):
        quote = check.get('claim_quote')
        if not isinstance(quote, str) or not quote or not any(quote in s for s in strings):
            raise ValueError('Mathematical claim quote not in response')
        if not isinstance(check.get('reason'), str) or not check['reason'].strip():
            raise ValueError('Missing claim check')
    shortcut = out.get('shortcut', {})
    boolean(shortcut.get('present', 'missing'))
    if shortcut['present'] is True:
        kind = shortcut.get('type')
        if kind not in ('answer-copy tautology', 'copy-only restatement', 'no usable question'):
            raise ValueError('Unknown shortcut type')
        if not isinstance(shortcut.get('evidence'), str) or not shortcut['evidence'].strip():
            raise ValueError('Missing shortcut evidence')
        quotes = (('premise_quote', 'target_quote') if kind == 'answer-copy tautology'
                  else ('target_quote',) if kind == 'copy-only restatement' else ())
        for field in quotes:
            quote = shortcut.get(field)
            if not isinstance(quote, str) or not quote or quote not in question:
                raise ValueError('Shortcut quote not in question: ' + field)
    elif shortcut['present'] is False and shortcut.get('type') is not None:
        raise ValueError('False shortcut with positive type')
    return out
