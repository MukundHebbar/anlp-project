"""2B vs 9B tokenizer check for token-level OPD (same IDs, same rendered prompts)."""
import sys
sys.path.insert(0, "src")
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
from anlp_project import baseline
s = AutoTokenizer.from_pretrained(snapshot_download("Qwen/Qwen3.5-2B", local_files_only=True))
t = AutoTokenizer.from_pretrained(snapshot_download("Qwen/Qwen3.5-9B", local_files_only=True))
vs, vt = s.get_vocab(), t.get_vocab()
diff = [k for k, i in vs.items() if vt.get(k) != i]
print("student vocab", len(vs), "teacher vocab", len(vt), "student tokens with different/missing IDs in teacher:", len(diff), diff[:5])
rows = [r for task in ("solve", "judge", "reconstruct") for r in baseline.rows_for("test", [task])[:10]]
same = 0
for r in rows:
    p = baseline.render_prompt(r)
    m = [{"role": "user", "content": p}]
    a = s.apply_chat_template(m, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    b = t.apply_chat_template(m, tokenize=True, add_generation_prompt=True, enable_thinking=False)
    same += a == b
print(f"rendered prompts identical token for token: {same}/{len(rows)}")
