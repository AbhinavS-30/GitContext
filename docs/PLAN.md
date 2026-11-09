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

Deferred: remote cloning, multiple languages/repositories, Git history ingestion,
target-code execution, autonomous edits, hosted vector databases, paid APIs,
watchers, authentication, large frontend, premature reranking, and fine-tuning.
