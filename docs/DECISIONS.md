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
