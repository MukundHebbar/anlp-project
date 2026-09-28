# RECONSTRUCT student v0.1

## Fixed instruction

You are given a final mathematical answer and a few unordered observations from a worked solution. Reconstruct one plausible, self-contained mathematical question that fits this evidence.

Your question must have the supplied answer. Give a concise mathematical justification showing that every displayed observation fits one coherent solution of your question. State any important missing details you chose. Several questions may fit; you are not required to recover the exact original wording or claim uniqueness.

Do not merely repeat the answer, state it as the requested fact in your premises, or attach the clues to an unrelated question. If the evidence is broad, choose reasonable details and verify them rather than asserting that your guess must be the original.

Return JSON with exactly these three fields:

```json
{"question":"...","justification":"...","assumptions":["..."]}
```

Use an empty assumptions list when no additional choice needs highlighting. Give a concise verification, not a transcript of exploratory deliberation.

## Demonstration 1

Input:

```text
Final answer: 5
Observations:
- The contributions to one prime exponent are 6, 3, and 1.
- The contributions to another prime exponent are 4 and 1.
- One of the two prime exponents is halved and rounded down before taking the minimum.
```

Output:

```json
{
  "question":"How many trailing zero digits does 13! have in base 12?",
  "justification":"Since 12=2^2*3, the number of trailing zeros is min(floor(v_2(13!)/2),v_3(13!)). Legendre's formula gives v_2=6+3+1=10 and v_3=4+1=5, matching the two contribution clues. Halving the first count and taking the minimum gives min(5,5)=5.",
  "assumptions":["I chose 13! as the integer and base 12 as the numeral base; the evidence does not uniquely determine the original integer."]
}
```

## Demonstration 2

Input:

```text
Final answer: 21
Observations:
- The two endpoint cases contribute 13 and 8 possibilities.
- Selecting that endpoint makes its immediate neighbour unavailable.
- The empty selection is counted as one valid possibility.
```

Output:

```json
{
  "question":"How many subsets of six positions in a row contain no adjacent positions? Include the empty subset.",
  "justification":"Let F(n) count such subsets. Omitting the last position leaves F(n-1) choices; selecting it excludes its neighbour and leaves F(n-2). With F(0)=1 and F(1)=2, the sequence through n=6 is 1,2,3,5,8,13,21. Thus the two endpoint cases give 13 and 8, and their sum is 21. The empty subset is included.",
  "assumptions":["I chose a row of six positions and a counting question about nonadjacent subsets."]
}
```

## Demonstration 3

Input:

```text
Final answer: 1/e
Observations:
- A stationary point occurs at the positive input e.
- The sign of the derivative is the sign of 1 minus the natural logarithm of the input.
- The function tends to zero as the input tends to positive infinity.
```

Output:

```json
{
  "question":"What is the maximum value of f(x)=ln(x)/x on x>0?",
  "justification":"The derivative is (1-ln(x))/x^2, so it is positive for 0<x<e, zero at e, and negative for x>e. Therefore the global maximum is f(e)=1/e. Also ln(x)/x tends to zero as x tends to positive infinity, matching the remaining clue.",
  "assumptions":["I chose f(x)=ln(x)/x and domain x>0; the observations do not explicitly supply the full function."]
}
```

## Actual input

```text
Final answer: {{final_answer}}
Observations:
{{rendered_clues}}
```

For answer-only controls, render `Observations: None supplied.` For full-solution controls, explicitly label the evidence `Worked solution supplied as evidence:`. These are experimental controls, not production RECONSTRUCT conditions. Keep the same task instruction and demonstrations.
