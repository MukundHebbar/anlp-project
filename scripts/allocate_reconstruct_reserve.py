#!/usr/bin/env python3
"""Freeze topic-balanced unused source allocation with conservative lexical screening.

Does not inspect student outcomes or claim semantic-family independence.
"""
import argparse
import hashlib
import json
import random
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path


def normalized(question):
    return re.sub(r'\s+', '', question.lower())


def shingles(text):
    return {text[i:i+5] for i in range(max(1, len(text)-4))}


def allocate(run, seed=20260922):
    ids = sorted(map(int, run['sources']))
    texts = {i: normalized(run['sources'][str(i)]['question']) for i in ids}
    grams = {i: shingles(texts[i]) for i in ids}
    masked = {i: re.sub(r'\d+(?:\.\d+)?', '#', texts[i]) for i in ids}
    flagged, similarities = [], []
    for i,j in combinations(ids,2):
        union = grams[i] | grams[j]
        overlap = len(grams[i] & grams[j]) / len(union) if union else 1.
        similarities.append((overlap,i,j))
        if masked[i] == masked[j] or overlap >= .8:
            flagged.append({'sources':[i,j], 'character_5gram_jaccard':overlap,
                            'same_digit_masked_text':masked[i]==masked[j]})
    quarantine = sorted({i for pair in flagged for i in pair['sources'] if i in run['partitions']['reserve']})
    by_topic = defaultdict(list)
    for i in run['partitions']['reserve']:
        if i not in quarantine:
            by_topic[run['sources'][str(i)]['broad_topic']].append(i)
    rng = random.Random(seed)
    allocated = {'D3':[], 'R':[], 'contingency':[]}
    for topic in sorted(by_topic):
        pool = sorted(by_topic[topic])
        rng.shuffle(pool)
        if len(pool) < 9:
            raise ValueError(f'Insufficient screened sources for topic {topic}')
        allocated['D3'].extend(pool[:3])
        allocated['R'].extend(pool[3:9])
        allocated['contingency'].extend(pool[9:])
    allocated = {k:sorted(v) for k,v in allocated.items()}
    flat = sum(allocated.values(), []) + quarantine
    assert sorted(flat) == sorted(run['partitions']['reserve']) and len(flat)==len(set(flat))
    return {'schema':'reconstruct_reserve_allocation_v1','allocation_seed':seed,
            'source_content_sha256':hashlib.sha256(json.dumps(texts,sort_keys=True).encode()).hexdigest(),
            'rule':'Three D3 and six R sources per broad topic, seeded shuffle; all others contingency. Quarantine reserve members of flagged lexical pairs before allocation.',
            'roles':{'D3':'fresh development replication; becomes development once inspected',
                     'R':'untouched replication reserved until candidate freeze',
                     'contingency':'unused replacement/expansion pool; no performance-based substitution'},
            'partitions':allocated,'quarantined':quarantine,
            'existing_partitions_unchanged':{k:v for k,v in run['partitions'].items() if k!='reserve'},
            'screen':{'threshold':.8,'threshold_status':'conservative design choice, not empirically validated',
                      'flagged_pairs':flagged,'highest_overlap_pairs':[{'sources':[i,j],'jaccard':score} for score,i,j in sorted(similarities,reverse=True)[:20]],
                      'limitations':'Lexical overlap and digit masking miss paraphrases and related mathematical families. Semantic family review is required before claiming source-family-independent confirmation.'},
            'source_metadata':{str(i):{k:run['sources'][str(i)][k] for k in ['broad_topic','topic','difficulty']} for i in flat}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    result = allocate(json.loads(a.run.read_text()))
    if a.output.exists() and json.loads(a.output.read_text()) != result:
        raise ValueError('Refusing to overwrite a different frozen allocation')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'partitions':result['partitions'],'quarantined':result['quarantined'],'flagged_pairs':result['screen']['flagged_pairs']},indent=2))


if __name__ == '__main__':
    main()
