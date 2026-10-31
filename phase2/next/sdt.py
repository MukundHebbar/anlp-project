#!/usr/bin/env python3
"""Signal-detection decomposition of checking ability: sensitivity (d') vs response bias (criterion c).

Hit rate H = says "incorrect" on wrong solutions; false-alarm rate F = says "incorrect" on correct solutions.
d' = z(H) - z(F) (how well the model separates them); c = -(z(H) + z(F)) / 2 (negative = quick to say "incorrect").
Sources: the GRPO report's JUDGE test table (verdicts per label), ProcessBench predictions, the tutor verdicts.
CPU only, reads committed results.
"""

import collections, gzip, json
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1] / "results"
z = NormalDist().inv_cdf


def sdt(h, f, n_pos, n_neg):
    # log-linear correction keeps z finite at 0 or 1
    h = (h * n_pos + 0.5) / (n_pos + 1); f = (f * n_neg + 0.5) / (n_neg + 1)
    return round(z(h) - z(f), 3), round(-(z(h) + z(f)) / 2, 3)


def row(name, h, f, n_pos, n_neg, extra=None):
    d, c = sdt(h, f, n_pos, n_neg)
    return {"model": name, "hit": round(100 * h, 1), "false_alarm": round(100 * f, 1), "d_prime": d, "criterion": c,
            **(extra or {})}


def main():
    out = {}
    # 1. GRPO report, Table 7 (FINAL-v3 JUDGE test set, 200 correct + 200 incorrect, 27B-free parser verdicts).
    t7 = {"untrained": (65.9, 62.7), "SOLVE-trained": (67.5, 76.5), "JUDGE-trained": (70.0, 87.0),
          "RECONSTRUCT-trained": (84.0, 52.5), "mixed": (81.5, 92.5), "qwen3.5-9b": (87.6 * 2 - 100 + 0, None)}
    out["judge_test_grpo_report"] = [row(m, h / 100, 1 - c / 100, 200, 200) for m, (h, c) in t7.items() if c is not None]

    # 2. ProcessBench (natural errors) and the synthetic set, same protocol (phase2/results/processbench).
    names = {"base": "untrained", "solve": "SOLVE-trained", "judge": "JUDGE-trained", "reconstruct": "RECONSTRUCT-trained",
             "mixed": "mixed", "qwen3.5-9b": "qwen3.5-9b"}
    for subset_group, subsets in (("processbench", ("gsm8k", "math", "olympiadbench", "omnimath")), ("synthetic", ("synthetic",))):
        rows = []
        for key, nm in names.items():
            recs = [json.loads(l) for l in gzip.open(ROOT / "processbench" / f"pred-{key}.jsonl.gz", "rt")]
            recs = [r for r in recs if r["subset"] in subsets and r["pred"] is not None]  # verdict given
            pos = [r for r in recs if r["label"] >= 0]; neg = [r for r in recs if r["label"] < 0]
            h = sum(r["pred"] >= 0 for r in pos) / len(pos); f = sum(r["pred"] >= 0 for r in neg) / len(neg)
            loc = sum(r["pred"] == r["label"] for r in pos) / max(1, sum(r["pred"] >= 0 for r in pos))
            rows.append(row(nm, h, f, len(pos), len(neg), {"exact_step_given_flag": round(100 * loc, 1)}))
        out[subset_group] = rows

    # 3. Tutor (short synthetic solutions): wrong = false-step + wrong-question items.
    items = [json.loads(l) for l in gzip.open(ROOT / "functional" / "tutor-agents.jsonl.gz", "rt")]
    rows = []
    for team in ("spec", "mixed"):
        v = [(x["label"], x[f"{team}_judge"]["verdict"]) for x in items if x[f"{team}_judge"]["verdict"]]
        pos = [d for l, d in v if l != "correct"]; neg = [d for l, d in v if l == "correct"]
        rows.append(row({"spec": "JUDGE-trained", "mixed": "mixed"}[team], sum(d == "incorrect" for d in pos) / len(pos),
                        sum(d == "incorrect" for d in neg) / len(neg), len(pos), len(neg)))
    out["tutor"] = rows

    (Path(__file__).resolve().parents[1] / "results" / "sdt.json").write_text(json.dumps(out, indent=1) + "\n")
    for k, rows in out.items():
        print(f"\n== {k}")
        print(f"{'model':22s} {'hit':>6s} {'FA':>6s} {'d_prime':>8s} {'criterion':>9s} {'step|flag':>9s}")
        for r in rows:
            print(f"{r['model']:22s} {r['hit']:6.1f} {r['false_alarm']:6.1f} {r['d_prime']:8.3f} {r['criterion']:9.3f} {r.get('exact_step_given_flag', ''):>9}")


if __name__ == "__main__":
    main()
