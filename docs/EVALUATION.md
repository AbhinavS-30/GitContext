# Evaluation contract v1 — no dataset or measured quality yet

This document defines future evaluation and the implemented arithmetic helper.
It contains no formal questions, relevance labels, benchmark runs, or quality
results. Tests use synthetic IDs only. Dataset creation remains a separate agreed
step; do not promote development examples into independent held-out evaluation.

## Dataset and labeling contract (planned)

A future dataset must record dataset ID/version, repository snapshot ID, labeling
rules, size, label author/reviewer and review status, and limitations. Each case
needs a stable case ID, question, split (development/held-out), expected behavior
(supported/unsupported), relevance-label status, and relevant chunk IDs. Empty labels
alone do not establish that a question is unsupported; unlabelled and intentionally
unsupported cases must be distinguishable. No case records are created here.

All labels must resolve to the exact saved snapshot, whose IDs bind source/version/
chunking configuration. Do not run labels from a different snapshot or silently
map invalid IDs to similar text. Chunk-policy changes require label revalidation.
Document whether labels enumerate all relevant evidence; incomplete labels limit
recall interpretation. Distinguish finding any useful evidence from finding enough
evidence for a complete explanation. Human agreement on relevance is required
before claiming human-labeled or human-reviewed quality. Codex review is not
independent human validation. Never tune on held-out examples and then call them
independent evaluation without disclosing that use.

## Observation/run contract (planned runner)

A future run records dataset/version/split and labeled case count; snapshot/schema
and file hashes/Git context; retrieval mode, tokenizer/ranking configuration, k;
model/version/settings when applicable; and execution environment. Embedding and
generation configuration are absent today and must not be fabricated.

Each observation records case ID, current/stale/unknown/error status, returned IDs
in rank order, diagnostic reasons, matched terms/scores, timing, and citation
validation outcomes. Search freshness must pass before returning evidence.
Blocked/error observations have no returned evidence, remain visible, and do not
receive success scores. Report attempted, successful-current, blocked, errored,
positively labeled, unsupported, and unlabelled case counts, plus denominator rules.
Do not hide failures by reporting only the cases that happened to run successfully.

## Implemented per-observation metrics

`evaluation.metrics_at_k(retrieved_ids, relevant_ids, k=..., status=...)` computes:

- hit_at_k: whether any of the first k IDs is labeled relevant.
- recall_at_k: distinct relevant IDs in the first k divided by the full relevant
  label count, including relevant evidence missed by retrieval.
- retrieved/relevant/matched counts for inspecting the calculation.

The cutoff is applied to the returned order before matching. Duplicate or malformed
IDs are rejected rather than deduplicated in a way that changes rank positions.
Fewer than k results are valid. A current empty result with positive labels is a
miss/zero recall. With no positive labels, hit/recall are undefined (None), not
perfect recall; unsupported behavior needs its separate recorded expectation.
Stale/unknown/error states are explicit and unscored (None), not zeros or successes.
Supplying evidence for those states is an error. The helper does not inspect files,
validate IDs against a snapshot, label relevance, time retrieval, or run a dataset.

Future hit rate@k is the mean of per-case hits over current positively labeled cases,
with that eligible count disclosed alongside attempted/blocked/error counts. Future
macro recall@k averages per-case recall over the same eligible cases. No eligible
cases means undefined metrics, never zero or 100%. Aggregate tooling is not yet
implemented. Any later end-to-end reliability measure must state its denominator
and keep failed versus current-no-match outcomes distinguishable.

## Timing, citations, unsupported questions, and future answers

Latency tooling is planned, not implemented. Use a monotonic timer; separately
record ranking-only time and total search time including snapshot load/validation
and freshness reads. Include empty successful queries, record blocked/error timing
separately, document cold/warm conditions and corpus size, and do not compare one
mode's ranking-only latency with another's full-request latency. Report sample
counts and variability rather than pretending one run is representative.

Citation validation tooling is also planned. Resolve every returned ID against the
saved snapshot and check path, inclusive line range, exact text, and file hash;
freshness is a separate source-state check. Invalid references fail visibly; do
not repair them silently. These checks establish traceability, not relevance or
semantic correctness. Existing persistence checks are not an independent citation
evaluation report.

Unsupported-question behavior is separate: a lexical match can occur for an
unsupported question, and no lexical match cannot prove that evidence is absent.
Record observed behavior against an explicit expectation; do not infer calibrated
answerability from overlap scores. Future answers require separate schema validity,
citation-reference validity, model availability, and human-reviewed correctness
and sufficiency. No answering model or answer correctness evaluation exists now.

Freshness and refresh behavior already have software tests, including unknown,
stale, and interrupted-write cases. They are not benchmark results. The formal
dataset, runner, aggregate reports, timing and citation tools, and human quality
review remain future work. Do not add retrieval complexity based on invented gains.
