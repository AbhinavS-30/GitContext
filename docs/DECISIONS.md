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
