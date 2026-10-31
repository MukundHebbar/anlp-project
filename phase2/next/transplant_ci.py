#!/usr/bin/env python3
"""Paired bootstrap CIs for the transplant adapters vs the plain SOLVE adapter (ProcessBench F1 and d', synthetic F1,
SOLVE dev accuracy). Resamples items (JUDGE) or questions (SOLVE), 2,000 times."""
import collections, json, random, sys
from pathlib import Path
from statistics import NormalDist
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src")); sys.path.insert(0, str(HERE.parents[0] / "scripts")); sys.path.insert(0, str(HERE))
import hint_pilot as hp
z = NormalDist().inv_cdf
B = 2000


def f1(recs):
    err = [r for r in recs if r["label"] >= 0]; cor = [r for r in recs if r["label"] < 0]
    ae = sum(r["pred"] == r["label"] for r in err) / len(err); ac = sum(r["pred"] == -1 for r in cor) / len(cor)
    return 100 * 2 * ae * ac / (ae + ac) if ae + ac else 0


def dprime(recs):
    v = [r for r in recs if r["pred"] is not None]
    pos = [r for r in v if r["label"] >= 0]; neg = [r for r in v if r["label"] < 0]
    h = (sum(r["pred"] >= 0 for r in pos) + .5) / (len(pos) + 1); f = (sum(r["pred"] >= 0 for r in neg) + .5) / (len(neg) + 1)
    return z(h) - z(f)


def main(dirs):
    judge, solve = {}, {}
    for d in dirs:
        for p in Path(d).glob("judge-*.jsonl"):
            judge.setdefault(p.stem[6:], {r["uid"]: r for r in hp.read_jsonl([p])})
        for p in Path(d).glob("solve-*.jsonl"):
            n = p.stem[6:]
            rows = hp.read_jsonl([p])
            if n not in solve or len(rows) > sum(len(v) for v in solve[n].values()):
                g = collections.defaultdict(list)
                for r in rows:
                    g[r["uid"]].append(r["correct_strict"])
                solve[n] = g
    ref = "solve"; rng = random.Random(0)
    uids = {k: sorted(u for u, r in judge[ref].items() if r["subset"] == k or (k == "pb" and r["subset"] in ("gsm8k", "math")))
            for k in ("pb", "synthetic")}
    print(f"{'adapter':18s} {'PB F1 (diff, 95% CI)':30s} {'PB dprime diff':22s} {'synthetic F1 diff':24s} {'SOLVE acc (diff)':26s}")
    for name in sorted(judge, key=lambda n: (n != "solve", n)):
        out = []
        for k, fn in (("pb", f1), ("pb", dprime), ("synthetic", f1)):
            us = uids[k]
            a = [judge[name][u] for u in us]; b = [judge[ref][u] for u in us]
            obs = fn(a) - fn(b)
            bs = []
            for _ in range(B):
                idx = [rng.randrange(len(us)) for _ in us]
                bs.append(fn([a[i] for i in idx]) - fn([b[i] for i in idx]))
            bs.sort()
            base = fn(a)
            out.append(f"{base:6.2f} ({obs:+.2f} [{bs[50]:+.2f},{bs[1949]:+.2f}])")
        if name in solve:
            q = sorted(set(solve[name]) & set(solve[ref]))
            acc = lambda s, qs: 100 * sum(sum(s[u]) / len(s[u]) for u in qs) / len(qs)
            obs = acc(solve[name], q) - acc(solve[ref], q)
            bs = sorted(acc(solve[name], qq) - acc(solve[ref], qq) for qq in ([q[rng.randrange(len(q))] for _ in q] for _ in range(B)))
            out.append(f"{acc(solve[name], q):5.1f} ({obs:+.1f} [{bs[50]:+.1f},{bs[1949]:+.1f}]) n={len(solve[name][q[0]])}")
        print(f"{name:18s} " + "  ".join(out))


if __name__ == "__main__":
    main(sys.argv[1:])
