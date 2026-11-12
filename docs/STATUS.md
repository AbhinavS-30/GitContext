# Status

Updated: November 12, 2026. Phase 2 of five core phases: chunking and index
snapshots. Core ingestion, Python chunking, and Markdown chunking are implemented;
no CLI exists.

## Current work

Standalone setup is published at https://github.com/AbhinavS-30/GitContext.
Initial commit: `4f904a8`; pushed successfully, with GitHub Actions passing.

Discovery is published in commit `8c1c3a5`, pushed with GitHub Actions passing.
Codex has now implemented bounded source reading in `src/gitcontext/reading.py`
with 18 additional test cases. It reads discovered files without execution, enforces
byte limits again, refuses symlink components, decodes UTF-8 strictly, rejects NUL
content, and reports individual failures while retaining useful source records.
README and decisions document the policies and POSIX platform requirement.
The reader is published as `3870439`, pushed with GitHub Actions passing.

Codex added `content_sha256` to accepted source records, hashing the exact bytes
already read. Three tests cover a known digest, repeatability/path independence,
same-size edits, and newline byte differences. No new dependencies were added.

Fingerprint metadata is published as `9f24312`, pushed with GitHub Actions passing.
Codex implemented `chunking.py` and 17 additional test cases. Top-level Python
definitions include decorators; nested definitions/methods stay inside the parent.
Remaining source is preserved in module chunks. Oversized ranges become flagged
fragments; parse errors return explicit issues and line-based fallback chunks.
Reports carry the policy version and max_lines. Documentation records the policy.

Python chunking is published as `0cbc888`, pushed with GitHub Actions passing.
Codex implemented `markdown.py` and 18 additional tests. It splits ATX headings,
ignores headings inside fenced code, reports unclosed fences, preserves exact text,
and flags oversized fragments. It reuses the chunk/report shape with Markdown kinds.

Markdown chunking is published as `f48ff8d`, pushed with GitHub Actions passing.
Codex implemented `identities.py` and 18 additional test cases for deterministic
chunk IDs. IDs bind all source chunk fields and chunking configuration using
canonical JSON and version-prefixed SHA-256. No new dependencies were added.

Chunk IDs are published as `058bc1c`, pushed with GitHub Actions passing.
Codex implemented in-memory snapshot orchestration in `snapshots.py` and 18 tests.
The manifest records selected paths, read file hashes/sizes/chunk references,
configuration, issues, partial and degraded flags, and a deterministic snapshot ID.
No disk persistence, Git integration, or new dependencies were added.

## Verification and publication

- pytest: 104 passed (86 existing cases plus 18 snapshot cases).
- Ruff lint and format checks: passed.
- Actual GitContext scan: eight selected files, 24 examined entries, partial=False.
- Actual scan with max_files=2: two selected files, partial=True, file_limit issue.
- Actual reader scan of GitContext before documentation updates: ten source files,
  31,466 bytes, partial=False.
- Grown-file fixture: a four-byte file grew to 100 bytes after discovery. With an
  eight-byte limit, reading consumed nine bytes, returned no source, and reported
  file_size_limit with partial=True.
- Actual fingerprint execution: `return True` and `return None` both occupy 11
  bytes, but their SHA-256 values differ. The existing discovery report was reused;
  the reader fingerprinted the actual newly read content.
- Actual Python chunking run: seven Python files, 97 chunks, zero parse issues.
  Joining each file's chunks reproduced its exact source. In reading.py,
  read_sources became two flagged fragments spanning lines 52–131 and 132–135.
- Actual Markdown run before documentation updates: five files, 23 chunks, zero
  issues. Joining each file's chunks reproduced its exact source. README sections
  were correctly distinguished from the code examples they contain.
- Actual ID execution: identical a.py inputs twice yielded chunk-v1:c8531b74…;
  identical source at b.py yielded chunk-v1:8e9d967d…. No file execution occurred.
- Actual snapshot run before documentation updates: 18 selected/read files, 196
  chunks, partial=False, degraded=False. Repeated fixture builds shared an ID;
  editing True to None changed it without Git or a size change.
- The learner requested progressing and committing/pushing. This status accompanies
  the snapshot commit; the session handoff records its ID, push, and remote CI result.

## Learning record

After explanation and a simplified example, the learner correctly answered that
reading source text does not execute its print statement. The learner also correctly
identified that reaching a scan limit must be reported as partial. Directory exclusion
rationale was explained; independent reasoning about it has not yet been demonstrated.
Codex wrote the implementation and tests.
The learner correctly answered that reading must enforce the size limit again
rather than trust discovery's recorded size. Codex implemented the reader and tests.
The learner was unsure why silently repairing invalid text is unsuitable. Codex
explained that replacement changes source evidence; independent understanding of
that trade-off has not yet been demonstrated.
The learner correctly answered that file size alone cannot detect changing
`return True` to `return None`. Codex implemented fingerprint metadata and tests.
The learner also correctly answered that differently named files with identical
bytes share a content hash, then requested publication and the next step.

The learner correctly answered that a function chunk should include its decorator.
The learner was given the explanation of context lost by splitting validation from
persistence; independent reasoning on that trade-off remains unverified. Codex
implemented all chunking code and tests.
The learner requested publication without answering the fragment follow-up.
Codex explained that one fragment cannot establish the whole function's behavior;
independent reasoning about this limitation remains unverified.

The learner asked to move forward after the fenced-code question. Codex explained
that heading-like comments inside fenced code must not start sections. Independent
understanding of that distinction remains unverified. Codex wrote all Markdown code
and tests; the learner has not independently written implementation code.

The learner requested moving forward after the path/ID question. Codex explained
that moving unchanged source changes its chunk ID because location is part of the
reference. Independent reasoning about that distinction remains unverified. Codex
implemented all identity code and tests.
Codex explained that max_lines changes IDs even for unchanged short chunks because
configuration is part of identity. Independent reasoning remains unverified.

The learner requested moving forward after the Git commit/content question. Codex
explained that commits cannot describe uncommitted file contents. Independent
reasoning on this topic remains unverified. Codex wrote all snapshot code and tests.

## Limitations and next task

The implementation and actual scan were explained. The follow-up distinction
between expected exclusions and limit-induced partial results remains a learning
gap; publication was explicitly requested without answering that question.
Next: walk through build_snapshot and the distinction between partial and degraded.
Ask whether a syntax-error file retained through fallback should vanish from the
manifest. Wait before implementing the next component: read-only Git metadata.
Safe persistence and freshness checks remain separate later steps.
Persistence, Git metadata, freshness checking, and search remain separate steps.

Discovery does not inspect content, detect all secrets, honor `.gitignore`, or
provide an atomic snapshot. Limited selection follows filesystem order. Reading
requires macOS/Linux, supports UTF-8 only, and does not guarantee an immutable
whole-repository snapshot. Hash persistence, Git version metadata, and automated
freshness detection remain future work.
Python chunks may be whitespace-only; line limits do not bound tokens, and methods
are not separate chunks. Markdown is a limited ATX/fence subset: no setext heading,
HTML-block, indented-code-state, or nested-container parsing. Fragment limits may
split code examples. Chunk IDs are index-scoped and bind whole-file versions, not
stable symbols across edits. Snapshot IDs describe the processing inventory and
configuration, not immutable repository state. No CLI, persisted indexing,
retrieval, model integration, or
formal evaluation dataset exists. Tests do not demonstrate retrieval quality.

Python 3.12.13 is available. Ollama was installed but not running at inspection;
local llama3.2:3b has a manifest, but inference and embeddings remain unverified.
