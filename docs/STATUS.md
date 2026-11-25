# Status

Updated: November 24, 2026. Phase 2 complete; Phase 3 in progress.

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

Aggregate summaries are published as 2eca04d. Codex added an evaluation CLI branch
and 12 integration tests. It requires supplied data and explicit split, emits
versioned detailed-run/summary JSON, and preserves execution-status exit codes.
It does not generate cases, save reports automatically, or refresh snapshots.

Evaluation CLI is published as 548076a with passing CI. At this session start,
the worktree was clean with no pending commit. Codex performed a development-only
identifier review on a temporary GitContext export of that commit and documented
it in docs/BASELINE_REVIEW.md. No app code, weights, questions, or labels changed.

Development review is published as dcfdb2b with passing CI. The user then explicitly
selected development-only cases and label review. Codex prepared three draft cases
and rationales in evaluation/development/, against a fixed source export of 548076a.
All are development/not_reviewed, authored by Codex; no human review is claimed.
No formal ten-question set, ranking change, or retrieval scoring was created.

## Verification and publication

- pytest: 310 passed (298 existing cases plus 12 evaluation CLI cases).
- Ruff lint and formatting: passed. Git diff whitespace check: passed.
- Actual temporary synthetic execution: two cases attempted, one current and one
  stale, one eligible for scoring. Both observations remained visible; blocked
  ranking-time population was empty. No formal data or report was retained.
- Tests distinguish macro from pooled recall using unequal label counts; retain
  citation failures after errors; handle zero eligible/checked populations without
  invented scores; separate timings; and reject missing/duplicate/inconsistent rows.
- Actual installed evaluate command with temporary synthetic input emitted a
  current report/exit 0, then stale/exit 3 and unknown/exit 4 after source changes.
  Saved snapshot bytes remained unchanged. No data/report was retained.
- Tests cover versioned serialization, explicit split/no other-split case leakage,
  no-hit success, setup mismatch, per-case error reports, arguments, symlink input,
  blocked populations, and preservation of input/snapshot bytes.
- Actual fixed-export CLI review: 43 supported files, 588 chunks, complete and
  not degraded; current freshness for three identifier diagnostics. Named function
  chunk positions were 4 (save_snapshot), 6 (check_freshness), and 7 (rank_chunks).
  These are mechanical observations, not relevance labels or benchmark scores.
- The source export had no Git metadata; source commit provenance is documented
  separately. Temporary source and saved snapshot were removed. No raw index/data
  enters Git. Runtime/configuration and limitations are in the review document.
- Development draft: strict loader accepted three cases and four unique chunk
  references against snapshot-v2:50bf1719…; all review statuses remain not_reviewed.
  Source freshness is current. Code was read as data; no queries/evaluation ran.
- The persistent private export is nested in the worktree, so Git observation is
  root_is_subdirectory, not the earlier temporary export's repository_unresolved.
  The source commit/chunk IDs match; differing snapshot provenance is documented.
- The learner explicitly requested publishing the development drafts. This status
  accompanies draft-v1 publication; no human review or evaluation result is implied.
  Strict input/membership/freshness and whitespace checks passed. Source/index
  artifacts remain ignored; the existing software baseline is 310 passing tests.

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

The learner requested progression/publication after the zero-denominator question.
Codex explained that zero eligible cases means undefined metrics, then implemented
CLI evaluation and synthetic tests. Independent reasoning about this remains
unverified. No formal question set or independent human labels were created.

The learner asked to progress after the execution-versus-quality question. Codex
explained that exit 0 does not certify retrieval quality. Codex reviewed baseline
behavior without changing ranking. Independent relevance review has not occurred.

The user selected development-only cases and label review. That authorizes draft
preparation, not a claim that a human reviewed their relevance. Codex chose narrow
mechanism questions and implementation evidence; one whole-function case has two
fragments. Independent relevance/completeness review is pending.

Next: review the first case's question and proposed save_snapshot evidence with
the learner, then the other two cases. Discuss whether direct implementation is
sufficient or documents/helpers should count under the intended task. Record actual
feedback and version label changes. Do not score before review or silently promote
draft labels to human_reviewed. The formal ten-question set remains deferred.

No formal dataset, reviewed relevance dataset, benchmark quality result, representative latency
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

CLI reports include private source/questions/provenance and local paths. They are
printed only, not saved automatically. Exit status reports execution conditions,
not a quality threshold. Per-case errors keep reports; invalid setup/input fails
before a run. Error > unknown > stale > current determines the non-argument exit.
