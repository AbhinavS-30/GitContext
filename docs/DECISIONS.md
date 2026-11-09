# Decisions

## 2026-11-09: independent, minimal project

Use a standalone Git repository, local Python 3.12 environment, and `src/` package
layout. Keeping importable code under `src/` helps expose installation mistakes
that can be hidden when imports resolve directly from the repository root.

Use setuptools as the build backend and Ruff for linting and formatting. Pin both
in project configuration. Add pytest with the first behavioral tests, Pydantic when
explicit data contracts are introduced, and HTTPX when local inference needs HTTP.
No application dependencies or orchestration framework are needed for setup.

Keep indexing separate from querying. Deliver useful search before generation.
Measure retrieval rather than assuming embeddings or hybrid ranking improve it.

Document capabilities as implemented. Do not create placeholder application
features, artificial benchmark questions, or tests that only assert placeholders.
