# Status

Updated: November 17, 2026. Phase 2 complete and published as 88acbb9 with passing CI.
Phase 3 of five core phases is in progress: lexical CLI search.

## Current implementation

Bounded discovery, bounded UTF-8 reading, file hashes, exact Python/Markdown chunks,
deterministic chunk IDs, and in-memory snapshot manifests are implemented.
Snapshot orchestration is published as `d2832ca`; Git metadata as `2fbb80e`.
Both were pushed with GitHub Actions passing.
Earlier steps and their publication records are available in Git history.

Codex added read-only Git inspection in `git_metadata.py`, 15 test cases, and
snapshot-v2 integration. It records available/not_repository/unavailable status,
commit, tri-state dirty, and issue codes. It does not import or run target source,
write to the Git index, invoke repository helpers, or access remotes. Git context
is observed after reading, not a guarantee that source matches HEAD. Documentation
and decisions describe dirty scope, subprocess bounds, and platform limitations.

Codex implemented validated JSON saving/loading in persistence.py and 17 tests.
Pydantic 2.12.4 validates strict data structure; semantic checks verify IDs, exact
file reconstruction, hashes/sizes, and line ranges/references. Saving uses a private
verified sibling and atomic replacement. snapshot_id was extracted for shared use.
Partial/degraded flags survive roundtrips. Persistence is published as ccd7d3f,
pushed with GitHub Actions passing.

Codex implemented freshness.py and 23 additional tests. Explicit comparison reads
supported scope/content again, compares configuration, and returns current/stale/
unknown with change lists, issues, and limitations. It does not call Git, reparse,
write, refresh, or clear saved degraded/partial flags. No dependencies were added.

Freshness is published as 22485dd, pushed with GitHub Actions passing.
Codex implemented the CLI (index/inspect/status/refresh), console/module entrypoints,
13 tests, and a CI console-command smoke check. Partial CLI builds are not saved;
complete degraded builds retain visible warnings. Status is read-only. Inspection
labels evidence as saved and not freshness-checked. No new dependencies were added.

Codex implemented tokenization.py and 17 tests for code-words-v1. It preserves
case-folded full identifiers and underscore/ASCII camel/acronym parts, handles
prose/error strings, and preserves occurrence counts without duplicate expansions.
No dependencies, ranking, persisted lexical index, or CLI search were added.

Tokenization is published as 668a8e6, pushed with GitHub Actions passing.
Codex implemented lexical.py and 18 test cases: unique-term match count, repeated
term behavior, full identifier matching, deterministic ties, limits, no-hit behavior,
and Python/Markdown snapshot integration. Reports retain source metadata and label
saved evidence as not freshness-checked. No dependencies or CLI search were added.

## Checks and actual execution

- pytest: 207 passed (189 existing cases plus 18 ranking cases).
- Ruff lint and formatting: passed. Git diff whitespace check: passed.
- Actual GitContext inspection: available, commit d2832ca…, dirty=True with local
  implementation edits. Snapshot-v2 recorded that context; partial=False and
  degraded=False. These are source flags, independent of Git availability.
- Tests include clean/modified/staged/deleted/untracked/ignored files, unborn and
  non-Git folders, ancestor rejection, inherited environment overrides, missing
  Git, timeouts, excessive output, status failure, index immutability, and a
  configured filesystem-monitor helper that must not execute.
- Actual persistence fixture: initial snapshot roundtripped exactly; simulated
  replacement failure preserved the old snapshot; a successful retry replaced it.
- Tests also interrupt a write halfway through and verify old bytes survive, plus
  fsync/verification failures, malformed JSON, wrong schema/IDs/types, broken
  references, content inconsistencies, size limits, and symlink refusal.
- Actual freshness fixture after save/load: unchanged=current, same-size True→None
  edit=stale with app.py modified, invalid UTF-8=unknown. Saved file stayed unchanged.
- Editable installation registered the gitcontext command successfully.
- Actual installed-command run in a temporary repository: index=0, inspect=0,
  exact chunk inspect=0, initial status=current/0, same-size edit status=stale/3,
  refresh=0, status=current/0. Invalid UTF-8 then produced unknown/4 and refresh=4;
  the valid saved snapshot remained byte-for-byte unchanged.
- Actual tokenizer run: save_reviewed_record produced the full identifier plus
  save/reviewed/record; ReviewedRecord produced reviewedrecord/reviewed/record;
  parseHTTPResponse produced parsehttpresponse/parse/http/response.
- Actual ranker run from a saved/loaded fixture: query save record ranked b.py's
  function above a.py's repeated-save comment, with scores 2 and 1 and exact matched
  terms. An unmatched query returned zero results. The report retained the explicit
  saved_snapshot_not_freshness_checked label.
- The learner explicitly requested publication after the ranking walkthrough.
  This status accompanies the ranking commit; Git history records its identifier.
- All recorded Phase 2 exit checks passed locally; Phase 2 implementation is complete.


## Learning record

The learner correctly recognized: text reads do not execute code; scan limits
require partial reporting; reading must enforce limits again; equal sizes can hide
edits; identical bytes share a hash; decorators belong with functions; syntax-error
source should remain with a fallback warning; and commit IDs alone cannot describe
indexed uncommitted edits. The learner correctly answered that a failed Git status
inspection requires dirty=None, not False. Codex implemented all components and
tests so far. The learner initially thought a failed refresh should remove the
old snapshot. After correction, the learner correctly identified changed source
as stale; the preserve-old-file reasoning was explained but not independently
restated. Codex implemented persistence and tests. The learner correctly identified
unreadable source as freshness unknown, then agreed to proceed. Codex implemented
freshness comparison and tests. Codex explained that Git context changes alone
do not make identical supported source/configuration stale; independent reasoning
on this distinction remains unverified.

Explanations were provided, but independent reasoning remains unverified, for:
expected exclusions versus missed source, strict decoding versus silent repair,
fragment context, fenced-code headings, path/configuration-sensitive chunk IDs,
and the distinction between a run inventory and an atomic repository snapshot.
The learner has not yet independently written implementation code.

After the detailed system walkthrough, the learner requested progression.
Codex explained retaining normalized exact identifiers alongside split terms;
independent reasoning about that trade-off remains unverified. Codex implemented
the tokenizer and tests. No formal evaluation questions were invented.

The learner requested progression after the coverage-versus-repetition question.
Codex explained that matching both save and record outranks repeating save. The
learner has not independently reasoned about this policy yet. Codex wrote ranking
and tests; these are development examples, not an evaluation question set.

## Limitations and next small task

The learner asked for the status/refresh answer and requested moving forward.
Codex explained that status should report and wait for explicit refresh. Independent
reasoning about that interface choice remains unverified. Codex wrote CLI and tests.

Phase 2 completion is published; docs/WALKTHROUGH.md records the detailed review.
Next: walk through rank_chunks, the term-set intersection and count, deterministic
sort, and the actual result. Ask what a score of 2 establishes (two distinct term
matches, not correctness). Wait before implementing freshness-enforced CLI search.
The learner answered that a score does not prove correctness, then requested
publication and progression. Next is freshness-enforced CLI search; stale/unknown
results must be blocked rather than shown as current source. Codex explained this
policy; independent reasoning about it remains unverified.

No automatic query-time freshness enforcement, CLI search, embeddings,
model inference, API, or formal evaluation dataset exists. Tests are not evidence
of retrieval quality. Reading/Git inspection target macOS/Linux. Discovery cannot
promise secret detection; limited traversal can select different subsets. Python
methods remain inside class chunks; Markdown handles a documented ATX/fence subset.
Line bounds do not bound model tokens; fragments can omit important context.

Git dirty is repository-wide, excluding ignored files and unstaged changes within
submodule worktrees. Source hashes remain authoritative for bytes read. Metadata
failure never means clean. Git stdout is temporarily spooled, capped on acceptance
at 64 KiB, with a five-second command timeout; temporary spool bytes are not capped.
No whole-repository atomicity is guaranteed. Git metadata contributes to snapshot-v2
IDs while chunk IDs remain source/configuration based.

Python 3.12.13 is available. Ollama was installed but not running at initial
inspection; llama3.2:3b had a manifest. Inference and embeddings remain unverified.

Persistence uses a trusted pre-existing local directory and a 64 MB serialized
file bound. No concurrent writer lock, directory-fsync power-loss guarantee, or
snapshot authentication is implemented. Abrupt termination can leave a temporary
sibling. Keep saved source snapshots in ignored .gitcontext or another private
location. Loading does not read target source and cannot certify freshness. The explicit
freshness check does read target source, but cannot freeze concurrent edits or
certify a saved partial inventory as current. Unknown takes precedence over known
changes while retaining those changes in the report. Removals need full discovery;
unchanged degraded snapshots retain their quality limitation.

Tokenizer v1 handles ASCII camel boundaries and retains Unicode words but does not
segment all languages, infer synonyms, stem, or remove stopwords. Its version is
available for future retrieval configuration; no persisted lexical data exists yet.

The pure ranker has no I/O, semantic understanding, stopword removal, or length/
frequency weighting. Long/common-word-heavy chunks can rank poorly. It retokenizes
all input chunks each call and assumes prepared/validated evidence; CLI search must
check snapshot integrity/completeness and current source before exposing results.
