# Status

Updated: November 23, 2026. Phase 2 complete; Phase 3 in progress.

## Current implementation

Local Python/Markdown discovery and bounded reading, exact source chunks and
hashes/IDs, Git observation, validated atomic JSON snapshots, freshness comparison,
and a lexical CLI search baseline are implemented. Search blocks stale/unknown
source and never auto-refreshes. The CLI snapshot lifecycle completed Phase 2.

Published evaluation preparation: bd02cec (contract/metrics), 2583c12 (strict input
validation), and 478369a (bounded loader/runner). All passed CI when published.
The runner validates supplied snapshot-bound labels, explicitly selects a split,
checks source per case, validates references, and preserves failures/timing/provenance.
Earlier implementation/publication details remain in Git history and the walkthrough.

Codex implemented evaluation_summary.py and 17 additional tests. It requires exact
case coverage and consistent per-case metrics, keeps all status/label populations,
exposes hit/recall eligibility, and reports observation-level citation validity and
outcome-specific timing. No dependencies or formal evaluation cases were added.

## Verification and publication

- pytest: 298 passed (281 existing cases plus 17 summary cases).
- Ruff lint and formatting: passed. Git diff whitespace check: passed.
- Actual temporary synthetic execution: two cases attempted, one current and one
  stale, one eligible for scoring. Both observations remained visible; blocked
  ranking-time population was empty. No formal data or report was retained.
- Tests distinguish macro from pooled recall using unequal label counts; retain
  citation failures after errors; handle zero eligible/checked populations without
  invented scores; separate timings; and reject missing/duplicate/inconsistent rows.
- The learner explicitly requested publication and progression. This status
  accompanies the aggregate-summary commit; Git history records its identifier.

## Learning record

The learner correctly identified: text reads do not execute code; limits can make
scans partial and must be rechecked during reads; same-size edits need content
hashes; identical bytes share hashes; decorators belong with functions; syntax-error
source should be retained with warnings; Git commits do not capture uncommitted
edits; unknown dirty/freshness must not be called clean/current; overlap scores do
not prove answer correctness. Codex authored all implementation and tests so far.

Explanations were supplied, but independent reasoning remains unverified for:
expected exclusions versus missing source, strict decoding versus repair, fragment
context, Markdown fence handling, path/configuration-sensitive IDs, atomicity versus
run inventories, preservation after failed refresh, explicit refresh versus checking,
label provenance and held-out independence, and aggregate denominator choices.
The learner requested progression rather than answering several follow-ups. This
is not evidence of independently implementing or fully explaining those components.

For the current step, Codex explained that a blocked case stays in attempted count
but receives no hit/recall score. The learner has not independently restated that
reasoning. Synthetic executions and Codex review are not independent human validation.

## Next small task and limitations

Walk through summarize_run, eligible versus attempted counts, macro recall, and
outcome-specific timing/citation populations. Ask why a zero-eligible report cannot
honestly claim 100% hit rate. Wait before the next component. Commit/push summaries
at the learner's request. Codex explained that zero eligible cases means undefined
metrics. Next: add an explicit evaluation CLI/report
boundary; formal question/label creation still requires separate agreement.

No formal dataset, benchmark quality result, evaluation CLI, representative latency
measurement, embeddings, hybrid ranking, model inference, or API exists. Unit tests
verify software behavior, not retrieval quality. Aggregate numbers on synthetic
fixtures must never be promoted into benchmark results.

Freshness is an observation, not a repository-wide atomic snapshot or watcher.
Source/CLI inspection does not guarantee secret detection. Python methods stay
inside class chunks; Markdown supports a documented subset; line limits are not
token limits. Snapshot storage uses trusted directories, no writer lock, and no
complete power-loss guarantee. Preserve saved source privately and outside Git.
Git dirty has documented ignored/submodule limits and is not source freshness.

Evaluation inputs are bounded at 1 MB/1,000 cases. Review/split declarations do not
verify human participation or independent held-out data. Runner totals include
per-case snapshot reload/freshness/reference checks, not process startup or report
serialization; shared setup is separate. Summaries preserve these boundaries and
assume runner-produced data. No references means no citation-validity credit.

Python 3.12.13 is available; Ollama/model state was last inspected at project setup
and must be rechecked before any local-model selection or download.
