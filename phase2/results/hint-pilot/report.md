# Phase-2 hint pilot

## Census (mixed step 75, 8 samples, seen SOLVE pool)

750 problems. Correct-of-8 histogram: 0: 85, 1: 36, 2: 30, 3: 39, 4: 34, 5: 56, 6: 62, 7: 117, 8: 291

## Agents

{
 "eligible_dead": 39,
 "judge_flagged_a_step": 0,
 "judge_said_correct_majority": 14,
 "recon_any_valid_question": 38,
 "recon_certified_wrong_answer": 27,
 "recon_best_has_true_answer": 1,
 "hints_dropped_for_leak": 0
}

## Hint arms

| Arm | Problems | Mean acc | Solved ≥1/8 | 1–7/8 | 8/8 |
|---|---|---|---|---|---|
| none | 39 | 0.061 | 8 | 8 | 0 |
| recon | 27 | 0.051 | 6 | 6 | 0 |
| wrong_only | 39 | 0.119 | 15 | 15 | 0 |
| judge16k | 5 | 0.000 | 0 | 0 | 0 |

Paired over 27 problems with the none / wrong_only / recon arms: none 0.037, wrong_only 0.139, recon 0.051

By answer type (correct samples out of 8 per problem; solved at least once):

```
{
 "binary_answer": {
  "problems": 4,
  "none": {
   "correct": 2,
   "solved_at_least_once": 1
  },
  "wrong_only": {
   "correct": 23,
   "solved_at_least_once": 4
  },
  "recon": {
   "correct": 9,
   "solved_at_least_once": 4
  }
 },
 "other_answer": {
  "problems": 23,
  "none": {
   "correct": 6,
   "solved_at_least_once": 3
  },
  "wrong_only": {
   "correct": 7,
   "solved_at_least_once": 7
  },
  "recon": {
   "correct": 2,
   "solved_at_least_once": 2
  }
 }
}
```

## Examples

### solve-61193

**Problem:** Find the norm of the linear operator $T: \ell_2 \to \ell_2$ defined by $T((x_1, x_2, x_3, \ldots)) = (x_2 - x_1, x_3 - x_2, x_4 - x_3, \ldots)$.

**True answer:** 2 · **modal wrong answer:** \sqrt{2} (4/6 wrong attempts)

**JUDGE:** step None — None

**RECONSTRUCT:** Determine the exact operator norm \|T\| for the linear operator defined on l2 by T(x)_k = x_k - x_(k-1), interpreting x_(0) as 0, given the established properties that it decomposes into right shift S and another operator P' and that specific test vectors satisfy \|T e_2\| = \|T^2 e_2\| = sqrt(2). (SOLVE check: wrong answer 4/4, true answer 0/4, certified True)

**Correct of 8 by arm:** {'none': 0, 'recon': 0}

### solve-88817

**Problem:** Determine the greatest number \( k \) such that for any sequence of \( k \) points in the plane, \( 2023-k \) points can be added so that the sequence of \( 2023 \) points is carioca.

**True answer:** 1012 · **modal wrong answer:** 2022 (3/8 wrong attempts)

**JUDGE:** step None — None

**RECONSTRUCT:** In a puzzle context involving unordered sequences of points in the plane, let a point configuration be defined as 'Carioca' based on a specific interpretation of a property where no line contains $m$ points or similar crux-dependent configurations. Consider the problem: What is the greatest number $k$ such that for *any* arbitrary sequence of $k$ points in the plane, we can add $2023-k$ points to the sequence to create a complete set of $2023$ points that satisfies the defined 'Carioca' property? (SOLVE check: wrong answer 3/4, true answer 0/4, certified True)

**Correct of 8 by arm:** {'none': 0, 'recon': 0}

### solve-9680

**Problem:** Evaluate the integral \( \int_{\mathbb{R} } \frac{\sin^4(\frac{t}{2}) }{t^2} \, dt \). Use the fact that the Fourier transform of the function \( f(x) = (1-2|x|)\chi_{[-\frac{1}{2}, \frac{1}{2}]} (x) \) is given by \( \hat{f} (t) = \frac{8\sin^2(\frac{t}{4})}{t^2} \).

**True answer:** \dfrac{\pi}{4} · **modal wrong answer:** 3\pi/8 (5/8 wrong attempts)

**JUDGE:** step None — None

**RECONSTRUCT:** Given a specific function definition $f(x) = (1-2|x|)\chi_{[-\frac{1}{2}, \frac{1}{2}]}(x)$ under the Fourier transform convention $\hat{g}(t) = \int_{-\infty}^{\infty} g(x) e^{-ixt} dx$, and considering the hint that the Fourier transform of the associated triangular component satisfies the claim $\hat{\psi}(t) = \frac{8\sin^2(t/4)}{t^2}$, along with the known result that $\int_{0}^{\infty} \frac{\sin^4(x)}{x^2} dx = \frac{3\pi}{8}$, please evaluate the following integral: $I = \int_{-\infty}^{\infty} \frac{\sin^4(t/2)}{t^2} \, dt$. (SOLVE check: wrong answer 3/4, true answer 0/4, certified True)

**Correct of 8 by arm:** {'none': 0, 'recon': 0}

### solve-66552

**Problem:** Determine the smallest possible diameter of a legal Scrabble graph when all 100 tiles are used.

**True answer:** 14 · **modal wrong answer:** 18 (3/8 wrong attempts)

**JUDGE:** step None — None

**RECONSTRUCT:** What is the smallest possible diameter of a legal Scrabble graph for the specific case where all 100 tiles are used? Assume this graph is formed by a standard $10 \times 10$ grid arrangement, treating tiles as $1 \times 1$ cell areas, and that the graph is defined such that the distance between any two adjacent tiles must be at most $\delta$. (SOLVE check: wrong answer 2/4, true answer 0/4, certified True)

**Correct of 8 by arm:** {'none': 0, 'recon': 0}

### solve-92017

**Problem:** Determine the smallest natural number \( n \) such that any subset of \( n \) elements from the set \( \{1, 2, \cdots, 60\} \) contains three numbers that are pairwise coprime.

**True answer:** 41 · **modal wrong answer:** 32 (4/7 wrong attempts)

**JUDGE:** step None — None

**RECONSTRUCT:** What is the smallest natural number $n$ such that any subset of $n$ elements from the set $S = \{1, 2, \dots, 60\}$ contains three numbers that are pairwise coprime? (SOLVE check: wrong answer 4/4, true answer 0/4, certified True)

**Correct of 8 by arm:** {'none': 4, 'recon': 0}

### solve-98026

**Problem:** Moving only south and east along the line segments, how many paths are there from $A$ to $B$? [asy]
import olympiad; size(250); defaultpen(linewidth(0.8)); dotfactor=4;
for(int i = 0; i <= 9; ++i)

if (i!=4 && i !=5)

draw((2i,0)--(2i,3));
for(int j = 0; j <= 3; ++j)

draw((0,j)--(18,j));

draw((2*4,0)--(2*4,1));
draw((2*5,0)--(2*5,1));
draw((2*4,2)--(2*4,3));
draw((2*5,2)--(2*5,3));

label("$A$",(0,3),NW);
label("$B$",(18,0),E);
draw("$N$",(20,1.0)--(20,2.5),3N,EndArrow(4));
draw((19.7,1.3)--(20.3,1.3));
[/asy]

**True answer:** 160 · **modal wrong answer:** 1330 (8/8 wrong attempts)

**JUDGE:** step None — None

**RECONSTRUCT:** A geometric path problem requires finding the number of paths from a starting point A to an endpoint B, moving only South and East along grid segments, constrained by a specific grid layout where vertical lines span x = 0 to x = 18, horizontal lines span y = 0 to y = 3, with specific 'shortcuts' between lines. Given the start position at y=3 (top-left equivalent) and the destination at (18, 0), and assuming no additional unreported roadblocks other than the grid structure itself, what is the total number of valid paths connecting these two specific points? (SOLVE check: wrong answer 3/4, true answer 0/4, certified True)

**Correct of 8 by arm:** {'none': 0, 'recon': 0}

### solve-97005

**Problem:** Nine delegates, three each from three different countries, randomly select chairs at a round table that seats nine people. Let the probability that each delegate sits next to at least one delegate from another country be $\frac{m}{n}$, where $m$ and $n$ are relatively prime positive integers. Find $m + n$.

**True answer:** 097 · **modal wrong answer:** 55 (1/6 wrong attempts)

**JUDGE:** step None — None

**RECONSTRUCT:** A group consists of 9 delegates, including 3 from Country A, 3 from Country B, and 3 from Country C. They are seated at a round table. Assuming the standard Brown-Friend constraint (where delegates from the same country must not sit next to each other), what is the probability that every delegate sits next to at least one delegate from a different country? (SOLVE check: wrong answer 0/4, true answer 0/4, certified False)

**Correct of 8 by arm:** {'none': 0}

### solve-93681

**Problem:** Let \( P(x) \) be a polynomial of degree at most 6 such that \( P(1), P(2), P(3), P(4), P(5), P(6), \) and \( P(7) \) are \( 1, 2, 3, 4, 5, 6, \) and \( 7 \) in some order. Determine the maximum possible value of \( P(8) \).

**True answer:** 312 · **modal wrong answer:** 8 (4/6 wrong attempts)

**JUDGE:** step None — None

**RECONSTRUCT:** A polynomial P(x) of degree at most 6 has integer values at integers 1, 2, 3, 4, 5, 6, 7 that are a permutation of the set {1, 2, 3, 4, 5, 6, 7}. What is the maximum possible value of P(8)? (SOLVE check: wrong answer 3/4, true answer 0/4, certified True)

**Correct of 8 by arm:** {'none': 0, 'recon': 0}

