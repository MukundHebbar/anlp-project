You are given a mathematics problem and its verified reference solution. Construct one EXPLAIN task and its private reference answer.

Choose a major step that depends on a theorem, mathematical principle, construction, or nontrivial correspondence. Reject steps involving only arithmetic, algebraic rearrangement, direct substitution, or simplification. If no suitable step exists, output `NOT_SUITABLE`.

For the student-facing task:

* Include the original problem.
* Provide the necessary local context before the selected step.
* Show the construction or result obtained at that step.
* Hide the conceptual justification for why the step works.
* Ask the student to identify the relevant principle, explain why it applies, and derive the supplied result from the context.
* Do not ask the student to discover the construction, complete the remaining solution, or find the original final answer.
* Do not name the relevant theorem in the question if identifying it is part of the task.

Also generate a private reference answer that explains only the selected step. This answer is not shown to the evaluated model.

Output:

```text
<student_facing_task>
<original_problem>
...
</original_problem>

<context>
...
</context>

<supplied_step_and_result>
...
</supplied_step_and_result>

<question>
...
</question>
</student_facing_task>

<private_reference_answer>
...
</private_reference_answer>
```

Example:

```text
<context>
The values \(u_1,u_2,u_3\) are exactly the roots of
\[
p(t)=t^3+t^2-2t-1.
\]
</context>

<supplied_step_and_result>
\[
u_1u_2+u_1u_3+u_2u_3=-2,
\qquad
u_1u_2u_3=1.
\]
</supplied_step_and_result>

<question>
Explain how the displayed relations follow from the fact that
\(u_1,u_2,u_3\) are the roots of \(p(t)\). State the relevant
mathematical result and show how it applies.
</question>

<private_reference_answer>
Since the polynomial is monic,
\[
p(t)=(t-u_1)(t-u_2)(t-u_3).
\]
Expanding and comparing coefficients with
\(t^3+t^2-2t-1\) gives the pairwise-product sum \(-2\) and
the total product \(1\). This is Vieta’s coefficient-root
relationship.
</private_reference_answer>
```

Now construct an EXPLAIN task from:

```text
<problem>
{question}
</problem>

<reference_solution>
{reference_solution}
</reference_solution>
```
