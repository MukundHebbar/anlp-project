# JUDGE student prompt

You are given a mathematics problem and a proposed step-by-step solution.

<problem>
{problem}
</problem>

<proposed_solution>
{proposed_solution}
</proposed_solution>

Decide whether the proposed solution is mathematically correct. If it is
incorrect, identify the **first** wrong step and explain the mathematical
error. If it is correct, state that there is no wrong step.

Return exactly this format:

```text
Decision: correct|incorrect
First wrong step: <step ID or none>
Explanation: <concise mathematical justification>
```

Check every step in order. Do not judge only from the final answer. Do not
solve a different problem or continue the proposed solution.
