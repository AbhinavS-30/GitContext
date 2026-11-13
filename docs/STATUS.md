# Status

Updated: November 13, 2026. Phase 2 of five core phases: chunking and index snapshots.

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

## Checks and actual execution

- pytest: 159 passed (136 existing cases plus 23 freshness cases).
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
- The learner explicitly requested committing/pushing freshness after the
  walkthrough. This status accompanies that commit; the session handoff records
  its identifier, push result, and remote CI outcome.

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

## Limitations and next small task

The freshness walkthrough is complete. Next: explain a minimal CLI for explicit
index/rebuild, status, and inspection, including exit codes and failure reporting.
Ask one understanding question and wait before implementation. Lexical retrieval
follows as milestone 3. The learner requested an explicit Phase 2 completion
announcement. Phase 2 remains in progress until the CLI can build, inspect, check,
and explicitly refresh snapshots, with tests and an actual end-to-end run verified.

No CLI, automatic query-time freshness enforcement, retrieval, embeddings,
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
