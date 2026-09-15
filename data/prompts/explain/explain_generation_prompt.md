# Generator Prompt: Create EXPLAIN Proof-Gap Tasks

Use this prompt to convert a verified full mathematical solution into one EXPLAIN training item.

## Design decision

The student is shown a short, ordered skeleton of **main steps**. The student must justify one or two omitted local transitions between adjacent shown main steps.

The generator may select a contiguous slice of two or three main steps from the full solution. It must **not skip a main mathematical idea inside that slice**. It may omit only the intermediate derivation between adjacent main steps.

Use **one transition by default**. Use two transitions only if both are short, dependency-complete, use the same already disclosed method, and the combined explanation fits in about 80--180 words. Otherwise, generate one transition or return `NOT_SUITABLE`.

## Prompt

```text
You create one EXPLAIN task from a verified mathematical solution.

<problem>
{problem}
</problem>

<verified_full_solution>
{reference_solution}
</verified_full_solution>

Create an EXPLAIN item with the following definition.

EXPLAIN does not ask the student to discover a solution strategy or finish the
problem. Instead, it supplies a short ordered skeleton of important main steps
from the verified solution. The student explains why one or two transitions
between adjacent supplied main steps are valid.

A main step is a non-routine mathematical move or result: for example, a
representation, theorem application, invariant, counting correspondence,
decisive bound, factorization, or essential case split. Routine algebra,
arithmetic, substitutions, expansions, index shifts, and simplifications are
intermediate work.

Selection rules:
1. First segment the full solution into main steps and intermediate work.
2. Select a contiguous slice of either:
   - two main steps and one transition, or
   - three main steps and two transitions.
3. Do not skip a main step inside the selected slice. If a fact is needed from
   before the slice, provide it as established context.
4. Hide only the local derivations between adjacent shown main steps.
5. The student must be able to derive each requested transition using only the
   problem, established context, and the preceding supplied main step. Do not
   require a new construction, method choice, invariant, or case split that is
   not already supplied.
6. Prefer one transition. Use two only when their combined explanation is
   short and coherent. Reject broad proof segments.
7. Do not select routine arithmetic or mere simplification as the target.
8. Do not expose the original final answer or later solution steps in the
   student-facing task.
9. If the verified solution is ambiguous, incorrect, or has no suitable local
   conceptual transition, return exactly `NOT_SUITABLE`.

Student instruction:
"Explain why each requested transition is mathematically valid. State the
relevant theorem, identity, construction, or principle; verify why it applies
here; and give only the minimal intermediate derivation. Do not introduce a
new strategy, solve the whole problem, or continue beyond the supplied
skeleton."

Return valid JSON only, using exactly this schema:

{
  "student_facing_task": {
    "problem": "...",
    "established_context": ["..."],
    "solution_skeleton": [
      {"id": "M1", "statement": "..."},
      {"id": "M2", "statement": "..."}
    ],
    "transitions_to_explain": [
      {"from": "M1", "to": "M2", "question": "..."}
    ],
    "student_instruction": "..."
  },
  "private_reference_explanation": "...",
  "required_criteria": ["...", "...", "..."],
  "material_errors": ["..."],
  "generation_notes": "one sentence explaining why this is a suitable local proof gap"
}

The student-facing task must contain no private reference answer, no full
solution, and no final answer to the original problem.
```

## Few-shot example 1: fixed-length cycle count

### Source problem and private full solution

Problem: How many permutations in \(S_{100}\) contain a cycle of length at least \(51\)?

Relevant full-solution portion: there can be at most one such cycle. For a fixed length \(k\), choose its \(k\) elements, arrange them as a cycle, and permute the remaining elements, giving \(\binom{100}{k}(k-1)!(100-k)!=100!/k\).

### Correct generator output

```json
{
  "student_facing_task": {
    "problem": "How many permutations in S_100 contain a cycle of length at least 51?",
    "established_context": [
      "A permutation of 100 elements has at most one cycle of length at least 51.",
      "Fix k with 51 <= k <= 100."
    ],
    "solution_skeleton": [
      {
        "id": "M1",
        "statement": "We count permutations whose unique long cycle has length exactly k."
      },
      {
        "id": "M2",
        "statement": "The number of these permutations is 100!/k."
      }
    ],
    "transitions_to_explain": [
      {
        "from": "M1",
        "to": "M2",
        "question": "Explain why the fixed-k count is 100!/k. Account for choosing the cycle elements, counting cyclic orders, and arranging the remaining elements."
      }
    ],
    "student_instruction": "Explain why the requested transition is mathematically valid. State the counting principle and give the minimal derivation. Do not continue to the final summation."
  },
  "private_reference_explanation": "Choose the k elements of the long cycle in C(100,k) ways. On a fixed k-element set, there are (k-1)! distinct k-cycles because the k cyclic rotations represent the same cycle. The other 100-k elements may be permuted arbitrarily in (100-k)! ways. By the multiplication principle, the count is C(100,k)(k-1)!(100-k)!=100!/k.",
  "required_criteria": [
    "Chooses the k cycle elements, counts the cycle as (k-1)!, and permutes the remaining elements.",
    "Explains why a k-cycle has (k-1)! distinct cyclic orders.",
    "Correctly multiplies and simplifies the factors to 100!/k."
  ],
  "material_errors": [
    "Using k! rather than (k-1)! without correcting for cyclic rotations.",
    "Omitting the permutation of the remaining elements."
  ],
  "generation_notes": "The route is supplied and the omitted bridge is one local combinatorial derivation."
}
```

## Few-shot example 2: roots of unity to a cubic, then reciprocal sum

### Source problem and private full solution

Let \(x\) be a primitive seventh root of unity and define \(u_r=x^r+x^{-r}\). A full solution reduces a sum to reciprocal \(u_r\)-terms, proves that \(u_1,u_2,u_3\) are roots of \(p(t)=t^3+t^2-2t-1\), then obtains their reciprocal sum from coefficient-root relations.

### Correct generator output

```json
{
  "student_facing_task": {
    "problem": "Let x be a primitive seventh root of unity. Define u_r=x^r+x^{-r} for r=1,2,3.",
    "established_context": [
      "x^7=1 and x is not 1.",
      "For each r=1,2,3, x^r is also a primitive seventh root of unity.",
      "The relevant reciprocal expression is 1/u_1+1/u_2+1/u_3."
    ],
    "solution_skeleton": [
      {
        "id": "M1",
        "statement": "u_1, u_2, and u_3 are the three roots of p(t)=t^3+t^2-2t-1."
      },
      {
        "id": "M2",
        "statement": "1/u_1+1/u_2+1/u_3=-2."
      }
    ],
    "transitions_to_explain": [
      {
        "from": "context",
        "to": "M1",
        "question": "Explain why each u_r satisfies p(u_r)=0. Derive the cubic from the seventh-root identity."
      },
      {
        "from": "M1",
        "to": "M2",
        "question": "Explain why the reciprocal sum is -2 using the coefficient-root relations of the cubic."
      }
    ],
    "student_instruction": "Explain both transitions in order. State the needed identities and coefficient-root principle, verify their use here, and give only the minimal derivation."
  },
  "private_reference_explanation": "For each r, divide 1+x^r+...+x^{6r}=0 by x^{3r}. With u_r=x^r+x^{-r}, use x^{2r}+x^{-2r}=u_r^2-2 and x^{3r}+x^{-3r}=u_r^3-3u_r. This gives u_r^3+u_r^2-2u_r-1=0. Since the three u_r are distinct, they are the roots. For the monic cubic, coefficient comparison gives u_1u_2+u_1u_3+u_2u_3=-2 and u_1u_2u_3=1. Therefore the reciprocal sum equals the pairwise-product sum divided by the total product, namely -2.",
  "required_criteria": [
    "Correctly derives the cubic identity for u_r from the seventh-root relation.",
    "Uses the coefficient-root relations with the correct signs.",
    "Uses the reciprocal-sum identity and notes that the total product is nonzero."
  ],
  "material_errors": [
    "Using the wrong signs in the coefficient-root relations.",
    "Treating the reciprocal sum as the sum of roots."
  ],
  "generation_notes": "This is a valid two-transition item because the same supplied root-of-unity setup supports both short bridges."
}
```

## Few-shot example 3: theorem application and limit transfer

### Source problem and private full solution

Suppose \(f\) is continuous on \(\mathbb R\), differentiable on
\(({-\infty},a)\cup(a,\infty)\), and

\[
\lim_{t\to a^-}f'(t)=\lim_{t\to a^+}f'(t)=L.
\]

Determine whether \(f\) must be differentiable at \(a\). The full solution applies the Mean Value Theorem separately on the two sides of \(a\). This EXPLAIN item isolates only the right-hand argument and does not reveal or request the final conclusion of the original problem.

### Correct generator output

```json
{
  "student_facing_task": {
    "problem": "Suppose f is continuous on R, differentiable on (-infinity,a) union (a,infinity), and the one-sided limits of f' at a both equal L. Determine whether f must be differentiable at a.",
    "established_context": [
      "Consider only x>a.",
      "The function f is continuous on [a,x] and differentiable on (a,x).",
      "lim_{t->a+} f'(t)=L."
    ],
    "solution_skeleton": [
      {
        "id": "M1",
        "statement": "For every x>a, there exists c_x in (a,x) such that (f(x)-f(a))/(x-a)=f'(c_x)."
      },
      {
        "id": "M2",
        "statement": "As x approaches a from the right, (f(x)-f(a))/(x-a) approaches L."
      }
    ],
    "transitions_to_explain": [
      {
        "from": "context",
        "to": "M1",
        "question": "Explain why c_x exists and why the displayed equality holds."
      },
      {
        "from": "M1",
        "to": "M2",
        "question": "Explain why c_x approaches a from the right and why this makes the difference quotient approach L."
      }
    ],
    "student_instruction": "Explain both transitions in order. State the relevant theorem, verify its conditions, and justify the limit transfer. Do not analyze the left-hand case or complete the original problem."
  },
  "private_reference_explanation": "For each x>a, f is continuous on [a,x] and differentiable on (a,x), so the Mean Value Theorem gives c_x in (a,x) with (f(x)-f(a))/(x-a)=f'(c_x). Since a<c_x<x, we have 0<c_x-a<x-a; hence c_x approaches a from the right whenever x does. The assumed right-hand limit f'(t)->L therefore implies f'(c_x)->L. Because the difference quotient equals f'(c_x), it also approaches L.",
  "required_criteria": [
    "Identifies the Mean Value Theorem and verifies continuity on [a,x] and differentiability on (a,x).",
    "Uses a<c_x<x to prove that c_x approaches a from the right.",
    "Uses the given right-hand limit of f' and the MVT equality to obtain the limit of the difference quotient."
  ],
  "material_errors": [
    "Applying the Mean Value Theorem without continuity at the endpoint a.",
    "Claiming c_x=a or assuming convergence of c_x without using a<c_x<x.",
    "Completing the left-hand argument or stating the final answer instead of explaining the selected transitions."
  ],
  "generation_notes": "This example demonstrates two short dependent transitions: checking a theorem's hypotheses and then transferring a one-sided limit."
}
```

## Implementation notes

- The generator sees the full verified solution. The student never does.
- Parse and store `student_facing_task` separately from the private fields.
- Automatically reject malformed JSON, more than two transitions, duplicate or non-ordered main-step IDs, empty criteria, and private-final-answer leakage into the student fields.
- Manually audit a sample for dependency completeness: every requested transition should be derivable from the displayed context and preceding supplied step, without another hidden main idea.
- If the generator returns a long proof, a new strategy, or an unclear dependency, discard the item rather than trying to repair it automatically.
