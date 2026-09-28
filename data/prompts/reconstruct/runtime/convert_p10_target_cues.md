Create two short supported clues to help reconstruct a mathematical question from its answer and partial observations. Preserve uncertainty: do not quote or paraphrase the complete requested target, disclose the entire question, or give the completed derivation. The existing observations will remain unchanged. Do not alter a given value.

Return JSON only:
{"target_family_cue":"One normal sentence indicating the broad kind of question, without specifying its exact mathematical target.","method_cue":"One normal sentence naming a useful mathematical method or tool without stating the requested target or the final calculation.","hidden_support":"Explain how both follow from the source and what essential target choice remains withheld."}

Example source: A rectangle has perimeter20 and area24. Find its longer side. Answer6.
Output: {"target_family_cue":"The requested result is a length associated with this rectangle.","method_cue":"A quadratic equation for a side length is useful.","hidden_support":"The target is a side length, but longer versus shorter is withheld. The sum and product of sides produce a quadratic; neither roots nor the full target are supplied."}

Example source: Two fair dice are rolled. Find the probability that their sum is at least10. Answer1/6.
Output: {"target_family_cue":"The result measures the likelihood of an event involving the dice.","method_cue":"Counting equally likely ordered outcomes is useful.","hidden_support":"Neither the sum condition nor its cutoff is disclosed; the solver still reconstructs the event."}

SOURCE QUESTION: {{SOURCE_QUESTION}}
ANSWER: {{FINAL_ANSWER}}
CHECKED SOLUTION: {{CHECKED_SOLUTION}}
EXISTING OBSERVATIONS: {{RENDERED_CLUES}}
