Reconstruct a self-contained mathematical question from its final answer and partial solution observations. The unknown being asked for must actually have the supplied answer. Work backward to choose the missing conditions and target, then verify your construction. An intermediate value in a clue need not be the answer. Use every clue substantively in one coherent solution. Several questions may fit; choose one and state your choices. Do not put the answer itself into the premises or ask to repeat it.

Example 1:
Answer: 5.
Observations: each unordered pair is counted once; the pair count is n(n-1)/2; there are 10 pairs.
Output: {"justification":"The observations constrain n(n-1)/2=10. This gives (n-5)(n+4)=0, so the positive group size is 5, the supplied answer. I use a handshake setting to realize the unordered pairs.","assumptions":["Every two distinct people shake hands exactly once."],"question":"At a gathering every two distinct people shake hands exactly once. There are 10 handshakes in total. How many people attend?"}

Example 2:
Answer: 12.
Observations: the two journeys cover the same distance; the times are 2 hours and 3 hours; the speeds differ by 2 km/h.
Output: {"justification":"For common distance d, the speeds are d/2 and d/3. Their difference gives d/2-d/3=2, hence d=12 km, matching the answer. Both speeds and times fit the same round trip.","assumptions":["Each leg has a constant positive speed."],"question":"A cyclist rides from A to B in 2 hours and returns along the same route in 3 hours. Each leg has constant speed, with the outward speed 2 km/h faster. What is the distance from A to B in kilometres?"}

Return JSON only, with a concise mathematical verification followed by the final question. Put every necessary chosen condition into the question itself:
{"justification":"...","assumptions":["..."],"question":"..."}

FINAL ANSWER: {{FINAL_ANSWER}}
OBSERVATIONS:
{{RENDERED_CLUES}}
