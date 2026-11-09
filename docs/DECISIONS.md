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
