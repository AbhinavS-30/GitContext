# Development draft for label review — not a benchmark

The user selected development-only cases and label review on November 24, 2026.
`gitcontext-548076a.draft.json` contains three Codex-authored draft cases, all in the
development split. Every case is not_reviewed with reviewer=null. No independent
human review, held-out status, retrieval score, or quality claim is implied.

The formal ten-question evaluation set remains deferred. No evaluation run or
result artifact is included. Do not report draft-label metrics as measured quality.

## Source provenance and label scope

Source is a tracked-file export of GitContext commit
`548076ad03eb936c61b8d7540feb65d5da8f60e2`, read as data without installing or
executing its application/tests. Runtime is Python 3.12.13 with default discovery,
reading, and 80-line chunking settings. The private source and snapshot live under
ignored `.gitcontext/development-548076a/source/` in this workspace.

Snapshot ID:
`snapshot-v2:50bf1719bb31faf1467fe9194c86b0111a5b13ddf2c92178f125a7bc3dcd9032`.
It contains 43 files and 588 chunks, complete and not degraded. The export has no
own Git repository; ancestor rejection is recorded as not_repository with issue
root_is_subdirectory. The original commit is external export provenance, not a
fabricated indexed commit. Recreating under a different Git context may change the
snapshot ID even when source chunks stay identical. Validate, never rewrite IDs
silently. Recreate privately and revalidate if runtime/configuration changes.

The earlier BASELINE_REVIEW used an export outside the worktree, with a different
Git observation/snapshot ID. Its labels cannot simply be assumed compatible; these
draft references were selected and validated against the current private snapshot.

These labels deliberately target direct implementation for narrow mechanisms,
not every useful document, import, call site, or test. For questions about an entire
named function, include its fragments to preserve complete evidence. For a narrow
branch question, include the fragment containing that branch. This is a proposed
rule for review, not a claim that relevance is objective or exhaustively labeled.
Recall against these labels would measure only this declared scope.

## The three proposals

| Case | Question | Proposed direct evidence | Reason |
| --- | --- | --- | --- |
| dev-atomic-save | Where does GitContext write a snapshot to a temporary file, verify it, and atomically replace the saved snapshot? | src/gitcontext/persistence.py:138–161, save_snapshot | It creates the temporary sibling, writes/flushes/fsyncs, loads it for verification, then calls os.replace; cleanup is in finally. |
| dev-freshness-states | How does GitContext decide whether a saved snapshot is current, stale, or unknown? | src/gitcontext/freshness.py:29–108 and 109–115, check_freshness | The first fragment contains comparison/status logic; the second completes the returned report. Both are proposed for the whole-function question. |
| dev-search-freshness-gate | What prevents CLI search from returning ranked snippets when source freshness is stale or unknown? | src/gitcontext/cli.py:177–233, main fragment | It checks freshness, returns an empty matches list and exit 3/4 on failure, and only calls rank_chunks after the gate passes. |

Paths/lines refer to the fixed exported commit, not later HEAD. The JSON stores
exact chunk IDs and no source text or absolute local filesystem paths. It passed
strict input validation, snapshot matching, and reference membership checks. The
private source remained current during preparation. This does not establish that
the questions or labels are good; that is the purpose of review.

## Review before scoring

For each case, check the intended developer task, read the proposed source, and
decide whether necessary evidence is missing or irrelevant evidence is included.
Discuss whether explanatory documentation should also count under a different
label rule. Keep all these cases development-only after inspection/tuning.

Do not change review_status to human_reviewed merely because the file was opened,
the schema validated, or the learner selected development-only work. Record actual
review scope and reviewer only after explicit feedback; otherwise leave not_reviewed.
If labels change, increment dataset_version and document why. If source/config
changes, rebuild/bind against the correct snapshot and revalidate labels.

All three cases are supported, so this draft cannot evaluate unsupported behavior,
broad question coverage, unseen-code generalization, or production retrieval quality.
No ranking weights, filters, rerankers, or models were changed to favor these cases.
