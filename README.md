# GitContext

GitContext is a local codebase search project for finding traceable evidence in
small Python repositories and selected Markdown documentation.

**Status:** initial project setup only. Repository ingestion, indexing, search,
and answer generation are not implemented. No CLI is available yet.

## Planned flow

Indexing: repository → supported-file discovery → parsing and chunking → source
metadata → lexical index and local embeddings → persisted manifest.

Querying: question → retrieval → ranked source snippets → optional local-model
explanation → citation-reference validation.

Search must work without a generative model. Target repositories are read as data;
their code must never be imported, executed, or installed by GitContext.

## Development setup

Use Python 3.12. From the project root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
python -m compileall -q src
python -c 'import gitcontext; print(gitcontext.__doc__)'
```

The last command checks this package's installation, not a target repository.
Development tools and the build backend are pinned in `pyproject.toml`; there are
no application dependencies yet. No model download is required for setup.

## Scope and limitations

The planned first release uses one local Python repository at a time, a CLI,
explicit index refresh, lexical and local semantic retrieval, and optional local
answer generation. A thin HTTP interface follows a working CLI pipeline.

No paid APIs, remote cloning, target-code execution, hosted vector database, or
autonomous code editing is planned. File allowlists and exclusions cannot guarantee
that every secret is detected. Generated indexes may contain source text and must
remain local and untracked.

There is no evaluation dataset or measured retrieval quality yet.

See [the plan](docs/PLAN.md), [current status](docs/STATUS.md), and
[design decisions](docs/DECISIONS.md).
