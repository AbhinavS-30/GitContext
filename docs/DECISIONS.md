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
