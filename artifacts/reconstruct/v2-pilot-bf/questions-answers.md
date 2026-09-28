#100-source RECONSTRUCT questions and answers

Private research/answer-key export. Public student inputs are in public-tasks.jsonl.

## Source 2074156 — conversion_failed

**Original question:** In a tetrahedron $ABCD$, the lengths of the edges are $7, 13, 18, 27, 36$, and $41$ units. Given that edge $AB$ measures $41$ units, find the length of edge $CD$.

**Answer:** 13

**Public clues:**

**Qwen output:** Not available; input did not pass both gates.

## Source 2070433 — rejected

**Original question:** Determine the smallest closed set containing $C^1[-1, 1]$ in the space $({\scr{B}}[-1, 1],||\cdot||_\infty)$. Provide your answer as a set description.

**Answer:** C[-1, 1]

**Public clues:**
1. The functions in the source problem are defined on the compact interval [-1,1].
2. The initial subset is the class of continuously differentiable functions on that interval, commonly written C^1[-1,1].
3. The ambient space is the bounded functions on [-1,1] equipped with the supremum norm.
4. The requested object is the smallest closed set in this ambient normed space that contains the initial subset.

**Qwen output:** Not available; input did not pass both gates.

## Source 2070420 — rejected

**Original question:** Determine whether every smooth variety over \(\mathbb{R}\) or \(\mathbb{C}\) can be considered as a real or complex manifold.

**Answer:** Yes

**Public clues:**
1. The source concerns whether an algebraic-geometric smoothness condition on a variety transfers to a differential-geometric manifold structure.
2. The relevant base fields are the real numbers and the complex numbers, so the possible manifold structures are real smooth and complex holomorphic.
3. For a smooth variety, local defining equations have a Jacobian of maximal rank at each point.
4. The implicit function theorem then supplies local coordinate charts, holomorphic in the complex case and smooth in the real case.

**Qwen output:** Not available; input did not pass both gates.

## Source 2034283 — accepted

**Original question:** Let $F$ be a field of order $32$. Determine the number of non-zero solutions $(a,b) \in F \times F$ to the equation $x^2 + xy + y^2 = 0$. Provide your answer as a single integer.

**Answer:** 0

**Public clues:**
1. The setting is a finite field of characteristic 2, and the equation is a homogeneous quadratic in two variables.
2. The equation is x^2 + xy + y^2 = 0, and the origin (0,0) is always a solution.
3. The requested quantity counts only solutions with at least one coordinate non-zero, so the origin is excluded.
4. For any non-zero solution, both coordinates must be non-zero, and the ratio t = x/y satisfies t^2 + t + 1 = 0.

**Qwen reconstructed question:** Let F be a finite field of characteristic 2. Consider the equation x^2 + xy + y^2 = 0 over F. How many non-trivial solutions (x, y) are there to this equation, where a non-trivial solution is defined as a solution where at least one of x or y is non-zero?

**Qwen verification:** The question is based on the observations provided. The equation x^2 + xy + y^2 = 0 is a homogeneous quadratic equation in two variables over a finite field of characteristic 2. The origin (0,0) is always a solution, but the question specifies to count only solutions where at least one coordinate is non-zero. The observations indicate that for any non-zero solution, both coordinates must be non-zero and the ratio t = x/y satisfies t^2 + t + 1 = 0. The final answer is 0, which suggests that there are no non-trivial solutions to the equation under the given conditions. The question is constructed to reflect these observations and the final answer, and the assumptions are based on the provided information and logical deductions from the observations.

**Score:** 50.0 /100

## Source 2070486 — rejected

**Original question:** Evaluate the integral \( \int_{C}\frac{\tan z}{z^2}dz \) over the unit circle \( |z| = 1 \).

**Answer:** 2\pi i

**Public clues:**
1. The integral is a contour integral over a positively oriented simple closed curve that encloses the origin once.
2. The integrand is \(\tan z / z^2\).
3. Inside the contour, the only singularity of the integrand is at \(z=0\).
4. The requested value is determined by the residue of the integrand at \(z=0\).

**Qwen output:** Not available; input did not pass both gates.

## Source 2037444 — unresolved

**Original question:** Evaluate the improper integral \(\int_0^\infty \frac{\sin x(1-\cos x)}{x^2}dx\) and determine whether it converges.

**Answer:** \ln 2

**Public clues:**
1. The problem asks about an improper integral whose interval is the positive half-line from 0 to infinity.
2. The integrand has a possible singularity at 0, but the numerator vanishes to third order there, so the quotient is bounded near 0.
3. At infinity the integrand is absolutely bounded by a constant multiple of x^{-2}, so the improper integral converges.
4. The requested value is a natural logarithm of a positive integer.

**Qwen output:** Not available; input did not pass both gates.

## Source 2034207 — accepted

**Original question:** Let $A_1 A_2 \dotsb A_{11}$ be a regular 11-gon inscribed in a circle of radius 2. Let $P$ be a point such that the distance from $P$ to the center of the circle is 3. Find the value of $PA_1^2 + PA_2^2 + \dots + PA_{11}^2.$

**Answer:** 143

**Public clues:**
1. A regular polygon is inscribed in a circle.
2. The circle has radius 2.
3. A point P is 3 units from the circle's center.
4. The requested value is the sum of the squared distances from P to every vertex of the polygon.

**Qwen reconstructed question:** A regular polygon is inscribed in a circle with radius 2. A point P is located 3 units from the center of the circle. What is the sum of the squared distances from P to every vertex of the polygon?

**Qwen verification:** The question is constructed based on the given observations. The polygon is inscribed in a circle of radius 2, and point P is 3 units from the center. The requested value is the sum of the squared distances from P to every vertex of the polygon. The answer 143 is consistent with the given observations and the mathematical relationships involved in the problem.

**Score:** 50.0 /100

## Source 2037426 — unresolved

**Original question:** Determine the range of values for the parameter $a$ such that the inequality \( x^{-3} e^{x} - a \ln x \geq x + 1 \) holds for all \( x \in (1, +\infty) \).

**Answer:** (-\infty, -3]

**Public clues:**
1. The variable x is required to lie in the open interval (1, +∞).
2. For every x in that interval, an inequality involving a real parameter a must be satisfied.
3. The inequality contains the term a ln x, and since ln x > 0 on (1, +∞), this term can be moved without reversing the inequality.
4. After isolating a, the condition becomes a bound on a by a quotient involving x^{-3}e^x, x, 1, and ln x.

**Qwen output:** Not available; input did not pass both gates.

## Source 2074162 — accepted

**Original question:** For the Cauchy problem $u_x - 6u_y = y$, determine the number of possible solutions given the initial condition $u(x,y) = e^x$ on the line $y = -x + 1$, which is not a characteristic line.

**Answer:** 1

**Public clues:**
1. The problem concerns a first-order linear partial differential equation of the form u_x - 6u_y = y.
2. An initial condition is imposed on a straight line in the xy-plane.
3. The initial line is stated not to be a characteristic line of the partial differential equation.
4. The requested result is the number of possible solutions to this Cauchy problem.

**Qwen reconstructed question:** Consider the first-order linear partial differential equation $ u_x - 6u_y = y $. An initial condition is imposed on a straight line in the xy-plane that is not a characteristic line of the PDE. Determine the number of possible solutions to this Cauchy problem.

**Qwen verification:** The given final answer is 1, which implies that there is a unique solution to the Cauchy problem. The observations indicate that the PDE is first-order linear, an initial condition is imposed on a straight line in the xy-plane, and the initial line is not a characteristic line. These conditions are consistent with the Cauchy problem being well-posed and having a unique solution. Therefore, the question is about determining the number of possible solutions to the Cauchy problem, and the answer is 1.

**Score:** 56.25 /100

## Source 2034240 — accepted

**Original question:** Suppose \( f:D(0,1) \longrightarrow \mathbb{C} \) is a holomorphic function, where \( D(0,1) = \{z \in \mathbb{C} \mid |z|<1\} \), and assume the maximum \(|f(z)| \le 2\). Estimate \(|f^{(3)}(i/3)|\) using Cauchy's estimate.

**Answer:** \dfrac{81}{2}

**Public clues:**
1. The function f is holomorphic on the open unit disk D(0,1).
2. There is a positive constant M such that |f(z)| ≤ M throughout D(0,1).
3. The requested quantity is an upper bound for |f^{(3)}(z0)| at an interior point z0 of the unit disk.
4. Cauchy's estimate applies on a disk centered at z0 and contained in D(0,1), using M and the radius of that disk.

**Qwen reconstructed question:** Let f be a holomorphic function on the open unit disk D(0,1) with |f(z)| ≤ M for all z in D(0,1). Let z0 be an interior point of D(0,1) and let r be the radius of a disk centered at z0 that is entirely contained within D(0,1). Use Cauchy's estimate to find an upper bound for |f^{(3)}(z0)| in terms of M and r.

**Qwen verification:** The question is constructed based on the given observations. The function f is holomorphic on the open unit disk and is bounded by a constant M. The requested quantity is an upper bound for the third derivative of f at an interior point z0. Cauchy's estimate is used on a disk centered at z0 with radius r, which is contained within the unit disk. The question asks for an upper bound for |f^{(3)}(z0)| in terms of M and r. The final answer of 81/2 is consistent with the application of Cauchy's estimate, which gives |f^{(3)}(z0)| ≤ 3M / r^3. If r is chosen as 1/3, then 3M / (1/3)^3 = 81M, but since the final answer is 81/2, it is likely that M = 1/2. Therefore, the question is consistent with the given answer.

**Score:** 50.0 /100

## Source 2070496 — rejected

**Original question:** If the closure of a subset $A$ of a vector space is convex, does it necessarily follow that $A$ itself is convex, even if $A$ is not bounded? Provide a justification for your answer.

**Answer:** No

**Public clues:**
1. A is a subset of a vector space, and its closure is taken in a compatible topology.
2. The hypothesis under consideration is that the closure of A is convex.
3. The question asks whether convexity of the closure forces convexity of A itself.
4. The boundedness of A is explicitly not assumed, so A may be unbounded.

**Qwen output:** Not available; input did not pass both gates.

## Source 2034265 — rejected

**Original question:** Is there always a partition $P$ such that the upper sum $U(f, P)$ equals the infimum of all upper sums $U(f)$ for a bounded function $f$ on a compact set $A$? Consider the definition of the Riemann Integral where $U(f) = \inf\{U(f,P) \mid P \in \mathcal{P}\}$. Determine if such a partition $P$ always exists.

**Answer:** No

**Public clues:**
1. The setting involves a bounded real-valued function f on a compact set A and finite partitions of A.
2. For a partition P, the upper sum U(f,P) uses the supremum of f on each piece of P.
3. The upper integral U(f) is defined as the infimum of all upper sums U(f,P) over all partitions P.
4. The central issue is whether the infimum defining U(f) is attained by some partition P.

**Qwen output:** Not available; input did not pass both gates.

## Source 2037469 — conversion_failed

**Original question:** Determine all entire functions \( f: \mathbb{C} \to \mathbb{C} \) that satisfy the following conditions for all complex numbers \( z \):
1. \( f(z+i) = f(z) \)
2. \( f(z+1) = e^{2\pi i} f(z) \)

**Answer:** f(z) = c

**Public clues:**

**Qwen output:** Not available; input did not pass both gates.

## Source 2034219 — accepted

**Original question:** Consider a function \( f: \mathbb{R} \to \mathbb{R} \) that is measurable with respect to the sigma-algebra \( \Sigma \), generated by the sets \([0, 1]\), \([2, 4]\), and \([3, \infty)\) in \( \mathbb{R} \). Does this function necessarily have to be measurable with respect to the Borel sigma-algebra \( \mathcal{B}(\mathbb{R}) \) of \( \mathbb{R} \)?

**Answer:** Yes

**Public clues:**
1. The object under consideration is a real-valued function whose domain and codomain are both the real line.
2. On the domain, measurability is taken with respect to a sigma-algebra generated by a finite family of intervals.
3. On the codomain, the usual Borel sigma-algebra is the reference sigma-algebra for defining measurability.
4. The question asks whether measurability with respect to that generated domain sigma-algebra necessarily implies measurability with respect to the Borel sigma-algebra on the domain.

**Qwen reconstructed question:** Let $ f: \mathbb{R} \to \mathbb{R} $ be a real-valued function whose domain is equipped with a sigma-algebra generated by a finite family of intervals and whose codomain is equipped with the usual Borel sigma-algebra. Is it necessarily true that measurability of $ f $ with respect to the domain sigma-algebra implies measurability of $ f $ with respect to the Borel sigma-algebra on the domain?

**Qwen verification:** The question is based on the observations provided. The function is real-valued with domain and codomain as the real line. The domain's sigma-algebra is generated by a finite family of intervals, and the codomain's sigma-algebra is the usual Borel sigma-algebra. The question asks whether measurability with respect to the domain sigma-algebra implies measurability with respect to the Borel sigma-algebra on the domain. The answer 'Yes' suggests that the implication holds, so the question is constructed to verify this relationship.

**Score:** 62.5 /100

## Source 2037489 — accepted

**Original question:** Find the integer $x$ such that $x^5 \equiv 3 \pmod{221}$ using the Chinese Remainder Theorem and Euler's Theorem.

**Answer:** 165

**Public clues:**
1. The problem asks for an integer x satisfying a single congruence of the form x^5 ≡ a (mod n).
2. The modulus n is 221, which is composite and factors into two distinct primes, so the Chinese Remainder Theorem can split the congruence.
3. The exponent 5 is coprime to the totients of both prime factors, so Euler's Theorem allows one to invert 5 modulo each totient.
4. The requested x is the least nonnegative residue modulo 221 that satisfies the original congruence.

**Qwen reconstructed question:** Find the least nonnegative residue modulo 221 that satisfies the congruence x^5 ≡ 10 (mod 221).

**Qwen verification:** The question is constructed based on the given observations. The modulus is 221, which factors into 13 and 17. The exponent 5 is coprime to the totients of both prime factors (φ(13) = 12 and φ(17) = 16). The congruence x^5 ≡ 10 (mod 221) is a specific instance of the form mentioned in the observations. The answer 165 is the least nonnegative residue modulo 221 that satisfies this congruence.

**Score:** 43.75 /100

## Source 2034234 — accepted

**Original question:** Evaluate the integral \( \int_0^1 \frac{x^{m-1} + x^{n-1}}{(1+x)^{m+n}} \, dx \) in terms of the Beta function.

**Answer:** B(m, n)

**Public clues:**
1. The integral is definite and runs from 0 to 1.
2. The integrand is a sum of two terms, each containing a power of x in the numerator.
3. The denominator is a power of 1+x, and its exponent equals the sum of the two parameters used in the numerator.
4. The requested answer is a single value of the Beta function.

**Qwen reconstructed question:** Evaluate the definite integral from 0 to 1 of [x^m(1 - x)^n + x^n(1 - x)^m] / (1 + x)^{m + n} dx and express the result in terms of the Beta function B(m, n).

**Qwen verification:** The integral is definite from 0 to 1, and the integrand is a sum of two terms with powers of x in the numerator. The denominator is a power of (1 + x) with an exponent equal to the sum of the two parameters in the numerator. The requested answer is a single value of the Beta function B(m, n), which is consistent with the given observations and the structure of the integral.

**Score:** 50.0 /100

## Source 2037439 — rejected

**Original question:** Calculate the limit \(\lim\limits_{n\to\infty} \frac{\log(n!)}{n\log(n)}\) when \(n\) is a positive integer.

**Answer:** 1

**Public clues:**
1. The variable n is a positive integer and is allowed to grow without bound.
2. The expression being studied is a quotient whose numerator is the natural logarithm of n factorial.
3. The denominator of that quotient is n multiplied by the natural logarithm of n.
4. The requested result is the limit of this quotient as n tends to infinity.

**Qwen output:** Not available; input did not pass both gates.

## Source 2070426 — unresolved

**Original question:** For a parabola with focus at $(1, 2)$ and a tangent line $x + y - 1 = 0$, this tangent intersects the directrix at point $B$ and the tangent at the vertex at point $C$. If point $A$ is the point of tangency, find the ratio $AC:BC$.

**Answer:** 1

**Public clues:**
1. A parabola is the locus of points equidistant from a fixed focus and a fixed directrix.
2. The focus is at (1,2), and one tangent line to the parabola has equation x + y = k for some constant k.
3. That tangent line meets the directrix at B and meets the tangent at the vertex at C, while A is its point of tangency with the parabola.
4. The quantity to be found is the ratio AC:BC.

**Qwen output:** Not available; input did not pass both gates.

## Source 2034259 — accepted

**Original question:** Evaluate the limit: $$\lim_{x \to 0^{+}} \sqrt{|\sin x - \tan x | } \int_{\cos x}^{1+ \sin x} e^y \, \, \mathrm{d}y$$

**Answer:** 0

**Public clues:**
1. The expression under consideration is a product of two factors that both depend on a real variable x.
2. One factor is the square root of the absolute value of sin x minus tan x.
3. The other factor is a definite integral of e^y with respect to y.
4. The integral has lower limit cos x and upper limit 1 + sin x.

**Qwen reconstructed question:** Evaluate the expression: sqrt(|sin x - tan x|) * ∫ from cos x to 1 + sin x of e^y dy, for which the value of the expression is zero.

**Qwen verification:** The expression is a product of two factors: the square root of the absolute value of sin x minus tan x and a definite integral of e^y with respect to y from cos x to 1 + sin x. The final answer is 0, which suggests that the expression evaluates to zero for certain values of x. The question is to determine for which values of x this expression is zero. The assumptions include that the expression is zero for specific x values, and that the integral and square root factors are defined and real for those x values. The problem is to find the x values for which the expression equals zero.

**Score:** 0.0 /100

## Source 2074144 — rejected

**Original question:** Provide an example of a function $f: \mathbb{R} \rightarrow \mathbb{R}$ such that $|f'(x)| \geq A$ for some constant $A > 1$, and $f$ has a fixed point.

**Answer:** f(x) = 2x

**Public clues:**
1. The function is defined on all real numbers and takes real values.
2. The function is differentiable everywhere on its domain.
3. Its derivative magnitude is bounded below by a single constant that is strictly greater than 1.
4. The function is required to have at least one real fixed point.

**Qwen output:** Not available; input did not pass both gates.

