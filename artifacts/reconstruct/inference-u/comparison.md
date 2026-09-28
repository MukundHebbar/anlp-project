# Amendment U: inference versus restatement

Decision: **passes_development_gate**.

| Evaluator | Authored controls | Production diagnostics | Resolved | Recorded cost |
|---|---:|---:|---:|---:|
| evaluate_p2 | 8/16 | 2/4 | 20/20 | $0.005448 |
| evaluate_p3 | 16/16 | 4/4 | 20/20 | $0.007118 |

Passes require both the registered score and shortcut flag, plus substantive inference for p3 positive controls.

| Case | Expected | p2 | p3 | p3 passes |
|---|---:|---:|---:|---|
| linear-copy | [0] | 4 | 0 | True |
| linear-decorated_copy | [0] | 4 | 0 | True |
| linear-substantive | [4] | 4 | 4 | True |
| linear-wrong | [1] | 1 | 1 | True |
| probability-copy | [0] | 4 | 0 | True |
| probability-decorated_copy | [0] | 4 | 0 | True |
| probability-substantive | [4] | 4 | 4 | True |
| probability-wrong | [1] | 1 | 1 | True |
| graph-copy | [0] | 4 | 0 | True |
| graph-decorated_copy | [0] | 4 | 0 | True |
| graph-substantive | [4] | 4 | 4 | True |
| graph-wrong | [1] | 1 | 1 | True |
| geometric-copy | [0] | 4 | 0 | True |
| geometric-decorated_copy | [0] | 4 | 0 | True |
| geometric-substantive | [4] | 4 | 4 | True |
| geometric-wrong | [1] | 1 | 1 | True |
| qwen-33-copy | [0] | 3 | 0 | True |
| stronger-33-copy | [0] | 4 | 0 | True |
| stronger-112-target | [4] | 4 | 4 | True |
| scale-86-copy | [0] | 0 | 0 | True |

Limitations:
- Assistant-authored/reviewed references, not independent human gold.
- Four authored families; multiple variants are correlated.
- Production diagnostics were selected for known failure modes.
- Expected labels use the proposed refinement; old-prompt differences need not violate its old specification.
- No change to Qwen semantic recovery follows from changing a rubric.
