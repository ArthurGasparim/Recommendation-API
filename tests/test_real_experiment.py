import pandas as pd
import pytest

from experiments.real_runner import (
    RealExperimentRequest,
    _prepare_experiment_context,
    _recommend_content_tags,
    run_real_experiment,
)
from recommender import get_recommendation_item_basedUsu


def measured_frames():
    books = pd.DataFrame(
        {
            "id": list(range(1, 13)),
            "good_id": list(range(101, 113)),
            "title": [f"Book {value}" for value in range(1, 13)],
            "authors": ["Author"] * 12,
            "average_rating": [4.0] * 12,
            "image_url": [""] * 12,
            "tag_id": [[value % 3, (value + 1) % 3] for value in range(1, 13)],
        }
    )
    ratings = []
    for user_id in range(1, 9):
        for offset in range(6):
            book_id = ((user_id + offset - 1) % 12) + 1
            ratings.append(
                {
                    "user_id": user_id,
                    "book_id": book_id,
                    "rating": 5 if offset in (0, 1) else 3 + (offset % 2),
                }
            )
    to_read = pd.DataFrame(columns=["user_id", "book_id"])
    return books, pd.DataFrame(ratings), to_read


def test_observable_attack_is_measured_without_mutating_snapshot():
    books, ratings, to_read = measured_frames()
    original = ratings.copy(deep=True)
    request = RealExperimentRequest(
        model="popularity",
        attack_type="push_attack",
        with_observability=True,
        intensity=0.2,
        seed=7,
        sample_users=5,
        top_k=5,
    )

    result = run_real_experiment(request, books, ratings, to_read)

    assert result["kind"] == "measured_experiment"
    assert result["method"]["database_mutated"] is False
    assert result["observability"]["detected"] is True
    assert result["observability"]["response_applied"] is True
    assert result["data_quality"]["effective"] == result["data_quality"]["baseline"]
    assert 0 <= result["measured"]["ndcg_at_k"] <= 1
    assert result["measured"]["evaluated_users"] == 5
    pd.testing.assert_frame_equal(ratings, original)


def test_attack_without_observability_keeps_attacked_copy_active():
    books, ratings, to_read = measured_frames()
    request = RealExperimentRequest(
        model="item_item",
        attack_type="nuke_attack",
        with_observability=False,
        intensity=0.2,
        seed=11,
        sample_users=5,
        top_k=5,
    )

    result = run_real_experiment(request, books, ratings, to_read)

    assert result["observability"]["detected"] is False
    assert result["observability"]["response_applied"] is False
    assert result["observability"]["action"] == "nenhuma ação automática"
    assert (
        result["data_quality"]["effective"]["users"]
        > result["data_quality"]["baseline"]["users"]
    )
    assert result["attack"]["injected_records"] > 0


def test_data_corruption_remains_visible_without_observability():
    books, ratings, to_read = measured_frames()
    request = RealExperimentRequest(
        model="popularity",
        attack_type="data_corruption",
        with_observability=False,
        intensity=0.2,
        seed=17,
        sample_users=5,
        top_k=5,
    )

    result = run_real_experiment(request, books, ratings, to_read)

    baseline = result["data_quality"]["baseline"]
    attacked = result["data_quality"]["attacked"]
    effective = result["data_quality"]["effective"]
    assert effective == attacked
    assert effective["quality_score"] < baseline["quality_score"]
    assert effective["invalid_records"] > 0
    assert effective["orphan_records"] > 0
    assert effective["duplicate_records"] > 0


def test_vectorized_content_model_preserves_recommendation_order():
    books, ratings, to_read = measured_frames()
    request = RealExperimentRequest(
        model="content_tags",
        attack_type="push_attack",
        with_observability=False,
        intensity=0.1,
        seed=29,
        sample_users=5,
        top_k=5,
    )
    context = _prepare_experiment_context(request, books, ratings, to_read)

    for user_id in context.cohort:
        original = get_recommendation_item_basedUsu(
            user_id,
            context.books,
            context.training,
            context.to_read,
            count=request.top_k,
        )
        vectorized = _recommend_content_tags(
            user_id,
            context.training,
            request.top_k,
            context.content_index,
            context.wanted_by_user.get(user_id, set()),
        )
        assert vectorized == original


@pytest.mark.parametrize(
    "attack_type",
    [
        "data_corruption",
        "distribution_drift",
        "latency_degradation",
        "dependency_outage",
    ],
)
def test_every_controlled_attack_produces_measured_observable_result(attack_type):
    books, ratings, to_read = measured_frames()
    request = RealExperimentRequest(
        model="popularity",
        attack_type=attack_type,
        with_observability=True,
        intensity=0.1,
        seed=23,
        sample_users=5,
        top_k=5,
    )

    result = run_real_experiment(request, books, ratings, to_read)

    assert result["attack"]["type"] == attack_type
    assert result["observability"]["detected"] is True
    assert result["observability"]["response_applied"] is True
    assert result["observability"]["action"] != "nenhuma ação automática"
    assert result["timing"]["total_seconds"] >= 0
    assert 0 <= result["measured"]["availability_percent"] <= 100
    assert 0 <= result["measured"]["ndcg_at_k"] <= 1
