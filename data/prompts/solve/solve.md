You are given a mathematics problem, its verified final answer, and a reference reasoning trace produced by another model.

Your task is to write a clean, mathematically correct solution to the problem.

<problem>
{question}
</problem>

<verified_final_answer>
{final_answer}
</verified_final_answer>

<reference_reasoning>
{reasoning_trace}
</reference_reasoning>

Use the reference reasoning only as a source of useful mathematical ideas. It may contain exploratory thoughts, repetition, abandoned approaches, self-corrections, or locally incorrect steps. Do not reproduce these artifacts.

Produce a direct solution that:

* explains the important mathematical steps needed to justify the answer;
* preserves a valid method from the reference reasoning when appropriate;
* corrects or omits any invalid reasoning;
* removes conversational or exploratory language such as "okay", "wait", "let me try", or repeated reconsideration;
* avoids unnecessary repetition and irrelevant alternative approaches;
* includes enough intermediate work that the result can be checked;
* ends with the verified final answer.

Do not mention the reference reasoning or say that you are rewriting another solution.

Return only the cleaned solution.