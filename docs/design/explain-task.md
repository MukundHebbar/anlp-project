## EXPLAIN: Local Step Justification

### Task definition

Given a mathematics problem, the necessary established facts, and one verified solution step, the model must explain why that step follows.

Formally, given problem \(q\), local context \(c\), and a correct claim or transition \(s\), the model produces a justification \(e\) showing that \(c \Rightarrow s\).

A valid explanation must:

1. State the relevant mathematical fact, theorem, identity, or argument.
2. Show why its conditions hold in the supplied context.
3. Connect that fact directly to the selected step.
4. Include necessary restrictions, equality conditions, or edge cases.

The model must not select a strategy, continue solving the problem, or merely restate the step.

### Distinction from other tasks

| Task      | Required operation                                                           |
| --------- | ---------------------------------------------------------------------------- |
| `SOLVE`   | Construct a complete derivation and answer from the problem.                 |
| `EXPLAIN` | Justify why a supplied correct step follows from supplied facts.             |
| `JUDGE`   | Determine whether a supplied solution is correct and locate its first error. |

Thus, `SOLVE` constructs, `EXPLAIN` justifies, and `JUDGE` verifies. Unlike `PLAN`, `EXPLAIN` does not require discovering what move to make.

### Dataset item

Each source problem produces at most one EXPLAIN item containing:

```json
{
  "problem": "...",
  "established_facts": "...",
  "selected_step": "...",
  "question": "...",
  "reference_explanation": "...",
  "required_criteria": ["...", "...", "..."],
  "material_errors": ["...", "..."]
}
```

The selected step must be:

* correct according to the verified reference solution;
* mathematically important rather than routine arithmetic;
* locally justifiable from the supplied facts;
* explainable without completing the original problem.

Suitable steps include substitutions, theorem applications, invariants, equality conditions, decisive bounds, case completeness, counting arguments, and induction steps. If no suitable step exists, the source problem is excluded from every matched task form.

The student sees only the problem, established facts, selected step, and explanation question—not the complete solution or reference explanation.

### Student instruction

```text
Explain why the selected step is mathematically valid.

State the relevant mathematical fact in words or equations, show why
its conditions hold here, and connect it directly to the selected step.
Include necessary restrictions, equality conditions, or edge cases.

Merely naming a theorem or repeating the step is insufficient.
Do not choose another strategy or continue solving the original problem.
```

Targets should normally be 50–150 words and substantially shorter than the corresponding SOLVE target.

### Evaluation

Each item has exactly three item-specific binary requirements. An external judge evaluates whether each requirement is:

* `satisfied`;
* `not_satisfied`;
* `uncertain`.

The judge also detects any material mathematical error. Alternative valid arguments must be accepted; wording or theorem names need not match the reference.

For candidate \(e\), define criterion score

$$
S(e)=\frac{1}{3}\sum_{j=1}^{3}\mathbf{1}[C_j\text{ is satisfied}].
$$

The explanation passes only if

$$
\operatorname{Pass}(e)=1
\iff
S(e)=1
\quad\text{and}\quad
\text{no material error is present}.
$$

`Uncertain` is conservatively treated as unsatisfied and reported separately. Primary metrics are pass rate and mean criterion score. Per-criterion results identify whether models fail to state the relevant fact, establish its conditions, or connect it to the step.

Outputs from all trained models can be anonymized, shuffled, and scored in one judge call per problem. Relative ranking may be reported secondarily, but it is not the primary evaluation.

### Automatic validation

Before training, deterministic checks verify that:

* all fields are present;
* the selected step and established facts occur in, or are faithful extracts from, the verified solution;
* exactly three evaluation criteria are supplied;
* the target respects the length limit;
* the item does not expose the final solution unnecessarily.

Semantic correctness remains judge-evaluated because unrestricted mathematical explanations cannot be verified deterministically.

### Motivation

MathBench separates theoretical knowledge from application using distinct question sets, but evaluates theory through multiple-choice accuracy. EXPLAIN extends this distinction by testing whether a model can ground mathematical theory in a particular valid inference. It therefore measures local explanatory reasoning rather than theory recognition, strategic planning, or complete problem solving.
