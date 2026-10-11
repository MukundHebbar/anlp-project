# Phase-2 experiments: summary

Models: the mixed GRPO model (step 75) and the three single-task specialists (SOLVE, JUDGE, RECONSTRUCT), all
Qwen3.5-2B LoRA adapters. Qwen3.8-27B is used as a referee where noted. All runs on Turing (node07).

---

## 1. Rescuing always-wrong problems during GRPO

**Question.** GRPO learns nothing from a problem the model always gets right or always gets wrong. Can the
specialists turn an always-wrong problem into a learnable one by writing a hint?

**Method.**
1. The mixed model answered the 750 SOLVE problems it trained on, 8 times each.
2. For each genuinely always-wrong problem, take the most common wrong answer and one attempt that reached it.
   JUDGE looks for the first wrong step in it. RECONSTRUCT writes the question that the wrong answer would be
   correct for.
3. The mixed model retries each problem 8 times under different hints.

**How many problems are dead**

| Result over 8 tries | Problems | Share |
|---|---|---|
| Always right | 291 | 39% |
| Sometimes right (useful to GRPO) | 374 | 50% |
| Always wrong | 85 | 11% |
| ↳ answer unreadable or cut off | 46 | |
| ↳ genuinely wrong | 39 | |

**What the specialists produced (39 problems)**

| | Result |
|---|---|
| JUDGE finds a usable wrong step | 0 / 39 (5 / 39 with 4× more room) |
| RECONSTRUCT writes a question | 38 / 39 |
| …that is actually different from the original | rarely; mostly a reworded original |

**Retrying with hints (23 non-Yes/No problems, 184 tries per hint)**

| Hint | Correct tries |
|---|---|
| No hint | 6 |
| RECONSTRUCT hint | 2 |
| "An earlier attempt got X, which is wrong" | 7 |
| JUDGE hint (5 problems, 40 tries) | 0 |

**Takeaway.** The specialists have the same blind spot as the learner, so they cannot explain its mistakes. No hint
beat simply saying which answer is wrong.

---

## 2. Tutor: marking a student's solution

**The idea.** A tutor sees a problem and a student's worked solution and must say what went wrong. Students make
two different kinds of mistake:

| Mistake | Example | What catches it |
|---|---|---|
| **False step**: one line of the maths is wrong | Problem: 3 × 4 + 5. Student: "3 × 4 = 11", then 11 + 5 = 16 | **JUDGE** finds the false line |
| **Wrong question**: every line is correct, but it answers a slightly different problem (the student misread it) | Problem: divisors of **k + 1**. Student finds k = 25, then counts divisors of **25** | No false line to point at. **RECONSTRUCT** rebuilds the question the work actually answers ("divisors of 25?"), and the 27B checks it against the problem that was set |

The JUDGE dataset contains only false-step solutions. To test the second kind, wrong-question solutions were made
from correct ones: change one detail of the *problem* (k → k + 1) so the unchanged solution now answers the wrong
question. A change was kept only if the 27B confirmed it changes the correct answer.

**Test set**

| Solutions | Count | Source |
|---|---|---|
| Correct | 200 | JUDGE test set |
| False step | 200 | JUDGE test set |
| Wrong question | 102 | correct solutions with one problem detail changed |

**Results** (each team marks every solution; "mixed" = the mixed model in both roles)

| Measure | Specialists | Mixed |
|---|---|---|
| Correct solutions wrongly flagged by JUDGE | 4.5% | 4.0% |
| False-step solutions caught by JUDGE | 64.5% | 80.5% |
| …with the exact wrong step named | 55.5% | 72.5% |
| Wrong-question solutions caught by JUDGE alone | 71 / 102 | 75 / 102 |
| Extra wrong-question solutions caught by adding RECONSTRUCT (at 10% extra false alarms) | +13 | +10 |
| **Wrong-question solutions caught, JUDGE + RECONSTRUCT** | **84 / 102** | **85 / 102** |
| RECONSTRUCT's question closer to what the student actually solved than to the problem set | 85 / 96 | 74 / 79 |

**RECONSTRUCT as a detector on its own** (share of wrong-question solutions caught, at a given false-alarm rate on
the other 400)

| False alarms | Specialists | Mixed |
|---|---|---|
| 2% | 19% | 25% |
| 5% | 36% | 35% |
| 10% | 48% | 52% |
| 20% | 56% | 68% |

**Takeaway.** On short, step-numbered solutions both specialists are useful. JUDGE handles false steps;
RECONSTRUCT adds wrong-question cases JUDGE misses and can tell the student which question they answered.

**Caveats.** The wrong-question solutions were made by the 27B, not by real students. The detection threshold was
picked on the test set and needs a separate tuning set. "Closer to what the student solved" is the 27B's
judgement, not an exact match.

---

## 3. Self-checking solver with drift detection

**Question.** While solving, does the model ever drift onto a different problem without making a false step, and can
RECONSTRUCT notice it?

**Method.**
1. The mixed model attempted 200 unseen problems, 4 times each (800 attempts).
2. JUDGE checked each attempt for a false step. RECONSTRUCT rebuilt the question from the work so far at ¼, ½, ¾
   and the end; the 27B checked whether it had drifted from the real problem.
3. Flagged attempts were cut at the flagged point and the model redid the rest. Compared against random flags and
   perfect flags.

**Attempts:** 800, of which 558 correct (69.75%) and 242 wrong.

**Can the checkers tell wrong attempts from right ones?** (AUROC 0.5 = coin flip)

| Checker | Flags wrong attempts | Flags correct attempts | AUROC |
|---|---|---|---|
| JUDGE (specialist) | 4.1% | 2.7% | 0.51 |
| JUDGE (mixed) | 7.4% | 2.2% | 0.53 |
| Drift check (specialist) | 0.0% | 0.0% | 0.44 |
| Drift check (mixed) | 0.4% | 0.5% | 0.38 |
| Wrong attempts with drift but no false step | 1 | | |

**Accuracy after one repair**

| Repair rule | Attempts repaired | Accuracy |
|---|---|---|
| No repair | 0 | 69.75% |
| Where JUDGE flagged (mixed) | 30 | 70.13% |
| Where JUDGE or drift flagged (mixed) | 34 | 70.13% |
| Random, same number | 34 | 69.75% |
| Perfect flags (every wrong attempt) | 242 | **76.75%** |

**Takeaway.** Repairing would be worth about 7 points if wrong attempts could be found, but neither checker can find
them in long solutions the model wrote itself. Drift without a false step was essentially never observed.

---

## Overall

| Input | Example | Specialists work? |
|---|---|---|
| Short, step-numbered solutions | Tutor test set | Yes |
| Long solutions the model wrote itself | Always-wrong problems, drift checks | No (near coin flip) |

Next step: confirm this gap on an external benchmark of natural solutions with labelled errors (ProcessBench).
