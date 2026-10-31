"""Paired bootstrap over problems for the AUROC difference between two judges on the same own attempts.

    python phase2/selfjudge/auroc_ci.py --split dev mixed sj-step16
"""
import argparse, collections, json, random
from pathlib import Path
EVAL = Path(__file__).resolve().parents[1] / "runs" / "selfjudge" / "eval"


def auroc(pairs):
    """pairs: (score, is_wrong). Rank AUROC with ties averaged."""
    pairs = sorted(pairs)
    rank_sum, n1, i = 0.0, 0, 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        w = sum(p[1] for p in pairs[i:j])
        rank_sum += w * (i + j + 1) / 2; n1 += w; i = j
    n0 = len(pairs) - n1
    return (rank_sum - n1 * (n1 + 1) / 2) / (n1 * n0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--split", default="dev"); ap.add_argument("a"); ap.add_argument("b")
    a = ap.parse_args()
    load = lambda n: {(r["uid"], r["attempt"]): r for r in map(json.loads, open(EVAL / a.split / f"{n}.jsonl"))}
    A, B = load(a.a), load(a.b)
    by = collections.defaultdict(list)
    for k in sorted(set(A) & set(B)):
        by[k[0]].append(k)
    qs = sorted(by)
    diff = lambda ks: (auroc([(B[k]["p_incorrect"], not B[k]["correct"]) for k in ks])
                       - auroc([(A[k]["p_incorrect"], not A[k]["correct"]) for k in ks]))
    rng = random.Random(0)
    bs = sorted(diff([k for _ in qs for k in by[qs[rng.randrange(len(qs))]]]) for _ in range(2000))
    print(f"AUROC {a.b} - {a.a}: {diff([k for q in qs for k in by[q]]):+.3f} [{bs[50]:+.3f}, {bs[1949]:+.3f}]")
