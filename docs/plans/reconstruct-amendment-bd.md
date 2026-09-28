# BD: distinguish true restatement from substantive verification

BC correctly detected the explicit tautological question but assigned M4 to its statement that the answer follows from its own premise. This conflicts with the frozen rubric's M0 for mere circular/restated verification, though the global shortcut override still yields zero. Preserve that failed label and the full BC run.

PC-v4 retains every prior grading rule and makes this boundary explicit: a literal given-answer restatement earns M0, even if the question is well-posed and that literal answer is correct. Do not fabricate an arithmetic error to justify the low verification score. Nontrivial concise proofs still earn M3/4. Keep raw components and the final zero override separate.

Freeze a new manifest and rerun all19 identical development controls once, after BC terminates, including positive proof controls. No change to expected labels, weights, bins or source responses. Same DeepSeek model/settings, max3 calls concurrently, no retries, incremental allowance$0.15 within the existing$5 research cap. Report every mismatch and missing case; passing these controls is not universal accuracy or independent held-out evidence.
