# GitContext

GitContext is a local codebase search project for finding traceable evidence in
small Python repositories and selected Markdown documentation.

**Status:** bounded file discovery and UTF-8 source reading are implemented as
Python functions with tests. Python and Markdown chunking are also implemented.
In-memory snapshot inventories and read-only Git context are implemented.
Validated local snapshot saving/loading and lexical CLI search are implemented.
The CLI supports indexing, inspection, status, explicit refresh, and search with
mandatory source-freshness checks. Model generation is not implemented.

For a component-by-component explanation, see [the walkthrough](docs/WALKTHROUGH.md).

## CLI usage

After the development installation below, activate `.venv` and run:

```sh
gitcontext index /path/to/repository
gitcontext inspect /path/to/repository
gitcontext status /path/to/repository
gitcontext refresh /path/to/repository
gitcontext search /path/to/repository "save record" --top-k 5
```

`python -m gitcontext` supports the same commands. Output is JSON. Data lives at
`REPOSITORY/.gitcontext/snapshot.json`; the storage directory is created privately
and excluded from discovery. Keep this source-containing directory out of the
target repository's Git tracking too; GitContext does not edit its `.gitignore`.

`index` refuses to overwrite an existing snapshot. `refresh` explicitly rebuilds
and replaces an existing valid snapshot, retaining saved limits unless overridden.
Both refuse to publish partial builds, preserving any previous snapshot. Degraded
but complete builds are saved with warnings and the degraded flag. Persistence
still supports explicit partial saves through its Python API.

`inspect` reports saved metadata and per-file chunk IDs. To see exact source:

```sh
gitcontext inspect /path/to/repository --chunk 'chunk-v1:FULL_DIGEST'
```

Inspection labels evidence as saved and not freshness-checked; it does not promise
current citations. `status` checks freshness without writing. A stale result must
be followed by an explicit `refresh` when a new snapshot is wanted. Search uses
the transparent lexical baseline described below; model generation is absent.

Exit codes: 0=success/current, 1=operational/validation error, 2=invalid arguments,
3=stale, 4=unknown freshness or refused partial build. Index/refresh accept positive
`--max-lines`, `--max-files`, `--max-entries`, `--max-file-bytes`, `--max-depth`, and
`--max-total-bytes` limits. Status checks use saved limits. Root/storage symlinks
are refused. Refresh requires a loadable saved snapshot for the same root; corrupt
saved data is reported, not silently replaced. Concurrent writers remain unsupported.

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
Pydantic is the application dependency for persisted-data validation. No model
download is required for setup.

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
byte changes do. Hashes are saved when a snapshot is explicitly persisted;
explicit freshness comparison uses those hashes. A hash does not
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
limit. Explicit freshness comparison is available below.
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

Snapshot data can be explicitly saved using the persistence functions below.
Model configuration and search indexes remain unimplemented. Freshness checks
require an explicit call; no background watcher runs. Limited scans
may select different subsets because discovery follows filesystem order. Indexing
does not freeze concurrent edits across files. Generated inventories and source
chunks can contain private code and must remain local.

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

## Local snapshot persistence

```python
from gitcontext.persistence import save_snapshot, load_snapshot

storage = Path(".gitcontext")
storage.mkdir(exist_ok=True)
save_snapshot(snapshot, storage / "snapshot.json")
restored = load_snapshot(storage / "snapshot.json")
```

Pydantic validates the saved JSON structure strictly. Additional checks recompute
snapshot/chunk IDs, reconstruct exact file contents to check hashes and sizes,
verify contiguous source line coverage, and reject duplicate/missing/unreferenced
chunks. Unknown/omitted fields and unsupported schema or chunk-policy versions
are rejected. Load/save accept at most 64,000,000 serialized bytes. This is
consistency validation, not authentication or proof that data matches current disk.

Saving validates first, writes a private (0600) temporary sibling, flushes and
fsyncs it, verifies it by loading, then atomically replaces the destination. Failures
before replacement preserve the previous file; temporary files are cleaned up on
handled failures. A process killed abruptly can leave a temporary sibling. This
does not promise power-loss durability of the containing directory. Concurrent
writers are last-writer-wins; locking is not implemented. Use a trusted local
destination directory that already exists; loading refuses a final-file symlink.

Partial/degraded snapshots retain their flags. Successfully loading an old snapshot
does not make it current: run the explicit freshness check below. Snapshot
JSON includes source text, absolute repository location, and diagnostics; keep it
in ignored `.gitcontext/` or another private location. Do not commit generated data.

## Explicit freshness comparison

```python
from gitcontext.freshness import check_freshness

freshness = check_freshness(restored, Path("/path/to/local/repository"))
print(freshness.status)
print(freshness.added, freshness.modified, freshness.removed)
print(freshness.config_changes, freshness.limitations)
```

The check discovers and reads supported files again, comparing selected paths,
actual content hashes, and current processing configuration. It does not reparse
source, invoke Git, write data, or refresh the saved snapshot. It accepts snapshots
from build_snapshot/load_snapshot and requires the explicit root to match the saved
root. Defaults use saved resource limits; optional limit overrides are compared as
configuration changes. Current policy versions and parser runtime are compared too.

`current` means complete observations match. `stale` means supported scope, bytes,
or configuration differ. `unknown` means a saved/current observation is partial,
the root differs/is unavailable, or inspection failed. Unknown takes precedence
over stale, while any observed added/modified differences remain visible. Removed
paths are only reported after complete discovery, so failed traversal does not
invent deletions. Removed means absent from supported scope: a file replaced by an
excluded symlink is removed from scope even if that path still exists.

Expected exclusions and unrelated Git commit/dirty changes do not by themselves
make source stale. An unchanged syntax-fallback snapshot may be current and still
degraded; current does not mean high quality. A saved partial snapshot cannot be
certified current; an explicit rebuild is needed. This is a bounded observation,
not a guarantee against concurrent edits or future changes. Automatic query-time
enforcement is provided by CLI search. The CLI also provides explicit status/refresh.

## Lexical tokenization (Phase 3 in progress)

```python
from gitcontext.tokenization import tokenize

print(tokenize("save_reviewed_record"))
# ('save_reviewed_record', 'save', 'reviewed', 'record')
```

Policy `code-words-v1` preserves a case-folded full word/identifier plus underscore
and ASCII CamelCase/acronym parts. Unicode word characters are retained and case
folded; general Unicode camel segmentation and language-specific word boundaries
are not implemented. Digits stay attached to word parts and numeric terms remain
searchable. Punctuation separates words; underscore-only and empty inputs yield
no terms. Leading/trailing underscores remain in full identifiers such as __init__.

Repeated source occurrences remain repeated, while duplicate expansions within
one occurrence are emitted once. Normalized full identifiers support future exact
name matching; split parts support prose queries. Exact here is case-insensitive,
not a byte-for-byte source comparison. No stemming, stopword removal, synonym
inference is performed by the tokenizer. Ranking and CLI search are described below;
no persisted lexical index is implemented yet.
Queries and chunks use the same policy during retrieval. Tokenizer
examples/tests are development checks, not a formal retrieval benchmark.

## Lexical ranking baseline (Python API)

```python
from gitcontext.lexical import rank_chunks

report = rank_chunks(restored.chunks, "save record", top_k=5)
for match in report.matches:
    print(match.score, match.matched_terms, match.source.path)
```

Policy `distinct-term-overlap-v1` scores each chunk by the number of distinct
normalized query terms found in its exact source text. Repetition in the query or
chunk cannot inflate the score. All query/chunk text uses `code-words-v1` tokenization.
Full identifiers and their parts are separate terms, so a single input word can
expand into several matches. Scores are counts, not probabilities or calibrated
relevance. No synonym inference, stopword removal, or length/frequency weighting
is applied; long chunks and common words can still produce poor matches.

Zero-match chunks are omitted. Ties use path, start/end lines, then chunk ID for
repeatable ordering independent of input order. Results include matched terms,
chunk ID, and exact source metadata. Queries are capped at 2,000 characters and
top_k at 1–100 (default 5). Empty/punctuation-only/unmatched queries return no hits.

This function assumes prepared/validated chunks and does not read files, establish
freshness, or enforce snapshot completeness. Its report explicitly labels results
as saved_snapshot_not_freshness_checked. It retokenizes the corpus per call; no
lexical cache/index exists yet. The CLI adds mandatory freshness checks as described
below. Passing tests and development examples do not
measure retrieval quality; no formal evaluation dataset has been created.

## Freshness-enforced CLI search

```sh
gitcontext search /path/to/repository "save_record" --top-k 5
```

Search loads/validates saved data, checks source freshness, then ranks only when
current. Stale (exit 3) and unknown (exit 4) return an empty matches list, the
freshness report, and an explicit refresh instruction. Blocked search never ranks,
rebuilds, saves, or presents source snippets. A partial baseline is unknown and
blocked. Missing/corrupt snapshots are operational errors (exit 1), not evidence.

Current results include snapshot ID, indexed Git context, query terms, tokenizer/
ranking versions, integer match counts, matched terms, chunk IDs, exact text, and
source paths/line ranges/file hashes. The evidence label is source_freshness_checked,
meaning checked during this request, not frozen against edits afterward. Saved
degraded state and snapshot warnings remain visible; unchanged fallback text can
still be searched. Scores do not prove an answer is correct or supported in meaning.

Empty/unmatched queries return an empty matches list with exit 0 after freshness
passes. Queries over 2,000 characters and --top-k outside 1–100 are argument errors
(exit 2); default top_k is 5. Search does not mutate the saved snapshot. Retrieval
quality is not yet measured; no BM25, semantic search, hybrid ranking, or model
answers are included in this baseline.
