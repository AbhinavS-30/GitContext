# GitContext: Phases 1–2 walkthrough

Current as of November 16, 2026. Phases 1–2 implement local source preparation and
snapshot management. Search, embeddings, and answer generation are not implemented.

## What the application does today

A developer supplies a local directory. GitContext selects Python and Markdown,
reads bounded source without executing it, splits it into exact source ranges,
identifies those ranges, and saves a validated snapshot. Later commands inspect
the saved evidence or compare it with the current repository. Refresh is explicit.

```text
CLI → discovery → bounded reading + file hashes → Python/Markdown chunking
    → chunk IDs → manifest + Git observation → validated snapshot file

status → load/validate saved snapshot → discover/read current supported source
       → compare paths + hashes + configuration → current / stale / unknown
```

## 1. Discovery: choosing paths

`discovery.py` selects .py/.md files and reports excluded or inaccessible entries.
It prunes known environments, Git internals, dependency/generated folders, model
directories, and credential-like names. Symlinks are skipped. Explicit allowlists
reduce exposure but do not detect every secret in otherwise allowed source.

Defaults: 10,000 examined entries, 1,000 selected files, 1,000,000 bytes per file,
and 20 directory levels. Access/limit failures make discovery partial; intentional
exclusions do not. Limited selection follows filesystem order, so subsets can
differ across machines. Final report records are sorted for readability.

## 2. Reading: obtaining exact text

`reading.py` opens each file relative to pinned directory descriptors, refusing
symlink components. Reading source as data avoids import side effects, missing
dependencies, service startup, or destructive top-level code in target modules.

The reader enforces byte limits again because files may have changed after discovery.
The default total budget is 10,000,000 bytes. One extra probe byte detects overflow;
oversized input is rejected rather than silently truncated. Rejected content still
consumes the total budget. It rejects non-regular files, invalid UTF-8, NUL content,
and commonly detectable changes during a read. Original newlines are preserved.
This is not a guarantee that the entire repository is read at one frozen moment.

Each accepted SourceFile contains path, exact text, byte size, and content_sha256.
SHA-256 fingerprints the already-read bytes. Same bytes mean the same file hash,
regardless of path; same-length edits can change the hash even when size cannot.

## 3. Chunking: searchable-sized source units

`chunking.py` uses ast.parse, which builds a structured representation without
execution. Top-level functions, async functions, and classes get their own ranges,
including decorators. Nested definitions and methods stay inside their parent.
Remaining module text, imports, comments, and blank gaps are retained too.

`markdown.py` splits ATX headings (# through ######), retaining preamble and all
source. Headings inside matching backtick/tilde fences remain code. An unclosed
fence produces a warning. This is a documented subset, not a full Markdown parser:
underlined headings and complex containers/HTML/indented-code state are not parsed.

Both policies cap chunks at 80 lines by default. Oversized ranges become flagged
fragments; they can split statements/examples and omit context. Line bounds are
not token bounds. Python syntax errors produce warnings plus labeled line-based
fallback chunks. Ordered chunks reconstruct each original file exactly, without
overlap. Empty files remain in the inventory even though they have no chunks.

## 4. Identity and the manifest

`identities.py` computes chunk-v1 references from canonical JSON: exact text, path,
file hash, line range, symbol/type, fragment flag, and chunking configuration.
Canonical means sorted keys, fixed separators, and UTF-8 encoding. Repeatable
serialization makes repeatable hashes. Moving identical code changes its chunk ID.
Because whole-file hashes are included, edits elsewhere in a file also invalidate
its chunk IDs. These are evidence-version references, not permanent function IDs.

`snapshots.py` composes the pipeline. SnapshotManifest records selected paths,
successful file records with hashes/sizes/chunk references, configuration, issues,
completeness flags, and Git context. Snapshot carries the manifest, exact identified
chunks, local root, and snapshot-v2 ID. Absolute root and diagnostic wording are
excluded from snapshot identity; issue paths/reasons and Git context are included.
Matching inventories/configuration can share IDs across local folders.

`partial` means source was missed. `degraded` means source was retained but chunking
reported limitations, such as syntax fallback. These are independent of freshness.

## 5. Git context

`git_metadata.py` observes the exact working-tree root, commit when resolvable,
and dirty state. Dirty includes staged/unstaged tracked changes and untracked,
non-ignored files, excluding unstaged changes within submodule worktrees. Unknown
is None, never an invented clean state. Non-Git source directories still work.

Fixed read-only Git commands avoid a shell, network, optional index writes, and
filesystem-monitor helper execution. Each command has a timeout and accepted-output
limit. Git context is observed after reading, not proof that read bytes match HEAD.
Hashes remain essential for uncommitted or Git-ignored source.

## 6. Persistence and freshness

`persistence.py` uses Pydantic for strict data shape validation, then checks IDs,
file hashes/sizes, line coverage, and chunk references. Saved files are bounded
to 64,000,000 bytes. Loading never executes saved content. Consistency checks do
not authenticate data or prove it matches current source.

Saving validates, writes a private temporary sibling, flushes/fsyncs, verifies by
loading, then atomically replaces the destination. A pre-replacement failure keeps
the prior snapshot intact. Trusted directories are required; locking and a complete
power-loss guarantee are not implemented. Abrupt termination can leave a temporary
sibling. Saved source must stay private and out of Git tracking.

`freshness.py` independently reads supported source and compares paths/hashes and
configuration. It does not reparse, call Git, or write. Results are current, stale,
or unknown. Partial observations take precedence over stale while retaining known
differences. Failed traversal does not invent deletions. Git-only changes and
expected excluded artifacts do not alone make supported source stale. Unchanged
fallback text can be current while still degraded. Freshness is an observation,
not a watcher or protection against subsequent edits.

## 7. CLI and actual execution

`cli.py` parses arguments with argparse, delegates, emits JSON, and returns exit
codes. `__main__.py` supports python -m gitcontext; pyproject.toml registers the
gitcontext console command. The fixed saved location is ROOT/.gitcontext/snapshot.json.

| Command | Behavior |
| --- | --- |
| index PATH | Initial build/save; refuses an existing snapshot |
| inspect PATH | Saved inventory; --chunk ID returns exact saved source |
| status PATH | Read-only freshness comparison |
| refresh PATH | Explicit full rebuild and safe replacement |

CLI builds refuse to publish partial results; old saved data remains available.
Degraded but complete builds retain visible warnings. Inspect always labels evidence
as saved and not freshness-checked. It cannot present an old snippet as verified current.

The installed-command test verified build → inspect → edit → stale → refresh →
current, exact chunk inspection, unknown after invalid UTF-8, and refusal of partial
refresh while preserving old saved bytes. Exit codes are 0 success/current,
1 operational error, 2 argument error, 3 stale, and 4 unknown/refused partial build.

## Validation and next phase

There are 172 passing software test cases at this checkpoint. Ruff checks code
style; GitHub Actions installs the package and runs checks on push/pull requests.
No formal retrieval dataset, retrieval score, or answer-quality result exists.
Codex authored the implementation; learner understanding is recorded separately
from code generation in STATUS.md.

Phase 3 adds a transparent lexical baseline: question → identifier-aware tokens →
ranked saved chunks with explainable match information and freshness enforcement.
Local embeddings/hybrid ranking and optional local answers follow in later phases.
