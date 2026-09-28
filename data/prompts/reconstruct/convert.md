# RECONSTRUCT converter v0.1

Send the instruction and demonstrations below as the fixed converter prompt. Append one source record. The model receives a checked worked solution, not a request to reveal its own private deliberation. The generated bank is private until the renderer selects the public fields.

## Instruction

You construct mathematical RECONSTRUCT tasks. A student will receive the final answer and a few unordered observations from a worked solution, then propose a question and justify it.

Read the source question, final answer, and checked solution. Produce four distinct, useful solution observations. For each, give:

- `id`: c1 through c4, used only for sampling;
- `sentence`: one short normal sentence, self-contained enough to interpret without the source;
- `fragment`: mathematically equivalent shorthand, with no additional or removed fact;
- `hidden_support`: a brief explanation of why the observation follows from the checked solution. This is never shown to the student.

Use medium disclosure: retain useful relationships and selected intermediate numbers, while leaving meaningful missing structure. An observation can identify a local operation, structural restriction, case split, or intermediate result. Do not name the original task directly, reproduce its premise/target bundle, merely re-encode its full defining equation, or give the full solution. Do not put several independent observations into one clue. Avoid filler such as “mathematics is used.” No chronological labels or source-specific unexplained symbols.

The observations must all be true and jointly compatible. Check the whole bank for direct question restatement. Exact quantities are allowed when they are intermediate evidence, not a disguised copy of the question. Some redundancy is natural; do not pad the bank with restatements.

Return `NOT_SUITABLE` if the source is inconsistent, its answer exposes the question, a grounded observation bank cannot be made without reproducing the task, or four useful distinct observations would require padding. Keep the reason brief. Do not invent a substitute source problem.

Return JSON only:

```json
{"status":"OK","clues":[{"id":"c1","sentence":"...","fragment":"...","hidden_support":"..."}],"withheld":"Briefly identify structure the student still has to infer."}
```

or:

```json
{"status":"NOT_SUITABLE","reason":"..."}
```

## Demonstration 1: number theory

Input:

```text
QUESTION: How many trailing zero digits does 12! have when written in base 12?
ANSWER: 5
CHECKED SOLUTION: Since 12 = 2^2 * 3, count complete factors of 12 in 12!. The exponent of 2 is 6+3+1=10. The exponent of 3 is 4+1=5. The number of factors is min(floor(10/2),5)=5.
```

Output:

```json
{
  "status":"OK",
  "clues":[
    {"id":"c1","sentence":"The contributions to one prime exponent are 6, 3, and 1.","fragment":"One prime exponent: 6 + 3 + 1.","hidden_support":"Legendre's formula gives v_2(12!) = 6+3+1."},
    {"id":"c2","sentence":"The contributions to another prime exponent are 4 and 1.","fragment":"Another prime exponent: 4 + 1.","hidden_support":"Legendre's formula gives v_3(12!) = 4+1."},
    {"id":"c3","sentence":"One of the two prime exponents is halved and rounded down before taking the minimum.","fragment":"Two prime counts; floor(half of one) enters their minimum.","hidden_support":"Each factor of 12 consumes two factors of 2 and one factor of 3."},
    {"id":"c4","sentence":"The target counts how many times the same integer factor can be removed successively.","fragment":"Target: number of successive removals of one fixed integer factor.","hidden_support":"Trailing base-12 zeros equal the largest t such that 12^t divides 12!."}
  ],
  "withheld":"The integer being factored and the repeated factor/base are not named; the student must construct a compatible problem. Several sources can fit."
}
```

## Demonstration 2: counting

Input:

```text
QUESTION: How many subsets of {1,2,3,4,5,6} contain no two consecutive integers?
ANSWER: 21
CHECKED SOLUTION: Let F(n) count valid subsets of a path of n positions. Splitting on whether the final position is selected gives F(n)=F(n-1)+F(n-2), since selecting it forbids the previous position. F(0)=1 includes the empty subset, and F(1)=2. Thus F(2)=3, F(3)=5, F(4)=8, F(5)=13 and F(6)=21.
```

Output:

```json
{
  "status":"OK",
  "clues":[
    {"id":"c1","sentence":"The cases are separated according to whether an endpoint is selected.","fragment":"Case split: endpoint selected / endpoint not selected.","hidden_support":"Split valid subsets by membership of the last position."},
    {"id":"c2","sentence":"Selecting that endpoint makes its immediate neighbour unavailable.","fragment":"Selected endpoint implies unavailable immediate neighbour.","hidden_support":"Two adjacent positions cannot both be selected."},
    {"id":"c3","sentence":"The empty selection is counted as one valid possibility.","fragment":"Empty selection: one valid possibility.","hidden_support":"The empty subset is valid, including the F(0)=1 base case."},
    {"id":"c4","sentence":"The two endpoint cases contribute 13 and 8 possibilities.","fragment":"Endpoint-case counts: 13 and 8.","hidden_support":"The omitted-endpoint case is F(5)=13; the selected-endpoint case is F(4)=8."}
  ],
  "withheld":"The source set and its size, and the exact wording of the counting target, remain unstated."
}
```

## Demonstration 3: calculus

Input:

```text
QUESTION: Find the maximum of log(x)/x for x>0, where log is the natural logarithm.
ANSWER: 1/e
CHECKED SOLUTION: For f(x)=log(x)/x, f'(x)=(1-log(x))/x^2. The derivative is positive below e and negative above e, so x=e is the global maximizer on x>0. Its value is 1/e. Also f(x) tends to 0 as x tends to positive infinity.
```

Output:

```json
{
  "status":"OK",
  "clues":[
    {"id":"c1","sentence":"A stationary point occurs at the positive input e.","fragment":"Stationary input: x=e>0.","hidden_support":"1-log(x)=0 at x=e."},
    {"id":"c2","sentence":"The sign of the derivative is the sign of 1 minus the natural logarithm of the input.","fragment":"sign(f'(x)) = sign(1-ln(x)).","hidden_support":"The derivative denominator x^2 is positive on the domain."},
    {"id":"c3","sentence":"The derivative's denominator in the worked expression is the square of the input.","fragment":"Worked derivative denominator: x^2.","hidden_support":"The quotient-rule derivative is (1-log(x))/x^2."},
    {"id":"c4","sentence":"The function tends to zero as the input tends to positive infinity.","fragment":"lim as x→+infinity of f(x) = 0.","hidden_support":"log(x)/x tends to zero."}
  ],
  "withheld":"The function itself and original domain specification are absent; the student must give a compatible optimization question."
}
```

## Demonstration 4: reject padding

Input:

```text
QUESTION: Solve x+2=5.
ANSWER: 3
CHECKED SOLUTION: Subtract 2 from both sides to obtain x=3.
```

Output:

```json
{"status":"NOT_SUITABLE","reason":"This one-step solution does not supply four useful distinct observations without padding or restating the original equation."}
```

## Actual input

```text
QUESTION: {{source_question}}
ANSWER: {{final_answer}}
CHECKED SOLUTION: {{checked_solution}}
```
