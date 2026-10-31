"""Gemma reward judge using the explicit-label protocol of the full calibration."""
import json
import math
from pathlib import Path
import urllib.request

from .qwen_judging import QwenJudge, render_question

MODEL = 'google/gemma-4-12B-it'
REVISION = '707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7'


def read_probabilities(top, labels, label_ids):
    """Keep all requested spellings; reject incomplete responses instead of inventing labels."""
    masses = []
    for label in labels:
        values = []
        for token_id in label_ids[label.lower()]:
            key = f'token_id:{token_id}'
            if key not in top:
                raise ValueError(f'Missing requested label token {key}')
            values.append(math.exp(top[key]))
        masses.append(sum(values))
    mass = sum(masses)
    if mass <= 0 or not math.isfinite(mass):
        raise ValueError('Invalid allowed-label probability mass')
    return [p/mass for p in masses], mass


class GemmaJudge(QwenJudge):
    def __init__(self, tokenizer_path, calibration_dir, port=8002):
        super().__init__(tokenizer_path, port=port, served_name='reward-judge')
        folder = Path(calibration_dir)
        metadata = json.loads((folder / 'metadata.json').read_text())
        source = metadata['model_source']
        local_source = json.loads((Path(tokenizer_path) / 'source.json').read_text())
        if source['model'] != MODEL or source['revision'] != REVISION or local_source != source:
            raise ValueError('Gemma model files do not match the calibrated source')
        if metadata.get('label_protocol') != 'explicit':
            raise ValueError('Reward judge requires explicit-label calibration')
        self.label_ids = metadata['label_token_ids']
        calibration = json.loads((folder / 'calibration.json').read_text())
        if calibration['model'] != MODEL:
            raise ValueError('Reward calibration model mismatch')
        # User accepted the measured reconstruction limitations; do not replace its scoring protocol.
        self.cutoffs = calibration['cutoffs']

    def call(self, state, questions):
        names = list(questions)
        rendered = [render_question(state, questions[name]) for name in names]
        token_ids = sorted({i for _, labels, _ in rendered for label in labels
                            for i in self.label_ids[label.lower()]})
        body = {'model': self.name,
                'prompt': [self.tok.encode(self.prompt(user), add_special_tokens=False) for user, _, _ in rendered],
                'max_tokens': 1, 'temperature': 0.0, 'seed': 0, 'logprobs': 1,
                'logprob_token_ids': token_ids, 'return_tokens_as_token_ids': True}
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), method='POST',
                                         headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=600) as response:
            result = json.loads(response.read())
        if sorted(c['index'] for c in result['choices']) != list(range(len(names))):
            raise ValueError('Incomplete or duplicated judge choices')
        self.tokens += result.get('usage', {}).get('prompt_tokens', 0)
        answers = {}
        for choice in result['choices']:
            index = choice['index']
            name = names[index]
            labels, meaning = rendered[index][1:]
            probabilities, mass = read_probabilities(choice['logprobs']['top_logprobs'][0], labels, self.label_ids)
            kind = questions[name]['type']
            if kind == 'score':
                answer = {'type': kind, 'score': sum(i*p for i,p in enumerate(probabilities)),
                          'probabilities': dict(zip(labels, probabilities)), 'mass': mass}
            elif kind == 'noul':
                answer = {'type': kind, 'noul': probabilities[0], 'mass': mass}
            else:
                answer = {'type': kind, 'choice': meaning[max(range(len(probabilities)), key=probabilities.__getitem__)],
                          'probabilities': dict(zip(meaning, probabilities)), 'mass': mass}
            answers[name] = answer
        return {'model': MODEL, 'answers': answers}
