# One-Transition EXPLAIN Generator Prompt (v2)

You generate **one EXPLAIN task** from a verified mathematics solution.

<problem>
{problem}
</problem>

<verified_full_solution>
{reference_solution}
</verified_full_solution>

## Objective

EXPLAIN tests whether a student can justify **one important local transition in a known solution**.

The student sees the problem, only the earlier facts needed for the transition, and exactly two consecutive important solution steps. The student must explain why the second supplied step follows from the first.

The student must not need to discover a new strategy, construction, substitution, invariant, case split, or later solution step.

Generate exactly one transition. If no transition meets every requirement below, return exactly:

`NOT_SUITABLE`

---

## 1. Build a private main-step skeleton

Reduce the verified solution to an ordered list of concise main steps:

`S1, S2, ..., Sn`.

Each main-step statement must express one substantive change in the solution state. Keep routine working inside the surrounding derivation rather than promoting it to a separate step.

A main step may involve:

- applying a theorem, lemma, or important identity;
- introducing an essential representation or substitution;
- establishing an invariant, decisive equation, bound, factorisation, or equality case;
- making an essential case split;
- setting up or using an important counting correspondence.

Do **not** treat any of the following as a separate main step by itself:

- routine arithmetic or algebra;
- expansion, cancellation, rearrangement, or coefficient matching;
- direct substitution into an already supplied identity;
- unrolling a simple recurrence;
- applying a standard formula when its applicability is immediate;
- a short mechanical enumeration.

Do not omit or merge genuinely distinct mathematical ideas. The private skeleton must remain ordered and dependency-correct.

---

## 2. Select one high-value local transition

Privately consider every adjacent pair `(Si, S(i+1))` in the main-step skeleton before selecting one.

Select exactly two consecutive main steps. The selected transition must satisfy all of the following:

1. **Consecutive:** no hidden main mathematical idea lies between the two steps.
2. **Local:** the problem, supplied earlier context, and `Si` contain everything needed to derive `S(i+1)`.
3. **Strategy already fixed:** the student only justifies the supplied bridge. They must not invent a new method or decide what to try next.
4. **Conceptually non-trivial:** the explanation requires a genuine mathematical reason, not only execution of a mechanical operation.
5. **Bounded:** a natural complete explanation normally needs about 50–120 words, without filler.
6. **Self-contained slice:** all necessary earlier facts can be supplied concisely, without exposing later work or the final answer.
7. **Stops locally:** the response ends once `S(i+1)` is justified.

### Hard rejection test

Reject a candidate transition when a complete correct explanation would mainly amount to any of the following:

- “substitute the supplied expression and simplify”;
- “expand, cancel, rearrange, or compare coefficients”;
- “iterate this elementary recurrence”;
- “apply this already supplied formula”;
- “enumerate these few cases”;
- a natural explanation under about 45 words unless padded.

Such an operation is acceptable **only if it is the decisive idea** and the student must also establish a non-obvious applicability condition, sign/domain restriction, equality case, bijection/correspondence, invariant, or structural reason.

Prefer transitions whose minimal correct explanation requires both:

1. identifying or using a substantive theorem, identity, representation, bound, factorisation, or counting correspondence; and
2. checking why it applies here or deriving the essential bridge to the next step.

It is better to return `NOT_SUITABLE` than to force a weak transition from an otherwise straightforward problem.

---

## 3. Construct the student-facing task

The student sees only:

- the original problem;
- `established_context`: the minimal earlier facts required for the transition;
- exactly two consecutive step statements, `Si` and `S(i+1)`;
- one question asking why `S(i+1)` follows from `Si`;
- the fixed student instruction below.

### Context rules

- Include every prerequisite needed for a local derivation.
- Do not include the omitted derivation itself.
- Do not include later solution steps, the final answer, the private reference explanation, or private evaluation criteria.
- Do not name or hint at the expected theorem in the transition question. The student should identify the relevant principle from the mathematical setup.
- Student-facing step statements should normally state mathematical facts or results rather than announce the theorem name.

### Question rules

Ask only for justification of the supplied move. Good forms include:

- “Explain why the stated counting argument gives this expression.”
- “Explain why these facts force the displayed factorisation.”
- “Explain why the previous relation implies the stated bound.”
- “Explain why the supplied conditions make this conclusion valid.”
- “Explain why these cases exhaust all possibilities.”

Do not ask the student to:

- choose a strategy;
- find a substitution, construction, invariant, or case split;
- solve the problem from scratch;
- continue past the second supplied step.

Use exactly this student instruction:

```text
Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps.
```

---

## 4. Private reference explanation and evaluation

Write a concise private gold explanation containing only the reasoning required for the selected transition. It should naturally fit about 50–120 words and must not continue the original solution.

Create exactly three binary, item-specific evaluation criteria. Together, they must check:

1. the relevant mathematical principle or argument;
2. the necessary applicability condition, sign, domain restriction, equality condition, or correspondence;
3. the derivation connecting the supplied first step to the supplied second step.

Alternative correct arguments must pass. Do not evaluate wording or stylistic similarity.

List material mathematical errors that should fail an answer. These should be specific to the item, such as an incorrect identity, an invalid theorem condition, a wrong sign, an omitted equality condition, a false counting correspondence, or reasoning that proceeds beyond the requested transition.

In `generation_notes`, state in one concise sentence:

- the non-routine idea selected; and
- why this is not merely substitution, simplification, formula application, or routine calculation.

If this cannot be stated concretely, return `NOT_SUITABLE`.

---

## 5. Output format

Return valid JSON only. Use this schema:

```json
{
  "main_step_skeleton": [
    {"id": "S1", "statement": "..."},
    {"id": "S2", "statement": "..."},
    {"id": "S3", "statement": "..."}
  ],
  "student_facing_task": {
    "problem": "...",
    "established_context": ["..."],
    "solution_skeleton": [
      {"id": "S2", "statement": "..."},
      {"id": "S3", "statement": "..."}
    ],
    "transition_to_explain": {
      "from": "S2",
      "to": "S3",
      "question": "..."
    },
    "student_instruction": "Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "...",
  "required_criteria": ["...", "...", "..."],
  "material_errors": ["...", "..."],
  "generation_notes": "..."
}
```

`main_step_skeleton` and every field outside `student_facing_task` are private. The student sees only `student_facing_task`.

---

## Example 1: Fixed cycle length counting

### Input

Problem: How many permutations in `S_100` contain a cycle of length at least 51?

Verified solution: A permutation can have at most one cycle of length at least 51. Partition by its exact length `k`. For fixed `k`, choose the cycle elements, arrange them into a cycle, and permute the remaining elements. This gives `C(100,k)(k-1)!(100-k)! = 100!/k`. Then sum over `k`.

### Output

```json
{
  "main_step_skeleton": [
    {"id": "S1", "statement": "Partition the desired permutations by the exact length k of their unique long cycle."},
    {"id": "S2", "statement": "For fixed k, the number of permutations is 100!/k."},
    {"id": "S3", "statement": "Sum the fixed-k counts over the allowed values of k."}
  ],
  "student_facing_task": {
    "problem": "How many permutations in S_100 contain a cycle of length at least 51?",
    "established_context": ["A permutation of 100 elements can contain at most one cycle of length at least 51."],
    "solution_skeleton": [
      {"id": "S1", "statement": "Partition the desired permutations by the exact length k of their unique long cycle."},
      {"id": "S2", "statement": "For fixed k, the number of permutations is 100!/k."}
    ],
    "transition_to_explain": {
      "from": "S1",
      "to": "S2",
      "question": "Explain why the fixed-k count is 100!/k."
    },
    "student_instruction": "Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "Choose the k elements of the long cycle in C(100,k) ways. On a fixed k-element set, there are (k-1)! cycles because cyclic rotations describe the same cycle. The remaining 100-k elements may be permuted arbitrarily in (100-k)! ways. Multiplying gives C(100,k)(k-1)!(100-k)! = 100!/k.",
  "required_criteria": [
    "Counts the choice of the k cycle elements and the permutation of the remaining elements.",
    "Uses (k-1)! rather than k! for cycles on a fixed k-element set.",
    "Combines the factors correctly to obtain 100!/k."
  ],
  "material_errors": [
    "Using k! without accounting for cyclic rotations.",
    "Ignoring the permutation of the remaining elements."
  ],
  "generation_notes": "The selected transition is a non-trivial counting correspondence: it derives the fixed-k count by decomposing a permutation into its long cycle and its remaining permutation."
}
```

---

## Example 2: Factorisation from four roots

### Input

Problem: Let `a,b,c,d` be distinct positive real numbers. Suppose `P(x)=x^4-8x^2-x+11`, `Q(x)=x^4-8x^2+x+11`, `P(a)=P(b)=0`, `Q(c)=Q(d)=0`, and `Q(x)=P(-x)`.

Verified solution: From `Q(c)=Q(d)=0` and `Q(x)=P(-x)`, obtain `P(-c)=P(-d)=0`. Thus `a,b,-c,-d` are four distinct roots of the monic quartic `P`, so `P(x)=(x-a)(x-b)(x+c)(x+d)`.

### Output

```json
{
  "main_step_skeleton": [
    {"id": "S1", "statement": "The equalities Q(c)=Q(d)=0 imply P(-c)=P(-d)=0."},
    {"id": "S2", "statement": "The monic quartic P factors as (x-a)(x-b)(x+c)(x+d)."}
  ],
  "student_facing_task": {
    "problem": "Let a,b,c,d be distinct positive real numbers. Suppose P(x)=x^4-8x^2-x+11, Q(x)=x^4-8x^2+x+11, P(a)=P(b)=0, Q(c)=Q(d)=0, and Q(x)=P(-x).",
    "established_context": ["The polynomial P is monic of degree 4.", "The numbers a,b,c,d are distinct and positive."],
    "solution_skeleton": [
      {"id": "S1", "statement": "P(a)=P(b)=P(-c)=P(-d)=0."},
      {"id": "S2", "statement": "P(x)=(x-a)(x-b)(x+c)(x+d)."}
    ],
    "transition_to_explain": {
      "from": "S1",
      "to": "S2",
      "question": "Explain why these four zeroes force the displayed factorisation of P."
    },
    "student_instruction": "Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "The values a, b, -c, and -d are roots of P. They are distinct because a,b,c,d are distinct positive numbers, so a and b are positive while -c and -d are negative and distinct. A degree-four polynomial with these four roots is a constant multiple of (x-a)(x-b)(x+c)(x+d). Since P is monic, that constant is 1.",
  "required_criteria": [
    "Identifies a,b,-c,-d as roots of P and explains why they are distinct.",
    "Uses the degree-four root-factor relationship to obtain the product of four linear factors.",
    "Uses monicity to show that the multiplicative constant is 1."
  ],
  "material_errors": [
    "Treating c and d rather than -c and -d as roots of P.",
    "Omitting the distinctness or monicity argument."
  ],
  "generation_notes": "The transition requires a structural root-factor argument, including sign-based distinctness and the leading-coefficient condition; it is not a mechanical substitution."
}
```

---

## Example 3: Transferring a one-sided derivative limit

### Input

Problem: Suppose `f` is continuous on `R`, differentiable away from `a`, and `lim_(t->a+) f'(t)=L`.

Verified solution: For `x>a`, there is `c_x` in `(a,x)` such that `(f(x)-f(a))/(x-a)=f'(c_x)`. Since `a<c_x<x`, as `x` approaches `a` from the right, so does `c_x`. Therefore the difference quotient approaches `L`.

### Output

```json
{
  "main_step_skeleton": [
    {"id": "S1", "statement": "For x>a, there is c_x in (a,x) with (f(x)-f(a))/(x-a)=f'(c_x)."},
    {"id": "S2", "statement": "As x approaches a from the right, the difference quotient approaches L."}
  ],
  "student_facing_task": {
    "problem": "Suppose f is continuous on R, differentiable away from a, and lim_(t->a+) f'(t)=L.",
    "established_context": ["For x>a, a point c_x satisfies a<c_x<x and (f(x)-f(a))/(x-a)=f'(c_x)."],
    "solution_skeleton": [
      {"id": "S1", "statement": "(f(x)-f(a))/(x-a)=f'(c_x) for a<c_x<x."},
      {"id": "S2", "statement": "As x approaches a from the right, the difference quotient approaches L."}
    ],
    "transition_to_explain": {
      "from": "S1",
      "to": "S2",
      "question": "Explain why the location of c_x and the assumed derivative limit imply the stated limit of the difference quotient."
    },
    "student_instruction": "Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "Because a<c_x<x, we have 0<c_x-a<x-a. Hence c_x approaches a from the right as x approaches a from the right. The assumed limit of f' then gives f'(c_x) -> L. Since the supplied equality identifies the difference quotient with f'(c_x), the difference quotient also approaches L.",
  "required_criteria": [
    "Uses a<c_x<x to show that c_x approaches a from the right.",
    "Applies the given one-sided limit of f' to f'(c_x).",
    "Uses the supplied equality to transfer this limit to the difference quotient."
  ],
  "material_errors": [
    "Failing to justify that c_x approaches a from the right.",
    "Using the wrong one-sided limit or treating c_x as constant."
  ],
  "generation_notes": "The transition is a local squeeze-and-substitution argument that checks the approach direction before transferring the derivative limit."
}
```

---

## Final validation before returning

Before returning JSON, verify all of the following:

1. `solution_skeleton` contains exactly two consecutive entries from `main_step_skeleton`.
2. Exactly one transition is requested.
3. No important mathematical idea is hidden between the two displayed steps.
4. Every prerequisite is present in `established_context`.
5. The context contains neither the omitted derivation nor a later result or final answer.
6. The selected transition passes the hard rejection test and naturally needs a substantive explanation.
7. The student question does not reveal the expected theorem or ask for a new strategy.
8. The private reference explanation is local, correct, and does not continue the solution.
9. There are exactly three item-specific binary criteria and specific material errors.
10. `generation_notes` concretely explains why the selected bridge is non-routine.

If any condition fails, return exactly `NOT_SUITABLE`.
