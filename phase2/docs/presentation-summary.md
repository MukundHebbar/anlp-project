# What Transfers Through Mathematical RL?

## Three task forms (same maths, different job)
- **SOLVE**: problem → worked solution and final answer
- **JUDGE**: problem + step-numbered solution → correct, or first wrong step and why
- **RECONSTRUCT**: final answer + 4 partial clues → the original question

Data: DeepMath-103K, 4,000 questions per task (3,600 train / 400 test), different questions per task, matched topic
and difficulty.

## Training
- Student: Qwen3.5-2B (LoRA), trained with Dr. GRPO
- One model per task, plus one **mixed** model on all three
- Every model tested on all three tasks

## Transfer results (change vs untrained model, points)

| Trained on | SOLVE | JUDGE | RECONSTRUCT |
|---|---|---|---|
| SOLVE | **+16.6** | +8.8 | +3.8 |
| JUDGE | −1.1 | **+17.2** | +6.0 |
| RECONSTRUCT | −10.7 | +14.2 | **+21.4** |
| Mixed | +17.1 | +32.2 | +18.3 |

- Each model improves most on its own task
- Transfer is uneven: SOLVE helps the others; RECONSTRUCT hurts SOLVE
- **Mixed is best overall**: no task gets worse, and it beats the JUDGE-only model at JUDGE

## Follow-up probes
- **Dead problems:** after training, half the training problems teach GRPO nothing (39% always right, 11% always
  wrong). Hints from the JUDGE/RECONSTRUCT models did not help the model solve them.
- **Tutor:** JUDGE names the exact wrong step in 72% of wrong solutions. Adding RECONSTRUCT catches more students
  who answered the wrong question: 70–74% → 78–81%.
- **Self-checking solver:** on the model's own long solutions, neither checker beats a coin flip at spotting wrong
  attempts. Perfect checking would add +7 points, so the bottleneck is detection.
- **Real errors (ProcessBench, 3,400 solutions by other models):** checking learned on injected errors transfers,
  but only about half the gain survives (mixed: +34.8 F1 on injected errors → +18.7 on real ones). RECONSTRUCT
  training helps real error-finding as much as JUDGE training.

## Takeaway
- Question form shapes what RL teaches; mixing forms works best
- Learned checking transfers to real errors in short, step-split solutions (about half the gain)
- It fails on long, unstructured solutions the model wrote itself
