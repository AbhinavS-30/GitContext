# BM25 experiment proposal — November 25, 2026

Status: specification published in 01e54a7 before implementation and results.
The candidate is now implemented as an explicit experimental mode. The controlled
comparison found no improvement on the three draft cases; overlap stays default.
See [comparison](../evaluation/development/BM25_COMPARISON.md).

## Motivation and hypothesis

The provisional draft-v2 top-five run missed the three direct-implementation
targets while returning related documentation. Distinct-term overlap treats common
words and distinctive terms alike and does not account for chunk length. BM25 is
a justified candidate to compare, not an assumed improvement or a reason to alter
labels retrospectively. The three exposed Codex-authored cases cannot establish
general quality, held-out performance, or independent human relevance.

BM25 uses corpus term rarity, diminishing returns from repeated term occurrences,
and length normalization. In this application, each chunk acts as a document and
the saved chunks form the collection. Long useful code can be penalized, and a rare
term can still occur in irrelevant evidence. Scores remain ranking weights, not
calibrated correctness/answerability probabilities. Vocabulary mismatch remains.

Primary reference: Stephen Robertson and Hugo Zaragoza (2009),
[The Probabilistic Relevance Framework: BM25 and Beyond](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf),
especially sections 3.4–3.5. Read the paper for model assumptions and variants;
this proposal does not claim any off-the-shelf implementation guarantees gains.

## Controlled comparison

- Keep the existing distinct-term baseline available and default initially.
- Keep source export 548076a, snapshot-v2:50bf1719…, draft-v2 input/hash, questions,
  relevance IDs, code-words-v1 tokenization, and k=5 fixed as recorded in the
  provisional results note. Do not rewrite labels after seeing candidate results.
- Explain/record the exact BM25 variant and fixed initial parameter values before
  implementation/evaluation. Do not sweep settings to manufacture a win on three
  development cases. No formal ten-question set is created.
- Implement a local ranker using the existing tokens and explicit corpus statistics,
  without model downloads or services. Preserve no-hit behavior, deterministic
  ties, traceable source, and freshness gating.
- Record algorithm/configuration in search/evaluation reports. Compare returned
  evidence and hit/recall under the existing narrow labels, not unrelated raw score
  magnitudes. Keep setup/ranking/request timing boundaries clear.
- Retain the original run. Report regressions, ties, and unchanged outcomes as well
  as improvements, with the same draft-label/human-review limitations.

## Teaching checkpoint and next step

Explain term rarity, frequency saturation (repetition has diminishing benefit), and
length normalization before coding. Ask why a term in almost every chunk should
be less useful for distinguishing results than a term in only a few chunks. Wait
for the learner's response, then implement one small, tested ranking component.
Do not add semantic retrieval or silently replace the baseline in parallel.

## Fixed candidate specification before implementation/results

The learner requested progression/publication after the rarity question. Codex
explained that common terms carry less distinguishing information. Independent
reasoning remains unverified. The following is the fixed initial candidate,
recorded before coding or observing candidate results; there will be no parameter
sweep on these three development cases.

- Algorithm/version: bm25-positive-idf-v1, k1=1.2, b=0.75.
- Each nonempty tokenized chunk is one document. Token-empty chunks are omitted
  from N and average length. Length and TF count occurrences emitted by existing
  code-words-v1, including full-identifier/split expansions; no tokenizer change.
- Query terms are unique as in the baseline; do not multiply repeated query terms.
- df is the number of these documents containing a term. Use natural logarithm:
  IDF(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5)).
- Contribution = IDF(t) * tf(t,d) * (k1+1) /
  (tf(t,d) + k1 * (1-b + b * length(d)/average_length)). Sum matched terms.
- Unmatched/empty queries yield no hits. Ties retain path/line/ID ordering.
  Scores are positive ranking weights, not match counts or probabilities.
- No stemming, stopword removal, definition boost, model, service, or dependency.
  Preserve overlap as default; expose the candidate explicitly for comparison.
- Search/evaluation must record method/version/parameters and retain freshness
  gates. The source snapshot/IDs need not change because lexical indexes are not
  persisted. Raw score magnitudes from the two methods are not comparable.

The IDF convention and initial k1/b values follow the documented choices in
[Apache Lucene BM25Similarity](https://lucene.apache.org/core/10_3_1/core/org/apache/lucene/search/similarities/BM25Similarity.html).
This implementation is not claimed bit-compatible with Lucene: token expansion,
length handling, and absence of Lucene index norms differ. Keep those choices
explicit and versioned. These are starting constants, not tuned GitContext optima.
