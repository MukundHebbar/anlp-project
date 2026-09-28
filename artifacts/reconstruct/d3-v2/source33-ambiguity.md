# A checked ambiguity example: grounding does not imply source recovery

The revised source33 input gives answerYes and two observations: differences of continuous functions are continuous, and a continuous zero-free function on[0,1] has constant sign. The original question assumes equal maxima and asks whether the functions must meet.

A different valid question assumes equal integrals instead and asks whether the functions must meet. The same two observations ground its proof: if h=f−g never vanishes, continuity makes its sign constant; compactness then makes its integral strictly positive or negative, contradicting the equal-integral premise. The answer is alsoYes.

The premises are not equivalent. For f(x)=x and g(x)=x², both maxima are1 but integrals are1/2 and1/3. For f(x)=0 and g(x)=x−1/2, both integrals are0 but maxima are0 and1/2. Exact integral calculations were checked with SymPy; these maxima follow directly from the functions on[0,1].

Thus the public evidence does not logically determine the original premise. This supports keeping grounded validity separate from original-question recovery. It does not predict Qwen's success rate, prove that the task is unusable, or justify secretly adding a source-specific hint. A future globally defined information-content intervention can test whether retaining more distinctive observations improves recovery while preserving non-disclosure.

Evidence: [questions, proof, counterexamples, and provenance](source33-ambiguity-certificate.json). This is an assistant-authored mathematical certificate, not a sampled model result or human annotation.
