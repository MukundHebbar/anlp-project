# AV: richer target-family and method cues

Registered during AU local generation, after inspecting the first six outputs (21,35,54 in both arms), before AV conversion or student calls. The exact same seven AP families remain included. AU shows one semantic recovery21 but wrong targets35/54 despite more derivation steps. Hypothesis: broad target-family information and a tool cue provide useful information beyond redundant calculations.

Use one fixed two-example DeepSeek converter, convert_p10_target_cues, to generate two sentences per source. Append to the unchanged first3 AP sentences. Level1 adds only the target-family cue; level2 adds that cue and the method cue. The original AP level0 is reused exactly. Do not edit individual cues after viewing student outcomes. Freeze and inspect all cues before student draws. Keep exact targets unspecified and reject complete-question paraphrases or full derivations as candidate inputs. Diagnostic outputs on invalid inputs do not count as task successes.

Run level2 first on all7. If it yields>=2 semantic recoveries, test level1 on all7 to narrow the bracket. Otherwise use a prospectively registered richer rule. Performance need not be monotonic, so report actual paired changes, not a mathematical binary-search guarantee. No per-source choice of exposure. Qwen,p13,seed0 and8192-token cap remain unchanged. Count semantic equivalence separately from proof validity and leakage. These are reused development sources, not confirmation.

Seven converter calls, up to14 local draws, up to28 source-equivalence/math judgments. Paid cap$0.40 within global$5, concurrency<=4. Preserve raw calls, failures, prompt hashes, manual support/leakage rationale and all planned denominators. No source or response selection based on favorable results.
