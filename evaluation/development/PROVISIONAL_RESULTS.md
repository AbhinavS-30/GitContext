# Provisional development diagnostic — draft-v2, top 5

This is not a formal benchmark, held-out result, human-validated relevance study,
or general quality claim. Three Codex-authored development questions were scored
against narrow, incomplete implementation labels reviewed by Codex only. Human
review remains pending. Do not describe these numbers as overall retrieval quality.

## Frozen inputs and method

- Source export: GitContext `548076ad03eb936c61b8d7540feb65d5da8f60e2`.
- Snapshot: `snapshot-v2:50bf1719bb31faf1467fe9194c86b0111a5b13ddf2c92178f125a7bc3dcd9032`.
- Corpus: 43 files, 588 chunks; complete and not degraded; Python 3.12.13.
- Input: gitcontext-development-548076a, dataset_version=draft-v2, development split.
- Exact input SHA-256: `cec6371b92a514219be0cf1da0e97457a0a2f96a08a275bffd7c14845dbc93f8`.
- Input was published as draft-v1 in 0198fd1 before this run. Draft-v2 changes only
  review/provenance/scoring-policy metadata: questions and relevant chunk IDs stayed
  unchanged. Codex checked the selected source for each narrow mechanism before
  scoring and recorded codex_reviewed/reviewer=Codex, not human_reviewed.
- Ranking: distinct-term-overlap-v1; tokenizer: code-words-v1; k=5, the existing
  default. One run. No ranking weights, questions, labels, or source changed after
  seeing results; no cutoff was selected to improve the outcome.
- Source freshness passed for every case. Evaluation CLI exited 0 because current
  execution completed, not because retrieval met a quality threshold.

Raw JSON, exact timings, source snippets, and absolute local paths remain in ignored
`.gitcontext/development-548076a/provisional-draft-v2.top5.json`. They are not
committed. This summary includes only public relative references and qualified
diagnostics. A single local run does not establish representative latency.

## Result against these draft implementation labels

| Case | Draft relevant chunks | Labeled chunks retrieved in top 5 | Hit@5 | Recall@5 |
| --- | ---: | ---: | --- | ---: |
| dev-atomic-save | 1 | 0 | false | 0 |
| dev-freshness-states | 2 | 0 | false | 0 |
| dev-search-freshness-gate | 1 | 0 | false | 0 |

Attempted=3; current=3; stale=0; unknown=0; errors=0; eligible=3. Conditional hit
rate@5=0/3 and macro recall@5=0 for these draft labels only. Unsupported/unlabelled
populations were empty. These labels do not exhaust every useful documentation,
call-site, or explanatory chunk, so zero labeled hits does not mean no useful
evidence was returned or every result was irrelevant.

All 15 returned references matched the saved source metadata. Three observations
had checked references, and all three passed that traceability check. This is not
semantic relevance, answer correctness, or independent human citation validation.

## What appeared first

| Case | First result at the fixed source commit | Match count |
| --- | --- | ---: |
| dev-atomic-save | README.md:330–360, Local snapshot persistence | 13 |
| dev-freshness-states | README.md:15–56, CLI usage | 12 |
| dev-search-freshness-gate | README.md:15–56, CLI usage | 10 |

All top-five results were documentation chunks: README, walkthrough, decisions,
and evaluation documentation. Some explain related mechanisms. The current ranker
counts all distinct query terms without stopword removal, term rarity, or document
length weighting. Long prose often overlaps more natural-language words than the
short implementation. The first query's top two results tied at 13 and then used
path ordering. These observations suggest limitations, not a proven cause of every
ranking choice or a justification to relabel after scoring.

## Next review, not an automatic fix

After seeing this result, the user asked for Codex's preference. Codex recommends
retaining the original direct-implementation target for these narrow cases and
treating documentation as useful supporting evidence rather than primary-hit credit.
This is a recommendation, not human review or a new label inventory. Questions,
labels, and ranking remain unchanged. Any expanded label inventory needs its own version and
declared scope; do not silently count these failed draft-label hits as successes.
Preserve this run if questions, labels, or ranking change. All exposed/tuned cases
remain development-only. The formal ten-question set remains deferred.

If implementation remains the target, test a documented ranking change only after
the label rule is agreed, using the same fixed inputs and exposing trade-offs. If
documentation also counts, review and label those chunks before rescoring rather
than claiming that schema-valid source references establish relevance. No ranking
change or formal model comparison is included in this commit.
