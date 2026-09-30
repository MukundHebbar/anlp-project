> **Superseded where it conflicts with [FINAL-v3](../../data/manifests/final-v3/README.md)
> (2026-09-28).** The topic paths below still describe the pool. The final splits are
> 3,600 train / 400 test per task, and each task uses different questions. Test questions are
> allocated in proportion to (topic, difficulty) cell size, not about 1,024 / 256 per topic. The upper band
> 7.0–8.0 makes up about 30% of each task, not 20%. See "Final sampling" at the end.

## Topic Selection and Sampling

We will restrict the DeepMath subset to the following topic paths.

### Algebra

* `Mathematics -> Algebra -> Algebra -> Algebraic Expressions`
* `Mathematics -> Algebra -> Algebra -> Equations and Inequalities`
* `Mathematics -> Algebra -> Algebra -> Polynomial Operations`
* `Mathematics -> Algebra -> Intermediate Algebra -> Complex Numbers`
* `Mathematics -> Algebra -> Intermediate Algebra -> Exponential Functions`
* `Mathematics -> Algebra -> Intermediate Algebra -> Logarithmic Functions`
* `Mathematics -> Algebra -> Intermediate Algebra -> Other`
* `Mathematics -> Algebra -> Intermediate Algebra -> Quadratic Functions`
* `Mathematics -> Algebra -> Linear Algebra -> Determinants`
* `Mathematics -> Algebra -> Linear Algebra -> Linear Transformations`
* `Mathematics -> Algebra -> Linear Algebra -> Matrices`
* `Mathematics -> Algebra -> Linear Algebra -> Other`
* `Mathematics -> Algebra -> Linear Algebra -> Vectors`
* `Mathematics -> Algebra -> Other`

### Calculus

* `Mathematics -> Calculus -> Differential Calculus -> Applications of Derivatives`
* `Mathematics -> Calculus -> Differential Calculus -> Derivatives`
* `Mathematics -> Calculus -> Differential Calculus -> Other`
* `Mathematics -> Calculus -> Differential Calculus -> Related Rates`
* `Mathematics -> Calculus -> Integral Calculus -> Applications of Integrals`
* `Mathematics -> Calculus -> Integral Calculus -> Integrals`
* `Mathematics -> Calculus -> Integral Calculus -> Other`
* `Mathematics -> Calculus -> Integral Calculus -> Techniques of Integration -> Multi-variable`
* `Mathematics -> Calculus -> Integral Calculus -> Techniques of Integration -> Other`
* `Mathematics -> Calculus -> Integral Calculus -> Techniques of Integration -> Single-variable`
* `Mathematics -> Calculus -> Other`

### Number Theory

* `Mathematics -> Number Theory -> Congruences`
* `Mathematics -> Number Theory -> Divisibility`
* `Mathematics -> Number Theory -> Factorization`
* `Mathematics -> Number Theory -> Greatest Common Divisors (GCD)`
* `Mathematics -> Number Theory -> Least Common Multiples (LCM)`
* `Mathematics -> Number Theory -> Other`
* `Mathematics -> Number Theory -> Prime Numbers`

### Discrete Mathematics / Combinatorics

* `Mathematics -> Discrete Mathematics -> Algorithms`
* `Mathematics -> Discrete Mathematics -> Combinatorics`
* `Mathematics -> Discrete Mathematics -> Graph Theory`
* `Mathematics -> Discrete Mathematics -> Logic`
* `Mathematics -> Discrete Mathematics -> Other`

We exclude `Mathematics -> Algebra -> Abstract Algebra -> *`, `Mathematics -> Algebra -> Prealgebra -> *`, `Mathematics -> Differential Equations -> *`, `Mathematics -> Geometry -> Differential Geometry -> *`, `Mathematics -> Geometry -> Non-Euclidean Geometry -> *`, and the remaining unrelated topic groups.

For the **4,096-example training set**, we sample approximately **1,024 source problems from each broad topic**. For the **1,024-example held-out DeepMath test set**, we sample approximately **256 source problems from each broad topic**.

Within each broad topic, subtopics are sampled roughly in proportion to their natural frequency rather than equally. Train and test should maintain similar subtopic proportions and similar mean difficulty.

Across both splits, we target approximately **80% of problems from difficulty 5–7 and 20% from difficulty 7–8**.

## Final sampling (FINAL-v3)

The paragraphs above were the original plan. What was built:

- **Per task:** 4,000 questions, 3,600 train / 400 test, chosen for compute constraints. There
  is no development split.
- **Different questions per task.** No DeepMath question, counting duplicates, appears in more
  than one task.
- **Matched distribution.** Cells are (broad topic, difficulty 5.0–8.0 in 0.5 steps). The test
  set is allocated to cells in proportion to cell size. Difficulty shares agree across tasks to
  within about one percentage point; about 30% of each task is in the upper band (7.0–8.0).
  Topic shares agree to within about three points; JUDGE has the most Number Theory.
- Full composition tables are in the [FINAL-v3 README](../../data/manifests/final-v3/README.md).
