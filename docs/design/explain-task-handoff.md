# EXPLAIN Task: Multi-Step Local Proof Gaps

## Purpose

EXPLAIN tests whether a model can justify the mathematical reasoning **between supplied key steps** of a solution. It is not asked to discover the method, choose a strategy, or finish the original problem.

The task is intended to be more structured and easier to evaluate than a free-form plan, while testing more than final-answer solving. It checks whether the model can identify the relevant concept, verify that it applies in the given setting, and derive the short missing bridge to the next supplied step.

## Student-facing format

The student receives:

1. The original problem.
2. A verified, ordered skeleton of the solution: two or three important main steps and any facts needed to interpret them.
3. A request to justify the omitted derivations between consecutive main steps.

The student must:

1. State the relevant theorem, identity, construction, or principle.
2. Explain why its assumptions or conditions hold here.
3. Give the minimal intermediate equations or inferences that connect each supplied main step to the next.

The student must not choose a different method, introduce a new strategy, derive omitted earlier constructions, or continue to an unsupplied part of the original solution.

## What is a main step?

A main step is a mathematically substantive transition that changes the state of the solution and enables what follows. It normally introduces or applies a non-routine mathematical idea, such as:

- a representation or substitution;
- a theorem application;
- an invariant or recurrence property;
- a counting correspondence or bijection;
- a decisive bound, factorization, or case split;
- a structural observation about roots, divisors, graphs, or functions.

A statement is a main step if removing it would force a competent solver to discover another mathematical idea. It is not defined by length: a one-line theorem application can be a main step, while a long expansion can be intermediate work.

Intermediate work is the local bridge needed to justify a main step: routine algebra, index shifts, substitutions, coefficient comparison, short inequalities, or a few concrete inferences from a supplied theorem.

## Boundary from other task forms

| Task | Student receives | Student must do |
| --- | --- | --- |
| SOLVE | Problem only | Discover and execute a complete method, then give the answer. |
| PLAN | Problem only | Choose and state a method and key future actions. |
| EXPLAIN | Problem plus supplied main steps | Justify why the supplied steps follow. |
| JUDGE | Problem plus a proposed solution | Decide whether it is correct and identify the first error if not. |

EXPLAIN stays distinct from PLAN because the mathematical decisions are already supplied. It stays distinct from SOLVE because the full route is visible and the student is not asked to discover or complete it.

## How many gaps per item?

Use two supplied transitions by default:

\[
\text{Main step A} \;\longrightarrow\; \text{Main step B} \;\longrightarrow\; \text{Main step C}.
\]

The answer reconstructs the two omitted local bridges. A third gap is allowed only when all gaps are short, use the same disclosed method, and fit in a concise explanation. Split the item when a bridge requires a new construction, a new case split, or a substantial proof.

Typical answer length: about 80--180 words. Very short easy items may be shorter. An item that needs a full proof is not a good EXPLAIN item.

## Generation rule

Given a verified solution:

1. Segment it into main steps and intermediate work.
2. Retain two or three ordered main steps whose missing bridges are locally derivable from the supplied context.
3. Supply the main-step outcomes, but do not supply the governing theorem or the bridging derivation.
4. Keep every earlier fact needed to make the requested explanation self-contained.
5. Exclude items where the omitted material is only arithmetic, or where filling it requires rediscovering the global strategy.

Each item should have a private reference explanation and a small criterion set. A useful three-part rubric is:

1. The required concept or theorem is used correctly.
2. Its assumptions are verified in the supplied context.
3. The intermediate derivation reaches the next main step without a material error.

## Examples from the pilot solutions

### Example 1: Primitive seventh roots of unity

#### Supplied main skeleton

\[
S=2\left(\frac1{u_1}+\frac1{u_2}+\frac1{u_3}\right),
\qquad u_r=x^r+x^{-r}.
\]

\[
u_1,u_2,u_3 \text{ are the roots of } p(t)=t^3+t^2-2t-1.
\]

\[
\frac1{u_1}+\frac1{u_2}+\frac1{u_3}=-2,
\qquad S=-4.
\]

#### Missing intermediate work

- Derive the cubic from the seventh-root identity by dividing by \(x^{3r}\) and expressing \(x^{2r}+x^{-2r}\) and \(x^{3r}+x^{-3r}\) in terms of \(u_r\).
- Apply the coefficient-root relationship for the cubic and use the reciprocal-sum identity.

The model does not need to discover the root-of-unity substitution or decide to use Vieta's formulas. Those are already fixed by the skeleton.

### Example 2: Long cycles in \(S_{100}\)

#### Supplied main skeleton

There is at most one cycle of length at least \(51\).

For a fixed \(k\in\{51,\ldots,100\}\), the number of permutations with a \(k\)-cycle is

\[
\frac{100!}{k}.
\]

Therefore the required count is

\[
\sum_{k=51}^{100}\frac{100!}{k}.
\]

#### Missing intermediate work

- Choose the \(k\) elements in the cycle, explain why they form \((k-1)!\) distinct cycles, and permute the remaining elements.
- Explain why the cases for different \(k\) are disjoint and can be summed.

### Example 3: Tower of Hanoi generating function

#### Supplied main skeleton

\[
H(x)=\sum_{n\ge0}h_nx^n,\qquad h_0=0.
\]

\[
H(x)=2xH(x)+\frac{x}{1-x}.
\]

\[
H(x)=\frac1{1-2x}-\frac1{1-x},
\qquad h_n=2^n-1.
\]

#### Missing intermediate work

- Justify the index shift \(\sum_{n\ge1}h_{n-1}x^n=xH(x)\) and the geometric-series term \(x/(1-x)\).
- Rearrange the functional equation, use partial fractions, and extract coefficients.

This is a valid but relatively easy EXPLAIN item because much of the second bridge is routine algebra.

### Example 4: Logistic recurrence

#### Supplied main skeleton

\[
x_n=\frac{t}{1+t}a_n
\quad\Longrightarrow\quad
x_{n+1}=r x_n(1-x_n),
\qquad p=1-\frac1r.
\]

\[
(x_n) \text{ is monotone and bounded around } p.
\]

\[
\lim x_n=p,
\qquad \lim a_n=1.
\]

#### Why this should be split

The first bridge needs an interval-invariance argument, a sign analysis of \(F(x)-x\), and separate cases. The second bridge uses monotone convergence, continuity, and fixed points. These should become two EXPLAIN items rather than one long answer.

## Quality checks

Reject or split an item if:

- the missing work is only arithmetic or routine simplification;
- the skeleton omits the central construction, substitution, invariant, or case split;
- the answer would need to discover a new method;
- the explanation would effectively reproduce the whole solution;
- the source solution is mathematically incorrect or ambiguous.

The desired item is a constrained proof gap: nontrivial enough to test mathematical understanding, but local enough to have a fixed, reliable evaluation rubric.
