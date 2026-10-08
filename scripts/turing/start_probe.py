#!/usr/bin/env python3
"""Base vs post-trained starting checkpoint: group-sampling probe on the dev slices.

    python scripts/turing/start_probe.py --model Qwen/Qwen3.5-2B-Base --out <dir>
    python scripts/turing/start_probe.py --model Qwen/Qwen3.5-2B --prompts v1 --tasks judge --questions 10 --out <dir>

For each task, the first N dev questions get K samples each, with the training rollout settings
(T 1.0, no truncation of the distribution, 8k cap, non-thinking chat template). Both checkpoints
get byte-identical prompts. Writes responses.jsonl (every sample) and probe.json:
- format: the share of samples the deterministic parser can read;
- reward: SOLVE exact answer; JUDGE 1 for verdict and first wrong step, 0.5 for verdict only
  (the verdict_reward rule); RECONSTRUCT has no checkable reward, so only its format is scored;
- GRPO signal: the share of questions whose K rewards are not all equal (non-zero group advantage);
- pass@1, pass@K, length, cap rate and repetition;
- gate_rate: the share of samples that fail a strict gate (src/anlp_project/strict_gates.py).
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project import baseline, opd  # noqa: E402
from anlp_project.opd_monitor import repetition_score  # noqa: E402
from anlp_project.strict_gates import judge_gate, reconstruct_gate, solve_gate  # noqa: E402


def reward(task, sc):
    if task == "solve":
        return float(sc["answer_status"] == "correct")
    if task == "judge":
        return 1.0 if sc["step_correct"] else 0.5 if sc["verdict_correct"] else 0.0
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tasks", default="solve,judge,reconstruct")
    ap.add_argument("--questions", type=int, default=64)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--prompts", default="v2", choices=["v1", "v2"])
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "probe.json").exists():
        raise SystemExit(f"{out} already has a probe")

    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams

    llm = LLM(model=snapshot_download(a.model, local_files_only=True), dtype="bfloat16", language_model_only=True,
              max_model_len=a.max_tokens + 8192, gpu_memory_utilization=0.90, max_num_seqs=256, seed=0)
    params = SamplingParams(n=a.samples, temperature=1.0, top_p=1.0, top_k=0, max_tokens=a.max_tokens, seed=0)
    summary = {"model": a.model, "prompts": a.prompts, "questions": a.questions, "samples": a.samples,
               "max_tokens": a.max_tokens}
    with (out / "responses.jsonl").open("w") as fh:
        for task in a.tasks.split(","):
            rows = opd.slice_rows(task, "dev")[: a.questions]
            outs = llm.chat([[{"role": "user", "content": baseline.render_prompt(r, a.prompts)}] for r in rows], params,
                            use_tqdm=False, chat_template_kwargs={"enable_thinking": False})
            groups, fmt, toks, cap, rep, gated = [], [], [], [], [], []
            for row, o in zip(rows, outs, strict=True):
                g = []
                for k, c in enumerate(o.outputs):
                    resp = {"text": c.text, "finish_reason": c.finish_reason, "completion_tokens": len(c.token_ids)}
                    sc = baseline.score_response(row, resp)
                    parsed = sc["answer_status"] != "missing" if task == "solve" else sc["parsed"]
                    if task == "solve":
                        gate = solve_gate(c.text)
                    elif task == "judge":
                        gate = judge_gate(c.text)
                    else:
                        rec, _ = baseline.extract_reconstruction_last(c.text)
                        gate = reconstruct_gate(row["public_input"]["final_answer"], rec["question"]) if rec else ["unparseable"]
                    gated.append(bool(gate))
                    r = 0.0 if gate and task != "reconstruct" else reward(task, sc)
                    g.append(r)
                    fmt.append(parsed)
                    toks.append(len(c.token_ids))
                    cap.append(c.finish_reason == "length")
                    rep.append(repetition_score(list(c.token_ids)))
                    fh.write(json.dumps({"uid": row["uid"], "task": task, "sample": k, **resp, "score": sc,
                                         "gate": gate, "reward": r}, ensure_ascii=False) + "\n")
                groups.append(g)
            s = {"format_rate": st.mean(fmt), "gate_rate": st.mean(gated), "mean_tokens": st.mean(toks), "cap_rate": st.mean(cap),
                 "repetition_mean": st.mean(rep), "looping_rate": st.mean(x > 0.5 for x in rep)}
            if task != "reconstruct":
                s.update(pass1=st.mean(x for g in groups for x in g),
                         passK=st.mean(any(x == 1.0 for x in g) for g in groups),
                         mixed_groups=st.mean(len(set(g)) > 1 for g in groups),
                         all_zero_groups=st.mean(all(x == 0 for x in g) for g in groups))
            else:
                s["mixed_format_groups"] = st.mean(
                    len({fmt[i * a.samples + k] for k in range(a.samples)}) > 1 for i in range(len(groups)))
            summary[task] = s
            print(task, json.dumps(s), flush=True)
    (out / "probe.json").write_text(json.dumps(summary, indent=1) + "\n")


if __name__ == "__main__":
    main()
