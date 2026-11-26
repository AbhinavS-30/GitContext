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

Explicit freshness comparison is implemented locally and tested, including content,
supported-scope/configuration changes, unknown inspection, and partial baselines.
Next: expose explicit rebuild/refresh and status through a minimal CLI, then add
lexical search in milestone 3. No search or CLI is implemented yet.

Deferred: remote cloning, multiple languages/repositories, Git history ingestion,
target-code execution, autonomous edits, hosted vector databases, paid APIs,
watchers, authentication, large frontend, premature reranking, and fine-tuning.

Phase 2 exit check: a minimal CLI can build/save, inspect, check freshness, and
explicitly rebuild/refresh snapshots. Failures preserve the old saved snapshot and
cannot masquerade as complete results. Verify tests and an actual end-to-end run.
Announce Phase 2 completion explicitly to the learner once those checks pass.

November 16: Phase 2 implementation complete locally. The minimal CLI and tests
passed; an installed-command run verified index → inspect → edit → stale status →
refresh → current status. It also verified unknown status and refused partial refresh
without replacing valid saved data. Publication status is tracked in docs/STATUS.md.
Next is milestone 3: explain and implement the lexical retrieval baseline in small
steps, retaining freshness enforcement and traceable evidence.

Phase 2 is published as 88acbb9 with passing CI. Phase 3 has begun with the shared
identifier-aware tokenizer. Next: explain and implement a transparent lexical
ranking baseline, then freshness-enforced CLI search. No retrieval quality has
been measured and no formal question set has been created.

November 17: the pure distinct-term lexical ranking baseline is implemented locally
and tested, with explainable matches and deterministic ties. Next: add CLI search
that loads/validates a snapshot and checks freshness before returning results.
Phase 3 remains in progress; no public search command or retrieval evaluation yet.

CLI lexical search is now implemented and tested with mandatory snapshot validation
and freshness checks. Installed-command execution verified current results, stale/
unknown blocking, explicit refresh, and no-match behavior. This is the first usable
search baseline; retrieval quality remains unmeasured. Next: review actual results
and agree on evaluation contracts/measurement before adding retrieval complexity.

November 19: docs/EVALUATION.md specifies the evaluation contract without creating
formal cases. A pure per-observation hit/recall helper is implemented and tested on
synthetic IDs, with explicit blocked/error/undefined states. Dataset/label creation,
run orchestration, aggregate reporting, citation evaluation, and timing remain
separate steps. No retrieval quality result is claimed.

November 20: evaluation input schema and snapshot/reference validation are
implemented locally and tested on synthetic records. Formal cases remain uncreated.
Next: explain a bounded dataset-loading/run boundary that preserves freshness,
blocked/error states, snapshot warnings, and measurement provenance before execution.

The bounded input loader and in-memory lexical runner are implemented and tested
with synthetic cases. They preserve split selection, setup/per-case/ranking timing,
source-reference validation, provenance, and blocked/error observations. Next:
review the runner, then add transparent aggregate reporting without hiding failed
or unlabelled cases. Formal questions/labels and measured quality remain uncreated.

November 23: aggregate reporting is implemented locally and tested with explicit
status/label/metric/citation populations and outcome-specific timing summaries.
Next: review denominators and connect the runner/report to an explicit evaluation
CLI without creating formal cases or claiming measured retrieval quality.

The explicit evaluation CLI is implemented and tested, producing a versioned run
and summary without automatic data/report creation or refresh. The installed
command passed synthetic current/stale/unknown execution and read-only checks.
Next: review the end-to-end baseline and agree on actual development evaluation
data/labels and their fixed snapshot before claiming quality or adding complexity.
The formal ten-question set has not been created.

November 24: reviewed the installed lexical CLI on a fixed GitContext source export
without creating relevance labels. docs/BASELINE_REVIEW.md records corpus/config
provenance and identifier-result ordering. Equal coverage tied definitions/imports/
docs and exposed the effect of path ordering. Ranking is unchanged. Next requires
agreement on development labels or explicit authorization to begin the deferred
formal set; no measured relevance or performance claims are made.

The user selected development-only cases/label review. Three draft cases were
published as draft-v1; draft-v2 records Codex source review with questions/reference
labels unchanged. A single provisional top-five run missed every narrow labelled
implementation target while returning related documentation. This qualified result
is preserved in evaluation/development/PROVISIONAL_RESULTS.md; no general quality,
human-review, held-out, or timing claim follows. Ranking remains unchanged. Next:
explain and compare one justified lexical-ranking experiment against the fixed
baseline, retaining scope/provenance and exposing trade-offs. Formal set stays deferred.

November 25: docs/BM25_EXPERIMENT.md proposes one controlled lexical comparison
and records the motivation/trade-offs. No BM25 implementation or new results yet.
Next: establish understanding of term rarity/saturation/length normalization, then
record the exact variant/configuration and build the candidate in a small step.
