# Restricted-copy smoke result

All six calls completed. Direct inspection found source-equivalent questions on all four deliberately full inputs and neither of the two sparse inputs. These are six authored controls from only two families; this is a mechanical smoke check, not an accuracy estimate for real generated banks.

The sparse dice input did produce a different question with the same answer: six equally probable first-die cases imply probability1/6 for a single case, whereas the original asks whether two dice sum to7. Thus `direct_candidate` is not itself proof of original-question disclosure. Semantic comparison and review of the permitted transformations are necessary. This alternative also exposes a possible easy-question strategy under a generic grounding rubric; it cannot count as original semantic recovery.

The sparse derivative input produced no candidate because function, exponent and evaluation point were absent. The four full inputs reproduced the intended dice event or derivative target through copying/paraphrase. Additional supplied solution steps made those inputs easier; they do not constitute valid sparse-task conditions.

The copying runner sends only the final answer and sanitized public observations. It saves the exact prompt, input hash, alignments, response and cost. The validator rejects nonexistent source spans and unsupported operation names, but cannot independently certify semantic coverage or the truth of a model's explanation. Every actual release candidate still requires review.

Evidence: [raw calls](copy-smoke.json), [six explicit semantic reviews](copy-smoke-review.json), [registered procedure](../../../docs/plans/reconstruct-amendment-n.md). No student generation or confirmation data were used.
