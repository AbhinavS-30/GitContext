"""Validate future evaluation records, without creating labels or running queries."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from gitcontext.lexical import MAX_QUERY_CHARACTERS
from gitcontext.snapshots import Snapshot

NonBlank = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]


class EvaluationCase(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    case_id: NonBlank
    question: Annotated[NonBlank, Field(max_length=MAX_QUERY_CHARACTERS)]
    split: Literal["development", "held_out"]
    expected_behavior: Literal["supported", "unsupported", "undetermined"]
    label_status: Literal["labelled", "unlabelled"]
    relevant_chunk_ids: tuple[NonBlank, ...]
    label_author: NonBlank | None
    review_status: Literal["not_reviewed", "codex_reviewed", "human_reviewed"]
    reviewer: NonBlank | None

    @model_validator(mode="after")
    def consistent_labels(self) -> Self:
        if len(set(self.relevant_chunk_ids)) != len(self.relevant_chunk_ids):
            raise ValueError("Duplicate relevant chunk IDs")
        if self.label_status == "unlabelled":
            if (
                self.expected_behavior != "undetermined"
                or self.relevant_chunk_ids
                or self.label_author is not None
                or self.review_status != "not_reviewed"
                or self.reviewer is not None
            ):
                raise ValueError(
                    "Unlabelled cases cannot imply relevance or reviewed expectations"
                )
        else:
            if self.label_author is None or self.expected_behavior == "undetermined":
                raise ValueError(
                    "Labelled cases require an author and explicit expectation"
                )
            if self.expected_behavior == "supported" and not self.relevant_chunk_ids:
                raise ValueError("Supported labelled cases require relevant evidence")
            if self.expected_behavior == "unsupported" and self.relevant_chunk_ids:
                raise ValueError(
                    "Unsupported cases cannot have positive relevance labels"
                )
        if self.review_status == "not_reviewed" and self.reviewer is not None:
            raise ValueError("Unreviewed cases cannot name a reviewer")
        if self.review_status != "not_reviewed" and self.reviewer is None:
            raise ValueError("Reviewed cases require an explicit reviewer")
        return self


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    schema_version: Literal["evaluation-input-v1"]
    dataset_id: NonBlank
    dataset_version: NonBlank
    snapshot_id: NonBlank
    labeling_rules: NonBlank
    limitations: tuple[NonBlank, ...]
    cases: Annotated[tuple[EvaluationCase, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_case_ids(self) -> Self:
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate evaluation case IDs")
        return self


def validate_evaluation_input(
    raw: str | bytes, snapshot: Snapshot
) -> EvaluationDataset:
    """Parse strict JSON and resolve all supplied labels against this snapshot.

    The snapshot must come from build_snapshot/load_snapshot. This function does
    not establish freshness, label relevance, verify reviewer identity, read a
    file, or invoke retrieval. A future file loader must bound input bytes.
    """
    dataset = EvaluationDataset.model_validate_json(raw, strict=True)
    if dataset.snapshot_id != snapshot.snapshot_id:
        raise ValueError("Evaluation labels belong to a different snapshot")
    if snapshot.manifest.partial:
        raise ValueError("Evaluation requires a complete source baseline")
    available = {item.chunk_id for item in snapshot.chunks}
    for case in dataset.cases:
        if not set(case.relevant_chunk_ids) <= available:
            raise ValueError(f"Unknown relevant chunk ID in case {case.case_id}")
    return dataset
