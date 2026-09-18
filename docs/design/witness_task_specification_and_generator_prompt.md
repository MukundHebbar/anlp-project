# WITNESS Task: Definition, Generation Prompt, and Evaluation Protocol

## 1. Task Definition

**WITNESS** is a problem-anchored mathematical construction task.

Starting from a mathematical problem and a verified solution, a generator identifies a **load-bearing feature** of the problem or reasoning. This may be an assumption, bound, threshold, domain restriction, structural condition, implication, or equality condition. It then either modifies that feature locally or asks for a concrete instance attaining it.

The student must construct:

1. a concrete mathematical object or instance satisfying the requested conditions; and
2. a short verification showing that the object has the required property.

Formally,

\[
(\text{problem},\text{verified solution})
\rightarrow \text{load-bearing feature}
\rightarrow \text{local construction request}
\rightarrow \text{witness and verification}.
\]

The task must remain closely tied to the source problem. It must not become a generic request for an example of a theorem merely because that theorem appeared in the solution.

A valid response does not need to match the reference witness created during dataset generation.

---

## 2. Capability Being Tested

WITNESS tests whether a model can:

- recognize how a mathematical conclusion depends on its conditions;
- reason about a nearby case obtained through a controlled change;
- construct an object satisfying several mathematical constraints; and
- verify that the constructed object demonstrates the requested phenomenon.

This distinguishes WITNESS from the other task forms:

| Task | Required capability |
|---|---|
| **SOLVE** | Derive a solution and final answer to the source problem. |
| **JUDGE** | Determine whether a proposed solution is correct and identify an error when present. |
| **WITNESS** | Construct and verify an instance demonstrating the role, limit, or attainability of a condition in the source reasoning. |

---

## 3. Inputs Seen by Each Model

### Generator input

The generator receives:

- the complete source problem;
- a verified worked solution; and
- any available metadata, such as topic and difficulty.

The full solution is provided to the generator so that it can identify a genuinely important feature rather than making a superficial change based only on the wording of the question.

### Student input

The student receives:

- the complete source problem;
- a short statement of the relevant fact established by the solution, when needed; and
- the generated WITNESS task.

The student should **not normally receive the complete worked solution**. Only the minimum context required to make the construction request self-contained should be included. This avoids unnecessarily long prompts and prevents the task from collapsing into extraction from the supplied solution.

### Judge input

The judge receives:

- the source problem;
- the complete verified solution;
- the WITNESS task;
- the hidden task-specific rubric;
- one reference witness and its verification; and
- the student's response.

The reference witness is evidence that the task is feasible. It is not the only accepted answer.

---

## 4. Allowed Construction Types

Each retained item should have one primary `transformation_type`.

### 4.1 `boundary_shift`

Change a meaningful numerical threshold or bound and request an instance demonstrating the consequence.

Typical form:

> The original argument relies on the threshold \(t\). Replace it by \(t'\). Construct an object showing that the original uniqueness, impossibility, or guarantee no longer holds.

### 4.2 `assumption_weakening`

Remove or weaken one assumption used essentially in the solution and request an instance for which the original conclusion fails.

Typical form:

> The original argument uses condition \(A\). Without \(A\), construct an object satisfying the remaining hypotheses but violating conclusion \(B\).

### 4.3 `domain_extension`

Extend a statement outside the domain or range on which it was established and request an example where the property fails.

Typical form:

> The identity was proved on domain \(D\). Construct an object in the specified extension of \(D\) for which the identity fails.

### 4.4 `converse_failure`

When the solution establishes \(A\Rightarrow B\), request an instance satisfying \(B\) but not \(A\).

This type is permitted only when a verified counterexample exists. Do not ask the student to decide freely whether the converse is true or false, because a true converse may require a general proof rather than witness construction.

### 4.5 `equality_case`

When the solution establishes an upper or lower bound, request an object attaining equality.

The construction must be a meaningful part of the mathematics. Reject equality cases obtained by directly copying a value already displayed in the student context.

### 4.6 `structural_stress_test`

Make a small structural change that preserves most of the original setting and request an instance revealing its effect. Use this type only when none of the preceding labels describes the construction accurately.

---

## 5. Requirements for a Valid Generated Item

A retained WITNESS item must satisfy all of the following.

### 5.1 Problem anchoring

The task must preserve the source problem's principal objects and mathematical setting. Merely mentioning the same theorem or topic is insufficient.

### 5.2 One primary change

The task should modify exactly one primary feature. Dependent consequences of that change are allowed, but two independent assumptions or parameters should not be changed simultaneously.

### 5.3 Constructive response

The requested output must be a concrete object, tuple, function, graph, set, polynomial, integer, sequence, or other explicit instance. The central requirement must not be a general proof or another unrestricted full solution.

### 5.4 Non-triviality

Producing the witness should require understanding the relevant mathematical structure. Reject tasks solved by copying an object from the supplied context or performing a single obvious substitution with no meaningful construction.

### 5.5 Feasibility

The generator must produce at least one correct reference witness before retaining the item.

### 5.6 Checkable conditions

The task must admit a finite list of success conditions that a judge can apply to arbitrary student witnesses. The rubric must describe properties, not surface similarity to the reference answer.

### 5.7 Controlled scope

Verifying the witness should normally be shorter than solving the source problem. A small minority of unusually difficult items is acceptable, but the generator should reject items whose verification generally requires a new long proof.

### 5.8 No unnecessary optimality requirement

Avoid phrases such as "smallest possible," "first," or "simplest" unless minimality is essential and the rubric contains a reliable way to verify it. Prefer a precise admissible range or degree instead.

---

## 6. When to Return `NOT_SUITABLE`

Return `NOT_SUITABLE` if any of the following holds:

- no natural load-bearing feature can be identified;
- every available modification is arbitrary or only weakly connected to the source problem;
- the task would require changing several independent parts of the setup;
- the requested witness is already explicitly given in the student context;
- the construction is merely routine substitution with no meaningful mathematical choice;
- no valid reference witness can be established confidently;
- correctness cannot be expressed as concrete rubric conditions;
- the modification turns the task into another full-length problem or general proof;
- the task asks whether a converse holds without already establishing a verified counterexample;
- the source solution itself appears incorrect or materially incomplete.

It is preferable to reject a source problem rather than force an artificial WITNESS task.

---

## 7. Generator Output Format

Return either the exact string:

```text
NOT_SUITABLE
```

or one valid JSON object with this structure:

```json
{
  "transformation_type": "boundary_shift | assumption_weakening | domain_extension | converse_failure | equality_case | structural_stress_test",
  "load_bearing_feature": "The exact assumption, bound, condition, or implication used by the source solution.",
  "connection_to_source": "Why this feature is important to the original reasoning and why the new task remains anchored to it.",
  "student_facing_task": {
    "source_problem": "Complete original problem statement.",
    "relevant_context": [
      "Only the facts from the verified solution needed to understand the task."
    ],
    "witness_request": "A precise request for one concrete object and a short verification.",
    "response_instruction": "Give a concrete witness and briefly verify every required condition. Do not re-solve the original problem."
  },
  "reference_witness": {
    "object": "One valid witness.",
    "verification": "A concise verification of every required property."
  },
  "evaluation_rubric": {
    "object_type": "The kind of mathematical object expected.",
    "required_conditions": [
      "Atomic binary condition 1.",
      "Atomic binary condition 2."
    ],
    "required_phenomenon": "The exact failure, boundary behavior, converse failure, or equality attainment that must be demonstrated.",
    "acceptable_variation": "Equivalent representations and alternative witnesses that must be accepted.",
    "material_errors": [
      "An error that makes the witness invalid."
    ]
  },
  "quality_checks": {
    "single_primary_change": true,
    "problem_anchored": true,
    "reference_verified": true,
    "not_trivial_copying": true,
    "verification_shorter_than_full_solution": true
  }
}
```

All rubric conditions must be independently understandable. Do not write criteria such as "matches the reference answer" or "uses the intended method."

---

## 8. Generator Prompt

```text
You are constructing one WITNESS training item from a mathematical problem and a verified worked solution.

A WITNESS task asks the student to construct a concrete mathematical instance that demonstrates the role, limit, failure, or attainability of a feature used in the source problem or its solution.

You will receive:
<problem>
{problem}
</problem>

<verified_solution>
{verified_solution}
</verified_solution>

Your job:

1. Identify one load-bearing feature of the source problem or reasoning: an assumption, threshold, bound, domain restriction, structural condition, implication, or equality condition.
2. Create one problem-anchored construction request using exactly one primary transformation:
   - boundary_shift
   - assumption_weakening
   - domain_extension
   - converse_failure
   - equality_case
   - structural_stress_test
3. Preserve the principal objects and setting of the source problem.
4. Require the student to give a concrete object and a short verification.
5. Produce one valid reference witness and verify it fully.
6. Create a hidden rubric containing atomic conditions that can be applied to witnesses different from the reference.

The student should receive the original problem and only the minimum solution context needed to make the new task self-contained. Do not expose the full worked solution unless every part is genuinely required.

Hard requirements:

- Modify exactly one primary feature.
- Keep the task directly tied to the source problem.
- Request a concrete mathematical object or instance.
- Ensure that at least one valid witness exists.
- Do not treat the reference witness as the only correct response.
- Do not create a generic theorem-example question.
- Do not ask for a new long proof or another unrestricted full solution.
- Do not require the smallest, first, or simplest witness unless minimality can be verified reliably.
- For converse_failure, request an example satisfying the conclusion but not the hypothesis; use this type only when such an example has been verified.
- For equality_case, ensure that the construction is not copied directly from the student context.
- If the source solution appears unreliable, or no natural non-trivial and checkable construction can be produced, return exactly NOT_SUITABLE.

Before returning an item, privately check:

- Is the changed feature genuinely used by the source reasoning?
- Does the task preserve most of the source setting?
- Does only one main feature change?
- Is the reference witness mathematically valid?
- Could a different valid witness be graded using the rubric alone?
- Is the task more meaningful than direct substitution or copying?
- Is verification normally shorter than solving the original problem?

Return exactly NOT_SUITABLE or one JSON object following the required schema. Return no commentary and no Markdown code fence.
```

---

## 9. Evaluation Protocol

WITNESS outputs are evaluated using a fixed LLM judge. When practical, deterministic calculations may supplement the judge, but they are not required for every item.

The judge evaluates the student's proposed witness independently. It must not reject a correct answer merely because it differs from the reference witness.

### Judge output

```text
well_definedness: PASS / FAIL
constraint_satisfaction: PASS / FAIL
required_phenomenon: PASS / FAIL
verification_correctness: PASS / FAIL
overall_witness: VALID / INVALID
```

Use the following aggregation rule:

```text
overall_witness = VALID
if and only if all four component decisions are PASS.
```

### Evaluation criteria

#### Well-definedness

Is the proposed object specified clearly enough to evaluate?

#### Constraint satisfaction

Does it satisfy every explicit condition in the task-specific rubric?

#### Required phenomenon

Does it actually demonstrate the requested failure, boundary behavior, converse failure, or equality case?

#### Verification correctness

Is the mathematical justification correct and sufficient to establish the required properties?

### Judge reliability

The judge model, prompt, decoding settings, and rubric format must be fixed before final evaluation. Human agreement should be measured on a stratified sample spanning:

- mathematical topics;
- WITNESS transformation types;
- correct and incorrect responses; and
- easy and difficult items.

A small number of difficult or ambiguous cases is acceptable. Their rate should be reported, and they should not be concentrated in one topic or transformation type.

---

## 10. Examples

### Example 1: Boundary Shift in Permutations

#### Source problem

How many permutations in \(S_{100}\) contain at least one cycle of length at least \(51\)?

#### Relevant source fact

A permutation cannot contain two cycles of length at least \(51\), because

\[
51+51>100.
\]

This uniqueness permits counting by the length of the single long cycle.

#### WITNESS task

Change the threshold from \(51\) to \(50\). Construct a permutation in \(S_{100}\) containing two distinct cycles of length at least \(50\). Briefly verify the cycle lengths and that the cycles are disjoint.

#### Reference witness

\[
(1\ 2\ \cdots\ 50)(51\ 52\ \cdots\ 100).
\]

The two displayed cycles are disjoint and each contains exactly \(50\) elements. Therefore, two cycles meeting the modified threshold can coexist, so the uniqueness property used at threshold \(51\) fails at threshold \(50\).

#### Hidden rubric

- The response specifies a permutation of the elements \(1,\ldots,100\).
- It contains two distinct disjoint cycles.
- Each of those cycles has length at least \(50\).
- The verification correctly explains why this contradicts uniqueness at the modified threshold.

---

### Example 2: Domain Extension in Polynomial Quadrature

#### Source problem

Suppose

\[
\int_0^2 f(x)\,dx=f(\alpha)+f(\beta)
\]

for every polynomial \(f\) of degree at most \(2\). Determine the required relation between \(\alpha\) and \(\beta\).

#### Relevant source fact

The solution establishes

\[
\alpha+\beta=2,
\qquad
\alpha\beta=\frac23.
\]

The quadrature identity is guaranteed only for polynomials of degree at most \(2\).

#### WITNESS task

Using the same \(\alpha\) and \(\beta\), give a polynomial of degree at least \(3\) for which

\[
\int_0^2 f(x)\,dx\ne f(\alpha)+f(\beta).
\]

Verify the inequality. You do not need to find the smallest possible degree.

#### Reference witness

Take \(f(x)=x^4\). Then

\[
\int_0^2x^4\,dx=\frac{32}{5}.
\]

Also,

\[
\alpha^2+\beta^2=(\alpha+\beta)^2-2\alpha\beta
=4-\frac43=\frac83,
\]

so

\[
\alpha^4+\beta^4
=(\alpha^2+\beta^2)^2-2(\alpha\beta)^2
=\frac{64}{9}-\frac89
=\frac{56}{9}.
\]

Since \(32/5\ne56/9\), the polynomial is a valid witness.

#### Hidden rubric

- The proposed object is a polynomial of degree at least \(3\).
- The integral and the two evaluation values are interpreted using the original \(\alpha,\beta\).
- The two sides are computed or compared correctly.
- The response demonstrates a genuine failure of the original identity.

Alternative polynomials must be accepted when they satisfy these conditions.

---

### Example 3: Assumption Weakening in a Carmichael-Type Criterion

#### Source problem

Find a composite integer \(m\) such that

\[
n^m\equiv n\pmod m
\]

for every integer \(n\).

#### Relevant source fact

A standard construction uses a squarefree composite \(m\) satisfying

\[
p-1\mid m-1
\]

for every prime divisor \(p\mid m\). Squarefreeness is a load-bearing condition.

#### WITNESS task

Remove squarefreeness. Construct a composite integer \(m\) such that

\[
p-1\mid m-1
\]

for every prime divisor \(p\mid m\), and give an integer \(n\) for which

\[
n^m\not\equiv n\pmod m.
\]

Verify both requirements.

#### Reference witness

Take \(m=9\). Its only prime divisor is \(3\), and

\[
3-1=2\mid 8=9-1.
\]

Choose \(n=3\). Since \(3^9\) is divisible by \(9\),

\[
3^9\equiv0\pmod9,
\qquad
3\equiv3\pmod9.
\]

Thus \(3^9\not\equiv3\pmod9\), showing that the remaining divisibility condition is insufficient without squarefreeness.

#### Hidden rubric

- \(m\) is composite and not squarefree.
- For every distinct prime divisor \(p\) of \(m\), the response verifies \(p-1\mid m-1\).
- The proposed integer \(n\) genuinely violates \(n^m\equiv n\pmod m\).
- All modular calculations used in the verification are correct.

---

### Example 4: Equality Construction for a Set-System Bound

#### Source problem

Let \(X=\{1,2,\ldots,9\}\). Determine the maximum number of three-element subsets in a family \(\mathcal C\) such that any two distinct members intersect in at most one element.

#### Relevant source fact

Every three-element subset contains three unordered pairs. Because two blocks cannot share a pair, pair counting gives

\[
3|\mathcal C|\le \binom92=36,
\]

and hence \(|\mathcal C|\le12\).

#### WITNESS task

Construct a family of \(12\) three-element subsets of \(X\) such that every two distinct subsets intersect in at most one element. Briefly verify the intersection property. Your construction should witness that the upper bound \(12\) is attainable.

#### Reference witness

Use the following family:

\[
\begin{aligned}
\mathcal C=\{&\{1,2,3\},\{4,5,6\},\{7,8,9\},\\
&\{1,4,7\},\{2,5,8\},\{3,6,9\},\\
&\{1,5,9\},\{2,6,7\},\{3,4,8\},\\
&\{1,6,8\},\{2,4,9\},\{3,5,7\}\}.
\end{aligned}
\]

Identify the elements with the nine points of \(\mathbb F_3^2\). The displayed triples are its affine lines, grouped by their four possible directions. Parallel lines are disjoint, while two nonparallel affine lines meet in exactly one point. Therefore, any two distinct triples intersect in at most one element, and the family contains \(12\) triples.

#### Hidden rubric

- The response gives exactly \(12\) distinct three-element subsets of \(X\).
- Every listed element belongs to \(X\).
- No unordered pair of elements occurs in two different subsets; equivalently, distinct subsets intersect in at most one element.
- The verification establishes the property for the whole family rather than checking only selected pairs.

The affine-plane construction is not required; any family satisfying the predicates is valid.

---

## 11. Dataset Construction Notes

Not every source problem needs a WITNESS counterpart. Short calculations, elementary recurrences, and questions with no meaningful condition to perturb may be rejected. This is preferable to admitting artificial or generic tasks.

Before large-scale generation, run a pilot and record:

- the `NOT_SUITABLE` rate overall and by mathematical topic;
- the distribution of transformation types;
- the human validity rate of generated tasks and reference witnesses;
- baseline student accuracy and response length;
- LLM-judge agreement with human labels; and
- the rate of judge-ambiguous cases.

If one transformation type dominates, balance the retained data or report subtype-specific results. Train, development, and test variants derived from the same source problem must remain in the same split.
