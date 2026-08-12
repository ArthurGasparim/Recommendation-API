import pandas as pd

from recommender import (
    build_collaborative_model,
    get_recommendation_item_based,
    get_recommendation_item_basedUsu,
    get_recommendation_user_based,
)


def sample_books():
    return pd.DataFrame(
        {
            "id": [10, 20, 30, 40],
            "good_id": [110, 120, 130, 140],
            "title": ["A", "B", "C", "D"],
            "authors": ["Author"] * 4,
            "average_rating": [4.8, 4.5, 4.0, 3.0],
            "image_url": [""] * 4,
            "tag_id": [[1, 2], [1, 2, 3], [4], [5]],
        }
    )


def test_content_recommendation_excludes_selected_book():
    result = get_recommendation_item_based(10, sample_books(), count=3)

    assert 10 not in result
    assert result[0] == 20


def test_profile_content_recommendation_uses_records_not_integer_ids():
    ratings = pd.DataFrame(
        {"user_id": [1], "book_id": [10], "rating": [5]}
    )
    to_read = pd.DataFrame({"user_id": [1], "book_id": [30]})

    result = get_recommendation_item_basedUsu(
        1, sample_books(), ratings, to_read, count=3
    )

    assert 10 not in result
    assert set(result).issubset({20, 30, 40})


def test_collaborative_recommendation_returns_real_book_ids():
    ratings = pd.DataFrame(
        {
            "user_id": [1, 2, 2, 3, 3],
            "book_id": [10, 10, 20, 10, 30],
            "rating": [5, 5, 5, 4, 5],
        }
    )
    model = build_collaborative_model(ratings)

    result = get_recommendation_user_based(
        1,
        ratings,
        sample_books(),
        collaborative_model=model,
        count=3,
    )

    assert 10 not in result
    assert result[0] in {20, 30}
    assert set(result).issubset({20, 30, 40})


def test_unknown_user_receives_cold_start_ranking():
    result = get_recommendation_user_based(
        999,
        pd.DataFrame(columns=["user_id", "book_id", "rating"]),
        sample_books(),
        count=2,
    )

    assert result == [10, 20]

