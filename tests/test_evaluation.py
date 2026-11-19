import pytest

from gitcontext.evaluation import metrics_at_k


def test_hit_can_be_true_while_recall_is_incomplete():
    result = metrics_at_k(["a", "x"], {"a", "b"}, k=2, status="current")
    assert result.hit_at_k is True
    assert result.recall_at_k == 0.5
    assert result.matched_relevant_count == 1
    assert result.relevant_count == 2


def test_cutoff_applies_before_matching_and_recall_uses_all_labels():
    first = metrics_at_k(["x", "a", "b"], {"a", "b"}, k=1, status="current")
    assert first.hit_at_k is False and first.recall_at_k == 0.0
    second = metrics_at_k(["x", "a", "b"], {"a", "b"}, k=2, status="current")
    assert second.recall_at_k == 0.5
    assert second.retrieved_count == 2
    assert second.relevant_count == 2


def test_fewer_than_k_and_empty_current_results_are_valid():
    result = metrics_at_k(["a"], {"a"}, k=5, status="current")
    assert result.retrieved_count == 1 and result.recall_at_k == 1.0
    empty = metrics_at_k([], {"a"}, k=5, status="current")
    assert empty.hit_at_k is False and empty.recall_at_k == 0.0


@pytest.mark.parametrize("retrieved", [[], ["x"]])
def test_empty_labels_do_not_become_perfect_recall_or_implied_unsupported(retrieved):
    result = metrics_at_k(retrieved, set(), k=5, status="current")
    assert result.hit_at_k is None and result.recall_at_k is None
    assert result.relevant_count == 0


@pytest.mark.parametrize("status", ["stale", "unknown", "error"])
def test_blocked_and_error_states_remain_unscored(status):
    result = metrics_at_k([], {"a"}, k=5, status=status)
    assert result.status == status
    assert result.hit_at_k is None and result.recall_at_k is None
    assert result.matched_relevant_count is None
    with pytest.raises(ValueError, match="cannot contain evidence"):
        metrics_at_k(["a"], {"a"}, k=5, status=status)


@pytest.mark.parametrize(
    "retrieved,relevant",
    [
        (["a", "a"], {"a"}),
        (["a"], ["a", "a"]),
        ([""], {"a"}),
        (["a"], [None]),
        ("a", {"a"}),
        (["a"], "a"),
    ],
)
def test_malformed_or_duplicate_ids_are_rejected(retrieved, relevant):
    with pytest.raises(ValueError):
        metrics_at_k(retrieved, relevant, k=5, status="current")


@pytest.mark.parametrize("k", [0, -1, True, 1.5])
def test_invalid_k(k):
    with pytest.raises(ValueError):
        metrics_at_k([], set(), k=k, status="current")


def test_invalid_status():
    with pytest.raises(ValueError, match="status"):
        metrics_at_k([], set(), k=5, status="apparently-current")
