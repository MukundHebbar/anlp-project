# EXPLAIN Task Generator

You are given a mathematics problem and a verified complete solution.

Your job is to create **one EXPLAIN training item**.

<problem>
{problem}
</problem>

<verified_full_solution>
{reference_solution}
</verified_full_solution>

## Task definition

EXPLAIN tests whether a student can justify an important local transition in a known solution.

The student is **not** asked to discover a solution strategy, predict the next step, or solve the problem. Instead, the student is shown a short ordered portion of the solution's main-step skeleton and must explain the missing reasoning between one or two adjacent supplied steps.

A good EXPLAIN task therefore has the form

$$
\text{shown main step}
\quad\Longrightarrow\quad
\boxed{\text{intermediate justification omitted}}
\quad\Longrightarrow\quad
\text{shown main step}.
$$

The omitted material should require mathematical understanding, but it must remain a **local derivation**, not another hidden solution idea.

---

## Step 1: Construct the main-step skeleton

First reduce the verified full solution to an ordered skeleton

$$
S_1,S_2,\ldots,S_n.
$$

Each skeleton step should represent an important mathematical action, result, or change in the state of the solution.

Examples include:

* introducing a useful representation or non-obvious substitution;
* applying a theorem or principle;
* establishing an invariant or important lemma;
* deriving a decisive equation, bound, or factorization;
* introducing an essential case split;
* establishing a counting correspondence;
* reducing the problem to a simpler mathematical object.

Do **not** make separate main steps out of routine execution such as arithmetic, straightforward algebraic rearrangement, direct substitution into an already chosen formula, expansion, cancellation, index manipulation, or other mechanical simplification.

Use this test:

> If removing a step would force the solver to discover another mathematical idea or make another non-routine decision, it should normally be a main step.
> If the missing material only works out why an already determined move is valid, it is normally intermediate reasoning.

A substitution, factorization, identity, or similar operation may therefore be a main step when choosing it is itself the important idea, but ordinary execution of an already supplied transformation is intermediate work.

The skeleton must preserve **every important mathematical idea in order**. Do not merge two main ideas merely to create an EXPLAIN gap.

---

## Step 2: Select the EXPLAIN gap

Select a **contiguous** portion of the skeleton containing either:

* two consecutive main steps \(S_i,S_{i+1}\), producing **one transition to explain**, or
* three consecutive main steps \(S_i,S_{i+1},S_{i+2}\), producing **two transitions to explain**.

Use one transition by default.

Use two transitions only when both are short, closely related, and can be justified locally without turning the task into a partial SOLVE problem.

For two-transition tasks, the student is explicitly shown the middle step:

$$
S_i \rightarrow S_{i+1} \rightarrow S_{i+2}.
$$

Therefore each transition must be independently explainable from its supplied starting step and the established context. The student must not need the hidden derivation of the first transition in order to understand the second.

### A valid transition must satisfy all of the following

1. **The two endpoints are genuinely consecutive main steps.**
   There must be no unshown main mathematical idea between them.

2. **The transition is locally derivable.**
   The problem, established context, and preceding supplied step contain everything necessary to justify the next supplied step.

3. **The solution strategy is already determined.**
   The student may need to recognize and state the theorem, identity, counting principle, or mathematical argument that validates the transition, but must not need to invent a different construction, substitution, invariant, case split, or overall method.

4. **The omitted reasoning is mathematically meaningful.**
   Do not ask the student merely to perform arithmetic or trivial simplification.

5. **The omitted reasoning is bounded.**
   It should normally take roughly 50–120 words for one transition. A two-transition explanation should normally fit in roughly 80–180 words total.

6. **The task stops locally.**
   Do not ask the student to continue solving after the final supplied skeleton step.

7. **Do not reveal the original final answer.**
   Do not select a slice whose final displayed step gives away the answer to the source problem. Do not place later solution facts in the established context.

If no such contiguous local gap exists, output exactly:

`NOT_SUITABLE`

Do not force an unsuitable problem into the EXPLAIN format.

---

## Step 3: Build the student-facing task

`established_context` may contain facts established **before** the selected skeleton slice that are necessary to explain it.

Only include facts that the student genuinely needs.

Do not put any of the following into established context:

* intermediate reasoning that the student is supposed to explain;
* a later result from the solution;
* the final answer;
* an additional hidden main idea that should instead appear as a skeleton step.

The student-facing skeleton must contain exactly the selected two or three **consecutive** main steps. Preserve their IDs from the complete skeleton so that their adjacency can be checked.

For every adjacent pair, write a direct explanation question.

The question should ask **why the supplied transition is valid**, not what should be done next.

Good forms include:

* "Explain why this counting argument gives the stated expression."
* "Explain why the assumptions allow this theorem to be applied and how it yields the next step."
* "Explain how the stated identity leads from S2 to S3."
* "Explain why these cases are exhaustive."
* "Explain why the previous relation implies the stated bound."

Do not ask:

* "What should we do next?"
* "How would you solve the problem?"
* "Find a useful substitution."
* "Can you prove the final answer?"
* anything requiring continuation beyond the supplied skeleton.

---

## Student instruction

Use the following instruction:

"Explain why each requested transition is mathematically valid. State the relevant theorem, identity, construction, counting principle, or argument when appropriate; show why its conditions hold here; and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new solution strategy, continue solving the original problem, or merely restate the supplied steps."

---

## Reference explanation and evaluation criteria

Create a concise gold explanation of the requested gap or gaps.

The `reference_explanation` is the **gold answer to the EXPLAIN task**, not the full solution to the original problem.

It should contain only the reasoning required for the selected transitions.

Also generate exactly **three item-specific binary criteria** for evaluating student explanations.

Together, the three criteria must cover the mathematically essential content of the explanation. They should test things such as:

* identifying or correctly using the governing mathematical fact;
* satisfying its assumptions, restrictions, or equality conditions;
* carrying out the critical intermediate inference that connects the supplied steps.

For a two-transition item, the three criteria must collectively cover **both transitions**.

Each criterion should describe mathematical content, not wording. Alternative correct explanations must be able to satisfy it.

Also list the most important mathematical mistakes that would invalidate an otherwise plausible response in `material_errors`.

---

## Output format

Return valid JSON only.

For a one-transition item:

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
    "transitions_to_explain": [
      {
        "from": "S2",
        "to": "S3",
        "question": "..."
      }
    ],
    "student_instruction": "..."
  },
  "reference_explanation": "...",
  "required_criteria": ["...", "...", "..."],
  "material_errors": ["...", "..."],
  "generation_notes": "..."
}
```

For a two-transition item, `solution_skeleton` contains three consecutive steps and `transitions_to_explain` contains exactly the two adjacent transitions.

`main_step_skeleton`, `reference_explanation`, `required_criteria`, `material_errors`, and `generation_notes` are private generation/evaluation fields. The student receives only `student_facing_task`.

---

# Few-shot Example 1: Local combinatorial counting

## Input

<problem>
How many permutations in S_100 contain a cycle of length at least 51?
</problem>

<verified_full_solution>
A permutation can contain at most one cycle of length at least 51. Partition the desired permutations according to the length k of this unique long cycle.

For fixed k, choose the k elements of the cycle in C(100,k) ways. A fixed set of k elements forms (k-1)! distinct cycles, because cyclic rotations describe the same cycle. The remaining 100-k elements can be permuted arbitrarily in (100-k)! ways. Thus the number for fixed k is

C(100,k)(k-1)!(100-k)! = 100!/k.

Summing this quantity over k=51,...,100 gives the required answer.
</verified_full_solution>

## Output

```json
{
  "main_step_skeleton": [
    {
      "id": "S1",
      "statement": "There is at most one cycle of length at least 51, so partition the desired permutations by its exact length k."
    },
    {
      "id": "S2",
      "statement": "For a fixed k, the number of such permutations is 100!/k."
    },
    {
      "id": "S3",
      "statement": "The total count is obtained by summing the fixed-k counts over 51 <= k <= 100."
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
        "statement": "For a fixed k, the number of such permutations is 100!/k."
      }
    ],
    "transitions_to_explain": [
      {
        "from": "S1",
        "to": "S2",
        "question": "Explain why the number of permutations with long-cycle length exactly k is 100!/k. Account for the cycle elements, their cyclic ordering, and the remaining elements."
      }
    ],
    "student_instruction": "Explain why each requested transition is mathematically valid. State the relevant theorem, identity, construction, counting principle, or argument when appropriate; show why its conditions hold here; and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new solution strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "Choose the k elements of the long cycle in C(100,k) ways. On a fixed k-element set there are (k-1)! distinct k-cycles, since the k cyclic rotations represent the same cycle. The remaining 100-k elements can be permuted arbitrarily in (100-k)! ways. Multiplying gives C(100,k)(k-1)!(100-k)! = 100!/k.",
  "required_criteria": [
    "Counts the choice of the k cycle elements and the arrangement of the remaining elements.",
    "Uses (k-1)! distinct cycles on a fixed k-element set and correctly accounts for cyclic rotations.",
    "Combines the factors correctly to obtain 100!/k."
  ],
  "material_errors": [
    "Counting a fixed k-element cycle as k! without correcting for cyclic rotations.",
    "Failing to account for arbitrary permutations of the remaining elements."
  ],
  "generation_notes": "The fixed-k enumeration is a substantive but local counting argument between consecutive solution steps."
}
```

---

# Few-shot Example 2: Algebraic identity followed by coefficient relations

## Input

<problem>
Let x be a primitive seventh root of unity and define
u_r = x^r + x^(-r) for r=1,2,3.
Evaluate
Q = (u_1+2)(u_2+2)(u_3+2).
</problem>

<verified_full_solution>
For r=1,2,3, y=x^r is also a primitive seventh root of unity, so

1+y+y^2+...+y^6=0.

Divide by y^3 and pair reciprocal powers. If u=y+y^(-1), then

y^2+y^(-2)=u^2-2
and
y^3+y^(-3)=u^3-3u.

Hence u satisfies

u^3+u^2-2u-1=0.

The three values u_1,u_2,u_3 are distinct, so they are precisely the three roots of

p(t)=t^3+t^2-2t-1.

Vieta's relations therefore give

u_1+u_2+u_3=-1,
u_1u_2+u_1u_3+u_2u_3=-2,
u_1u_2u_3=1.

Expanding Q using these symmetric sums then gives the required value.
</verified_full_solution>

## Output

```json
{
  "main_step_skeleton": [
    {
      "id": "S1",
      "statement": "For each r, apply the seventh-root identity to y=x^r, divide by y^3, and group reciprocal powers."
    },
    {
      "id": "S2",
      "statement": "Each u_r satisfies p(t)=t^3+t^2-2t-1, so the three distinct u_r are the roots of p."
    },
    {
      "id": "S3",
      "statement": "Vieta's relations determine the sum, pairwise-product sum, and product of u_1,u_2,u_3."
    },
    {
      "id": "S4",
      "statement": "Expand Q in terms of these symmetric quantities to obtain the requested value."
    }
  ],
  "student_facing_task": {
    "problem": "Let x be a primitive seventh root of unity and define u_r=x^r+x^(-r) for r=1,2,3. Evaluate Q=(u_1+2)(u_2+2)(u_3+2).",
    "established_context": [
      "For r=1,2,3, y=x^r is a primitive seventh root of unity.",
      "The three values u_1,u_2,u_3 are distinct."
    ],
    "solution_skeleton": [
      {
        "id": "S1",
        "statement": "For each r, use 1+y+...+y^6=0 with y=x^r, divide by y^3, and group reciprocal powers."
      },
      {
        "id": "S2",
        "statement": "Each u_r satisfies p(t)=t^3+t^2-2t-1, and u_1,u_2,u_3 are therefore its three roots."
      },
      {
        "id": "S3",
        "statement": "Their symmetric quantities satisfy u_1+u_2+u_3=-1, u_1u_2+u_1u_3+u_2u_3=-2, and u_1u_2u_3=1."
      }
    ],
    "transitions_to_explain": [
      {
        "from": "S1",
        "to": "S2",
        "question": "Explain how grouping the reciprocal powers produces the cubic equation for u_r."
      },
      {
        "from": "S2",
        "to": "S3",
        "question": "Explain how the stated symmetric quantities follow from the cubic."
      }
    ],
    "student_instruction": "Explain why each requested transition is mathematically valid. State the relevant theorem, identity, construction, counting principle, or argument when appropriate; show why its conditions hold here; and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new solution strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "After dividing the seventh-root identity by y^3, the grouped equation is (y^3+y^-3)+(y^2+y^-2)+(y+y^-1)+1=0. Writing u=y+y^-1 gives y^2+y^-2=u^2-2 and y^3+y^-3=u^3-3u, hence u^3+u^2-2u-1=0. Thus each distinct u_r is a root of the cubic. For a monic cubic t^3+at^2+bt+c with roots u_1,u_2,u_3, Vieta gives their sum as -a, pairwise-product sum as b, and product as -c. Here these are -1, -2, and 1.",
  "required_criteria": [
    "Correctly converts the grouped reciprocal powers into u^3+u^2-2u-1=0 using the identities for the second and third powers.",
    "Correctly connects the three distinct u_r values with the three roots of the cubic.",
    "Applies Vieta's relations with the correct signs to obtain all three stated symmetric quantities."
  ],
  "material_errors": [
    "Using incorrect reciprocal-power identities.",
    "Using incorrect signs in Vieta's relations."
  ],
  "generation_notes": "The two consecutive gaps execute the same disclosed root-of-unity reduction and remain short enough to justify locally."
}
```

---

# Few-shot Example 3: Theorem conditions and limit transfer

## Input

<problem>
Suppose f is continuous on R, differentiable on
(-infinity,a) union (a,infinity), and

lim_(t->a-) f'(t) = lim_(t->a+) f'(t) = L.

Determine whether f must be differentiable at a. </problem>

<verified_full_solution>
Consider x>a. Since f is continuous on [a,x] and differentiable on (a,x), the Mean Value Theorem gives some c_x in (a,x) such that

(f(x)-f(a))/(x-a)=f'(c_x).

Since a<c_x<x, as x approaches a from the right we also have c_x approaching a from the right. The assumed limit of f' therefore gives

(f(x)-f(a))/(x-a) -> L.

The same argument on the left gives the corresponding left-hand difference quotient limit. Since both one-sided difference quotient limits agree, f is differentiable at a with derivative L.
</verified_full_solution>

## Output

```json
{
  "main_step_skeleton": [
    {
      "id": "S1",
      "statement": "For x>a, apply the Mean Value Theorem to f on [a,x]."
    },
    {
      "id": "S2",
      "statement": "There exists c_x in (a,x) such that (f(x)-f(a))/(x-a)=f'(c_x)."
    },
    {
      "id": "S3",
      "statement": "As x approaches a from the right, the right-hand difference quotient approaches L."
    },
    {
      "id": "S4",
      "statement": "Apply the corresponding argument on the left and compare the two one-sided difference quotient limits."
    }
  ],
  "student_facing_task": {
    "problem": "Suppose f is continuous on R, differentiable on (-infinity,a) union (a,infinity), and both one-sided limits of f'(t) at a equal L. Determine whether f must be differentiable at a.",
    "established_context": [
      "Consider only x>a.",
      "f is continuous on [a,x] and differentiable on (a,x).",
      "lim_(t->a+) f'(t)=L."
    ],
    "solution_skeleton": [
      {
        "id": "S1",
        "statement": "Apply the Mean Value Theorem to f on [a,x]."
      },
      {
        "id": "S2",
        "statement": "There exists c_x in (a,x) such that (f(x)-f(a))/(x-a)=f'(c_x)."
      },
      {
        "id": "S3",
        "statement": "As x approaches a from the right, (f(x)-f(a))/(x-a) approaches L."
      }
    ],
    "transitions_to_explain": [
      {
        "from": "S1",
        "to": "S2",
        "question": "Explain why the Mean Value Theorem applies here and gives the stated point c_x and equality."
      },
      {
        "from": "S2",
        "to": "S3",
        "question": "Explain why c_x approaches a from the right and why this implies the stated limit of the difference quotient."
      }
    ],
    "student_instruction": "Explain why each requested transition is mathematically valid. State the relevant theorem, identity, construction, counting principle, or argument when appropriate; show why its conditions hold here; and give only the intermediate reasoning needed to connect the two supplied steps. Do not choose a new solution strategy, continue solving the original problem, or merely restate the supplied steps."
  },
  "reference_explanation": "For x>a, f is continuous on [a,x] and differentiable on (a,x), so the Mean Value Theorem provides c_x in (a,x) with (f(x)-f(a))/(x-a)=f'(c_x). Since a<c_x<x, we have 0<c_x-a<x-a. Thus c_x approaches a from the right whenever x does. The assumed right-hand limit f'(t)->L then gives f'(c_x)->L, and the Mean Value Theorem equality transfers this limit to the difference quotient.",
  "required_criteria": [
    "Uses the Mean Value Theorem and verifies continuity on [a,x] and differentiability on (a,x).",
    "Uses a<c_x<x to justify that c_x approaches a from the right.",
    "Uses the given right-hand limit of f' together with the MVT equality to obtain the difference-quotient limit."
  ],
  "material_errors": [
    "Applying the Mean Value Theorem without establishing its hypotheses.",
    "Assuming c_x approaches a without using its location between a and x.",
    "Applying the left-hand derivative limit to the right-hand sequence c_x."
  ],
  "generation_notes": "The task isolates theorem application and the immediately following limit argument without requiring the student to complete the differentiability proof."
}
```

Before returning the JSON, verify internally that every selected pair is consecutive in `main_step_skeleton`, no important solution idea has been hidden inside a transition, no required premise comes from a later solution step, and no student-facing field reveals the original final answer.

If any of these conditions fail and a different valid local slice cannot be selected, return exactly `NOT_SUITABLE`.
