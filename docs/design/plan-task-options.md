# PLAN Task: Current Prompt, Issues, and Strategy-Sketch Alternative

## Bottom line

The current PLAN prompt is closely aligned with PLAN-TUNING: it asks for an ordered decomposition and leaves execution and the answer out. The issue is output adherence, not a flawed concept. Use the **refined current PLAN** if alignment with PLAN-TUNING is the priority. Use **Strategy Sketch** only if a sharper experimental separation from SOLVE is more important.

## Current prompt (`plan.txt`)

```text
You are given a mathematics problem and a correct reference solution.

Your task is to write a concise, mathematically correct plan for solving the problem.

<problem>
{question}
</problem>

<reference_solution>
{solution}
</reference_solution>

Use the reference solution to identify the intended method and the logically necessary steps. Do not copy its full derivation, wording, exploratory reasoning, or final answer.

The plan must:

- state the main method or key idea;
- list the important steps in the order they should be performed;
- include essential equations, substitutions, identities, constructions, case splits, or intermediate observations;
- preserve any assumptions, domain restrictions, or conditions needed for the method to be valid;
- provide enough detail for another model to carry out the remaining reasoning correctly;
- omit routine algebra, arithmetic, repetitive case checking, and mechanical simplification;
- use only one coherent solution route unless separate cases are mathematically necessary;
- stop once the method and necessary setup are clear.

A plan is not a shortened full solution. Do not carry out all calculations, complete the derivation, or state the final answer. Do not include the final answer even if it appears in the reference solution.

Write the plan as a short numbered list. Do not add a title, preamble, conclusion, or commentary about the reference solution. Output only the plan.
```

## Observed issues

| Issue | Effect |
|---|---|
| Boundary is qualitative: “necessary setup” can include much of a solution. | Some plans execute the final target-index substitution, inequality, or count. |
| No explicit stop point. | PLAN can become a compressed SOLVE target. |
| Free-form numbered list. | PLAN length averaged about 78% of SOLVE in the 46-item pilot, rather than the desired <=70%. |
| Short existence/construction problems inherently overlap with solving. | Cannot be eliminated completely; report as a limitation. |

The mathematical content is usually sound. The problem is not that invariants or key calculations appear; these are often the core of a valid plan.

## Minimal revision: retain PLAN (recommended for PLAN-TUNING alignment)

Append this rule after the current bullet list:

```text
Once a general formula, invariant, recurrence, bound, or construction has been established, do not substitute the problem’s requested target value, solve the final equation or inequality, perform the final count or CRT recombination, or evaluate the final expression. End by stating that this remaining operation should be carried out.
```

Dataset target: mean PLAN length <=70% of mean SOLVE length; do not impose this ratio on every example.

## Alternative: PLAN as a Strategy Sketch

This alternative makes PLAN more distinct from SOLVE by constraining the output to mathematical decisions rather than a partially executed derivation.

```text
Method: name the main approach or representation.
Key insight: state and briefly justify the decisive invariant, lemma, transformation, or construction.
Subgoals: list 2–4 ordered operations needed to finish.
```

Rules: no final answer; no target-index substitution; no final arithmetic/count/inequality; no complete proof verification. A competent solver should need execution, but no further central discovery.

Example:

```text
Method: Convert the recurrence into one for partial sums of reciprocals.
Key insight: For S_k=sum_{i=1}^k 1/a_i, the recurrence gives
S_{k+1}=S_k+1/a_{k+1}=2S_k.
Subgoals: derive the closed form from S_1; relate the required term to the appropriate S_k; take the reciprocal.
```

## Trade-off

| Choice | Advantages | Cost |
|---|---|---|
| Refined current PLAN | Closest to PLAN-TUNING; preserves rich planning trajectories. | PLAN/SOLVE boundary remains partly porous. |
| Strategy Sketch | Stronger task distinction; shorter targets; clearer scoring rubric. | Less like PLAN-TUNING’s natural planning trajectories; can be too high-level on some problems. |

## Recommendation

Keep PLAN, apply the minimal revision, and use two short few-shot examples (one invariant/recurrence and one counting/algebra example). Move to Strategy Sketch only if the primary research goal is a cleaner PLAN-versus-SOLVE transfer comparison rather than closest alignment with PLAN-TUNING.
