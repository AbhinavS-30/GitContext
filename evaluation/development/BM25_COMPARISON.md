# Controlled BM25 development comparison — November 25, 2026

This is a provisional comparison on three exposed, Codex-authored implementation
labels, reviewed by Codex only. It is not a formal benchmark, independent human
validation, held-out performance, or a general quality/speed claim. Source relevance
scope remains narrow and incomplete; useful documentation may be unlabeled.

## Fixed experiment

The specification was published in 01e54a7 before implementation/results. See
docs/BM25_EXPERIMENT.md for formula and design choices, and PROVISIONAL_RESULTS.md
for the original baseline. No parameter search or post-result label/question edits.

- Source: 548076ad03eb936c61b8d7540feb65d5da8f60e2; 43 files, 588 chunks.
- Snapshot: snapshot-v2:50bf1719bb31faf1467fe9194c86b0111a5b13ddf2c92178f125a7bc3dcd9032.
- Dataset: gitcontext-development-548076a, draft-v2, development only, k=5.
- Input SHA-256: cec6371b92a514219be0cf1da0e97457a0a2f96a08a275bffd7c14845dbc93f8.
- Tokenizer: code-words-v1 for both modes, including full/split expansions.
- Baseline: distinct-term-overlap-v1; no parameters.
- Candidate: bm25-positive-idf-v1; k1=1.2, b=0.75, positive log1p IDF; token-empty
  chunks excluded from collection statistics. Corpus statistics are computed inside
  each ranking call; there is no persisted/cached lexical index.
- One installed-CLI evaluate invocation per method, with current source for all
  cases. The overlap rerun exactly reproduced the original top-five chunk IDs,
  scores, matched terms, and source metadata. Candidate ordering differed.
- Snapshot contents/IDs, questions, relevance IDs, cutoff, and parameters were
  unchanged after observing either result. Evaluation-version metadata now records
  the method and parameters; snapshot schema/identity did not change.

Private raw reports remain ignored:
.gitcontext/development-548076a/bm25-experiment-overlap.top5.json and
.gitcontext/development-548076a/bm25-experiment-bm25.top5.json. They include exact
timings, private root paths, provenance, and snippets and are not committed. A single
run is insufficient for representative timing; no latency improvement is claimed.

## Outcomes against unchanged draft implementation labels

| Case | Overlap labeled hits / relevant | BM25 labeled hits / relevant | Outcome |
| --- | --- | --- | --- |
| dev-atomic-save | 0 / 1 | 0 / 1 | unchanged miss |
| dev-freshness-states | 0 / 2 | 0 / 2 | unchanged miss |
| dev-search-freshness-gate | 0 / 1 | 0 / 1 | unchanged miss |

Each method attempted 3 cases, all 3 current and eligible, with no blocked/error
cases. Conditional hit rate@5=0/3 and macro recall@5=0 for both methods under these
draft labels. Each returned 15 references matching saved source metadata. This
traceability result does not establish semantic relevance or answer correctness.

All top-five results remained documentation. First results were:

| Case | Overlap first result | BM25 first result |
| --- | --- | --- |
| dev-atomic-save | README.md:330–360, Local snapshot persistence | same |
| dev-freshness-states | README.md:15–56, CLI usage | docs/WALKTHROUGH.md:6–20, What the application does today |
| dev-search-freshness-gate | README.md:15–56, CLI usage | docs/DECISIONS.md:263–277, freshness-gated lexical CLI search |

Raw BM25 weights and overlap counts are on different scales and are not compared
as quality. Changing result order or increasing a numeric score is not a measured
relevance improvement. No label was expanded to turn these misses into successes.

## Decision and limits

Do not promote BM25 based on this run. Overlap remains the default; BM25 is an
explicit experimental comparison mode. Its local implementation and tests can
support later method comparisons, but no gain is established here. No additional
parameter tweaks, definition boosts, stopword lists, or model downloads were added.

This result is consistent with vocabulary/evidence-scope mismatch remaining after
statistical weighting: documentation speaks in natural-language terms, while the
narrow labels require implementation chunks. That is a hypothesis for further
review, not a proof that BM25 always fails on code or that documentation is useless.
Human intent/label review and broader development coverage remain needed. All these
exposed cases stay development-only; the formal ten-question set remains deferred.
