#!/usr/bin/env python3
"""Score stored baseline responses with the repository's DeepSeek judges.

    python3 scripts/judge_baseline.py --model qwen3.5-4b --split pilot --limit 4   # smoke test
    python3 scripts/judge_baseline.py --model qwen3.5-4b --split pilot
    python3 scripts/judge_baseline.py --model qwen3.5-4b --split pilot --summary-only

Needs DEEPINFRA_API_KEY (or DEEPINFRA_KEY) in .env. Writes judgments.jsonl (raw calls),
judged-scores.jsonl and judged-summary.json next to responses.jsonl. See
src/anlp_project/baseline_judging.py for the exact pipelines.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from anlp_project import baseline_judging as bj  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True, help="run folder, e.g. qwen3.5-4b or qwen3.5-2b-cap16k")
    p.add_argument("--split", default="pilot", choices=["pilot", "test", "dev"],
                   help="dev = an OPD dev evaluation folder in artifacts/opd/evals/<model>")
    p.add_argument("--limit", type=int, default=0, help="at most this many new calls")
    p.add_argument("--workers", type=int, default=bj.MAX_CONCURRENCY, help="parallel judge calls")
    p.add_argument("--summary-only", action="store_true")
    a = p.parse_args()
    if not a.summary_only:
        print(json.dumps(bj.run(a.split, a.model, a.limit, a.workers)))
    print(json.dumps(bj.summarize(a.split, a.model), indent=1))


if __name__ == "__main__":
    main()
