"""Report the fixed SOLVE test baseline against the saved Qwen3.5-2B reference."""
import gzip
import hashlib
import json
from pathlib import Path
import random

REPO = Path(__file__).resolve().parents[2]
NEW = REPO / "local/ministral-baseline/test"
REFERENCE = REPO / "artifacts/baselines/final-v3/test/v3-pass4-2b"
OUT = REPO / "phase2/results/ministral-baseline"


def load(folder):
    by_question, records = {}, []
    for sample in range(4):
        rows = [json.loads(line) for line in (folder / f"s{sample}/scores.jsonl").open()]
        rows = [x for x in rows if x["task"] == "solve"]
        assert len(rows) == 400 and len({x["uid"] for x in rows}) == 400
        for x in rows:
            by_question.setdefault(x["uid"], []).append(bool(x["correct_strict"]))
            records.append({"sample": sample, **x})
    assert len(by_question) == 400 and all(len(v) == 4 for v in by_question.values())
    return by_question, records


def interval(values):
    rng = random.Random(0)
    n = len(values)
    bootstrap = sorted(100 * sum(values[rng.randrange(n)] for _ in values) / n for _ in range(10000))
    return {"points": 100 * sum(values) / n, "ci95": [bootstrap[250], bootstrap[9750]]}


def main():
    new, rows = load(NEW)
    base, base_rows = load(REFERENCE)
    assert set(new) == set(base)
    metadata = json.loads((NEW / "metadata.json").read_text())
    assert metadata["model"] == "mistralai/Ministral-3-3B-Instruct-2512-BF16"
    assert metadata["chat_mode"] == "instruct" and metadata["model_format"] == "mistral"
    assert metadata["split"] == "test" and metadata["samples"] == 4
    assert metadata["limit"] is None and metadata["prompts"] == "v2"
    base_metadata = json.loads((REFERENCE / "s0/metadata.json").read_text())
    assert metadata["sampling"] == base_metadata["sampling"]
    assert metadata["two_pass"] == base_metadata["two_pass"]
    assert metadata["sampling"] == {"temperature": 1.0, "top_p": 1.0, "top_k": 0,
                                   "seed": 0, "max_tokens": 32768}
    qs = sorted(new)
    functions = {"mean_accuracy": lambda v: sum(v) / 4, "pass_at_4": lambda v: float(any(v))}
    summary = {"date": "2026-10-27", "questions": 400, "samples_per_question": 4,
               "metrics": {}, "metadata": metadata, "diagnostics": {}}
    for name, f in functions.items():
        summary["metrics"][name] = {
            "ministral_percent": 100 * sum(f(new[q]) for q in qs) / len(qs),
            "qwen_2b_percent": 100 * sum(f(base[q]) for q in qs) / len(qs),
            "paired_difference": interval([f(new[q]) - f(base[q]) for q in qs]),
        }
    for name, rs in (("ministral", rows), ("qwen_2b", base_rows)):
        summary["diagnostics"][name] = {
            "gate_percent": 100 * sum(bool(x["gate"]) for x in rs) / len(rs),
            "cap_percent": 100 * sum(x["hit_token_cap"] for x in rs) / len(rs),
            "mean_completion_tokens": sum(x["completion_tokens"] for x in rs) / len(rs),
            "answer_status_counts": {status: sum(x["answer_status"] == status for x in rs)
                                     for status in ("correct", "incorrect", "unverified", "missing")},
        }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    provenance = REPO / "local/ministral-baseline/provenance.json"
    if provenance.exists():
        (OUT / "provenance.json").write_text(provenance.read_text())
    with gzip.open(OUT / "scores.jsonl.gz", "wt") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with gzip.open(OUT / "paired-outcomes.jsonl.gz", "wt") as f:
        for q in qs:
            f.write(json.dumps({"uid": q, "ministral": new[q], "qwen_2b": base[q]}) + "\n")
    table = ["# Ministral Instruct BF16 SOLVE baseline", "", "Completed 2026-10-27. "
             "400 FINAL-v3 SOLVE test questions, four samples each; no training.", "",
             "| Metric | Ministral | Qwen3.5-2B | Paired difference, points (95% CI) |",
             "|---|---:|---:|---:|"]
    for name, x in summary["metrics"].items():
        d = x["paired_difference"]
        label = "Mean accuracy" if name == "mean_accuracy" else "pass@4"
        table.append(f"| {label} | {x['ministral_percent']:.1f}% | {x['qwen_2b_percent']:.1f}% | "
                     f"{d['points']:+.1f} [{d['ci95'][0]:+.1f}, {d['ci95'][1]:+.1f}] |")
    table += ["", "Paired bootstrap over 400 questions, 10,000 resamples, seed 0. Both use the unchanged SOLVE "
              "prompt, BF16, temperature 1, top-p 1, top-k disabled, evaluation seed 0, and 16k generation with "
              "continuation to 32k. Scores use the existing checker and strict gates. Ministral uses its native "
              "Instruct checkpoint/chat serialization; Qwen uses its non-thinking template.", "",
              "The same per-model token cap does not imply the same amount of text or compute because tokenizers "
              "and architectures differ. This is a comparison under the shared evaluation recipe.", "",
              "See [the frozen protocol](../../ministral_baseline/README.md). Full generated responses are backed "
              "up under `local/ministral-baseline/test/responses-solve.jsonl.gz`.", ""]
    (OUT / "README.md").write_text("\n".join(table))
    source_hashes = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for folder in (NEW, REFERENCE) for p in sorted(folder.glob("s[0-9]/scores.jsonl"))}
    (OUT / "source-checksums.json").write_text(json.dumps(source_hashes, indent=2) + "\n")
    print("\n".join(table[:8]))
    print(json.dumps(summary["diagnostics"], indent=2))


if __name__ == "__main__":
    main()
