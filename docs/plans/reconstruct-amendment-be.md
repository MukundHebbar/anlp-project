# BE: deterministic quote-validation replay, no model calls

BD found one claim quotation differing only by whitespace: source “has2^m” versus quoted “has 2^m”. Its mathematical and shortcut labels matched the prespecified references. Preserve BD as a strict-validator run, including the rejection and original validator snapshot.

Permit whitespace-only differences in mathematical claim quotations, while rejecting any change to non-whitespace characters. Record each non-exact match as an explicit validation note; retain raw output unchanged. This is text traceability, not proof of semantic equivalence of mathematical expressions. Shortcut premise/target quotes still require exact question substrings and cannot use this fallback.

After BD terminates, replay EVERY one of its19 original responses through the revised validator. Do not resample, retry, regenerate quotes, edit model labels, alter expected labels or select a subset. Freeze original manifest/run hashes and revised validator hash. Preserve failure outputs and raw usage provenance. Missing calls or other invalid judgments remain failures. Report original strict acceptance and revised acceptance separately. No new LLM accuracy or independent replication claim follows from a validator replay.
