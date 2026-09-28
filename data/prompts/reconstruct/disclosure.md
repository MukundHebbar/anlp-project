# Disclosure variants v0.1 — pilot only

## Instruction

You receive a checked mathematical source and a four-observation clue bank. Preserve the four observation identities. For each observation create low, medium, and high disclosure versions. Medium must be copied exactly from the bank.

- Low: a true qualitative weakening of medium. Remove some quantities or identifiers while retaining a meaningful constraint.
- High: a more specific form of the same observation, justified by the source. Do not add a second independent clue, disclose the source premise/target bundle, or give a complete defining equation or solution.
- High must imply medium; medium must imply low. Do not turn the clue into a different observation.
- Each level needs a normal `sentence` and an information-equivalent `fragment`. No unexplained source-specific symbols.
- If no honest weaker/stronger version exists, repeat the nearest level and set `tied: true` with a reason. Do not force a difference. A later audit decides eligibility.

Return JSON with `observations`, each containing `id`, `low`, `medium`, `high`, `tied`, and `support`. Each level is an object with `sentence` and `fragment`. Return no candidate question.

## Demonstration 1

Source fact: v_2(12!) = floor(12/2)+floor(12/4)+floor(12/8) = 6+3+1.

Medium observation: The contributions to one prime exponent are 6, 3, and 1.

```json
{
  "id":"c1",
  "low":{"sentence":"A prime exponent is obtained by adding several positive contributions.","fragment":"Prime exponent: sum of several positive contributions."},
  "medium":{"sentence":"The contributions to one prime exponent are 6, 3, and 1.","fragment":"One prime exponent: 6 + 3 + 1."},
  "high":{"sentence":"The contributions to the exponent of 2 are 6, 3, and 1.","fragment":"Exponent of 2: 6 + 3 + 1."},
  "tied":false,
  "support":"The high clue names the prime already counted in the source; medium omits its identity; low removes the numerical contributions."
}
```

## Demonstration 2

Source fact: endpoint cases of the six-position path have F(5)=13 and F(4)=8 possibilities.

```json
{
  "id":"c4",
  "low":{"sentence":"Both endpoint cases have at least one valid possibility.","fragment":"Both endpoint-case counts are positive."},
  "medium":{"sentence":"The two endpoint cases contribute 13 and 8 possibilities.","fragment":"Endpoint-case counts: 13 and 8."},
  "high":{"sentence":"Omitting the endpoint contributes 13 possibilities; selecting it contributes 8.","fragment":"Endpoint omitted: 13; endpoint selected: 8."},
  "tied":false,
  "support":"The high clue assigns each count to its branch; medium leaves the assignment unspecified; low retains positivity only."
}
```

## Actual input

```text
SOURCE QUESTION: {{source_question}}
ANSWER: {{final_answer}}
CHECKED SOLUTION: {{checked_solution}}
CLUE BANK: {{clue_bank_json}}
```
