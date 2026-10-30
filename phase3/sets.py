"""Phase-3 question sets, deterministic. Writes phase3/manifests/sets.json.

test   FINAL-v3 SOLVE test (400), as in Phase 2
dev    the SOLVE dev slice (200, Phase 2's dev); used only for tuning (beta, thresholds)
extra  400 SOLVE train questions that no mixed-model run could have seen: not in the mixed GRPO manifest
       (all 1,134 SOLVE uids, of which the first 750 were used), not in the OPD trial train or dev slices
train  1,200 further such questions, reserved for judge training (Stage 2)
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anlp_project import baseline  # noqa: E402

M = ROOT / "data" / "manifests" / "final-v3"
SEED = 20261028


def build() -> dict:
    mixed = {u for u in json.loads((M / "grpo-mixed-1134.json").read_text())["uids"] if u.startswith("solve-")}
    trial = json.loads((M / "opd-trial-solve.json").read_text())["uids"]
    train_rows = baseline.load_rows("solve", "train")
    excluded = mixed | set(trial["train"]) | set(trial["dev"])
    pool = sorted(r["uid"] for r in train_rows if r["uid"] not in excluded)
    random.Random(SEED).shuffle(pool)
    test = sorted(r["uid"] for r in baseline.load_rows("solve", "test"))
    sets = {"test": test, "dev": sorted(trial["dev"]), "extra": sorted(pool[:400]), "train": sorted(pool[400:1600])}
    assert len(sets["train"]) == 1200, len(pool)
    all_uids = [u for s in sets.values() for u in s]
    assert len(all_uids) == len(set(all_uids)), "sets overlap"
    return {"description": __doc__.strip(), "seed": SEED, "pool_size": len(pool),
            "sizes": {k: len(v) for k, v in sets.items()}, "uids": sets}


if __name__ == "__main__":
    out = ROOT / "phase3" / "manifests" / "sets.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = build()
    out.write_text(json.dumps(data, indent=1) + "\n")
    print(out, data["sizes"], "clean pool", data["pool_size"])
