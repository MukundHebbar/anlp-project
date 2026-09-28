"""Explicit source normalization for open-ended RECONSTRUCT experiments."""
import copy
import re


def normalize_option_answer(source):
    """Resolve a standalone option label only when its explicit choice is unique.

    Preserve the original question and answer as provenance. This does not
    verify that the selected option is mathematically correct.
    """
    result = copy.deepcopy(source)
    answer = source['final_answer'].strip()
    if not re.fullmatch(r'[A-H]', answer):
        return result
    matches = list(re.finditer(r'^\s*([A-H])[.)]\s+(.+?)\s*$', source['question'], re.M))
    if len(matches) < 2:
        return result  # A symbolic answer such as A is not necessarily a label.
    labels = [m.group(1) for m in matches]
    if len(labels) != len(set(labels)):
        raise ValueError('Ambiguous duplicate option labels; source requires review')
    for index, match in enumerate(matches):
        end = matches[index+1].start() if index+1 < len(matches) else len(source['question'])
        if source['question'][match.end():end].strip():
            raise ValueError('Only explicit single-line options are supported; source requires review')
    selected = [m.group(2) for m in matches if m.group(1)==answer]
    if len(selected) != 1:
        raise ValueError('Final option label has no unique explicit answer')
    result['final_answer'] = selected[0]
    result['answer_normalization'] = {
        'method':'unique explicit option-label lookup, no mathematical repair',
        'original_answer':source['final_answer'], 'normalized_answer':selected[0]}
    return result
