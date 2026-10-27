"""Token lengths of the self-judge training prompts (chat template applied, as the trainer sends them)."""
import json, sys
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(sys.argv[1])
P = [json.loads(l) for l in open("phase2/runs/selfjudge/prompts.jsonl")]
n = sorted(len(tok.apply_chat_template([{"role": "user", "content": p["prompt"]}], tokenize=True, add_generation_prompt=True,
                                       enable_thinking=False, return_dict=False)) for p in P)
print("median", n[len(n) // 2], "p90", n[int(.9 * len(n))], "max", n[-1], "over16384", sum(x > 16384 for x in n))
