# Milestones

Planning baseline: November 9, 2026. The project began as an empty folder.
Available time: approximately three hours per weekday and six total on weekends;
interview preparation stays on weekends. Estimates include learning and will be
revisited after ingestion. The old early-November release target is obsolete.

1. Setup and ingestion (about one week): standalone package, environment, public
   repository, CI; bounded supported-file discovery with visible skip/error reports.
2. Chunking and snapshots (one to two weeks): AST-based Python chunks, Markdown
   sections, exact source metadata, persisted manifest, explicit refresh and stale
   detection, safe publication of completed indexes.
3. Lexical CLI search (about one week): transparent identifier-aware ranking and
   inspectable source results. Introduce BM25 only with justification.
4. Semantic and hybrid retrieval (one to two weeks): inspect local resources,
   select an embedding model, track configuration, cache compatible vectors, and
   compare lexical, semantic, and reciprocal-rank fusion results.
5. Optional answers and evaluation tooling (one to two weeks): bounded local-model
   input, schema and citation validation, failure reporting, evaluation contract,
   reproducible checks. Draft formal evaluation data only when explicitly agreed.

First usable milestone: lexical search with reliable source metadata and freshness
checks. A thin FastAPI interface follows the working, understood CLI pipeline.

Progress on November 9: setup, bounded discovery, bounded UTF-8 reading, and exact-byte
file fingerprints are implemented and tested. We are entering milestone 2 with
Python chunking next. Ingestion is currently exposed through Python functions;
the user-facing CLI remains future work, with the lexical search milestone.

Progress on November 10: first Python AST chunking policy implemented locally and
tested. The next chunking component is Markdown section handling; snapshots and
persistence remain later parts of milestone 2.

Markdown ATX heading chunking is also implemented and tested, with fenced
code handling and explicit subset limitations. Stable chunk/snapshot identifiers
and persisted manifests remain the next parts of milestone 2.

Progress on November 11: deterministic, versioned chunk ID computation is implemented
locally and tested. Snapshot metadata, Git context, persistence, and freshness
comparison remain unfinished parts of milestone 2.

Progress on November 12: in-memory snapshot orchestration and manifests are
implemented and tested, including selected/read inventories, configuration,
issues, chunk references, deterministic snapshot IDs, and completeness flags.
Next: Git context, safe persistence, and explicit freshness comparison in small steps.

Progress on November 13: read-only Git commit/dirty observations are implemented
locally and tested, including unavailable states and snapshot-v2 integration.
Next: safe persistence, then explicit refresh/freshness checks. Phase 2 continues.

Validated JSON snapshot saving/loading is implemented with private temporary
siblings, verification, and atomic replacement. Pydantic is added for boundary
validation. Next: explicit freshness comparison and refresh behavior, then the CLI.

Deferred: remote cloning, multiple languages/repositories, Git history ingestion,
target-code execution, autonomous edits, hosted vector databases, paid APIs,
watchers, authentication, large frontend, premature reranking, and fine-tuning.
