from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.preprocessing import normalize


DEFAULT_RECOMMENDATION_COUNT = 5


@dataclass(frozen=True)
class CollaborativeModel:
    user_item: csr_matrix
    normalized_items: csr_matrix
    user_to_row: dict[int, int]
    book_to_column: dict[int, int]
    book_ids: np.ndarray


def create_useful_book_dataframe(
    books_dirty_df: pd.DataFrame,
    tags_df: pd.DataFrame | None = None,
    books_tags_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Seleciona somente as colunas usadas pela aplicação.

    Os parâmetros de tags são aceitos por compatibilidade, mas a associação é
    feita posteriormente usando ``good_id`` para preservar a integridade dos IDs.
    """
    required_columns = {
        "id",
        "book_id",
        "original_title",
        "authors",
        "average_rating",
        "image_url",
    }
    missing = required_columns.difference(books_dirty_df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes em books.csv: {sorted(missing)}")

    books_df = pd.DataFrame(
        {
            "id": books_dirty_df["id"].astype(int),
            "good_id": books_dirty_df["book_id"].astype(int),
            "title": books_dirty_df["original_title"].fillna(
                books_dirty_df.get("title", "")
            ),
            "authors": books_dirty_df["authors"].fillna("Autor desconhecido"),
            "average_rating": pd.to_numeric(
                books_dirty_df["average_rating"], errors="coerce"
            ).fillna(0.0),
            "image_url": books_dirty_df["image_url"].fillna(""),
        }
    )
    return books_df


def attach_tags_to_books(
    books_df: pd.DataFrame, books_tags_df: pd.DataFrame
) -> pd.DataFrame:
    """Associa tags aos livros usando o ID externo do Goodreads."""
    result = books_df.copy()
    if result.empty:
        result["tag_id"] = pd.Series(dtype=object)
        return result
    if books_tags_df.empty:
        result["tag_id"] = [[] for _ in range(len(result))]
        return result

    grouped_tags = (
        books_tags_df.groupby("goodreads_book_id")["tag_id"]
        .apply(lambda values: sorted({int(value) for value in values}))
        .rename("tag_id")
    )
    result = result.merge(
        grouped_tags,
        how="left",
        left_on="good_id",
        right_index=True,
    )
    result["tag_id"] = result["tag_id"].apply(
        lambda value: value if isinstance(value, list) else []
    )
    return result


def build_collaborative_model(ratings_df: pd.DataFrame) -> CollaborativeModel | None:
    """Cria uma representação esparsa item-usuário sem matriz N x N densa."""
    if ratings_df.empty:
        return None

    required_columns = {"user_id", "book_id", "rating"}
    missing = required_columns.difference(ratings_df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes nas avaliações: {sorted(missing)}")

    clean = ratings_df.loc[:, ["user_id", "book_id", "rating"]].copy()
    clean = clean.dropna().astype(
        {"user_id": int, "book_id": int, "rating": float}
    )
    clean = clean[clean["rating"].between(1, 5)]
    if clean.empty:
        return None

    # Garante uma única nota por par mesmo se uma fonte externa contiver duplicatas.
    clean = clean.groupby(["user_id", "book_id"], as_index=False)["rating"].mean()
    user_ids = np.sort(clean["user_id"].unique())
    book_ids = np.sort(clean["book_id"].unique())
    user_to_row = {int(user_id): index for index, user_id in enumerate(user_ids)}
    book_to_column = {
        int(book_id): index for index, book_id in enumerate(book_ids)
    }

    rows = clean["user_id"].map(user_to_row).to_numpy()
    columns = clean["book_id"].map(book_to_column).to_numpy()
    values = clean["rating"].to_numpy(dtype=float)
    user_item = csr_matrix(
        (values, (rows, columns)), shape=(len(user_ids), len(book_ids))
    )
    normalized_items = normalize(user_item.T.tocsr(), norm="l2", axis=1)
    return CollaborativeModel(
        user_item=user_item,
        normalized_items=normalized_items,
        user_to_row=user_to_row,
        book_to_column=book_to_column,
        book_ids=book_ids.astype(int),
    )


def _tag_set(value: object) -> set[int]:
    if isinstance(value, (list, tuple, set, np.ndarray)):
        return {int(tag) for tag in value}
    return set()


def _tag_similarity(first: Iterable[int], second: Iterable[int]) -> float:
    first_set = set(first)
    second_set = set(second)
    union = first_set | second_set
    return len(first_set & second_set) / len(union) if union else 0.0


def _popular_books(
    books_df: pd.DataFrame, excluded_ids: set[int], count: int
) -> list[int]:
    if books_df.empty:
        return []
    candidates = books_df[~books_df["id"].astype(int).isin(excluded_ids)].copy()
    candidates["average_rating"] = pd.to_numeric(
        candidates["average_rating"], errors="coerce"
    ).fillna(0.0)
    return (
        candidates.sort_values(["average_rating", "id"], ascending=[False, True])
        .head(count)["id"]
        .astype(int)
        .tolist()
    )


def get_recommendation_item_based(
    book_id: int,
    books_df: pd.DataFrame,
    count: int = DEFAULT_RECOMMENDATION_COUNT,
) -> list[int]:
    """Recomenda livros por conteúdo, excluindo o próprio livro consultado."""
    selected = books_df[books_df["id"].astype(int) == int(book_id)]
    if selected.empty:
        raise ValueError("Livro não encontrado no modelo de recomendação")

    selected_tags = _tag_set(selected.iloc[0].get("tag_id", []))
    candidates: list[tuple[int, float]] = []
    for _, candidate in books_df.iterrows():
        candidate_id = int(candidate["id"])
        if candidate_id == int(book_id):
            continue
        similarity = _tag_similarity(
            selected_tags, _tag_set(candidate.get("tag_id", []))
        )
        average_rating = float(candidate.get("average_rating", 0) or 0)
        score = 0.7 * similarity + 0.3 * max(0.0, min(5.0, average_rating)) / 5
        candidates.append((candidate_id, score))

    candidates.sort(key=lambda item: (-item[1], item[0]))
    return [book for book, _ in candidates[:count]]


def get_recommendation_item_basedUsu(
    user_id: int,
    books_df: pd.DataFrame,
    ratings_df: pd.DataFrame,
    to_read_df: pd.DataFrame,
    count: int = DEFAULT_RECOMMENDATION_COUNT,
) -> list[int]:
    """Recomenda por conteúdo a partir dos livros mais bem avaliados pelo usuário."""
    user_ratings = ratings_df[
        ratings_df["user_id"].astype(int) == int(user_id)
    ].copy()
    user_ratings = user_ratings.sort_values("rating", ascending=False)
    already_rated = set(user_ratings["book_id"].astype(int).tolist())
    if user_ratings.empty:
        return _popular_books(books_df, already_rated, count)

    book_by_id = books_df.set_index(books_df["id"].astype(int), drop=False)
    seeds: list[tuple[set[int], float]] = []
    for row in user_ratings.head(5).itertuples(index=False):
        seed_id = int(row.book_id)
        if seed_id not in book_by_id.index:
            continue
        seed = book_by_id.loc[seed_id]
        seeds.append((_tag_set(seed.get("tag_id", [])), float(row.rating) / 5))
    if not seeds:
        return _popular_books(books_df, already_rated, count)

    wanted = set(
        to_read_df[to_read_df["user_id"].astype(int) == int(user_id)]["book_id"]
        .astype(int)
        .tolist()
    )
    candidates: list[tuple[int, float]] = []
    for _, candidate in books_df.iterrows():
        candidate_id = int(candidate["id"])
        if candidate_id in already_rated:
            continue
        candidate_tags = _tag_set(candidate.get("tag_id", []))
        weighted_similarities = [
            _tag_similarity(tags, candidate_tags) * weight for tags, weight in seeds
        ]
        content_score = sum(weighted_similarities) / max(
            1.0, sum(weight for _, weight in seeds)
        )
        average_rating = float(candidate.get("average_rating", 0) or 0)
        wanted_bonus = 0.1 if candidate_id in wanted else 0.0
        score = (
            0.7 * content_score
            + 0.2 * max(0.0, min(5.0, average_rating)) / 5
            + wanted_bonus
        )
        candidates.append((candidate_id, score))

    candidates.sort(key=lambda item: (-item[1], item[0]))
    return [book for book, _ in candidates[:count]]


def get_recommendation_user_based(
    user_id: int,
    ratings_df: pd.DataFrame,
    books_df: pd.DataFrame,
    rating_matrix: pd.DataFrame | None = None,
    item_similarity: object | None = None,
    collaborative_model: CollaborativeModel | None = None,
    count: int = DEFAULT_RECOMMENDATION_COUNT,
) -> list[int]:
    """Recomenda por filtragem colaborativa item-item e retorna IDs reais."""
    model = collaborative_model or build_collaborative_model(ratings_df)
    if model is None or int(user_id) not in model.user_to_row:
        return _popular_books(books_df, set(), count)

    user_row = model.user_item.getrow(model.user_to_row[int(user_id)])
    rated_columns = user_row.indices
    if rated_columns.size == 0:
        return _popular_books(books_df, set(), count)

    ratings = user_row.data.astype(float)
    similarities = (
        model.normalized_items @ model.normalized_items[rated_columns].T
    ).toarray()
    scores = similarities @ ratings
    denominator = np.abs(similarities).sum(axis=1)
    scores = np.divide(
        scores,
        denominator,
        out=np.zeros_like(scores, dtype=float),
        where=denominator > 0,
    )
    scores[rated_columns] = -np.inf

    available_book_ids = set(books_df["id"].astype(int).tolist())
    ranked_columns = np.argsort(scores)[::-1]
    recommendations: list[int] = []
    for column in ranked_columns:
        if not np.isfinite(scores[column]) or scores[column] <= 0:
            continue
        book_id = int(model.book_ids[column])
        if book_id in available_book_ids:
            recommendations.append(book_id)
        if len(recommendations) == count:
            break

    if len(recommendations) < count:
        excluded = set(model.book_ids[rated_columns].astype(int)) | set(recommendations)
        recommendations.extend(
            _popular_books(books_df, excluded, count - len(recommendations))
        )
    return recommendations
