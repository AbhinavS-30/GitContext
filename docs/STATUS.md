# Status

Updated: November 9, 2026. Phase 1 of five core phases: setup and ingestion.

## Current work

Standalone setup is published at https://github.com/AbhinavS-30/GitContext.
Initial commit: `4f904a8`; pushed successfully, with GitHub Actions passing.

Discovery is published in commit `8c1c3a5`, pushed with GitHub Actions passing.
Codex has now implemented bounded source reading in `src/gitcontext/reading.py`
with 18 additional test cases. It reads discovered files without execution, enforces
byte limits again, refuses symlink components, decodes UTF-8 strictly, rejects NUL
content, and reports individual failures while retaining useful source records.
README and decisions document the policies and POSIX platform requirement.

## Verification and publication

- pytest: 30 passed (12 discovery, 18 reading).
- Ruff lint and format checks: passed.
- Actual GitContext scan: eight selected files, 24 examined entries, partial=False.
- Actual scan with max_files=2: two selected files, partial=True, file_limit issue.
- Actual reader scan of GitContext before documentation updates: ten source files,
  31,466 bytes, partial=False.
- Grown-file fixture: a four-byte file grew to 100 bytes after discovery. With an
  eight-byte limit, reading consumed nine bytes, returned no source, and reported
  file_size_limit with partial=True.
- After the walkthrough, the learner requested an explanation of strict decoding
  and asked to move forward. This status accompanies the reader commit; its hash,
  push result, and remote CI result are reported in the session handoff.

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

## Limitations and next task

The implementation and actual scan were explained. The follow-up distinction
between expected exclusions and limit-induced partial results remains a learning
gap; publication was explicitly requested without answering that question.
Reader walkthrough and probe-byte execution are complete. Next: explain a file
content hash as a fingerprint of the exact bytes read, including its role in later
freshness checks. Ask one understanding question before implementing hashes.
Do not add parsing, manifests, Git metadata, or search in the same step.

Discovery does not inspect content, detect all secrets, honor `.gitignore`, or
provide an atomic snapshot. Limited selection follows filesystem order. Reading
requires macOS/Linux, supports UTF-8 only, and does not guarantee an immutable
whole-repository snapshot. Hash/version metadata remains future work.
No CLI, chunking, indexing, retrieval, model integration, or
formal evaluation dataset exists. Tests do not demonstrate retrieval quality.

Python 3.12.13 is available. Ollama was installed but not running at inspection;
local llama3.2:3b has a manifest, but inference and embeddings remain unverified.
