# A substantive sparse reconstruction, with its failed paired sample

This is a development case study, not a success-rate claim. Both samples received the same two observations and supplied answer 11.

- For p=2,3,5,7, the values v_p(100!) are 97, 48, 24, and 16, respectively, so each is at least p.
- In base p, the number of trailing zeros of 100! equals v_p(100!), the exponent of p in the prime factorization of 100!.

## Seed 0

What is the smallest prime p such that the number of trailing zeros of 100! in base p is at least p?

The number of trailing zeros of 100! in base p is equal to v_p(100!), the exponent of p in the prime factorization of 100!. For p=2,3,5,7, the values v_p(100!) are 97, 48, 24, and 16, respectively, so each is at least p. The smallest prime p for which this condition holds is 2. However, the answer is 11, which is not a prime. This suggests that the question might be asking for the smallest integer p (not necessarily prime) such that the number of trailing zeros of 100! in base p is at least p. For p=11, the value v_11(100!) is 9, which is less than 11. Hence, the answer is 11, which is not a prime, indicating that the question is not restricted to prime numbers.

## Seed 1

What is the smallest prime p such that the number of trailing zeros of 100! in base p is less than p?

The number of trailing zeros of 100! in base p is equal to v_p(100!), the exponent of p in the prime factorization of 100!. For p=2,3,5,7, the values v_p(100!) are 97, 48, 24, and 16, respectively, so each is at least p. However, for p=11, v_11(100!)=9, which is less than 11. Hence, the smallest prime p is 11.

Independent arithmetic check: v_2=97, v_3=48, v_5=24, v_7=16, v_11=9. Seed1 correctly infers the missing “less than p” criterion and checks minimality; seed0 chooses “at least p”, which has answer2, and misidentifies11 as nonprime.

The successful sample demonstrates the intended skill: choose an unstated condition consistent with both the observations and the answer, then verify it. The failed paired sample shows why retaining seeds and reporting aggregate uncertainty matter.

Evidence: [mathematical review](sparse-factorial-math-review.json), [raw experiment](sparse-role-study.json).
