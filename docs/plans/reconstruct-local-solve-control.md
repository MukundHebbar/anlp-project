# Matched local SOLVE diagnostic

Registered before local SOLVE calls. The16 RECONSTRUCT outputs are generated and are being judged; none will be regenerated based on this control.

Use the same four fixed sources8,27,33,77, the exact historical SOLVE prompt stored for each, and the currently running local Qwen3-4B Q4_K_M in non-thinking mode. Use seed0, temperature.7, top-p.8, top-k20,8192 cap,300s timeout, one attempt per source. Save raw outputs and score with the existing deterministic final-answer verifier v2; do not interpret answer verification alone as a proof-quality audit.

The historical unquantized vLLM SOLVE run was non-thinking with the same cap and sampling values, and got3/4 of these source answers correct (source27 incorrect). Its generation seed is not recorded in the inspected metadata. Consequently this tiny comparison cannot isolate quantization or backend effects, nor establish a rate difference. It asks whether the current local runtime can solve the same mathematical problems when given complete questions, using an established prompt.

Store controls outside the reconstruction artifact. They are SOLVE, not extra clues or teacher feedback to Qwen. No original questions or solutions enter RECONSTRUCT requests, and no task bank is selected based on these outcomes. No C/R sources are inspected. Local controls may run concurrently with paid grading because they use a separate runtime and no provider budget.
