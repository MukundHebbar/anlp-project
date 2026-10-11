# Drift experiment

```
{
 "attempts": 800,
 "accuracy_none": 0.6975,
 "wrong_attempts": 242,
 "spec": {
  "judge_flag_rate_on_wrong": 0.04132231404958678,
  "judge_flag_rate_on_correct": 0.026881720430107527,
  "drift_flag_rate_on_wrong": 0.0,
  "drift_flag_rate_on_correct": 0.0,
  "wrong_with_drift_but_no_judge_flag": 0,
  "correct_with_drift_flag": 0,
  "checkpoints_judged": 2322,
  "auroc_drift_wrong_vs_correct": 0.4438853342812287,
  "auroc_judge_flag_wrong_vs_correct": 0.5072202968097397
 },
 "mixed": {
  "judge_flag_rate_on_wrong": 0.0743801652892562,
  "judge_flag_rate_on_correct": 0.021505376344086023,
  "drift_flag_rate_on_wrong": 0.004132231404958678,
  "drift_flag_rate_on_correct": 0.005376344086021506,
  "wrong_with_drift_but_no_judge_flag": 1,
  "correct_with_drift_flag": 3,
  "checkpoints_judged": 1868,
  "auroc_drift_wrong_vs_correct": 0.3829052993275867,
  "auroc_judge_flag_wrong_vs_correct": 0.5264373944725851
 },
 "accuracy_after_one_repair": {
  "mixed:drift": {
   "accuracy": 0.6975,
   "repaired": 4
  },
  "mixed:either": {
   "accuracy": 0.70125,
   "repaired": 34
  },
  "mixed:judge": {
   "accuracy": 0.70125,
   "repaired": 30
  },
  "mixed:random": {
   "accuracy": 0.6975,
   "repaired": 34
  },
  "oracle": {
   "accuracy": 0.7675,
   "repaired": 242
  },
  "spec:either": {
   "accuracy": 0.70125,
   "repaired": 25
  },
  "spec:judge": {
   "accuracy": 0.70125,
   "repaired": 25
  },
  "spec:random": {
   "accuracy": 0.695,
   "repaired": 25
  }
 }
}
```

## Wrong attempts flagged by drift but not by JUDGE (mixed role set)

**solve-89105** attempt 1 answer 2 (key 50); drift checkpoints {2: 0.4007519242620916, 3: 0.7872841890384638, 4: 0.690305263379771}

Problem: Petya and Vasya created ten fifth-degree polynomials. Vasya then began calling out consecutive natural numbers, starting from a certain number. Petya chose one of the polynomials for each number called and substituted the number into it, writing the resulting values on the board in sequence. These values formed an arithmetic progression. What is the maximum number of numbers Vasya could call out?

Rebuilt questions:

- step 2: Let the coefficients of a sequence of polynomials $P_n(x)$ form an arithmetic progression. If the first coefficient is 0 and the common difference is 2, what is the value of the second term of this AP?
- step 3: Let there be 10 fifth-degree polynomials $P_1(x), P_2(x), \dots, P_{10}(x)$. When Vasya calls out consecutive natural numbers $n, n+1, \dots, n+9$, the values $P_i(n_k)$ for all $i$ and $k$ form an arithmetic progression of values. How many such consecutive natural numbers exist for which this condition holds?
- step 4: Ten polynomials $P_1(x), P_2(x), \dots, P_{10}(x)$ of degree less than 10 are evaluated at ten consecutive natural numbers. If the resulting ten values form an arithmetic progression, what is the sum of these values?
- step 6: None

---

