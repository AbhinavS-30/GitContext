# Lexical baseline development review — November 24, 2026

This is a development-only identifier smoke review. It is not the formal evaluation
set, an independently labeled benchmark, a relevance judgment, or a quality result.
No formal questions, relevance labels, hit/recall scores, or latency claims are created.

## Fixed source and execution

- Source: GitContext commit `548076ad03eb936c61b8d7540feb65d5da8f60e2`.
- Method: export tracked source with git archive into a temporary directory; extract
  with Python's data filter; run the installed GitContext CLI against that export.
  Do not import, install, or execute any application/test code from the export.
- Corpus: 43 supported files, 588 chunks; partial=False, degraded=False.
- Snapshot: `snapshot-v2:dfaac5165b83d0455e62df16f91a19ddbf8b1548ddb6706b3284b785c22de13b`.
- Runtime: Python 3.12.13. Tokenization: code-words-v1. Ranking:
  distinct-term-overlap-v1. Python chunks: python-top-level-v1; Markdown:
  markdown-atx-v1. Chunk limit: 80 lines.
- Limits: 10,000 entries, 1,000 files, 1,000,000 bytes/file, 20 directory levels,
  10,000,000 total read bytes. Default discovery/reading policies were used.
- The export has no .git directory. Its manifest truthfully records not_repository,
  commit=None, dirty=None; the source commit above is external export provenance,
  not invented indexed Git metadata.

The original worktree was clean before this review. Exporting a fixed commit kept
the review corpus independent of this new documentation. The CLI indexed it and
searched each identifier below with --top-k 100. Every source-freshness check was
current. Temporary source and snapshot files were removed after execution; no
generated index or raw source report is committed.

## Observed order

The function position below is determined mechanically from returned symbol_name
and source path. It is not a human relevance label, a hit@k result, or evidence that
the function alone would answer a natural-language behavior question.

| Identifier | First result | Named function chunk position | Returned count |
| --- | --- | ---: | ---: |
| save_snapshot | README.md:330–360, Local snapshot persistence | 4 | 100 (capped) |
| check_freshness | README.md:361–393, Explicit freshness comparison | 6 | 85 |
| rank_chunks | README.md:419–448, Lexical ranking baseline (Python API) | 7 | 86 |

All first results scored 3, matching the full normalized identifier and its two
parts. For save_snapshot, the first four results were:

1. README.md, lines 330–360: documentation section.
2. src/gitcontext/cli.py, lines 1–19: module source including imports.
3. src/gitcontext/cli.py, lines 97–176: a fragment of main containing usage.
4. src/gitcontext/persistence.py, lines 138–161: save_snapshot itself.

For check_freshness, CLI source and evaluation-runner source preceded the named
function chunk. For rank_chunks, README, decisions documentation, CLI source, and
evaluation-runner source appeared before the named definition. Paths/line ranges
refer to the fixed exported commit, not necessarily later HEAD.

## What this reveals and what it does not

The baseline works as documented: matching distinct terms produces equal scores
for definitions, imports, call sites, and explanatory prose. It does not understand
which kind of evidence the developer wants. Ties then use path/line/ID order, so
alphabetical placement can dominate equal-coverage results. Split terms also admit
many weaker matches; a returned count capped at 100 is not the total matching count.

Documentation and call sites may be useful evidence. Their early position is not
automatically a relevance failure. A developer asking for a definition may prefer
different ordering from someone asking how that function is used. We need agreed
intent and labels before claiming ranking improvements or measured failure rates.

No ranking weights, filters, symbol boosts, BM25, embeddings, or source policies
were changed in response to these three diagnostics. Do not tune on these cases
and later describe them as independent held-out evaluation. Indexing a later commit
that includes this review can change results and cannot be compared blindly with
this fixed corpus.

## Next decision

Agree on actual development cases and label rules against a fixed snapshot, or
explicitly revisit the deferred formal ten-question set. Review who authors labels,
what counts as relevant/complete evidence, and development versus held-out exposure.
Until then, do not publish hit/recall gains or infer quality from unit-test counts.
