train: 4096 questions
test: 1024 questions

how do we split the dataset?
## Making a smaller dataset
equal weightage for high level domain concepts. Then random sampling for sub domain concpets. Equal weightage to these topics: algebra , number theory , combinometrics, discrete mathematics, geometry

2 difficulty bands: 5-7 , 7-8. 80% weightage for 5-7 band. 20% weightage for 7-8 band. Similar mean difficulty should be maintaned between test , validation datasets

metrics to measure:
- performnace per topic
- performance per difficulty band
- performance per taks form
- worst cell performance
- maximum gap between cells
- confidence intervals

---
## Making the questions

solve: compare between model solution , ideal solution given in the dataset. Convert the reasoning trace into a proper solution using external model

plan: LLM as a judge compares between the tested models plan and the reasoning trace given in the dataset

Judge: we generate judge questions from the reasoning trace, by asking another model to make errors in the reasoning trace solution.

|Task|Student receives|Student must produce|How the external model is used|
|---|---|---|---|
|SOLVE|Problem only|Complete solution and final answer|Rewrite/check the DeepMath trace to create a trusted reference solution|
|PLAN|Problem only|Valid method and initial steps, without solving fully|Compare the generated plan with the trusted method during evaluation|
|JUDGE|Problem + proposed solution|Correct/incorrect decision; if incorrect, locate first error|Generate proposed solutions by injecting controlled errors|
