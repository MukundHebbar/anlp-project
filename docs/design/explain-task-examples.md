# EXPLAIN Task Demonstrations

This document shows how a verified mathematical solution can be converted into an EXPLAIN task.

For each example, the complete solution is retained privately for dataset construction and verification. The student-facing task contains the original problem, the necessary local context, and a supplied application or result from the solution. The student must identify and explain the mathematical principle that makes the supplied reasoning valid. The student is not asked to discover the construction or complete the original solution.

## Example 1: Differentiability at a Missing Point

### Original question

Suppose \(f\) is continuous on \(\mathbb{R}\) and differentiable on

\[
(-\infty,a)\cup(a,\infty).
\]

The left- and right-hand limits of its derivative at \(a\) both equal a real number \(L\):

\[
\lim_{x\to a^-}f'(x)=\lim_{x\to a^+}f'(x)=L.
\]

Must \(f\) be differentiable at \(a\)? Justify the answer.

### Complete solution

Yes. In fact, \(f'(a)=L\).

Define

\[
Q(x)=\frac{f(x)-f(a)}{x-a},\qquad x\ne a.
\]

We show that \(Q(x)\to L\) as \(x\to a\).

First take \(x>a\). The function \(f\) is continuous on \([a,x]\) and differentiable on \((a,x)\). By the Mean Value Theorem, there is a point \(c_x\in(a,x)\) such that

\[
\frac{f(x)-f(a)}{x-a}=f'(c_x).
\]

Because \(a<c_x<x\),

\[
0<c_x-a<x-a.
\]

Therefore \(c_x\to a^+\) as \(x\to a^+\). Using the assumed right-hand limit of \(f'\),

\[
\lim_{x\to a^+}\frac{f(x)-f(a)}{x-a}
=\lim_{x\to a^+}f'(c_x)
=L.
\]

Now take \(x<a\). The function is continuous on \([x,a]\) and differentiable on \((x,a)\). The Mean Value Theorem gives a point \(d_x\in(x,a)\) such that

\[
\frac{f(a)-f(x)}{a-x}=f'(d_x).
\]

Equivalently,

\[
\frac{f(x)-f(a)}{x-a}=f'(d_x).
\]

Since \(x<d_x<a\), we have \(d_x\to a^-\) as \(x\to a^-\). Hence

\[
\lim_{x\to a^-}\frac{f(x)-f(a)}{x-a}
=\lim_{x\to a^-}f'(d_x)
=L.
\]

Both one-sided limits of the difference quotient equal \(L\). Therefore

\[
\lim_{x\to a}\frac{f(x)-f(a)}{x-a}=L,
\]

so \(f\) is differentiable at \(a\) and

\[
\boxed{f'(a)=L}.
\]

### Student-facing EXPLAIN task

#### Previous solution context

Consider the right-hand case \(x>a\). The original assumptions state that \(f\) is continuous on \(\mathbb{R}\), differentiable on \((a,\infty)\), and

\[
\lim_{t\to a^+}f'(t)=L.
\]

#### Supplied application and result

For every \(x>a\), there is a point \(c_x\in(a,x)\) satisfying

\[
\frac{f(x)-f(a)}{x-a}=f'(c_x).
\]

Since \(a<c_x<x\), it follows that \(c_x\to a^+\) as \(x\to a^+\). Consequently,

\[
\lim_{x\to a^+}\frac{f(x)-f(a)}{x-a}=L.
\]

#### EXPLAIN question

Explain why the point \(c_x\) is guaranteed to exist and why the supplied argument correctly shows that the right-hand difference quotient converges to \(L\). State the relevant mathematical result and verify its conditions. Do not analyze the left-hand case or complete the original solution.

### Required answer

For each \(x>a\), \(f\) is continuous on \([a,x]\) and differentiable on \((a,x)\). The Mean Value Theorem therefore guarantees a point \(c_x\in(a,x)\) such that

\[
\frac{f(x)-f(a)}{x-a}=f'(c_x).
\]

The inequalities \(a<c_x<x\) imply \(0<c_x-a<x-a\), so \(c_x\to a^+\) whenever \(x\to a^+\). The assumed limit \(f'(t)\to L\) as \(t\to a^+\) therefore gives \(f'(c_x)\to L\). Since the difference quotient equals \(f'(c_x)\), it also converges to \(L\).

The answer must:

1. Identify the Mean Value Theorem and verify its continuity and differentiability conditions.
2. Explain why \(a<c_x<x\) forces \(c_x\to a^+\).
3. Use the one-sided limit of \(f'\) to justify the limit of the difference quotient.

## Example 2: Primitive Seventh Roots and Symmetric Root Relations

### Original question

The pilot statement uses \(r\) both in the definition of \(x\) and as the summation index. The generated solution interprets the intended problem as follows:

Let \(x\) be a primitive seventh root of unity. Evaluate

\[
S=\sum_{r=1}^{6}\frac{x^r}{1+x^{2r}}.
\]

### Complete solution

Since \(x\) is a primitive seventh root of unity,

\[
x^7=1,\qquad x\ne1.
\]

For every \(r\),

\[
\frac{x^r}{1+x^{2r}}=\frac{1}{x^r+x^{-r}}.
\]

Define \(u_r=x^r+x^{-r}\). Because \(u_{7-r}=u_r\), the terms pair as \(r\) and \(7-r\), giving

\[
S=2\left(\frac1{u_1}+\frac1{u_2}+\frac1{u_3}\right).
\]

The seventh-root relation is

\[
1+x+x^2+x^3+x^4+x^5+x^6=0.
\]

Dividing by \(x^3\) gives

\[
(x^3+x^{-3})+(x^2+x^{-2})+(x+x^{-1})+1=0.
\]

Let \(u=x+x^{-1}\). Then

\[
x^2+x^{-2}=u^2-2,\qquad
x^3+x^{-3}=u^3-3u.
\]

Substitution gives

\[
u^3+u^2-2u-1=0.
\]

Applying the same argument to \(x^r\) for \(r=1,2,3\) shows that \(u_1,u_2,u_3\) are the three roots of

\[
p(t)=t^3+t^2-2t-1.
\]

Vieta's formulas give

\[
u_1+u_2+u_3=-1,
\]

\[
u_1u_2+u_1u_3+u_2u_3=-2,
\]

and

\[
u_1u_2u_3=1.
\]

Therefore,

\[
\frac1{u_1}+\frac1{u_2}+\frac1{u_3}
=\frac{u_1u_2+u_1u_3+u_2u_3}{u_1u_2u_3}
=-2.
\]

Thus

\[
S=2(-2)=-4,
\]

so

\[
\boxed{-4}.
\]

### Student-facing EXPLAIN task

#### Previous solution context

Define

\[
u_j=x^j+x^{-j},\qquad j=1,2,3.
\]

Earlier steps establish that \(u_1,u_2,u_3\) are exactly the three roots of

\[
p(t)=t^3+t^2-2t-1
\]

and that

\[
S=2\left(\frac1{u_1}+\frac1{u_2}+\frac1{u_3}\right).
\]

#### Supplied application and result

The solution obtains

\[
u_1u_2+u_1u_3+u_2u_3=-2,
\qquad
u_1u_2u_3=1,
\]

and therefore

\[
\frac1{u_1}+\frac1{u_2}+\frac1{u_3}=-2.
\]

#### EXPLAIN question

Explain how the displayed relations follow from the fact that \(u_1,u_2,u_3\) are the roots of \(p(t)\). State the relevant mathematical result and show how it applies here. Do not rederive the cubic or continue evaluating \(S\).

### Required answer

Because \(u_1,u_2,u_3\) are exactly the roots of the monic cubic, Vieta's formulas follow from

\[
p(t)=(t-u_1)(t-u_2)(t-u_3).
\]

Expanding gives

\[
t^3-(u_1+u_2+u_3)t^2
+(u_1u_2+u_1u_3+u_2u_3)t
-u_1u_2u_3.
\]

Comparing this with \(t^3+t^2-2t-1\) shows that the pairwise product sum is \(-2\) and the total product is \(1\). Since the product is nonzero, the reciprocals are defined. Hence

\[
\frac1{u_1}+\frac1{u_2}+\frac1{u_3}
=\frac{u_1u_2+u_1u_3+u_2u_3}{u_1u_2u_3}
=-2.
\]

The answer must:

1. Identify Vieta's formulas or state the equivalent coefficient-root relationship.
2. Compare the coefficients with the correct signs to obtain the pairwise sum and product.
3. Explain how these symmetric products give the reciprocal sum.

## Example 3: Counting Tuples as Closed Graph Walks

### Original question

Determine the number of 6-tuples

\[
(a_1,a_2,a_3,a_4,a_5,a_6)
\]

such that every \(a_i\in\{1,2,3,4\}\) and the expressions

\[
a_j^2-a_ja_{j+1}+a_{j+1}^2
\]

for \(j=1,2,3,4,5,6\), with \(a_7=a_1\), are all equal.

### Complete solution

Define

\[
F(x,y)=x^2-xy+y^2.
\]

For a fixed possible common value \(q\), form a graph \(G_q\) on the vertices \(\{1,2,3,4\}\). Place an edge between \(x\) and \(y\) exactly when \(F(x,y)=q\), allowing loops. A valid 6-tuple with common value \(q\) is exactly a closed walk of length \(6\) in \(G_q\). If \(A_q\) is the adjacency matrix of \(G_q\), the number of these tuples is

\[
\operatorname{tr}(A_q^6).
\]

The values of \(F(x,y)\) are

\[
\begin{array}{c|cccc}
F(x,y)&1&2&3&4\\
\hline
1&1&3&7&13\\
2&3&4&7&12\\
3&7&7&9&13\\
4&13&12&13&16
\end{array}
\]

The possible values of \(q\) and associated graphs are:

| \(q\) | Edges | Graph type | \(\operatorname{tr}(A_q^6)\) |
|---:|---|---|---:|
| \(1\) | loop at \(1\) | one loop | \(1\) |
| \(3\) | \(1\text{-}2\) | single edge | \(2\) |
| \(4\) | loop at \(2\) | one loop | \(1\) |
| \(7\) | \(1\text{-}3,2\text{-}3\) | \(K_{1,2}\) | \(16\) |
| \(9\) | loop at \(3\) | one loop | \(1\) |
| \(12\) | \(2\text{-}4\) | single edge | \(2\) |
| \(13\) | \(1\text{-}4,3\text{-}4\) | \(K_{1,2}\) | \(16\) |
| \(16\) | loop at \(4\) | one loop | \(1\) |

A graph consisting of one loop contributes \(1\). A single edge has adjacency eigenvalues \(1,-1\), so it contributes

\[
1^6+(-1)^6=2.
\]

The graph \(K_{1,2}\) has adjacency eigenvalues \(\sqrt2,-\sqrt2,0\), so it contributes

\[
(\sqrt2)^6+(-\sqrt2)^6=16.
\]

Summing the contributions gives

\[
1+2+1+16+1+2+16+1=40.
\]

Therefore,

\[
\boxed{40}.
\]

### Student-facing EXPLAIN task

#### Previous solution context

Define

\[
F(x,y)=x^2-xy+y^2.
\]

Fix a possible common value \(q\). Construct a graph \(G_q\) with vertex set \(\{1,2,3,4\}\), placing an edge between \(x\) and \(y\) exactly when

\[
F(x,y)=q.
\]

Loops are allowed. Let \(A_q\) be the adjacency matrix of \(G_q\).

#### Supplied application and result

A valid 6-tuple having common value \(q\) corresponds exactly to a closed walk of length \(6\) in \(G_q\). Therefore, the number of such tuples is

\[
\operatorname{tr}(A_q^6).
\]

#### EXPLAIN question

Explain why the graph construction gives an exact correspondence between the valid 6-tuples and closed walks of length \(6\), and why their number is \(\operatorname{tr}(A_q^6)\). Do not enumerate the possible values of \(q\) or complete the original count.

### Required answer

For a valid tuple, the equality \(F(a_j,a_{j+1})=q\) means that every consecutive pair \(a_j,a_{j+1}\) is an edge of \(G_q\). Thus

\[
a_1,a_2,\ldots,a_6,a_1
\]

is a walk of length \(6\). The condition \(a_7=a_1\) makes the walk closed. Conversely, every closed length-\(6\) walk gives a valid ordered tuple.

For an adjacency matrix, the entry \((A_q^6)_{uv}\) counts length-\(6\) walks from \(u\) to \(v\). Therefore, \((A_q^6)_{vv}\) counts the walks that begin and end at \(v\). Summing these diagonal entries over all vertices gives

\[
\operatorname{tr}(A_q^6).
\]

The starting vertex is distinguished in this count, matching the fact that the 6-tuples are ordered rather than identified up to cyclic rotation.

The answer must:

1. Explain both directions of the correspondence between valid tuples and closed walks.
2. State why powers of an adjacency matrix count walks of a fixed length.
3. Explain why the trace counts all closed walks and why the distinguished starting position matches an ordered tuple.
