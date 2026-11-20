# Decisions

## 2026-11-09: independent, minimal project

Use a standalone Git repository, local Python 3.12 environment, and `src/` package
layout. Keeping importable code under `src/` helps expose installation mistakes
that can be hidden when imports resolve directly from the repository root.

Use setuptools as the build backend and Ruff for linting and formatting. Pin both
in project configuration. Use pytest for behavioral tests, and add Pydantic when
explicit data contracts are introduced, and HTTPX when local inference needs HTTP.
No application dependencies or orchestration framework are needed for setup.

Keep indexing separate from querying. Deliver useful search before generation.
Measure retrieval rather than assuming embeddings or hybrid ranking improve it.

Document capabilities as implemented. Do not create placeholder application
features, artificial benchmark questions, or tests that only assert placeholders.

## 2026-11-09: bounded path discovery

Use standard-library frozen dataclasses for small internal contracts: limits,
selected paths/sizes, issues, and the aggregate report. Dataclasses hold named
fields; frozen ones prevent field reassignment. They do not provide Pydantic's
runtime schema validation. Limits explicitly validate positive integers.

Select Python and Markdown, prune explicit excluded directories, and skip symlinks.
Reject a symlink root and resolve the root to an absolute path. Check child path
containment. Git metadata belongs to a later component.

Stream directory traversal rather than collecting and sorting an unbounded directory
first. Sort final records for presentation. Limited subsets therefore depend on
filesystem order. Distinguish expected exclusions from incomplete discovery caused
by limits or access errors. Discovery never reads source content.

This does not guarantee secret detection or safety against concurrent path
replacement. Future reading must validate paths again and bound actual reads.

## 2026-11-09: bounded source reading

Read source as unbuffered bytes before strict UTF-8 decoding, preserving newlines.
Use the discovery per-file limit and a separate 10 MB default total-read budget.
Allow one probe byte beyond a cap to distinguish an exact fit from oversized input.
Count rejected content against the total budget. Reject oversized input rather than
returning truncated text that could later look like complete evidence.

Use POSIX directory-relative open operations with no-follow flags on each path
component. This avoids following a file or intermediate directory replaced by a
symlink after discovery. Nonblocking open prevents a replaced FIFO from hanging
before its file type can be checked. Reject non-regular descriptors. Pin the root
descriptor for the batch and close descriptors through context managers/finally.
Windows support is deferred. An atomic snapshot of the whole tree is not promised.

Reject invalid UTF-8 and NUL-containing text explicitly. Do not guess encodings;
non-UTF-8 Python source is currently unsupported even if Python could interpret its
encoding declaration. Compare size and modification/change times around each read;
this detects common concurrent edits but cannot guarantee an immutable snapshot.
Reuse the small issue record from discovery for now; no new dependencies are needed.

## 2026-11-09: exact-byte source fingerprints

Attach `content_sha256` to each accepted source record using standard-library
`hashlib.sha256(raw).hexdigest()`. Hash the already-read bytes rather than reopening
the file, so text and fingerprint refer to the same read. Keep line endings intact.
The field name identifies the algorithm; the digest is a 64-character hexadecimal
string. Identical bytes at different paths have identical content hashes: this is
not a path identity or repository snapshot identifier.

This step adds metadata only. Persistence, current-versus-indexed comparisons,
Git metadata, and snapshot identifiers remain separate later components. A content
hash detects byte differences in practice; it is not a secret detector or evidence
that source behavior is correct.

## 2026-11-10: first Python chunking policy

Use built-in AST parsing to identify only direct module-level functions, async
functions, and classes. Start at the first decorator and end at AST end_lineno.
Keep methods and nested definitions in the enclosing definition to avoid overlapping
source chunks. Definitions inside module control flow remain module source. This
sacrifices method-level retrieval granularity for an inspectable first policy.

Preserve all intervening source as module chunks, including whitespace-only gaps.
Slice original lines rather than AST-unparsing, which would change formatting and
comments. Use universal-newline recognition that preserves newline bytes and does
not mistake form feeds for new Python lines. Ranges are one-based and inclusive.

Split ranges over 80 lines into non-overlapping fragments retaining parent symbol
metadata. Fragments may split statements; explicitly flag every fragment. A line
bound is not a token or character bound. Later model input needs its own budget.

Parsing failures produce reported issues plus exact line-based fallback chunks.
Do not claim symbols for fallback text. Empty source yields no chunks. Reports
record policy version python-top-level-v1 and max_lines for later manifests.
No chunk IDs, snapshot IDs, Git metadata, or persistence are added in this step.

## 2026-11-10: explicit Markdown heading subset

Reuse SourceChunk and ChunkingReport; add markdown_section and markdown_preamble
kinds and keep section titles in symbol_name. This avoids a second result shape
before retrieval. Names are metadata, not unique IDs. Start a new section at any
ATX heading level; preserve preamble and exact line coverage without duplication.

Use a small state machine for backtick/tilde fenced blocks so heading-like code
does not create sections. Match fence character/length and require a plain closer.
Report unclosed fences and preserve the remaining text. Apply the same 80-line
fragmentation policy as Python, including explicit fragment metadata.

Do not add a Markdown dependency yet. Document the narrow subset: setext headings,
HTML blocks, indented-code state, and nested list/blockquote containers are not
parsed. Do not claim CommonMark compliance. Improve this policy from observed
retrieval failures rather than silently claiming all heading boundaries are correct.

## 2026-11-11: deterministic chunk references

Keep identity computation separate from source chunking. `chunk_id` accepts one
SourceChunk plus policy_version and max_lines from its report; it returns a
version-prefixed SHA-256 reference without mutating the chunk. Include all chunk
fields and configuration in canonical JSON (sorted keys, compact separators,
UTF-8). Do not use Python's process-dependent built-in hash or random UUIDs.

Include exact chunk text as well as the file hash so even inconsistent caller data
gets a distinct reference; this does not validate that caller data is truthful.
The entire file hash deliberately makes all its chunk IDs change after any file
edit. Prefer that conservative version binding over tracking symbols across edits.
IDs are scoped to an index, not globally unique repository identities. Collection
snapshot context and persistence remain later work. No dependencies are added.

## 2026-11-12: in-memory snapshot manifest

Compose the existing functions in build_snapshot rather than requiring callers to
assemble unrelated reports. Separate the manifest (inventory/configuration) from
identified source chunks. Keep selected paths and successful files distinct so
unreadable files do not disappear from the record. Include empty files even though
they have no chunks. Store exact chunk references in each file record.

Record discovery limits, total-read budget, line limit, allowlists/exclusions,
versioned policies, chunk ID version, and Python parser runtime. Hard-coded policy
changes must bump their policy version. No embeddings exist, so no embedding
configuration is invented. Git metadata and disk persistence are separate steps.

Hash the canonical manifest with sorted files, selected paths, and issue reasons.
Retain diagnostic details for inspection but exclude their wording and the absolute
root from identity to avoid machine-dependent IDs. IDs are collection identities
within this tool's scope; identical inventories/configuration can match across roots.
Expected skipped files are part of the reported inventory, so changes to excluded
entries can change this ID; it is not yet a relevant-scope freshness comparison.

Use partial for missed discovery/read content and degraded for chunker warnings
with retained source. Full rebuild orchestration remains in memory. No atomic
repository snapshot or persistent completion guarantee is claimed.

## 2026-11-13: read-only Git observation

Record GitMetadata in the manifest after source processing: inspection status,
resolved commit when available, tri-state dirty, and explicit issue code. Bump the
snapshot schema/ID prefix to snapshot-v2 and include Git context in its identity.
Chunk IDs are unaffected. Source flags do not claim Git inspection success.

Use fixed subprocess argument lists without a shell or network. Clear inherited
GIT_* settings, avoid global/system config, disable local fsmonitor helpers and
optional index locking, and use timeouts. Spool stdout to avoid unbounded memory,
then reject outputs over 64 KiB; spool storage during the five-second timeout is
not byte-capped. No repository helpers or hooks should run. Tests verify that a
configured fsmonitor helper is not invoked and index bytes stay unchanged.

Require the exact working-tree root, not an ancestor. Non-Git folders remain valid
source targets. Dirty considers tracked and untracked non-ignored files, but not
unstaged submodule-worktree changes. An unresolved HEAD (including unborn repos)
is explicit; unknown dirty is None. Git state is observed once, not evidence that
all files match a commit or stayed unchanged across indexing. Keep file hashes.

## 2026-11-13: validated JSON persistence

Add pinned Pydantic 2.12.4 to validate strict nested dataclass JSON through a
TypeAdapter. Keep existing internal dataclasses. Compare the input JSON shape to
its validated serialization to reject unknown/omitted fields that dataclass
adapters would otherwise ignore/default. Validate semantic consistency separately:
IDs, references, reconstructed file hashes/sizes, and contiguous line ranges.
Extract snapshot_id(manifest) so builder and loader use one identity algorithm.

Use one bounded JSON file (64 MB serialized), not pickle or multiple coordinated
files. Validate before writing, create a private sibling, flush/fsync, load-verify,
and os.replace. Preserve the old destination on pre-replacement failures. Record
partial/degraded state without silently promoting it to complete. Keep generated
data local and ignored. This is a saved source snapshot, not yet a search index.

Destination directories are trusted; this component does not implement concurrent
writer locking, directory-fsync power-loss guarantees, authentication, or automatic
freshness checking. A killed process may leave an unpublished temporary sibling.

## 2026-11-13: explicit source freshness comparison

Discover/read/hash again without rebuilding chunks, inspecting Git, or saving.
Compare supported selected paths, read content hashes, and processing configuration
against the saved snapshot. Reuse saved limits unless explicitly overridden, but
construct current policy/runtime configuration so drift is visible.

Use current/stale/unknown. Unknown takes precedence if either source inventory is
partial or inspection cannot establish scope. Retain observed changes alongside
unknown, and never infer removal from incomplete discovery. Removed refers to
supported scope, not necessarily filesystem deletion. Expected skipped artifacts
and Git observation changes alone do not determine source freshness.

Keep degraded separate: unchanged fallback text can be current without being
structurally parsed. Partial snapshots require an explicit rebuild to establish a
complete baseline. Require an explicit root matching saved location; do not silently
read a different folder. Freshness remains a non-atomic observation, not a watcher.

## 2026-11-16: thin snapshot CLI and Phase 2 exit

Use standard-library argparse, a console script, and python -m gitcontext. Delegate
to existing functions instead of duplicating pipeline logic. Emit JSON and stable
exit codes: 0 success/current, 1 operational error, 2 arguments, 3 stale, 4 unknown
or partial rebuild refused. Add index/inspect/status/refresh, not search or an API.

Use a fixed .gitcontext/snapshot.json under the explicit repository root, rejecting
root/storage symlinks. Index refuses an existing file; refresh loads its configuration
and performs a full rebuild, preserving saved limits unless explicitly overridden.
Do not publish partial CLI builds; report their issues and keep the previous saved
snapshot. A complete degraded build can be saved if its warnings remain visible.
Status never writes. Inspect labels chunks as saved evidence without asserting
freshness. Target Git tracking remains the user's responsibility; do not edit it.

Local tests and installed-command execution passed the Phase 2 exit sequence,
including chunk inspection, stale/unknown status, explicit refresh, and preservation
after partial refresh. Phase 2 implementation is complete locally; lexical retrieval
is next, with no claims yet about retrieval or answer quality.

## 2026-11-16: identifier-aware lexical tokenizer

Use a shared, standard-library tokenizer for both questions and source. Keep
case-folded full identifiers plus underscore/ASCII camel and acronym parts. This
preserves normalized exact-name matches without requiring a question to contain
source underscores. Retain numeric tokens and Unicode words, but document that
Unicode camel segmentation and language-specific boundaries are not implemented.

Preserve occurrence counts across text; deduplicate expansions within an occurrence
so plain words do not get artificial double frequency. Empty/punctuation-only
input yields no tokens. Do not remove stopwords, stem, or infer synonyms in v1.
Record TOKENIZATION_VERSION=code-words-v1 for future retrieval configuration.
There is no persisted lexical index to invalidate yet, so snapshot schema remains
unchanged. Ranking and CLI search are separate small steps. No dependency is added.

## 2026-11-17: distinct-term lexical baseline

Implement rank_chunks as a pure function over identified source chunks. Use unique
query terms and exact source-text term overlap; do not reward repeated occurrences.
Retain count scores and matched terms to make ordering inspectable. Full normalized
identifiers plus split parts can contribute multiple matches from one input word;
document this rather than describing scores as probabilities.

Omit zero-match chunks and sort ties by relative path, line range, and ID. Bound
queries at 2,000 characters and top_k at 100. Retokenize chunks per query for this
small baseline; do not add persistence or caching without a demonstrated need.
Record ranking/tokenization policy versions in the response. No snapshot schema
change is needed because no lexical index is persisted.

Explicitly label evidence as saved and not freshness-checked. Snapshot validation
and filesystem freshness belong to the upcoming CLI search boundary. Do not expose
a public search command without those checks. No evaluation dataset or quality
result is inferred from tests; BM25/semantic retrieval remain separate later work.

## 2026-11-17: freshness-gated lexical CLI search

Add search PATH QUERY --top-k N to the existing thin CLI. Load/validate saved data,
check freshness, and only then call the pure ranker. Stale/unknown responses include
no snippets and exit 3/4; tests ensure ranking/rebuild/save are never invoked on
those branches. Operational/argument errors remain exit 1/2. No-match on current
source is a successful empty result, not an error or invented explanation.

Current responses retain exact evidence metadata, snapshot identity, indexed Git,
policy versions, matched terms/counts, and saved warnings. Override the pure ranker's
unchecked evidence label only after this request's freshness check passes. Keep
degraded separate; fallback source can match when current with visible warnings.
No no-check/stale override, automatic refresh, cache, or new dependency is added.
This check does not freeze source after inspection or establish answer quality.

## 2026-11-19: evaluation contract and per-observation metrics

Document evaluation before creating any formal dataset. Keep labels versioned and
snapshot-bound, separate development/held-out cases and unsupported/unlabelled
expectations, and disclose attempted/eligible/blocked/error counts in future reports.
Define timing and citation validation scope without pretending tools exist yet.

Implement only pure per-observation hit/recall arithmetic for now. Apply cutoff
before matching and reject duplicate IDs rather than moving rank positions. Require
explicit source status; blocked/error observations are unscored and cannot contain
evidence. Empty positive-label sets produce undefined metrics, not perfect recall
or an inferred unsupported expectation. Current no-hit with positive labels is a
miss and zero recall. Keep counts inspectable alongside hit and recall.

No questions, labels, runner, aggregate metrics, measured latency, or retrieval gains
are invented. Synthetic-ID unit tests establish arithmetic behavior only. Snapshot
validation and relevance labeling belong to a later runner/workflow. No dependencies
are added, and no new retrieval complexity is justified by these software tests.

## 2026-11-20: evaluation input models and snapshot binding

Use existing Pydantic for strict, frozen, extra-forbidding EvaluationDataset and
EvaluationCase models. Require explicit fields and nonblank text rather than
inventing labels or default review assertions. Validate label/expectation/reviewer
consistency; distinguish unlabelled/undetermined from authored unsupported cases.

Parse supplied JSON, reject snapshot mismatches and unknown/duplicate references,
and reject partial source baselines before future query execution. Complete
degraded snapshots remain distinguishable from missing source. Split/review fields
are declarations; schema validation cannot certify held-out independence, relevance
truth, or human participation. Do not silently relabel, repair, or migrate IDs.

This is a pure validation boundary, not a file loader, runner, freshness check, or
benchmark. Future file loading needs byte bounds. Use only synthetic unit-test
records now; do not create the formal question set or any measured quality claim.

## 2026-11-20: bounded input loader and lexical runner

Use a regular-file/no-follow loader capped at 1 MB and 1,000 supplied cases. Require
an explicit development/held_out split; validate all input but execute/report only
the selected cases. Preserve the original total input count without echoing other
split questions. Splits are metadata, not proof of held-out isolation.

Record shared setup time separately, then reload/validate the snapshot per case
so total case time includes load/freshness like the search boundary. Use perf_counter
and separate ranking time; exclude process startup/report serialization. Preserve
blocked/error observations rather than dropping failures or manufacturing scores.
Per-case exceptions are recorded and later cases continue; invalid setup fails fast.

Verify returned IDs and exact source against the validated snapshot; invalid
references become unscored errors with no evidence. Zero citations produce None
validity, not a perfect percentage. Preserve labels/provenance, full manifest,
configuration/runtime, warnings, timing, matches, and metrics in memory. No tuning,
refresh, automatic output save, aggregate report, or evaluation CLI is added.
Synthetic tests/executions do not constitute a formal dataset or quality results.
