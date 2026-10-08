#!/usr/bin/env python3
"""Score stored baseline responses with the Jev judge (default) or the repository's DeepSeek judges.

    python3 scripts/judge_baseline.py --model qwen3.5-4b --split pilot --limit 4   # smoke test
    python3 scripts/judge_baseline.py --model qwen3.5-4b --split pilot
    python3 scripts/judge_baseline.py --model qwen3.5-4b --split pilot --summary-only

Jev (--judge jev): needs JEV_KEY in .env; writes judgments.jev.jsonl, judged-scores.jev.jsonl and
judged-summary.jev.json (src/anlp_project/jev_judging.py). DeepSeek (--judge deepseek): needs
DEEPINFRA_API_KEY in .env; writes judgments.jsonl, judged-scores.jsonl, judged-summary.json
(src/anlp_project/baseline_judging.py).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from anlp_project import baseline_judging as bj  # noqa: E402
from anlp_project import jev_judging as jj  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True, help="run folder, e.g. qwen3.5-4b or qwen3.5-2b-cap16k")
    p.add_argument("--split", default="pilot", choices=["pilot", "test", "dev"],
                   help="dev = an OPD dev evaluation folder in artifacts/opd/evals/<model>")
    p.add_argument("--limit", type=int, default=0, help="at most this many new calls")
    p.add_argument("--workers", type=int, default=bj.MAX_CONCURRENCY, help="parallel judge calls")
    p.add_argument("--summary-only", action="store_true")
    p.add_argument("--judge", default="jev", choices=["jev", "deepseek"],
                   help="jev (default): strict gates + Jev, writes *.jev.* files; deepseek: the earlier pipeline")
    a = p.parse_args()
    mod = jj if a.judge == "jev" else bj
    if not a.summary_only:
        print(json.dumps(mod.run(a.split, a.model, a.limit, a.workers)))
    print(json.dumps(mod.summarize(a.split, a.model), indent=1))


if __name__ == "__main__":
    main()
