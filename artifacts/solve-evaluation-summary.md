# Current SOLVE evaluation evidence

Both retained SOLVE evaluations are scored against DeepMath dataset gold final
answers using deterministic verifier v2. They must not be compared as though
they have the same denominator.

| Model | Evaluated set | Correct | Strict accuracy | Detailed report |
| --- | --- | ---: | ---: | --- |
| DeepSeek V4 Flash | Full 146-problem manifest | 113 / 146 | 77.40% | [report](deepseek-v4-flash/solve/146/report.txt) |
| Qwen3-4B | 113-problem subset selected from DeepSeek-v2-correct SOLVE records | 62 / 113 | 54.87% | [reevaluated v2 report](qwen3-4b/solve/113/reevaluated-v2-report.txt) |

The Qwen subset was generated with Qwen receiving only the original problem;
DeepSeek answers were never used as Qwen references. Its raw outputs, response
metadata, and verifier-v2 details are retained in
`qwen3-4b/solve/113/results.json`. The DeepSeek full-manifest records are
retained in `deepseek-v4-flash/solve/146/results.json`.

The Qwen3-4B results were re-scored from the retained responses with the
current verifier v2; the fresh output is
`qwen3-4b/solve/113/reevaluated-v2-results.json`.
