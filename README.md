# GitContext

GitContext is a local codebase search project for finding traceable evidence in
small Python repositories and selected Markdown documentation.

**Status:** bounded file discovery and UTF-8 source reading are implemented as
Python functions with tests. Python and Markdown chunking are also implemented.
In-memory snapshot inventories and read-only Git context are implemented.
Persistence, search, and generation are not implemented.
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

## Python chunking

```python
from gitcontext.chunking import chunk_python

for source in sources.files:
    if source.path.endswith(".py"):
        result = chunk_python(source, max_lines=80)
        for chunk in result.chunks:
            print(chunk.path, chunk.start_line, chunk.end_line, chunk.symbol_name)
        for issue in result.issues:
            print(issue.path, issue.reason)
```

Policy `python-top-level-v1` uses `ast.parse` without execution. Top-level functions,
async functions, and classes get their own ranges, starting at the first decorator.
Methods and nested definitions remain in their enclosing definition. Definitions
under module control flow remain module source. Imports, comments, blank lines, and
other remaining source form separate module ranges, including whitespace-only gaps.
Comments before the first decorator remain module source. No source is discarded.

Every range is split at the configured line limit (80 by default) when necessary;
all pieces of a split range have `is_fragment=True` and retain its symbol metadata.
This can split statements and does not guarantee independently executable chunks.
The bound is lines, not tokens or characters; a long individual line stays intact.
Syntax/recursion/value parsing failures produce visible issues and line-based
`fallback` chunks rather than invented symbol metadata. Empty files have no chunks.

Line ranges are one-based and inclusive. Text is sliced from the original source,
preserving newlines, and carries the file's content hash. Ordered chunks cover the
source exactly once without overlap. The report records policy version and line
limit. Index persistence and freshness comparisons are not implemented yet.
Chunk count and passing tests are not measurements of retrieval quality.

## Markdown chunking

```python
from gitcontext.markdown import chunk_markdown

for source in sources.files:
    if source.path.endswith(".md"):
        result = chunk_markdown(source)
        for chunk in result.chunks:
            print(chunk.start_line, chunk.end_line, chunk.symbol_name)
```

Policy `markdown-atx-v1` starts sections at `#` through `######` headings with up
to three leading spaces. Any heading level starts a new section. Text before the
first heading is a `markdown_preamble`; sections are `markdown_section` chunks,
with the heading title in `symbol_name`. Repeated titles are allowed; they are not
identifiers. Closing heading hashes are omitted from metadata, not source text.

Backtick and tilde fences suppress heading recognition until a matching closing
fence. A closing fence must use the same character, at least the opening length,
and no trailing info text. Unclosed fences produce a visible issue and preserve the
rest as code. Sections over max_lines (80 by default) become flagged fragments;
this mechanical limit may split a code example, so fragments can lack context.
Exact text, original line ranges, and file hashes are retained without overlap.

This is an explicit Markdown subset, not a full CommonMark parser. Underlined
headings are kept as ordinary text; HTML blocks, indented-code state, and nested
list/blockquote containers are not parsed. Documents using those constructs can
have imperfect section boundaries. Heading hierarchy and inline markup are not
interpreted. No Markdown or embedded code is rendered or executed.

## Deterministic chunk IDs

```python
from gitcontext.identities import chunk_id

for chunk in result.chunks:
    reference = chunk_id(
        chunk, policy_version=result.policy_version, max_lines=result.max_lines
    )
    print(reference, chunk.path, chunk.start_line, chunk.end_line)
```

An ID is `chunk-v1:` plus a SHA-256 digest of canonical JSON containing all chunk
fields (including exact text, relative path, file hash, range, symbol metadata,
and fragment flag), chunking policy version, and line limit. Canonical JSON uses
sorted keys, fixed separators, and UTF-8 to make serialization repeatable. Identical
inputs produce identical IDs without a timestamp or random value.

Changing paths, content, ranges, or configuration changes IDs. Including the whole
file hash intentionally invalidates references even for chunks untouched by an edit
elsewhere in that file. IDs identify evidence versions, not functions across edits.
They are scoped to the selected repository/index; two repositories with identical
relative paths, content, and configuration can share IDs. Snapshot identity will
provides collection context in the in-memory snapshot. The helper does not validate data against disk,
detect staleness, persist anything, or prove code safety or answer correctness.

## In-memory snapshot inventory

```python
from pathlib import Path
from gitcontext.snapshots import build_snapshot

snapshot = build_snapshot(Path("/path/to/local/repository"))
print(snapshot.snapshot_id)
print(snapshot.manifest.partial, snapshot.manifest.degraded)
for file in snapshot.manifest.files:
    print(file.path, file.content_sha256, file.chunk_ids)
```

`build_snapshot` composes discovery, reading, Python/Markdown chunking, and chunk
identification. The manifest records selected paths separately from successfully
read files, including empty files. File records contain actual read sizes, hashes,
and ordered chunk IDs. `snapshot.chunks` associates IDs with exact source chunks.
Configuration records resource limits, allowlists/excluded directories, versioned
discovery/reading/chunking policies, chunk ID version, and Python parser runtime.
Changes to hard-coded filename policies require a discovery policy version bump.

`partial=True` means discovery or reading missed source. `degraded=True` means
chunking reported an issue while retaining source, such as syntax fallback or an
unclosed Markdown fence. Expected exclusions alone set neither flag. Issues remain
visible; a snapshot is not a declaration that retrieval is good or input is safe.

The `snapshot-v2:` ID hashes a canonical, sorted manifest inventory. Absolute root
paths and diagnostic wording are excluded from identity; issue paths/reasons are
included. Timestamps and random values are not used. Identical inventories and
configuration can share IDs across local folders. Configuration, selected files,
read hashes, issues, and completeness changes can change IDs. This identifies a
processing inventory, not a globally unique repository or an atomic Git snapshot.

Snapshot data is not saved to disk. Model configuration, persisted indexes, and
automatic freshness comparisons remain unimplemented. Limited scans
may select different subsets because discovery follows filesystem order. Indexing
does not freeze concurrent edits across files. Generated inventories and source
chunks can contain private code and must remain local when persistence is added.

## Read-only Git context

`manifest.git` records `status`, `commit`, `dirty`, and an optional issue code.
`available` means Git inspection succeeded; `not_repository` means the selected
folder is not itself a working-tree root; `unavailable` means inspection failed.
Unknown dirty state is `None`, never silently `False`. Repositories without a
resolvable HEAD have no commit and an explicit `head_unavailable` issue. In an
empty repository, dirty=False means status has no entries, not that a commit exists.

Dirty includes staged/unstaged tracked changes and untracked non-ignored files
across the repository, not only indexed Python/Markdown. Ignored files and unstaged
changes inside submodule worktrees are excluded. Indexed source can therefore
change while dirty stays False (for example an indexed Git-ignored Markdown file);
file hashes remain the source-content authority. Ancestor repository metadata is
not attributed to a selected subfolder. Linked worktrees are supported by Git's
normal root discovery; bare repositories are not working-tree roots.

Inspection runs only fixed read-only Git commands, without a shell or network.
It clears inherited GIT_* overrides, disables filesystem-monitor helpers and
optional index locks, and suppresses interactive prompting. Each command has a
five-second timeout; stdout is temporarily spooled and accepted only up to 64 KiB.
This bounds accepted output/memory, not temporary spool size during the timeout.
No target code, hooks, package installation, or remote access is requested.

Git context is observed after source processing. It does not prove an atomic read
or that the indexed bytes match HEAD. The manifest includes this observation and
its policy; changing Git context can change snapshot IDs even when chunk contents
are unchanged. Source-completeness flags remain independent of Git availability.
