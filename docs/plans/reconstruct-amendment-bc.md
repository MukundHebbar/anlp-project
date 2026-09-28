# BC: complete JSON schema for the repaired judges

BB exposed an output-contract defect: the prompt requested a verification_certificate in prose but omitted it from its example JSON. Some correct fidelity judgments therefore failed structural validation. Preserve BB unchanged.

Create partial_credit_v3 with identical grading rules and an explicit complete JSON schema, including verification certificates and shortcut quotation fields. Freeze a new manifest and validator hash. Rerun all19 registered controls once under the new version; do not retry only failed cases or cherry-pick grades. The cases are now reused development calibration, not held-out validation. Apply the same acceptance checks. A pass supports these tested boundaries only.

At most three paid calls concurrently; start after BB terminates. DeepSeek V4.1 Flash, reasoninglow, temperature0,8192 cap,180-second timeout, no retries. Incremental allowance$0.15, within the existing$5 cap. Log raw outputs, errors and missing usage; preserve original scores. No Qwen or conversion calls are needed for this judge repair.
