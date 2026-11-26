# Status

Updated: November 25, 2026. Phase 2 complete; Phase 3 in progress.

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
Draft-v1 was published as 0198fd1. Draft-v2 records Codex source review only;
question and reference labels are unchanged, and no human review is claimed.
A provisional top-five diagnostic is now documented with full limitations. No
formal ten-question set or ranking/source change was created.

## Verification and publication

The development drafts and provisional results are published as 0198fd1/16b1826
with passing CI (310 tests). The fixed BM25 specification was published as 01e54a7
before implementation/results. Codex implemented an opt-in BM25 ranker and CLI
selection, with method/parameter provenance in evaluation runs and summaries.
Overlap remains default; no dependencies, models, snapshot schema, or labels changed.

Current local checks: 337 tests passed, Ruff lint/format and whitespace checks passed.
The controlled installed-CLI comparison used the unchanged draft-v2 input and fixed
source: both modes had 0/3 top-five hits and macro recall 0. All cases were current;
all 15 references per mode matched saved metadata. Overlap exactly reproduced the
original matches, scores, terms, and source metadata. These are three exposed
Codex-reviewed cases, not independent relevance validation. See
 evaluation/development/BM25_COMPARISON.md. Implementation/results publication is
pending the current commit/push; its hash is available in Git history afterward.

Earlier verification:

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
- Development input: three cases/four unique references passed exact snapshot,
  membership, and freshness checks. Codex reviewed the narrow source mechanisms;
  metadata changed to draft-v2/codex_reviewed before scoring, not human_reviewed.
- Provisional top-five run: attempted/current/eligible=3, no stale/unknown/error;
  zero draft-labeled implementation hits and macro recall 0. All 15 returned
  references matched saved metadata; documentation occupied every top-five slot.
  These are conditional development diagnostics, not general or independent quality.
- Exact input was unchanged after the run and matches the raw report's dataset.
  The raw report remains private/ignored; a qualified summary/rationale is public.
- The persistent private export is nested in the worktree, so Git observation is
  root_is_subdirectory, not the earlier temporary export's repository_unresolved.
  The source commit/chunk IDs match; differing snapshot provenance is documented.
- The learner requested publication/progression. Draft-v1 was pushed as 0198fd1;
  this status accompanies draft-v2 review metadata and the provisional results note.
  Source/index/raw-report artifacts remain ignored. App code is unchanged; schema,
  source checks, actual evaluate execution, and whitespace checks were run. The
  software baseline remains 310 tests; session handoff records push/CI results.

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

The learner requested publication/progression without giving label judgments.
Codex explained the first case's narrow workflow scope, reviewed all three proposed
source mechanisms, and recorded Codex review only. The first diagnostic was preserved
without post-result label/ranking changes. When asked for a relevance preference,
the user asked Codex's preference; Codex recommended retaining implementation as
primary for these cases, with docs as support. This is not human relevance review.

Codex explained rarity, saturation, and length normalization. The user requested
progression/publication; independent understanding was not demonstrated. The fixed
candidate was implemented without tuning after observing results. Larger BM25
weights than overlap counts do not imply better retrieval: the scales differ.

Next: review why weighting alone did not find the implementation targets and clarify
query/evidence vocabulary before another agreed experiment. Keep questions/labels
fixed and preserve the negative result. Human label/scope review remains pending;
the formal set stays deferred. Phase 3 continues; Phase 2 is already complete.

No formal dataset, human-reviewed relevance dataset, general benchmark quality result, representative latency
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
