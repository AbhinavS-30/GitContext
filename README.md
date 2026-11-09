# GitContext

GitContext is a local codebase search project for finding traceable evidence in
small Python repositories and selected Markdown documentation.

**Status:** bounded file discovery and UTF-8 source reading are implemented as
Python functions with tests. Indexing, search, and generation are not implemented.
No CLI exists yet.

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
python -m pytest -q
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

## File discovery

```python
from pathlib import Path
from gitcontext.discovery import discover_repository

report = discover_repository(Path("/path/to/local/repository"))
for source in report.files:
    print(source.path, source.size_bytes)
print("Partial:", report.partial)
for issue in report.issues:
    print(issue.path, issue.reason)
```

Discovery selects `.py` and `.md` paths without reading their contents. It skips
symlinks, known dependency/generated/private directories, credential-like filenames,
unsupported extensions, and non-regular files. Excluded directories produce one
report entry; their contents are not enumerated. Selection uses the explicit policy
in `discovery.py`, not `.gitignore`. Git history is not required.

Defaults: 10,000 examined directory entries, 1,000 selected files, 1,000,000 bytes
per selected file, and 20 directory levels beneath the root. Configure these with
`DiscoveryLimits`. Access failures and applied limits make results partial;
expected exclusions do not. Invalid roots raise exceptions. Source encoding,
binary content, and syntax are not inspected yet.

Filesystem order determines selection when a limit is reached; output records are
sorted afterward. Discovery is not an atomic snapshot. Future source reading must
recheck containment, symlinks, and actual byte limits. Concurrent adversarial path
replacement is not prevented by this component. Exclusions cannot detect all secrets.

## Source reading (macOS/Linux)

```python
from gitcontext.reading import read_sources

sources = read_sources(report, max_total_bytes=10_000_000)
for source in sources.files:
    print(source.path, source.size_bytes)
print("Partial:", sources.partial)
```

The reader accepts a discovery report. It opens paths relative to directory file
descriptors, refusing symlinks at each component, and rejects non-regular files.
It enforces the discovery per-file limit again and a total read budget (10 MB by
default), using unbuffered reads with one extra byte to detect overflow. The total
budget counts bytes from rejected content too; total consumption is at most the
budget plus one probe byte. Oversized files are rejected, never silently truncated.

UTF-8 decoding is strict, newlines are preserved, and NUL-containing content is
rejected. There is no encoding fallback or automatic repair. UTF-8 decoding and
the NUL check are conservative content checks, not a complete binary detector.
Changed size/timestamps during reading produce a failure report. Discovery issues
and partial status are preserved; other useful files survive individual failures.

Directory-descriptor operations target macOS/Linux. This is not a whole-repository
atomic snapshot or a guarantee against every concurrent edit. A file changed before
reading is accepted if it meets current limits.

Each accepted source record includes `content_sha256`, a 64-character hexadecimal
SHA-256 fingerprint of the exact bytes read. The hash uses those in-memory bytes,
not a second file read. Paths and timestamps do not affect it; newline and other
byte changes do. This metadata prepares for later freshness checks, but no hashes
are persisted and no automatic stale-index detection exists yet. A hash does not
establish that source text is safe or correct.
