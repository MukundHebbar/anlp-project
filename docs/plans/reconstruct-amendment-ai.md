# AI: same-family direct SOLVE control

Registered before any control outputs. AF/AG yielded no recoveries; prior local SOLVE controls used other source families and do not establish forward competence here. Test the same fixed twelve D4 source questions [0,13,46,62,63,80,87,96,118,120,129,137] directly, with original question visible and source answer/solution hidden. No source selection based on reconstruction outcomes within the cohort.

Purpose: distinguish lack of forward mathematical competence from additional reconstruction difficulty. This is a task/input-package diagnostic, not a training-transfer result, a pure information-only causal effect, or a new RECONSTRUCT candidate. SOLVE has a different instruction and receives the full question rather than the answer and clues. Do not count its successes as reconstruction successes. AH conversion and student settings remain unchanged.

Same original non-thinking Qwen3-4B Q4_K_M, sampling0.7/0.8/20, seed0,8192 output cap,300-second timeout. One draw per question. Freeze prompt and exact question bindings before running; persist attempts before dispatch; preserve raw responses and failures. Local calls only while AH uses the paid API. Do not run a second local student runner concurrently.

Prompt: Solve the mathematical problem. Give a concise mathematical justification and the final answer. Return JSON only with keys justification and final_answer. The source question follows. No example or reference answer.

Initially report completion and exact extracted answers with analytic checks; answers alone do not establish proof validity. Review all outputs against original sources and record unsupported claims separately. Any later model verification must be registered and respect global4-call/$5 bounds. All twelve scheduled draws stay in the denominator. This control cannot prove a reasoning taxonomy or training transfer.
