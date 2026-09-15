You generate one EXPLAIN task from a verified mathematics solution.

<problem>
{problem}
</problem>

<verified_full_solution>
{reference_solution}
</verified_full_solution>

## Goal

EXPLAIN tests whether a student can justify **one important local transition in a known solution**.

The student is shown two consecutive important solution steps and must explain why the second follows from the first.

The student must **not** need to discover a new strategy, construction, substitution, invariant, case split, or later solution step.

---

## 1. Build the main-step skeleton

Reduce the verified solution to an ordered list of its important mathematical steps:

S1, S2, ..., Sn.

A main step is a non-routine mathematical move or result, such as:

* applying a theorem or important identity;
* introducing an essential representation or substitution;
* establishing an invariant, lemma, decisive equation, bound, or factorization;
* making an essential case split;
* setting up an important counting argument or correspondence.

Routine algebra, arithmetic, expansion, cancellation, direct substitution, and mechanical simplification are **not** separate main steps.

Do not merge or omit important mathematical ideas.

---

## 2. Select exactly one transition

Choose exactly **two consecutive main steps** Si and S(i+1).

The transition between them will be the EXPLAIN task.

Choose a transition that is mathematically important and requires genuine justification, while remaining locally explainable.

A valid transition must satisfy all of the following:

1. **The steps are genuinely consecutive.**
   There is no hidden main mathematical idea between them.

2. **The reasoning is local.**
   The problem, supplied context, and Si contain everything needed to justify S(i+1).

3. **The strategy is already determined.**
   The student may identify and use a theorem, identity, counting principle, or mathematical argument, but must not invent another main idea.

4. **The gap is non-trivial.**
   Do not select mere arithmetic or routine algebraic simplification.

5. **The gap is bounded.**
   A good explanation should normally require about 50–120 words.

6. **The task stops at S(i+1).**
   The student must not continue solving the original problem.

7. **Do not reveal the original final answer or later solution steps.**

If a fact established before Si is necessary, include it in `established_context`.

Do not put the missing derivation itself or any later solution result in `established_context`.

If no suitable transition exists, return exactly:

`NOT_SUITABLE`

---

## 3. Create the explanation target

Write one question asking why S(i+1) follows from Si.

The question should ask for justification of the supplied move, not ask what to do next.

Good examples:

* "Explain why this counting argument gives the stated expression."
* "Explain why the theorem applies here and yields the next step."
* "Explain how the stated identity leads to the next equation."
* "Explain why the previous relation implies the stated bound."
* "Explain why these cases exhaust all possibilities."

Do not ask:

* "What should we do next?"
* "How would you solve the problem?"
* "Find a useful substitution."
* "Continue the solution."

---

## Reference explanation and evaluation

Write a concise gold explanation containing **only the reasoning needed for this transition**.

Also create exactly **three binary evaluation criteria** covering the essential mathematical content of a correct explanation.

The criteria should evaluate mathematical content, not wording. Alternative correct arguments must be accepted.

Also list important mathematical errors that should cause the response to fail.

## Student instruction

Use exactly:

"Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps."

---

## Output format

Return valid JSON only:

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
    "student_instruction": "..."
  },
  "reference_explanation": "...",
  "required_criteria": ["...", "...", "..."],
  "material_errors": ["...", "..."],
  "generation_notes": "..."
}
```

`main_step_skeleton` and all fields outside `student_facing_task` are private.

The student sees only `student_facing_task`.

---

# Example 1: Counting a fixed cycle length

## Input

Problem:

How many permutations in S_100 contain a cycle of length at least 51?

Relevant solution:

There can be at most one such cycle. Partition the permutations according to its exact length k.

For fixed k, choose the k elements of the cycle in C(100,k) ways. They can be arranged into a cycle in (k-1)! ways, and the remaining 100-k elements can be permuted in (100-k)! ways. Therefore the fixed-k count is

C(100,k)(k-1)!(100-k)! = 100!/k.

Finally sum over the possible values of k.

## Output

```json
{
  "main_step_skeleton": [
    {
      "id": "S1",
      "statement": "Partition the desired permutations by the exact length k of their unique long cycle."
    },
    {
      "id": "S2",
      "statement": "For fixed k, the number of such permutations is 100!/k."
    },
    {
      "id": "S3",
      "statement": "Sum the fixed-k counts over the allowed values of k."
    }
  ],
  "student_facing_task": {
    "problem": "How many permutations in S_100 contain a cycle of length at least 51?",
    "established_context": [
      "A permutation of 100 elements can contain at most one cycle of length at least 51."
    ],
    "solution_skeleton": [
      {
        "id": "S1",
        "statement": "Partition the desired permutations by the exact length k of their unique long cycle."
      },
      {
        "id": "S2",
        "statement": "For fixed k, the number of such permutations is 100!/k."
      }
    ],
    "transition_to_explain": {
      "from": "S1",
      "to": "S2",
      "question": "Explain why the number of permutations with long-cycle length exactly k is 100!/k."
    },
    "student_instruction": "Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "Choose the k elements of the long cycle in C(100,k) ways. On a fixed k-element set there are (k-1)! distinct cycles because cyclic rotations represent the same cycle. The remaining 100-k elements may be permuted arbitrarily in (100-k)! ways. Multiplying gives C(100,k)(k-1)!(100-k)! = 100!/k.",
  "required_criteria": [
    "Accounts for choosing the k elements and permuting the remaining elements.",
    "Correctly uses (k-1)! for the number of cycles on a fixed k-element set.",
    "Combines and simplifies the factors to obtain 100!/k."
  ],
  "material_errors": [
    "Using k! without correcting for cyclic rotations.",
    "Ignoring permutations of the remaining elements."
  ],
  "generation_notes": "The fixed-k count is one important local counting argument and does not require continuing the solution."
}
```

---

# Example 2: Deriving a cubic from roots of unity

## Input

Problem:

Let x be a primitive seventh root of unity and define

u_r = x^r + x^(-r), for r=1,2,3.

Relevant solution:

For y=x^r,

1+y+y^2+...+y^6=0.

Divide by y^3 and pair reciprocal powers. With u=y+y^(-1),

y^2+y^(-2)=u^2-2

and

y^3+y^(-3)=u^3-3u.

This gives

u^3+u^2-2u-1=0.

Therefore u_1,u_2,u_3 are the three roots of this cubic, after which coefficient-root relations can be used.

## Output

```json
{
  "main_step_skeleton": [
    {
      "id": "S1",
      "statement": "Apply the seventh-root identity, divide by y^3, and group reciprocal powers."
    },
    {
      "id": "S2",
      "statement": "For u=y+y^(-1), the grouped relation becomes u^3+u^2-2u-1=0."
    },
    {
      "id": "S3",
      "statement": "Identify u_1,u_2,u_3 as the three roots of this cubic and use its coefficients."
    }
  ],
  "student_facing_task": {
    "problem": "Let x be a primitive seventh root of unity and define u_r=x^r+x^(-r) for r=1,2,3.",
    "established_context": [
      "For each r, y=x^r is also a primitive seventh root of unity.",
      "Let u=y+y^(-1)."
    ],
    "solution_skeleton": [
      {
        "id": "S1",
        "statement": "Use 1+y+...+y^6=0, divide by y^3, and group reciprocal powers."
      },
      {
        "id": "S2",
        "statement": "The resulting relation is u^3+u^2-2u-1=0."
      }
    ],
    "transition_to_explain": {
      "from": "S1",
      "to": "S2",
      "question": "Explain how the grouped reciprocal-power relation becomes u^3+u^2-2u-1=0."
    },
    "student_instruction": "Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "After dividing by y^3, the equation is (y^3+y^-3)+(y^2+y^-2)+(y+y^-1)+1=0. Since u=y+y^-1, we have y^2+y^-2=u^2-2 and y^3+y^-3=u^3-3u. Substituting these expressions gives (u^3-3u)+(u^2-2)+u+1=0, which simplifies to u^3+u^2-2u-1=0.",
  "required_criteria": [
    "Writes the correct grouped reciprocal-power relation after division by y^3.",
    "Correctly expresses the second and third reciprocal-power sums in terms of u.",
    "Substitutes and simplifies them to the stated cubic."
  ],
  "material_errors": [
    "Using an incorrect identity for y^2+y^(-2) or y^3+y^(-3).",
    "Obtaining a cubic with incorrect coefficients."
  ],
  "generation_notes": "The omitted reasoning is a substantive algebraic identity derivation with the overall strategy already supplied."
}
```

---

# Example 3: Transferring a derivative limit

## Input

Problem:

Suppose f is continuous on R, differentiable away from a, and

lim_(t->a+) f'(t)=L.

Relevant solution:

For x>a, the Mean Value Theorem gives c_x in (a,x) such that

(f(x)-f(a))/(x-a)=f'(c_x).

Since a<c_x<x, as x approaches a from the right, c_x also approaches a from the right. Hence the assumed limit of f' gives

(f(x)-f(a))/(x-a) -> L.

## Output

```json
{
  "main_step_skeleton": [
    {
      "id": "S1",
      "statement": "Apply the Mean Value Theorem on [a,x] for x>a."
    },
    {
      "id": "S2",
      "statement": "There exists c_x in (a,x) such that (f(x)-f(a))/(x-a)=f'(c_x)."
    },
    {
      "id": "S3",
      "statement": "As x approaches a from the right, the difference quotient approaches L."
    }
  ],
  "student_facing_task": {
    "problem": "Suppose f is continuous on R, differentiable away from a, and lim_(t->a+) f'(t)=L.",
    "established_context": [
      "For x>a, the Mean Value Theorem has already given c_x in (a,x) with (f(x)-f(a))/(x-a)=f'(c_x)."
    ],
    "solution_skeleton": [
      {
        "id": "S2",
        "statement": "There exists c_x in (a,x) such that (f(x)-f(a))/(x-a)=f'(c_x)."
      },
      {
        "id": "S3",
        "statement": "As x approaches a from the right, the difference quotient approaches L."
      }
    ],
    "transition_to_explain": {
      "from": "S2",
      "to": "S3",
      "question": "Explain why the location of c_x and the assumed derivative limit imply that the difference quotient approaches L."
    },
    "student_instruction": "Explain why the requested transition is mathematically valid. State the relevant theorem, identity, counting principle, construction, or argument when appropriate, show why it applies here, and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "Because a<c_x<x, we have 0<c_x-a<x-a. Hence as x approaches a from the right, c_x also approaches a from the right. The hypothesis lim_(t->a+)f'(t)=L therefore implies f'(c_x)->L. Since the Mean Value Theorem gives (f(x)-f(a))/(x-a)=f'(c_x), the right-hand difference quotient also approaches L.",
  "required_criteria": [
    "Uses a<c_x<x to justify that c_x approaches a from the right.",
    "Correctly applies the given right-hand limit of f' to f'(c_x).",
    "Uses the equality with f'(c_x) to transfer the limit to the difference quotient."
  ],
  "material_errors": [
    "Assuming c_x approaches a without using its location between a and x.",
    "Using the wrong one-sided derivative limit."
  ],
  "generation_notes": "This isolates one local limit argument after the theorem application has already been established."
}
```

Before returning the item, check:

1. `solution_skeleton` contains exactly **two consecutive** entries from `main_step_skeleton`;
2. exactly **one** transition is requested;
3. no other important mathematical idea is hidden inside that transition;
4. all required earlier facts are supplied as context;
5. no later solution result or final answer is exposed;
6. the task requires justification, not strategy discovery or continuation.

If these conditions cannot be satisfied, return exactly `NOT_SUITABLE`.
