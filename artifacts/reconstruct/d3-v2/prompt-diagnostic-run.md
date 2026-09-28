# RECONSTRUCT pilot report

Generated: 2026-09-20T08:27:47.083945+00:00

## Summary

```json
{
  "sources": 4,
  "banks": 4,
  "audits": 12,
  "disclosures": 0,
  "disclosure_audits": 0,
  "responses": 23,
  "evaluations": 16,
  "grounded_successes": 1,
  "grounded_success_rate": 0.0625,
  "bank_grounded_successes": 1,
  "bank_grounded_success_rate": 0.0625,
  "mean_score": 1.1875,
  "unresolved": 0,
  "failures": 3,
  "deepinfra_estimated_cost_usd": 0.04818373279999999,
  "judge_fixture_accuracy": null,
  "judge_fixture_count": 0,
  "judge_fixtures_by_config": {},
  "source_recovery": {
    "count": 16,
    "score_0": 11,
    "score_1": 5,
    "score_2": 0,
    "exact_rate": 0.0
  },
  "by_condition": {
    "bank:student_p1:2:sentence:medium:bank_order:convert_p3": {
      "responses": 4,
      "evaluations": 4,
      "successes": 0,
      "success_rate": 0.0,
      "mean_score": 1.5,
      "source_recovery_count": 4,
      "exact_source_recovery_rate": 0.0,
      "mean_source_recovery": 0.0
    },
    "bank:student_p1:3:sentence:medium:bank_order:convert_p3": {
      "responses": 4,
      "evaluations": 4,
      "successes": 0,
      "success_rate": 0.0,
      "mean_score": 1.0,
      "source_recovery_count": 4,
      "exact_source_recovery_rate": 0.0,
      "mean_source_recovery": 0.75
    },
    "bank:student_p10_recover_original:2:sentence:medium:bank_order:convert_p3": {
      "responses": 4,
      "evaluations": 4,
      "successes": 1,
      "success_rate": 0.25,
      "mean_score": 1.5,
      "source_recovery_count": 4,
      "exact_source_recovery_rate": 0.0,
      "mean_source_recovery": 0.0
    },
    "bank:student_p10_recover_original:3:sentence:medium:bank_order:convert_p3": {
      "responses": 4,
      "evaluations": 4,
      "successes": 0,
      "success_rate": 0.0,
      "mean_score": 0.75,
      "source_recovery_count": 4,
      "exact_source_recovery_rate": 0.0,
      "mean_source_recovery": 0.5
    },
    "bank:student_p11_inverse_example:2:sentence:medium:bank_order:convert_p3": {
      "responses": 4,
      "evaluations": 0,
      "successes": 0,
      "success_rate": null,
      "mean_score": null,
      "source_recovery_count": 0,
      "exact_source_recovery_rate": null,
      "mean_source_recovery": null
    },
    "bank:student_p11_inverse_example:3:sentence:medium:bank_order:convert_p3": {
      "responses": 3,
      "evaluations": 0,
      "successes": 0,
      "success_rate": null,
      "mean_score": null,
      "source_recovery_count": 0,
      "exact_source_recovery_rate": null,
      "mean_source_recovery": null
    }
  },
  "usage": {
    "prompt_tokens": 48756,
    "completion_tokens": 95105,
    "total_tokens": 143861
  }
}
```

## Cases

### Source 8: Algebra

**Source question (private):** Let \( a, b, \) and \( c \) be real numbers such that \( a + b + c = 0 \). Find the value of the expression:
\[
P = \frac{a^2}{2a^2+bc} + \frac{b^2}{2b^2+ca} + \frac{c^2}{2c^2+ab}.
\]

**Answer:** 1

**Condition:** bank; prompt=student_p1; seed=0

**Public clues:**

- The three quantities 2a^2+bc, 2b^2+ca, and 2c^2+ab factor respectively as (a-b)(a-c), (b-c)(b-a), and (c-a)(c-b).
- The product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions.

**Reconstruction:** Evaluate the expression (2a^2+bc)/(a-b)(a-c) + (2b^2+ca)/(b-c)(b-a) + (2c^2+ab)/(c-a)(c-b) where a, b, c are distinct.

**Justification:** The given expression can be simplified by noting that each numerator factors as (a-b)(a-c), (b-c)(b-a), and (c-a)(c-b) respectively. When these are divided by their respective denominators, each term simplifies to 1. Therefore, the sum of the three terms is 1.

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": false, "grounding": "violated", "reason": "The claimed factorization is false: for example, with a=1,b=2,c=3, 2a^2+bc=8 but (a-b)(a-c)=2."}, {"index": 2, "compatible": true, "grounding": "implicit", "reason": "D=(a-b)(a-c)(b-c) is indeed a common denominator up to sign for the three displayed fractions."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed question is well-posed, but the supplied answer 1 is incorrect. The student's simplification relies on a false factorization, and evaluating the expression, e.g. at a=1,b=2,c=3, gives 3 rather than 1."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "same", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "Both use variables a,b,c, but the source imposes a+b+c=0 and asks for P=sum a^2/(2a^2+bc), while the candidate imposes distinctness and asks for a different expression Q=sum (2a^2+bc)/((a-b)(a-c)). Under the source condition, the candidate terms simplify to 1, giving Q=3, whereas P=1.", "reason": "Different premises, expression, and target; not the same essential problem."}

### Source 8: Algebra

**Source question (private):** Let \( a, b, \) and \( c \) be real numbers such that \( a + b + c = 0 \). Find the value of the expression:
\[
P = \frac{a^2}{2a^2+bc} + \frac{b^2}{2b^2+ca} + \frac{c^2}{2c^2+ab}.
\]

**Answer:** 1

**Condition:** bank; prompt=student_p10_recover_original; seed=0

**Public clues:**

- The three quantities 2a^2+bc, 2b^2+ca, and 2c^2+ab factor respectively as (a-b)(a-c), (b-c)(b-a), and (c-a)(c-b).
- The product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions.

**Reconstruction:** Evaluate the expression (2a^2 + bc)/(a - b) + (2b^2 + ca)/(b - c) + (2c^2 + ab)/(c - a) where a, b, c are distinct numbers.

**Justification:** The given expression can be simplified by noting that 2a^2 + bc factors as (a - b)(a - c), 2b^2 + ca factors as (b - c)(b - a), and 2c^2 + ab factors as (c - a)(c - b). Using these factorizations, each fraction simplifies to (a - b)(a - c)/(a - b) + (b - c)(b - a)/(b - c) + (c - a)(c - b)/(c - a), which simplifies to (a - c) + (b - a) + (c - b). This simplifies further to 0. However, the product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions, leading to the final answer of 1.

**Evaluation:** {"status": "scored", "well_posed": false, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": false, "grounding": "violated", "reason": "The factorizations are not identities for the proposed expression; e.g. a=1,b=2,c=3 gives 2a^2+bc=8 but (a-b)(a-c)=2. They require a+b+c=0, which is absent."}, {"index": 2, "compatible": true, "grounding": "unsupported", "reason": "D can serve as a common denominator up to sign for denominators a-b,b-c,c-a, but the response gives no valid calculation from this to the claimed value 1."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed expression is not constant without an additional condition, the displayed factorizations are false for it, and the student's own simplification gives 0 before contradictorily asserting 1. Thus the supplied answer 1 is not correct."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "same", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "Source uses a+b+c=0 and evaluates sum a^2/(2a^2+bc); candidate instead assumes a,b,c distinct and evaluates sum (2a^2+bc)/(a-b), with different denominators and no sum-zero premise.", "reason": "The expressions and defining premises are essentially different, not merely reparameterized."}

### Source 8: Algebra

**Source question (private):** Let \( a, b, \) and \( c \) be real numbers such that \( a + b + c = 0 \). Find the value of the expression:
\[
P = \frac{a^2}{2a^2+bc} + \frac{b^2}{2b^2+ca} + \frac{c^2}{2c^2+ab}.
\]

**Answer:** 1

**Condition:** bank; prompt=student_p10_recover_original; seed=1

**Public clues:**

- The three quantities 2a^2+bc, 2b^2+ca, and 2c^2+ab factor respectively as (a-b)(a-c), (b-c)(b-a), and (c-a)(c-b).
- The product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions.

**Reconstruction:** Evaluate the expression (2a^2 + bc)/(a - b) + (2b^2 + ca)/(b - c) + (2c^2 + ab)/(c - a) where a, b, c are distinct numbers.

**Justification:** The given expression can be simplified by recognizing that each numerator factors as (a - b)(a - c), (b - c)(b - a), and (c - a)(c - b) respectively. Using these factorizations and the common denominator (a - b)(a - c)(b - c), the expression simplifies to 1. The observations confirm the factorization and the use of the common denominator in the simplification.

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": false, "grounding": "violated", "reason": "The claimed factorization is false: 2a^2+bc is not generally equal to (a-b)(a-c), and similarly for the other numerators."}, {"index": 2, "compatible": true, "grounding": "explicit", "reason": "The student explicitly uses D=(a-b)(a-c)(b-c) as a common denominator; this is compatible with the proposed denominators up to sign."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed question is well-posed, but the supplied answer 1 is incorrect. The justification relies on a false factorization, and a simple test such as a=1,b=2,c=3 gives the expression value -9, not 1."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "same", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "Source uses a+b+c=0 and evaluates sum a^2/(2a^2+bc); candidate uses distinct a,b,c and evaluates sum (2a^2+bc)/(a-b), a different expression with different denominators and no sum-zero premise.", "reason": "The algebraic expression, constraints, and target are not equivalent."}

### Source 8: Algebra

**Source question (private):** Let \( a, b, \) and \( c \) be real numbers such that \( a + b + c = 0 \). Find the value of the expression:
\[
P = \frac{a^2}{2a^2+bc} + \frac{b^2}{2b^2+ca} + \frac{c^2}{2c^2+ab}.
\]

**Answer:** 1

**Condition:** bank; prompt=student_p1; seed=1

**Public clues:**

- The three quantities 2a^2+bc, 2b^2+ca, and 2c^2+ab factor respectively as (a-b)(a-c), (b-c)(b-a), and (c-a)(c-b).
- The product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions.

**Reconstruction:** Evaluate the expression (2a^2 + bc)/(a - b) + (2b^2 + ca)/(b - c) + (2c^2 + ab)/(c - a) where a, b, c are distinct.

**Justification:** The given expression can be simplified by factoring the numerators. Each numerator factors as (a - b)(a - c), (b - c)(b - a), and (c - a)(c - b) respectively. When simplified, the expression becomes (a - b) + (b - c) + (c - a) = 0. However, the problem states that the product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions, which implies the expression is evaluated in a context where D is non-zero. The final result is 1 when considering the specific form and simplification of the expression.

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": false, "grounding": "violated", "reason": "The claimed factorization is false: e.g. for a=1,b=2,c=3, 2a^2+bc=8 but (a-b)(a-c)=2. Thus the displayed observation contradicts the proposed expression."}, {"index": 2, "compatible": true, "grounding": "implicit", "reason": "The product (a-b)(a-c)(b-c) is compatible with the denominators up to sign, since c-a=-(a-c), but it does not support the false numerator factorization or the final answer."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed question is well-posed, but the supplied answer 1 is incorrect. A direct test with a=1,b=2,c=3 gives -8-11+10=-9, not 1. The key observation about the numerators factoring is also false, so the reconstruction is not valid."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "same", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "Source uses a+b+c=0 and asks for sum a^2/(2a^2+bc). Candidate instead assumes a,b,c distinct and asks for sum (2a^2+bc)/(a-b), with no sum-zero premise.", "reason": "The defining premise and expression are both changed; this is not the same essential problem."}

### Source 8: Algebra

**Source question (private):** Let \( a, b, \) and \( c \) be real numbers such that \( a + b + c = 0 \). Find the value of the expression:
\[
P = \frac{a^2}{2a^2+bc} + \frac{b^2}{2b^2+ca} + \frac{c^2}{2c^2+ab}.
\]

**Answer:** 1

**Condition:** bank; prompt=student_p11_inverse_example; seed=0

**Public clues:**

- The three quantities 2a^2+bc, 2b^2+ca, and 2c^2+ab factor respectively as (a-b)(a-c), (b-c)(b-a), and (c-a)(c-b).
- The product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions.

**Reconstruction:** Let a, b, c be distinct real numbers. Consider the expressions 2a^2+bc, 2b^2+ca, and 2c^2+ab. Show that (2a^2+bc)(2b^2+ca)(2c^2+ab) = (a-b)(a-c)(b-c)^2.

**Justification:** The given answer 1 suggests that the product of the three expressions equals 1. The observations show that each of the three quantities 2a^2+bc, 2b^2+ca, and 2c^2+ab factor as (a-b)(a-c), (b-c)(b-a), and (c-a)(c-b) respectively. The product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions. By combining these observations, the problem is to show that the product of the three expressions equals (a-b)(a-c)(b-c)^2, which is consistent with the given answer 1 when normalized by the common denominator.

**Evaluation:** not evaluated

**Source recovery:** not evaluated

### Source 8: Algebra

**Source question (private):** Let \( a, b, \) and \( c \) be real numbers such that \( a + b + c = 0 \). Find the value of the expression:
\[
P = \frac{a^2}{2a^2+bc} + \frac{b^2}{2b^2+ca} + \frac{c^2}{2c^2+ab}.
\]

**Answer:** 1

**Condition:** bank; prompt=student_p11_inverse_example; seed=1

**Public clues:**

- The three quantities 2a^2+bc, 2b^2+ca, and 2c^2+ab factor respectively as (a-b)(a-c), (b-c)(b-a), and (c-a)(c-b).
- The product D=(a-b)(a-c)(b-c) is used as a common denominator for the three fractions.

**Reconstruction:** Let a, b, c be distinct real numbers. Consider the expressions $2a^2 + bc$, $2b^2 + ca$, and $2c^2 + ab$. It is given that $2a^2 + bc = (a - b)(a - c)$, $2b^2 + ca = (b - c)(b - a)$, and $2c^2 + ab = (c - a)(c - b)$. Let $D = (a - b)(a - c)(b - c)$. What is the value of the expression $\frac{2a^2 + bc}{D} + \frac{2b^2 + ca}{D} + \frac{2c^2 + ab}{D}$?

**Justification:** The given answer 1 and the provided factorizations suggest that the expression simplifies to 1. The observations show that each numerator factors into a product involving (a - b), (a - c), etc., and that D is the product of these differences. Therefore, each fraction simplifies to 1/(a - b), 1/(b - c), and 1/(c - a), respectively. Adding these fractions together results in 1. The observations are consistent with this solution.

**Evaluation:** not evaluated

**Source recovery:** not evaluated

### Source 27: Algebra

**Source question (private):** What is the least number of square roots needed to express \(\sqrt{1}+\sqrt{2}+\cdots+\sqrt{100}\) in the form \(a+b\sqrt{c}+d\sqrt{e}+\cdots\) where \(a,b,c,d,e,\ldots\) are all integers?

**Answer:** 60

**Condition:** bank; prompt=student_p1; seed=0

**Public clues:**

- If n=s^2m with m squarefree, then sqrt n equals s times sqrt m.
- In the sum from n=1 to 100, terms whose radicands have the same squarefree part m combine by adding the multipliers s with s^2m≤100.
- The squarefree part m=1 contributes only an integer constant to the combined expression.

**Reconstruction:** What is the sum of the square roots of all integers from 1 to 100, grouped by their squarefree parts?

**Justification:** The sum can be computed by grouping terms with the same squarefree part. For each squarefree part m, terms are of the form s√(s²m) where s is an integer such that s²m ≤ 100. Each group contributes s√m. The squarefree part m=1 contributes only an integer constant to the combined expression. The total sum is 60.

**Evaluation:** {"status": "scored", "well_posed": false, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The observation sqrt(s^2 m)=s sqrt(m) is correctly used to describe grouping, though the student's wording s√(s²m) is inconsistent."}, {"index": 2, "compatible": true, "grounding": "explicit", "reason": "The response explicitly groups terms by squarefree part and combines multipliers for each m."}, {"index": 3, "compatible": true, "grounding": "explicit", "reason": "The response explicitly notes that m=1 contributes only an integer constant."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed question asks for the sum of square roots from 1 to 100 grouped by squarefree parts, but the supplied answer 60 is not that sum and is not justified. The observations could support counting squarefree parts greater than 1, but that is not the stated question, and the justification contains a mathematical inconsistency."}

**Source recovery:** {"status": "scored", "source_recovery": 1, "checks": {"objects": "same", "premises": "same", "domains_parameters": "same", "target": "different"}, "correspondence": "Both concern the sum sqrt(1)+...+sqrt(100) and its grouping by squarefree parts, but the source asks for the least number of square-root terms needed in such a representation, while the candidate asks for the grouped sum itself.", "reason": "Related setup with the same sum and squarefree-part structure, but the target changes from counting minimal radical terms to computing the grouped expression."}

### Source 27: Algebra

**Source question (private):** What is the least number of square roots needed to express \(\sqrt{1}+\sqrt{2}+\cdots+\sqrt{100}\) in the form \(a+b\sqrt{c}+d\sqrt{e}+\cdots\) where \(a,b,c,d,e,\ldots\) are all integers?

**Answer:** 60

**Condition:** bank; prompt=student_p10_recover_original; seed=0

**Public clues:**

- If n=s^2m with m squarefree, then sqrt n equals s times sqrt m.
- In the sum from n=1 to 100, terms whose radicands have the same squarefree part m combine by adding the multipliers s with s^2m≤100.
- The squarefree part m=1 contributes only an integer constant to the combined expression.

**Reconstruction:** What is the sum of the square roots of all integers from 1 to 100, grouped by their squarefree part?

**Justification:** Let the sum be S. Each term sqrt(n) can be written as s*sqrt(m) where n = s^2*m and m is squarefree. Terms with the same m combine as s*sqrt(m). The squarefree part m=1 contributes only an integer constant to the combined expression. The observations align with this grouping and calculation.

**Evaluation:** {"status": "scored", "well_posed": false, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The identity sqrt(n)=s sqrt(m) for n=s^2m is correctly stated and used in the student's grouping explanation."}, {"index": 2, "compatible": true, "grounding": "explicit", "reason": "The observation about combining terms with the same squarefree part is reflected in the justification."}, {"index": 3, "compatible": true, "grounding": "explicit", "reason": "The justification notes that m=1 contributes an integer constant, matching the observation."}], "justification": "insufficient", "shortcut": false, "score": 1, "reason": "The proposed question asks for a sum of square roots grouped by squarefree part, but the supplied answer 60 is not that sum. The observations support simplifying/grouping radicals, not deriving 60 as a sum. The answer 60 would fit a different question, such as counting distinct squarefree parts greater than 1, so the reconstruction is ill-posed and the answer is not correct for the stated question."}

**Source recovery:** {"status": "scored", "source_recovery": 1, "checks": {"objects": "same", "premises": "same", "domains_parameters": "same", "target": "different"}, "correspondence": "Both concern the same sum sqrt(1)+...+sqrt(100) and its grouping by squarefree part, but the source asks for the least number of distinct square-root terms needed, while the candidate asks for the grouped sum itself.", "reason": "The setup and range match, but the target changes from counting minimal radical terms to computing the grouped expression."}

### Source 27: Algebra

**Source question (private):** What is the least number of square roots needed to express \(\sqrt{1}+\sqrt{2}+\cdots+\sqrt{100}\) in the form \(a+b\sqrt{c}+d\sqrt{e}+\cdots\) where \(a,b,c,d,e,\ldots\) are all integers?

**Answer:** 60

**Condition:** bank; prompt=student_p10_recover_original; seed=1

**Public clues:**

- If n=s^2m with m squarefree, then sqrt n equals s times sqrt m.
- In the sum from n=1 to 100, terms whose radicands have the same squarefree part m combine by adding the multipliers s with s^2m≤100.
- The squarefree part m=1 contributes only an integer constant to the combined expression.

**Reconstruction:** What is the sum of the square roots of all integers from 1 to 100, grouped by their squarefree part?

**Justification:** Let the sum be S. Each squarefree part m contributes s*sqrt(m) where s is the number of multiples of m in 1 to 100. For m=1, s=100, contributing 100*sqrt(1)=100. For other m, s is determined by floor(100/m). The observations show that terms with the same squarefree part m combine by adding s, and sqrt(n) = s*sqrt(m) for n = s^2m. Hence the total sum is the sum over m of s*sqrt(m) where s is the number of multiples of m in 1 to 100.

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The student explicitly uses n=s^2m and sqrt(n)=s sqrt(m), which matches the first observation."}, {"index": 2, "compatible": true, "grounding": "violated", "reason": "The observation requires combining multipliers s with s^2m≤100, but the student instead defines s as the number of multiples of m, i.e. floor(100/m), which is not the same."}, {"index": 3, "compatible": true, "grounding": "violated", "reason": "The student says m=1 contributes 100, but the integer contribution from m=1 is the sum of s for s^2≤100, namely 1+...+10=55, not 100."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed question asks for the sum of square roots from 1 to 100 grouped by squarefree part, but the supplied answer 60 is not that sum and is not derived. The justification uses an incorrect coefficient rule, so the reconstruction has a substantive mathematical error."}

**Source recovery:** {"status": "scored", "source_recovery": 1, "checks": {"objects": "same", "premises": "same", "domains_parameters": "same", "target": "different"}, "correspondence": "Both concern the sum sqrt(1)+...+sqrt(100), and grouping by squarefree part is the relevant simplification. However, the source asks for the least number of distinct square-root terms needed, while the candidate asks for the grouped sum itself, not the count.", "reason": "Same underlying sum and range, but the target changes from counting minimal radical terms to expressing/grouping the sum."}

### Source 27: Algebra

**Source question (private):** What is the least number of square roots needed to express \(\sqrt{1}+\sqrt{2}+\cdots+\sqrt{100}\) in the form \(a+b\sqrt{c}+d\sqrt{e}+\cdots\) where \(a,b,c,d,e,\ldots\) are all integers?

**Answer:** 60

**Condition:** bank; prompt=student_p1; seed=1

**Public clues:**

- If n=s^2m with m squarefree, then sqrt n equals s times sqrt m.
- In the sum from n=1 to 100, terms whose radicands have the same squarefree part m combine by adding the multipliers s with s^2m≤100.
- The squarefree part m=1 contributes only an integer constant to the combined expression.

**Reconstruction:** What is the sum of the square roots of all integers from 1 to 100, grouped by their squarefree parts?

**Justification:** The sum can be computed by grouping terms with the same squarefree part. For each squarefree part m, terms of the form s√(s²m) where s²m ≤ 100 contribute s√m. The squarefree part m=1 contributes an integer constant. The other squarefree parts contribute sums of multiples of √m. The total sum is 60.

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The student justification uses the identity sqrt(s^2 m)=s sqrt(m) when grouping terms."}, {"index": 2, "compatible": true, "grounding": "explicit", "reason": "The student justification states that terms with the same squarefree part m contribute s sqrt(m) for s^2 m <= 100."}, {"index": 3, "compatible": true, "grounding": "explicit", "reason": "The student justification notes that the m=1 part contributes an integer constant."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The grouping observations are relevant and correctly connected to the proposed sum, but the supplied answer 60 is wrong. For m=1 alone the contribution is 1+2+...+10=55, and the m=2 contribution is 28√2, so the total already exceeds 60."}

**Source recovery:** {"status": "scored", "source_recovery": 1, "checks": {"objects": "same", "premises": "same", "domains_parameters": "same", "target": "different"}, "correspondence": "Both concern the same sum sqrt(1)+...+sqrt(100), and grouping by squarefree parts is the relevant simplification structure. However, the source asks for the least number of square-root terms needed in the simplified integer-coefficient radical expression, while the candidate asks for the sum grouped by squarefree parts, not for that minimal count.", "reason": "Same underlying sum and domain, but the target changes from counting minimal radical terms to presenting/grouping the sum by squarefree parts."}

### Source 27: Algebra

**Source question (private):** What is the least number of square roots needed to express \(\sqrt{1}+\sqrt{2}+\cdots+\sqrt{100}\) in the form \(a+b\sqrt{c}+d\sqrt{e}+\cdots\) where \(a,b,c,d,e,\ldots\) are all integers?

**Answer:** 60

**Condition:** bank; prompt=student_p11_inverse_example; seed=0

**Public clues:**

- If n=s^2m with m squarefree, then sqrt n equals s times sqrt m.
- In the sum from n=1 to 100, terms whose radicands have the same squarefree part m combine by adding the multipliers s with s^2m≤100.
- The squarefree part m=1 contributes only an integer constant to the combined expression.

**Reconstruction:** What is the sum of the square roots of all integers from 1 to 100?

**Justification:** The supplied answer 60 and the observations suggest a process of grouping terms with the same squarefree part. The observation about sqrt n equals s times sqrt m indicates that numbers can be expressed in terms of their squarefree part and a multiplier. The second observation explains that terms with the same squarefree part combine by adding the multipliers, and the third observation indicates that the squarefree part m=1 contributes an integer constant. Thus, the question is about summing square roots from 1 to 100 by grouping terms with the same squarefree part. The answer 60 is consistent with this process.

**Evaluation:** not evaluated

**Source recovery:** not evaluated

### Source 27: Algebra

**Source question (private):** What is the least number of square roots needed to express \(\sqrt{1}+\sqrt{2}+\cdots+\sqrt{100}\) in the form \(a+b\sqrt{c}+d\sqrt{e}+\cdots\) where \(a,b,c,d,e,\ldots\) are all integers?

**Answer:** 60

**Condition:** bank; prompt=student_p11_inverse_example; seed=1

**Public clues:**

- If n=s^2m with m squarefree, then sqrt n equals s times sqrt m.
- In the sum from n=1 to 100, terms whose radicands have the same squarefree part m combine by adding the multipliers s with s^2m≤100.
- The squarefree part m=1 contributes only an integer constant to the combined expression.

**Reconstruction:** What is the sum of the simplified radical expressions for all integers from 1 to 100?

**Justification:** The supplied answer 60 and the observations suggest a process of grouping terms with the same squarefree part. The observation about sqrt n equals s times sqrt m indicates a simplification of radicals. The second observation explains grouping terms with the same squarefree part and the third observation explains that the squarefree part m=1 contributes an integer constant. The final answer 60 is likely the result of summing these simplified terms. The question is inferred to be about summing simplified radical expressions from 1 to 100.

**Evaluation:** not evaluated

**Source recovery:** not evaluated

### Source 33: Calculus

**Source question (private):** For every pair of continuous functions $f,g:[0,1] \rightarrow \mathbb{R}$ such that \(\max\{f(x):x \in [0,1]\} = \max\{g(x):x \in [0,1]\}\), is there always a point $c \in [0,1]$ such that $f(c) = g(c)$? Answer yes or no.

**Answer:** Yes

**Condition:** bank; prompt=student_p1; seed=0

**Public clues:**

- The difference of two continuous real-valued functions on [0,1] is continuous on [0,1].
- A continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values.

**Reconstruction:** Is it true that if two continuous real-valued functions on [0,1] differ by a function that is never zero, then the difference is continuous on [0,1]?

**Justification:** The difference of two continuous real-valued functions on [0,1] is continuous on [0,1] because the difference of continuous functions is continuous. Additionally, a continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values, which is a consequence of the Intermediate Value Theorem. These two observations together support the truth of the statement.

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": true, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The first observation directly proves that the difference of two continuous functions on [0,1] is continuous, which is exactly the continuity claim in the proposed question."}, {"index": 2, "compatible": true, "grounding": "unsupported", "reason": "The second observation is true but irrelevant to the proposed question: it would support sign-constancy of a never-zero continuous difference, not its continuity. The student merely asserts it supports the statement without connecting it to the asked continuity claim."}], "justification": "insufficient", "shortcut": false, "score": 2, "reason": "The proposed question is well-posed and the answer Yes is correct, but the reconstruction makes the never-zero condition and second observation irrelevant to the actual question. Only the first observation grounds the answer, so an essential clue connection is unsupported."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "different", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "The source concerns whether two continuous functions with equal maxima must intersect. The candidate concerns whether the difference of two continuous functions is continuous when that difference is never zero.", "reason": "The candidate omits the equal-maxima premise and changes the target from existence of an intersection point to continuity of a difference function."}

### Source 33: Calculus

**Source question (private):** For every pair of continuous functions $f,g:[0,1] \rightarrow \mathbb{R}$ such that \(\max\{f(x):x \in [0,1]\} = \max\{g(x):x \in [0,1]\}\), is there always a point $c \in [0,1]$ such that $f(c) = g(c)$? Answer yes or no.

**Answer:** Yes

**Condition:** bank; prompt=student_p10_recover_original; seed=0

**Public clues:**

- The difference of two continuous real-valued functions on [0,1] is continuous on [0,1].
- A continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values.

**Reconstruction:** Is it true that if two continuous real-valued functions on [0,1] agree at one point, then their difference is continuous on [0,1] and that a continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values?

**Justification:** The difference of two continuous real-valued functions on [0,1] is continuous on [0,1]. A continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values. These are both true statements based on the properties of continuous functions on closed intervals.

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": true, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The student explicitly states that the difference of two continuous real-valued functions on [0,1] is continuous, which grounds the first part of the question. The 'agree at one point' condition is irrelevant but not contradictory."}, {"index": 2, "compatible": true, "grounding": "explicit", "reason": "The student explicitly states that a continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values, which grounds the second part. This is true by the intermediate value theorem, though the proof is omitted."}], "justification": "minor_omission", "shortcut": false, "score": 3, "reason": "The reconstruction is well-posed and the supplied answer Yes is correct. Both observations are compatible and explicitly connected to the proposed question, but the justification omits the routine proof of the second fact via the intermediate value theorem."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "different", "premises": "different", "domains_parameters": "same", "target": "different"}, "correspondence": "Source concerns existence of an intersection point for two continuous functions with equal maxima. Candidate concerns continuity of a difference when two functions agree at one point and a sign property of a never-zero continuous function.", "reason": "The candidate changes the objects, premises, and target; it is not the same essential mathematical problem."}

### Source 33: Calculus

**Source question (private):** For every pair of continuous functions $f,g:[0,1] \rightarrow \mathbb{R}$ such that \(\max\{f(x):x \in [0,1]\} = \max\{g(x):x \in [0,1]\}\), is there always a point $c \in [0,1]$ such that $f(c) = g(c)$? Answer yes or no.

**Answer:** Yes

**Condition:** bank; prompt=student_p10_recover_original; seed=1

**Public clues:**

- The difference of two continuous real-valued functions on [0,1] is continuous on [0,1].
- A continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values.

**Reconstruction:** Is it true that if two continuous real-valued functions on [0,1] agree at one point, then they are equal?

**Justification:** The observations indicate that the difference of two continuous functions is continuous, and a continuous function that is never zero cannot take both positive and negative values. These properties support the conclusion that two continuous functions agreeing at one point do not necessarily imply they are equal, hence the answer 'Yes' is incorrect.

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "unsupported", "reason": "The continuity of the difference is true, but it does not support the proposed claim that agreeing at one point implies equality; it is only a general fact."}, {"index": 2, "compatible": true, "grounding": "unsupported", "reason": "The fact about a never-zero continuous function is irrelevant to the proposed question, since the difference is zero at the agreement point, so the never-zero hypothesis does not apply."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed question asks whether two continuous functions agreeing at one point must be equal, whose correct answer is No. The supplied final answer is Yes, and the student's own justification even says Yes is incorrect. The observations are not substantively connected to the proposed question."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "same", "premises": "different", "domains_parameters": "same", "target": "different"}, "correspondence": "Source assumes the two continuous functions have equal maxima and asks whether they must intersect somewhere; candidate assumes they agree at one point and asks whether they must be equal everywhere.", "reason": "The premise and target are both essentially different, so this is not the same mathematical problem."}

### Source 33: Calculus

**Source question (private):** For every pair of continuous functions $f,g:[0,1] \rightarrow \mathbb{R}$ such that \(\max\{f(x):x \in [0,1]\} = \max\{g(x):x \in [0,1]\}\), is there always a point $c \in [0,1]$ such that $f(c) = g(c)$? Answer yes or no.

**Answer:** Yes

**Condition:** bank; prompt=student_p1; seed=1

**Public clues:**

- The difference of two continuous real-valued functions on [0,1] is continuous on [0,1].
- A continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values.

**Reconstruction:** Is it true that if two continuous functions on [0,1] differ by a function that is never zero, then the difference is continuous on [0,1]?

**Justification:** The difference of two continuous functions on [0,1] is continuous on [0,1] because the difference of continuous functions is continuous. Additionally, a continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values, which is a property of continuous functions on compact sets. These observations align with the properties of continuous functions on [0,1].

**Evaluation:** {"status": "scored", "well_posed": true, "answer_correct": true, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The proposed question asks about continuity of the difference of two continuous functions, and the first observation directly supports that."}, {"index": 2, "compatible": true, "grounding": "unsupported", "reason": "The observation that a never-zero continuous function cannot change sign is true, but the proposed question only asks whether the difference is continuous; it does not require or use the sign conclusion."}], "justification": "insufficient", "shortcut": false, "score": 2, "reason": "The proposed question is well-posed and the answer Yes is correct for it, but the second observation is not substantively connected to the question. The reconstruction only uses the continuity of the difference and omits the sign-related conclusion that the second observation would support."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "different", "premises": "different", "domains_parameters": "same", "target": "different"}, "correspondence": "Source concerns two continuous functions with equal maxima and asks whether their graphs must intersect. Candidate concerns whether the difference of two continuous functions is continuous when that difference is never zero. The equal-maxima premise and intersection target are absent.", "reason": "Different mathematical problem; the candidate asks about continuity of a difference, not existence of a point where f(c)=g(c) under equal maxima."}

### Source 33: Calculus

**Source question (private):** For every pair of continuous functions $f,g:[0,1] \rightarrow \mathbb{R}$ such that \(\max\{f(x):x \in [0,1]\} = \max\{g(x):x \in [0,1]\}\), is there always a point $c \in [0,1]$ such that $f(c) = g(c)$? Answer yes or no.

**Answer:** Yes

**Condition:** bank; prompt=student_p11_inverse_example; seed=0

**Public clues:**

- The difference of two continuous real-valued functions on [0,1] is continuous on [0,1].
- A continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values.

**Reconstruction:** Let f and g be continuous real-valued functions on [0,1]. If f(x) - g(x) is continuous on [0,1], and f is never zero, can f(x) - g(x) take both positive and negative values?

**Justification:** The given answer 'Yes' and the observations suggest that the difference of two continuous functions is continuous, and that a non-zero continuous function cannot take both positive and negative values. The question is about whether the difference can take both signs given the constraints. The answer 'Yes' implies that despite f being non-zero, the difference can still take both signs. The observations support this by stating that the difference is continuous and that a non-zero function cannot take both signs, but the answer 'Yes' indicates that the difference can, which is consistent with the properties of continuous functions.

**Evaluation:** not evaluated

**Source recovery:** not evaluated

### Source 33: Calculus

**Source question (private):** For every pair of continuous functions $f,g:[0,1] \rightarrow \mathbb{R}$ such that \(\max\{f(x):x \in [0,1]\} = \max\{g(x):x \in [0,1]\}\), is there always a point $c \in [0,1]$ such that $f(c) = g(c)$? Answer yes or no.

**Answer:** Yes

**Condition:** bank; prompt=student_p11_inverse_example; seed=1

**Public clues:**

- The difference of two continuous real-valued functions on [0,1] is continuous on [0,1].
- A continuous real-valued function on [0,1] that is never zero cannot take both positive and negative values.

**Reconstruction:** Let f and g be continuous real-valued functions on [0,1]. If f(x) - g(x) is continuous on [0,1], and f is never zero, can f(x) - g(x) take both positive and negative values?

**Justification:** The observations indicate that the difference of two continuous functions is continuous, and that a non-zero continuous function cannot take both positive and negative values. The question likely explores whether the difference can take both signs given that one function is non-zero. The answer 'Yes' suggests that despite f being non-zero, the difference can still take both signs. The observations are consistent with this conclusion.

**Evaluation:** not evaluated

**Source recovery:** not evaluated

### Source 77: Calculus

**Source question (private):** Find the maximum area of the region bounded by the curves \( C_1 : y = x^3 - x \) and \( C_2 : y = (x-a)^3 - (x-a) \), given that they intersect at two points.

**Answer:** \dfrac{1}{2}

**Condition:** bank; prompt=student_p1; seed=0

**Public clues:**

- The two curves are horizontal translates of the same cubic function.
- The two distinct intersection x-coordinates are roots of a quadratic whose discriminant is positive exactly when the shift parameter has absolute value between 0 and 2.
- The area between the curves equals half the absolute shift parameter times the cube of the distance between the two intersection x-coordinates.

**Reconstruction:** Let f(x) be a cubic function and g(x) = f(x - h) for some shift parameter h. If the area between f(x) and g(x) is equal to (1/2)|h| times the cube of the distance between the two distinct intersection x-coordinates, what is the value of the area between the curves when |h| = 2?

**Justification:** Given that the area between the curves equals (1/2)|h| times the cube of the distance between the two intersection x-coordinates, and when |h| = 2, the area is (1/2)(2) times the cube of the distance between the intersection points. Since the discriminant is positive exactly when |h| is between 0 and 2, the distance between the intersection points is non-zero. Therefore, the area is (1/2)(2) times a non-zero value, which simplifies to 1 times the cube of the distance. However, the exact value of the area depends on the specific cubic function and the distance between the intersection points. But the problem states that the area is (1/2)|h| times the cube of the distance, and when |h| = 2, the area is (1/2)(2) = 1 times the cube of the distance. Thus, the area is 1 times the cube of the distance, which is not necessarily equal to 1/2. However, the problem states that the area is (1/2)|h| times the cube of the distance, and when |h| = 2, the area is (1/2)(2) = 1 times the cube of the distance. Therefore, the area is 1 times the cube of the distance, which is not necessarily equal to 1/2. However, the problem does not specify the distance between the intersection points, so the answer is 1/2.

**Evaluation:** {"status": "scored", "well_posed": false, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The proposed question defines g(x)=f(x-h), so the curves are horizontal translates of the same cubic."}, {"index": 2, "compatible": false, "grounding": "violated", "reason": "The observation says distinct intersections occur only for 0<|h|<2, but the question asks for |h|=2 while still referring to two distinct intersection x-coordinates."}, {"index": 3, "compatible": false, "grounding": "unsupported", "reason": "The area formula is quoted, but at |h|=2 it gives area = d^3, or 0 if the intersections coincide, not 1/2; the distance d is not determined and the final answer is unsupported."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed question is ill-posed/contradictory at |h|=2 and the supplied answer 1/2 does not follow from the stated formula or observations."}

**Source recovery:** {"status": "scored", "source_recovery": 1, "checks": {"objects": "different", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "Both involve the area between a cubic and its horizontal shift, but the source uses the specific cubic x^3-x and maximizes over shifts satisfying two intersections, while the candidate uses an arbitrary cubic, adds a stated area formula, fixes |h|=2, and asks for the area value rather than the maximum.", "reason": "Related shifted-cubic area setup, but the objects, premises, parameter condition, and target are essentially changed."}

### Source 77: Calculus

**Source question (private):** Find the maximum area of the region bounded by the curves \( C_1 : y = x^3 - x \) and \( C_2 : y = (x-a)^3 - (x-a) \), given that they intersect at two points.

**Answer:** \dfrac{1}{2}

**Condition:** bank; prompt=student_p10_recover_original; seed=0

**Public clues:**

- The two curves are horizontal translates of the same cubic function.
- The two distinct intersection x-coordinates are roots of a quadratic whose discriminant is positive exactly when the shift parameter has absolute value between 0 and 2.
- The area between the curves equals half the absolute shift parameter times the cube of the distance between the two intersection x-coordinates.

**Reconstruction:** Let f(x) be a cubic function and g(x) = f(x - h) for some shift parameter h. Suppose the area between the curves f(x) and g(x) is equal to (1/2)|h| times the cube of the distance between the two distinct intersection x-coordinates. Determine the relationship between h and the cubic function f(x).

**Justification:** The given answer is 1/2, which is the coefficient in the area formula. The observations describe the relationship between the shift parameter h and the area between the curves, which is given as (1/2)|h| times the cube of the distance between the intersection points. This matches the structure of the area between two horizontal translates of the same cubic function. The discriminant condition and the area formula confirm that the relationship holds for h between -2 and 2.

**Evaluation:** {"status": "scored", "well_posed": false, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The proposed question states f is cubic and g(x)=f(x-h), matching the horizontal-translate observation."}, {"index": 2, "compatible": false, "grounding": "unsupported", "reason": "The proposed question does not specify a cubic whose intersection discriminant is positive exactly for 0<|h|<2; this depends on the cubic coefficients."}, {"index": 3, "compatible": true, "grounding": "explicit", "reason": "The proposed question assumes the area formula involving (1/2)|h| times the cube of the intersection distance, so the observation is explicitly built into the premise."}], "justification": "incorrect", "shortcut": true, "score": 0, "reason": "The reconstruction is tautological: it assumes the area formula containing 1/2 and then treats 1/2 as the answer, while the actual question asks for a relationship between h and f(x). The proposed question is ill-posed and the supplied answer does not answer it."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "different", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "Source uses the specific cubic f(x)=x^3-x and its shift by a, with the condition of two intersections, and asks for the maximum bounded area. Candidate uses an arbitrary cubic f, a shift h, and an assumed area formula, then asks for a relationship between h and f.", "reason": "The specific polynomial, given condition, parameters, and requested target are all changed; this is not the same essential problem."}

### Source 77: Calculus

**Source question (private):** Find the maximum area of the region bounded by the curves \( C_1 : y = x^3 - x \) and \( C_2 : y = (x-a)^3 - (x-a) \), given that they intersect at two points.

**Answer:** \dfrac{1}{2}

**Condition:** bank; prompt=student_p10_recover_original; seed=1

**Public clues:**

- The two curves are horizontal translates of the same cubic function.
- The two distinct intersection x-coordinates are roots of a quadratic whose discriminant is positive exactly when the shift parameter has absolute value between 0 and 2.
- The area between the curves equals half the absolute shift parameter times the cube of the distance between the two intersection x-coordinates.

**Reconstruction:** Let f(x) be a cubic function and g(x) = f(x - h) for some shift parameter h. If the area between the curves f(x) and g(x) is equal to (1/2)|h| times the cube of the distance between their two distinct intersection x-coordinates, find the value of |h| when the discriminant of the quadratic equation formed by the intersection points is positive.

**Justification:** The given observations indicate that the area between the curves is related to the shift parameter h and the distance between intersection points. The discriminant being positive implies that the shift parameter h has absolute value between 0 and 2. The final answer of 1/2 suggests that the value of |h| is 1, which is within the range where the discriminant is positive. Thus, the value of |h| is 1.

**Evaluation:** {"status": "scored", "well_posed": false, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The proposed question explicitly states that f is cubic and g is a horizontal translate f(x-h)."}, {"index": 2, "compatible": true, "grounding": "explicit", "reason": "The proposed question references the discriminant being positive, matching the observation that this occurs for |h| between 0 and 2, but it then asks for a unique |h| despite the observation giving only a range."}, {"index": 3, "compatible": true, "grounding": "explicit", "reason": "The proposed question includes the area formula from the observation, but treats it as a condition without showing how it determines a unique value."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The reconstructed question is ill-posed: discriminant positivity only gives 0<|h|<2, not a unique value. The student's justification also contradicts the final answer by saying 1/2 suggests |h|=1, so the supplied answer is not correctly connected to the proposed question."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "different", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "Source concerns the specific cubic f(x)=x^3-x and its shift f(x-a), asking for the maximum bounded area when there are two intersections. Candidate concerns an arbitrary cubic f, assumes a stated area formula, and asks for |h| under a discriminant positivity condition.", "reason": "The candidate changes the function class, premises, parameter role, and target; it is not the same essential problem."}

### Source 77: Calculus

**Source question (private):** Find the maximum area of the region bounded by the curves \( C_1 : y = x^3 - x \) and \( C_2 : y = (x-a)^3 - (x-a) \), given that they intersect at two points.

**Answer:** \dfrac{1}{2}

**Condition:** bank; prompt=student_p1; seed=1

**Public clues:**

- The two curves are horizontal translates of the same cubic function.
- The two distinct intersection x-coordinates are roots of a quadratic whose discriminant is positive exactly when the shift parameter has absolute value between 0 and 2.
- The area between the curves equals half the absolute shift parameter times the cube of the distance between the two intersection x-coordinates.

**Reconstruction:** Let f(x) be a cubic function and g(x) = f(x - h) for some shift parameter h. If the area between the curves f(x) and g(x) is equal to (1/2)|h| times the cube of the distance between their two distinct intersection points, what is the value of h when the discriminant of the quadratic equation formed by their intersection is positive exactly when |h| is between 0 and 2?

**Justification:** The problem involves a cubic function and its horizontal translation. The area between the curves is given as (1/2)|h| times the cube of the distance between the intersection points. The discriminant condition implies that the shift parameter h must satisfy |h| < 2 for the quadratic to have real roots. The answer is 1/2, which is consistent with the discriminant condition and the area formula.

**Evaluation:** {"status": "scored", "well_posed": false, "answer_correct": false, "clue_checks": [{"index": 1, "compatible": true, "grounding": "explicit", "reason": "The proposed question defines f as a cubic and g(x)=f(x-h), so the curves are horizontal translates."}, {"index": 2, "compatible": true, "grounding": "explicit", "reason": "The discriminant condition is explicitly included, but it only implies |h|<2 and does not determine a unique h."}, {"index": 3, "compatible": true, "grounding": "explicit", "reason": "The area formula is explicitly stated, but it is not used to constrain h or derive 1/2."}], "justification": "incorrect", "shortcut": false, "score": 1, "reason": "The proposed question is ill-posed: the condition that the discriminant is positive exactly when |h| is between 0 and 2 is satisfied by any h with |h|<2, so h=1/2 is not uniquely determined. The area formula is merely restated and does not force h=1/2."}

**Source recovery:** {"status": "scored", "source_recovery": 0, "checks": {"objects": "different", "premises": "different", "domains_parameters": "different", "target": "different"}, "correspondence": "The source concerns the specific cubic family y=x^3-x and its shift by a, asking for the maximum bounded area when there are two intersections. The candidate introduces a general cubic f, a shift h, an area-distance relation, and asks for h under a discriminant positivity condition.", "reason": "The candidate changes the function family, parameters, premises, and target; it is not the same essential mathematical problem."}

### Source 77: Calculus

**Source question (private):** Find the maximum area of the region bounded by the curves \( C_1 : y = x^3 - x \) and \( C_2 : y = (x-a)^3 - (x-a) \), given that they intersect at two points.

**Answer:** \dfrac{1}{2}

**Condition:** bank; prompt=student_p11_inverse_example; seed=0

**Public clues:**

- The two curves are horizontal translates of the same cubic function.
- The two distinct intersection x-coordinates are roots of a quadratic whose discriminant is positive exactly when the shift parameter has absolute value between 0 and 2.
- The area between the curves equals half the absolute shift parameter times the cube of the distance between the two intersection x-coordinates.

**Reconstruction:** Let f(x) be a cubic function such that f(x) = x^3 - 3x. Consider two horizontal translations of f(x), namely f(x - a) and f(x - b), where a and b are constants with |a| < 2 and |b| < 2. What is the area between the curves f(x - a) and f(x - b) in terms of a and b?

**Justification:** The given answer of 1/2 and the observations suggest a relationship between the area between the curves and the shift parameter. The observation that the area equals half the absolute shift parameter times the cube of the distance between the two intersection x-coordinates implies that the area is a function of the shift parameter. The discriminant condition suggests that the shift parameter is constrained to a specific range. The final answer of 1/2 is consistent with the area being half the shift parameter times the cube of the distance between the intersection points, which is derived from the specific cubic function and the shift parameter constraints. The observations are all consistent with the derived question and answer.

**Evaluation:** not evaluated

**Source recovery:** not evaluated

