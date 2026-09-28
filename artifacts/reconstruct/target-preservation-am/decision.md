# AM: target-preservation instruction test

The instruction addition did not produce semantic recovery. All six Qwen draws were readable; all six source-recovery judgments and all six analytic reviews classified them as non-equivalent to the original question. Grounded semantic recovery remains0/6 eligible and0/16 allocated. The prior AL draw for source16 correctly inferred2000 but asked the inverse question; AM still asks that inverse question and now incorrectly infers80. No favorable parameter-inference result is counted as recovery.

| Outcome | AL p13 | AM p16 |
|---|---:|---:|
| Same public inputs |6|6|
| Readable student outputs |5/6|6/6|
| Semantic recovery |0/6|0/6|
| Grounded semantic recovery |0/6|0/6|
| Primary scores returned |5/6|2/6|
| Mean on returned scores |10/100|0/100|
| Bounds on mean over all planned slots |8.33–25|0–66.67|

Four AM primary judgments failed with connection errors. Preserve them as missing, without retrying or treating them as scored zeros. All six separate source-recovery calls returned: five related-but-non-equivalent1/2, one unrelated0/2. Missing primary scores prevent a valid conclusion that the mean rubric score improved or worsened. The semantic endpoint and analytic failures remain observed independently.

The sole intervention is a fixed paragraph added to p13: preserve a stated target, insert inferred missing values into premises, and do not reverse the rectangle demonstration into an area question. The existing example, output field order, six public evidence objects, original nonthinking Qwen model, decoding settings and seed are unchanged. This is one adaptive development draw per source under each prompt, not a population effect or final confirmation. Source113's readable completion in AM versus its earlier cap failure does not establish a general reliability gain.

Failure details: threshold75 instead of51; answer27 inserted as a premise instead of recovering n51; inverse question with wrongN80 instead of a count atN2000; unspecified modulus plus wrongR99; unspecified scalarc incorrectly declared irrelevant; unspecified root multiplieralpha and invalid factorial cancellation. Exact responses, source-bound analytic certificates and judge outputs are in [student.json](student.json), [response-math-review.json](response-math-review.json) and [comparison.json](comparison.json). The registered intervention is [AM](../../../docs/plans/reconstruct-amendment-am.md); exact prompt delta is [prompt-change.json](prompt-change.json).

Independent source-blind mathematics checks are terminal: five invalid and one valid (source10, whose question presupposes the answer27). Mathematical consistency does not override the separate circularity and semantic-recovery failures. Do not promote this prompt. Stop further instruction-only changes on these six examples. The separately registered [AN conversion experiment](../../../docs/plans/reconstruct-amendment-an.md) changes what is withheld: retain essential premises, omit the requested quantity. It uses all sixteen allocated sources and may abstain or fail leakage review. It is not a claim of improvement before results or a reason to relax semantic equivalence.
