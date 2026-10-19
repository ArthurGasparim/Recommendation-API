"""Execução controlada de experimentos sobre o snapshot real do banco.

O módulo nunca altera os DataFrames recebidos. Ataques são aplicados a cópias
do conjunto de treino e as medições são devolvidas como um documento JSON
persistível. O objetivo é oferecer um experimento curto e seguro para o painel
administrativo; execuções científicas extensas continuam podendo reutilizar as
mesmas funções em lote.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import chain
from typing import Callable, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator
from scipy.sparse import csr_matrix

from recommender import (
    build_collaborative_model,
    get_recommendation_user_based,
)


RealModel = Literal["popularity", "content_tags", "item_item"]
RealAttack = Literal[
    "push_attack",
    "nuke_attack",
    "data_corruption",
    "distribution_drift",
    "latency_degradation",
    "dependency_outage",
]


class RealExperimentRequest(BaseModel):
    model: RealModel = "item_item"
    attack_type: RealAttack = "push_attack"
    with_observability: bool = True
    intensity: float = Field(default=0.05, ge=0.01, le=0.30)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    sample_users: int = Field(default=20, ge=5, le=100)
    top_k: int = Field(default=10, ge=5, le=20)
    target_book_id: int | None = Field(default=None, gt=0)

    @field_validator("intensity")
    @classmethod
    def stable_intensity(cls, value: float) -> float:
        return round(float(value), 4)


class RealExperimentSuiteRequest(BaseModel):
    """Configuração comum usada em todas as combinações do lote."""

    intensity: float = Field(default=0.05, ge=0.01, le=0.30)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    sample_users: int = Field(default=20, ge=5, le=100)
    top_k: int = Field(default=10, ge=5, le=20)
    target_book_id: int | None = Field(default=None, gt=0)

    @field_validator("intensity")
    @classmethod
    def stable_intensity(cls, value: float) -> float:
        return round(float(value), 4)


MODEL_CATALOG = [
    {
        "id": "popularity",
        "label": "Popularidade regularizada",
        "description": "Baseline real calculado a partir das avaliações do snapshot.",
    },
    {
        "id": "content_tags",
        "label": "Conteúdo por tags",
        "description": "Modelo funcional atual baseado em tags e perfil do usuário.",
    },
    {
        "id": "item_item",
        "label": "Colaborativo item-item",
        "description": "Matriz esparsa e similaridade item-item do backend atual.",
    },
]


ATTACK_CATALOG = [
    {
        "id": "push_attack",
        "label": "Push attack",
        "description": "Perfis artificiais atribuem nota máxima a um livro-alvo.",
    },
    {
        "id": "nuke_attack",
        "label": "Nuke attack",
        "description": "Perfis artificiais atribuem nota mínima a um livro-alvo.",
    },
    {
        "id": "data_corruption",
        "label": "Corrupção de dados",
        "description": "Introduz duplicatas, notas fora do domínio e referências órfãs.",
    },
    {
        "id": "distribution_drift",
        "label": "Drift de distribuição",
        "description": "Desloca uma fração controlada das avaliações para notas altas.",
    },
    {
        "id": "latency_degradation",
        "label": "Degradação de latência",
        "description": "Injeta atraso real nas consultas do experimento.",
    },
    {
        "id": "dependency_outage",
        "label": "Indisponibilidade",
        "description": "Injeta falhas controladas e testa o fallback após detecção.",
    },
]


@dataclass(frozen=True)
class _ContentTagIndex:
    """Representação vetorial reutilizável dos livros e de suas tags."""

    book_ids: np.ndarray
    book_to_row: dict[int, int]
    tag_matrix: csr_matrix
    tag_counts: np.ndarray
    average_ratings: np.ndarray


@dataclass(frozen=True)
class _ExperimentContext:
    """Recorte imutável compartilhado por toda a bateria."""

    books: pd.DataFrame
    ratings: pd.DataFrame
    to_read: pd.DataFrame
    valid_book_ids: set[int]
    training: pd.DataFrame
    held_out: dict[int, int]
    cohort: list[int]
    target_book_id: int
    content_index: _ContentTagIndex
    wanted_by_user: dict[int, set[int]]


def real_experiment_catalog() -> dict:
    return {
        "kind": "measured_experiment",
        "disclaimer": (
            "As métricas são medidas sobre uma cópia controlada do snapshot real. "
            "O banco principal não é alterado pelo ataque."
        ),
        "models": MODEL_CATALOG,
        "attacks": ATTACK_CATALOG,
        "default_request": RealExperimentRequest().model_dump(),
        "suite": {
            "models": len(MODEL_CATALOG),
            "attacks": len(ATTACK_CATALOG),
            "comparisons": len(MODEL_CATALOG) * len(ATTACK_CATALOG),
            "scenario_runs": len(MODEL_CATALOG) * len(ATTACK_CATALOG) * 2,
            "default_request": RealExperimentSuiteRequest().model_dump(),
        },
    }


def _clean_ratings(ratings_df: pd.DataFrame, valid_book_ids: set[int]) -> pd.DataFrame:
    required = {"user_id", "book_id", "rating"}
    missing = required.difference(ratings_df.columns)
    if missing:
        raise ValueError(f"Avaliações sem colunas obrigatórias: {sorted(missing)}")
    clean = ratings_df.loc[:, ["user_id", "book_id", "rating"]].copy()
    for column in ("user_id", "book_id", "rating"):
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
    clean = clean.dropna()
    clean = clean[
        clean["book_id"].isin(valid_book_ids)
        & clean["rating"].between(1, 5)
        & (clean["user_id"] > 0)
    ]
    clean = clean.astype({"user_id": int, "book_id": int, "rating": float})
    return clean.groupby(["user_id", "book_id"], as_index=False, sort=False)[
        "rating"
    ].mean()


def _prepare_evaluation(
    ratings_df: pd.DataFrame,
    sample_users: int,
    seed: int,
) -> tuple[pd.DataFrame, dict[int, int], list[int]]:
    rng = np.random.default_rng(seed)
    grouped = ratings_df.groupby("user_id")["rating"]
    counts = grouped.size()
    relevant = grouped.apply(lambda values: int((values >= 4).sum()))
    eligible = counts[(counts >= 5) & (relevant >= 1)].index.to_numpy(dtype=int)
    if len(eligible) < 5:
        raise ValueError(
            "São necessários ao menos cinco usuários com cinco avaliações e um item relevante"
        )

    cohort_size = min(sample_users, len(eligible))
    cohort = sorted(rng.choice(eligible, size=cohort_size, replace=False).tolist())
    all_users = ratings_df["user_id"].drop_duplicates().to_numpy(dtype=int)
    population_size = min(len(all_users), max(500, cohort_size * 20))
    remaining = np.setdiff1d(all_users, np.asarray(cohort), assume_unique=False)
    extra_size = max(0, population_size - cohort_size)
    extra = (
        rng.choice(remaining, size=min(extra_size, len(remaining)), replace=False)
        if extra_size
        else np.asarray([], dtype=int)
    )
    population = np.unique(np.concatenate([np.asarray(cohort), extra])).astype(int)
    training = ratings_df[ratings_df["user_id"].isin(population)].copy()

    held_out: dict[int, int] = {}
    indexes_to_remove: list[int] = []
    for user_id in cohort:
        candidates = training[
            (training["user_id"] == user_id) & (training["rating"] >= 4)
        ]
        chosen_index = int(rng.choice(candidates.index.to_numpy()))
        held_out[user_id] = int(training.loc[chosen_index, "book_id"])
        indexes_to_remove.append(chosen_index)

    training = training.drop(index=indexes_to_remove).reset_index(drop=True)
    return training, held_out, cohort


def _target_book(training: pd.DataFrame, requested: int | None) -> int:
    available = set(training["book_id"].astype(int))
    if requested is not None:
        if requested not in available:
            raise ValueError("O livro-alvo não possui avaliações no recorte experimental")
        return requested
    return int(training["book_id"].value_counts().index[0])


def _tag_values(value: object) -> tuple[int, ...]:
    if isinstance(value, (list, tuple, set, np.ndarray)):
        return tuple(sorted({int(tag) for tag in value}))
    return ()


def _build_content_tag_index(books_df: pd.DataFrame) -> _ContentTagIndex:
    """Monta uma matriz livro × tag uma única vez por experimento."""

    book_ids = books_df["id"].astype(int).to_numpy()
    book_to_row = {int(book_id): row for row, book_id in enumerate(book_ids)}
    tag_lists = tuple(_tag_values(value) for value in books_df["tag_id"])
    unique_tags = sorted(set(chain.from_iterable(tag_lists)))
    tag_to_column = {tag_id: column for column, tag_id in enumerate(unique_tags)}
    lengths = np.fromiter((len(tags) for tags in tag_lists), dtype=np.int32)
    nonzero_count = int(lengths.sum())
    if nonzero_count:
        rows = np.repeat(np.arange(len(book_ids), dtype=np.int32), lengths)
        columns = np.fromiter(
            (
                tag_to_column[tag_id]
                for tags in tag_lists
                for tag_id in tags
            ),
            dtype=np.int32,
            count=nonzero_count,
        )
        tag_matrix = csr_matrix(
            (
                np.ones(nonzero_count, dtype=np.float32),
                (rows, columns),
            ),
            shape=(len(book_ids), len(unique_tags)),
            dtype=np.float32,
        )
    else:
        tag_matrix = csr_matrix((len(book_ids), 0), dtype=np.float32)
    average_ratings = (
        pd.to_numeric(books_df["average_rating"], errors="coerce")
        .fillna(0.0)
        .clip(0.0, 5.0)
        .to_numpy(dtype=float)
    )
    return _ContentTagIndex(
        book_ids=book_ids,
        book_to_row=book_to_row,
        tag_matrix=tag_matrix,
        tag_counts=lengths.astype(float),
        average_ratings=average_ratings,
    )


def _wanted_books_by_user(
    to_read_df: pd.DataFrame, cohort: list[int]
) -> dict[int, set[int]]:
    if to_read_df.empty or not {"user_id", "book_id"}.issubset(to_read_df.columns):
        return {}
    selected = to_read_df[to_read_df["user_id"].isin(cohort)][
        ["user_id", "book_id"]
    ].copy()
    if selected.empty:
        return {}
    return {
        int(user_id): {int(book_id) for book_id in values}
        for user_id, values in selected.groupby("user_id")["book_id"]
    }


def _prepare_experiment_context(
    request: RealExperimentRequest | RealExperimentSuiteRequest,
    books_df: pd.DataFrame,
    ratings_df: pd.DataFrame,
    to_read_df: pd.DataFrame,
) -> _ExperimentContext:
    if books_df.empty or ratings_df.empty:
        raise ValueError("Carregue os CSVs no banco antes de executar o experimento")
    books = books_df.copy(deep=True)
    ratings_snapshot = ratings_df.copy(deep=True)
    to_read = to_read_df.copy(deep=True)
    valid_book_ids = set(books["id"].astype(int))
    ratings = _clean_ratings(ratings_snapshot, valid_book_ids)
    training, held_out, cohort = _prepare_evaluation(
        ratings, request.sample_users, request.seed
    )
    return _ExperimentContext(
        books=books,
        ratings=ratings,
        to_read=to_read,
        valid_book_ids=valid_book_ids,
        training=training,
        held_out=held_out,
        cohort=cohort,
        target_book_id=_target_book(training, request.target_book_id),
        content_index=_build_content_tag_index(books),
        wanted_by_user=_wanted_books_by_user(to_read, cohort),
    )


def _inject_attack(
    training: pd.DataFrame,
    request: RealExperimentRequest,
    target_book_id: int,
    valid_book_ids: set[int],
) -> tuple[pd.DataFrame, dict]:
    attacked = training.copy(deep=True)
    rng = np.random.default_rng(request.seed + 991)
    metadata: dict[str, int | float | str] = {"injected_records": 0}

    if request.attack_type in {"push_attack", "nuke_attack"}:
        user_count = training["user_id"].nunique()
        synthetic_count = max(1, math.ceil(user_count * request.intensity))
        first_user_id = int(training["user_id"].max()) + 10_000
        filler_books = [
            int(book_id)
            for book_id in training["book_id"].value_counts().index
            if int(book_id) != target_book_id
        ][:5]
        artificial_rows = []
        for user_id in range(first_user_id, first_user_id + synthetic_count):
            artificial_rows.append(
                {
                    "user_id": user_id,
                    "book_id": target_book_id,
                    "rating": 5.0 if request.attack_type == "push_attack" else 1.0,
                }
            )
            artificial_rows.extend(
                {
                    "user_id": user_id,
                    "book_id": filler_book,
                    "rating": 4.0 if request.attack_type == "push_attack" else 5.0,
                }
                for filler_book in filler_books
            )
        artificial = pd.DataFrame(artificial_rows)
        attacked = pd.concat([attacked, artificial], ignore_index=True)
        metadata.update(
            injected_records=len(artificial),
            synthetic_users=synthetic_count,
            filler_books=len(filler_books),
        )

    elif request.attack_type == "data_corruption":
        amount = max(3, math.ceil(len(training) * request.intensity))
        sample = training.sample(
            n=min(amount, len(training)), random_state=request.seed
        ).copy()
        third = max(1, len(sample) // 3)
        sample.iloc[:third, sample.columns.get_loc("rating")] = 9.0
        sample.iloc[third : third * 2, sample.columns.get_loc("book_id")] = (
            max(valid_book_ids) + 100_000
        )
        if third * 2 < len(sample):
            sample.iloc[third * 2 :, sample.columns.get_loc("rating")] = 5.0
        attacked = pd.concat([attacked, sample], ignore_index=True)
        metadata.update(injected_records=len(sample), corrupted_records=len(sample))

    elif request.attack_type == "distribution_drift":
        amount = max(1, math.ceil(len(attacked) * request.intensity))
        indexes = rng.choice(attacked.index.to_numpy(), size=min(amount, len(attacked)), replace=False)
        attacked.loc[indexes, "rating"] = 5.0
        metadata.update(injected_records=len(indexes), modified_records=len(indexes))

    else:
        metadata["injected_requests"] = max(1, math.ceil(len(training) * request.intensity))

    return attacked, metadata


def _data_quality(frame: pd.DataFrame, valid_book_ids: set[int]) -> dict:
    total = max(1, len(frame))
    numeric_ratings = pd.to_numeric(frame["rating"], errors="coerce")
    numeric_users = pd.to_numeric(frame["user_id"], errors="coerce")
    numeric_books = pd.to_numeric(frame["book_id"], errors="coerce")
    invalid = (
        numeric_ratings.isna()
        | ~numeric_ratings.between(1, 5)
        | numeric_users.isna()
        | (numeric_users <= 0)
        | numeric_books.isna()
    )
    orphan = ~numeric_books.isin(valid_book_ids)
    duplicate = frame.duplicated(["user_id", "book_id"], keep=False)
    invalid_rate = float(invalid.mean())
    orphan_rate = float(orphan.mean())
    duplicate_rate = float(duplicate.mean())
    score = max(0.0, 1.0 - invalid_rate - orphan_rate - duplicate_rate)
    return {
        "records": int(len(frame)),
        "users": int(frame["user_id"].nunique()),
        "invalid_rate": round(invalid_rate, 6),
        "orphan_rate": round(orphan_rate, 6),
        "duplicate_rate": round(duplicate_rate, 6),
        "mean_rating": round(float(numeric_ratings.dropna().mean()), 6),
        "quality_score": round(score, 6),
        "invalid_records": int(invalid.sum()),
        "orphan_records": int(orphan.sum()),
        "duplicate_records": int(duplicate.sum()),
        "total_checked": total,
    }


def _sanitize(frame: pd.DataFrame, valid_book_ids: set[int]) -> pd.DataFrame:
    return _clean_ratings(frame, valid_book_ids)


def _detect(
    attack_type: str,
    before: dict,
    after: dict,
    metadata: dict,
) -> tuple[bool, str, str]:
    if attack_type in {"push_attack", "nuke_attack"}:
        detected = int(metadata.get("synthetic_users", 0)) > 0 and after["users"] > before["users"]
        return detected, "aumento de perfis de interação única", "rollback do lote atacado"
    if attack_type == "data_corruption":
        detected = (
            after["invalid_rate"] > before["invalid_rate"]
            or after["orphan_rate"] > before["orphan_rate"]
            or after["duplicate_rate"] > before["duplicate_rate"]
        )
        return detected, "quebra de domínio, integridade ou unicidade", "quarentena do lote"
    if attack_type == "distribution_drift":
        delta = abs(after["mean_rating"] - before["mean_rating"])
        return delta >= 0.001, "mudança na distribuição das notas", "rollback para o snapshot íntegro"
    if attack_type == "latency_degradation":
        return True, "latência acima do baseline", "circuit breaker e desvio do caminho degradado"
    return True, "falha de dependência", "fallback por popularidade"


def _popular_ranking(training: pd.DataFrame) -> list[int]:
    stats = training.groupby("book_id")["rating"].agg(["count", "mean"])
    global_mean = float(training["rating"].mean())
    minimum_votes = max(1.0, float(stats["count"].quantile(0.75)))
    stats["score"] = (
        stats["count"] / (stats["count"] + minimum_votes) * stats["mean"]
        + minimum_votes / (stats["count"] + minimum_votes) * global_mean
    )
    return stats.sort_values(["score", "count"], ascending=False).index.astype(int).tolist()


def _recommend_content_tags(
    user_id: int,
    training: pd.DataFrame,
    top_k: int,
    content_index: _ContentTagIndex,
    wanted_books: set[int],
) -> list[int]:
    """Calcula Jaccard em lote, sem iterar pelos 10 mil livros em Python."""

    user_ratings = training[training["user_id"] == user_id].sort_values(
        "rating", ascending=False
    )
    seen = set(user_ratings["book_id"].astype(int).tolist())
    seed_rows: list[int] = []
    weights: list[float] = []
    for row in user_ratings.head(5).itertuples(index=False):
        book_row = content_index.book_to_row.get(int(row.book_id))
        if book_row is not None:
            seed_rows.append(book_row)
            weights.append(float(row.rating) / 5.0)

    if seed_rows and content_index.tag_matrix.shape[1]:
        intersections = (
            content_index.tag_matrix
            @ content_index.tag_matrix[np.asarray(seed_rows)].T
        ).toarray()
        seed_counts = content_index.tag_counts[np.asarray(seed_rows)]
        unions = (
            content_index.tag_counts[:, np.newaxis]
            + seed_counts[np.newaxis, :]
            - intersections
        )
        similarities = np.divide(
            intersections,
            unions,
            out=np.zeros_like(intersections, dtype=float),
            where=unions > 0,
        )
        weight_array = np.asarray(weights, dtype=float)
        content_scores = (similarities @ weight_array) / max(
            1.0, float(weight_array.sum())
        )
    else:
        content_scores = np.zeros(len(content_index.book_ids), dtype=float)

    scores = 0.7 * content_scores + 0.2 * content_index.average_ratings / 5.0
    for wanted_id in wanted_books:
        wanted_row = content_index.book_to_row.get(int(wanted_id))
        if wanted_row is not None:
            scores[wanted_row] += 0.1

    eligible = ~np.isin(
        content_index.book_ids,
        np.fromiter(seen, dtype=int) if seen else np.asarray([], dtype=int),
    )
    eligible_rows = np.flatnonzero(eligible)
    order = np.lexsort(
        (
            content_index.book_ids[eligible_rows],
            -scores[eligible_rows],
        )
    )
    return content_index.book_ids[eligible_rows[order[:top_k]]].astype(int).tolist()


def _recommend(
    model: str,
    user_id: int,
    training: pd.DataFrame,
    books_df: pd.DataFrame,
    to_read_df: pd.DataFrame,
    top_k: int,
    popularity: list[int],
    collaborative_model,
    content_index: _ContentTagIndex,
    wanted_by_user: dict[int, set[int]],
) -> list[int]:
    seen = set(
        training[training["user_id"] == user_id]["book_id"].astype(int).tolist()
    )
    if model == "popularity":
        return [book for book in popularity if book not in seen][:top_k]
    if model == "content_tags":
        return _recommend_content_tags(
            user_id,
            training,
            top_k,
            content_index,
            wanted_by_user.get(user_id, set()),
        )
    return get_recommendation_user_based(
        user_id=user_id,
        ratings_df=training,
        books_df=books_df,
        collaborative_model=collaborative_model,
        count=top_k,
    )


def _percentile(values: list[float], percentile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), percentile)) if values else 0.0


def _evaluate(
    request: RealExperimentRequest,
    training: pd.DataFrame,
    books_df: pd.DataFrame,
    to_read_df: pd.DataFrame,
    held_out: dict[int, int],
    cohort: list[int],
    *,
    inject_infrastructure: bool,
    observability_active: bool,
    content_index: _ContentTagIndex,
    wanted_by_user: dict[int, set[int]],
) -> dict:
    popularity = _popular_ranking(training)
    collaborative_model = (
        build_collaborative_model(training) if request.model == "item_item" else None
    )
    rng = np.random.default_rng(request.seed + 313)
    latencies_ms: list[float] = []
    scores: list[float] = []
    hits = 0
    failures = 0
    recommended_items: set[int] = set()
    latency_injections = max(1, math.ceil(len(cohort) * request.intensity))
    outage_probability = max(0.08, min(0.60, request.intensity * 2))

    for index, user_id in enumerate(cohort):
        started = time.perf_counter()
        recommendations: list[int] = []
        failed = False

        if inject_infrastructure and request.attack_type == "latency_degradation":
            should_delay = not observability_active or index < latency_injections
            if should_delay:
                delay_seconds = 0.01 + request.intensity * 0.12
                time.sleep(delay_seconds)

        if inject_infrastructure and request.attack_type == "dependency_outage":
            injected_failure = bool(rng.random() < outage_probability)
            if injected_failure and not observability_active:
                failed = True
            elif injected_failure and observability_active and index == 0:
                failed = True
            elif observability_active:
                seen = set(
                    training[training["user_id"] == user_id]["book_id"].astype(int)
                )
                recommendations = [book for book in popularity if book not in seen][
                    : request.top_k
                ]

        if not failed and not recommendations:
            recommendations = _recommend(
                request.model,
                user_id,
                training,
                books_df,
                to_read_df,
                request.top_k,
                popularity,
                collaborative_model,
                content_index,
                wanted_by_user,
            )

        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies_ms.append(elapsed_ms)
        if failed:
            failures += 1
            scores.append(0.0)
            continue

        recommended_items.update(recommendations)
        relevant_book = held_out[user_id]
        if relevant_book in recommendations:
            rank = recommendations.index(relevant_book) + 1
            hits += 1
            scores.append(1.0 / math.log2(rank + 1))
        else:
            scores.append(0.0)

    users = max(1, len(cohort))
    return {
        "ndcg_at_k": round(float(np.mean(scores)), 6),
        "precision_at_k": round(hits / (users * request.top_k), 6),
        "recall_at_k": round(hits / users, 6),
        "hit_rate_at_k": round(hits / users, 6),
        "catalog_coverage": round(len(recommended_items) / max(1, len(books_df)), 6),
        "latency_p50_ms": round(_percentile(latencies_ms, 50), 3),
        "latency_p95_ms": round(_percentile(latencies_ms, 95), 3),
        "latency_p99_ms": round(_percentile(latencies_ms, 99), 3),
        "availability_percent": round((users - failures) / users * 100, 3),
        "successful_requests": users - failures,
        "failed_requests": failures,
        "evaluated_users": users,
        "unique_recommended_items": len(recommended_items),
    }


def run_real_experiment(
    request: RealExperimentRequest,
    books_df: pd.DataFrame,
    ratings_df: pd.DataFrame,
    to_read_df: pd.DataFrame,
    *,
    _context: _ExperimentContext | None = None,
    _baseline_metrics: dict | None = None,
    _baseline_seconds: float | None = None,
) -> dict:
    started_at = datetime.now(timezone.utc)
    wall_started = time.perf_counter()
    context = _context or _prepare_experiment_context(
        request, books_df, ratings_df, to_read_df
    )
    books = context.books
    ratings = context.ratings
    to_read = context.to_read
    valid_book_ids = context.valid_book_ids
    training = context.training
    held_out = context.held_out
    cohort = context.cohort
    target_book_id = context.target_book_id

    baseline_reused = _baseline_metrics is not None
    if _baseline_metrics is None:
        baseline_started = time.perf_counter()
        baseline_metrics = _evaluate(
            request,
            training,
            books,
            to_read,
            held_out,
            cohort,
            inject_infrastructure=False,
            observability_active=False,
            content_index=context.content_index,
            wanted_by_user=context.wanted_by_user,
        )
        baseline_seconds = time.perf_counter() - baseline_started
    else:
        baseline_metrics = _baseline_metrics
        baseline_seconds = float(_baseline_seconds or 0.0)

    attack_started = time.perf_counter()
    attacked_raw, attack_metadata = _inject_attack(
        training, request, target_book_id, valid_book_ids
    )
    before_quality = _data_quality(training, valid_book_ids)
    attacked_quality = _data_quality(attacked_raw, valid_book_ids)

    detection_started = time.perf_counter()
    detected, signal, action = _detect(
        request.attack_type, before_quality, attacked_quality, attack_metadata
    )
    detection_ms = (time.perf_counter() - detection_started) * 1000
    response_applied = bool(request.with_observability and detected)

    if response_applied and request.attack_type not in {
        "latency_degradation",
        "dependency_outage",
    }:
        effective_training = training.copy(deep=True)
    else:
        # Sem observabilidade, o sistema atacado permanece ativo. Sanitizar
        # silenciosamente este frame esconderia justamente a degradação que a
        # bateria precisa comparar.
        effective_training = attacked_raw.copy(deep=True)
    effective_quality = _data_quality(effective_training, valid_book_ids)
    recovery_ms = (time.perf_counter() - attack_started) * 1000 if response_applied else None

    scenario_started = time.perf_counter()
    scenario_metrics = _evaluate(
        request,
        effective_training,
        books,
        to_read,
        held_out,
        cohort,
        inject_infrastructure=request.attack_type
        in {"latency_degradation", "dependency_outage"},
        observability_active=response_applied,
        content_index=context.content_index,
        wanted_by_user=context.wanted_by_user,
    )
    scenario_seconds = time.perf_counter() - scenario_started

    baseline_ndcg = baseline_metrics["ndcg_at_k"]
    scenario_ndcg = scenario_metrics["ndcg_at_k"]
    latency_base = max(0.000001, baseline_metrics["latency_p95_ms"])
    result = {
        "kind": "measured_experiment",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "configuration": request.model_dump(),
        "dataset": {
            "books": int(len(books)),
            "ratings_snapshot": int(len(ratings)),
            "training_records": int(len(training)),
            "evaluation_users": int(len(cohort)),
            "population_users": int(training["user_id"].nunique()),
            "target_book_id": target_book_id,
        },
        "attack": {
            "type": request.attack_type,
            "intensity": request.intensity,
            **attack_metadata,
        },
        "observability": {
            "enabled": request.with_observability,
            "detected": bool(detected) if request.with_observability else False,
            "response_applied": response_applied,
            "signal": signal if request.with_observability else None,
            "action": action if response_applied else "nenhuma ação automática",
            "detection_ms": round(detection_ms, 3)
            if request.with_observability
            else None,
            "recovery_ms": round(recovery_ms, 3) if recovery_ms is not None else None,
        },
        "data_quality": {
            "baseline": before_quality,
            "attacked": attacked_quality,
            "effective": effective_quality,
        },
        "baseline": baseline_metrics,
        "measured": scenario_metrics,
        "deltas": {
            "ndcg_at_k": round(scenario_ndcg - baseline_ndcg, 6),
            "quality_loss": round(max(0.0, baseline_ndcg - scenario_ndcg), 6),
            "latency_p95_overhead_percent": round(
                (scenario_metrics["latency_p95_ms"] - latency_base)
                / latency_base
                * 100,
                3,
            ),
            "availability_percentage_points": round(
                scenario_metrics["availability_percent"]
                - baseline_metrics["availability_percent"],
                3,
            ),
        },
        "timing": {
            "baseline_seconds": round(baseline_seconds, 3),
            "scenario_seconds": round(scenario_seconds, 3),
            "total_seconds": round(time.perf_counter() - wall_started, 3),
        },
        "method": {
            "split": "um item relevante ocultado por usuário; sem timestamps",
            "relevance_threshold": 4,
            "top_k": request.top_k,
            "seed": request.seed,
            "database_mutated": False,
            "baseline_reused": baseline_reused,
            "raw_attack_retained_without_observability": True,
        },
        "started_at": started_at.isoformat(),
    }
    return result


def run_real_experiment_suite(
    request: RealExperimentSuiteRequest,
    books_df: pd.DataFrame,
    ratings_df: pd.DataFrame,
    to_read_df: pd.DataFrame,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict:
    """Executa todos os modelos/ataques nos modos sem e com observabilidade."""

    started_at = datetime.now(timezone.utc)
    wall_started = time.perf_counter()
    total_scenarios = len(MODEL_CATALOG) * len(ATTACK_CATALOG) * 2
    completed_scenarios = 0
    comparisons: list[dict] = []

    def report(message: str) -> None:
        if progress_callback is not None:
            progress_callback(completed_scenarios, total_scenarios, message)

    report("Preparando recorte compartilhado e índice vetorial de tags")
    context = _prepare_experiment_context(
        request, books_df, ratings_df, to_read_df
    )

    for model_definition in MODEL_CATALOG:
        model_id = model_definition["id"]
        baseline_request = RealExperimentRequest(
            **request.model_dump(),
            model=model_id,
            attack_type="push_attack",
            with_observability=False,
        )
        report(f"{model_definition['label']}: calculando baseline compartilhado")
        baseline_started = time.perf_counter()
        baseline_metrics = _evaluate(
            baseline_request,
            context.training,
            context.books,
            context.to_read,
            context.held_out,
            context.cohort,
            inject_infrastructure=False,
            observability_active=False,
            content_index=context.content_index,
            wanted_by_user=context.wanted_by_user,
        )
        baseline_seconds = time.perf_counter() - baseline_started
        for attack_definition in ATTACK_CATALOG:
            attack_id = attack_definition["id"]
            common = {
                **request.model_dump(),
                "model": model_id,
                "attack_type": attack_id,
            }
            report(
                f"{model_definition['label']} × {attack_definition['label']}: "
                "executando sem observabilidade"
            )
            without = run_real_experiment(
                RealExperimentRequest(**common, with_observability=False),
                books_df,
                ratings_df,
                to_read_df,
                _context=context,
                _baseline_metrics=baseline_metrics,
                _baseline_seconds=baseline_seconds,
            )
            completed_scenarios += 1

            report(
                f"{model_definition['label']} × {attack_definition['label']}: "
                "executando com observabilidade"
            )
            with_observability = run_real_experiment(
                RealExperimentRequest(**common, with_observability=True),
                books_df,
                ratings_df,
                to_read_df,
                _context=context,
                _baseline_metrics=baseline_metrics,
                _baseline_seconds=baseline_seconds,
            )
            completed_scenarios += 1

            comparisons.append(
                {
                    "model": model_id,
                    "model_label": model_definition["label"],
                    "attack": attack_id,
                    "attack_label": attack_definition["label"],
                    "baseline": without["baseline"],
                    "without_observability": without["measured"],
                    "with_observability": with_observability["measured"],
                    "data_quality": {
                        "baseline": without["data_quality"]["baseline"]["quality_score"],
                        "without_observability": without["data_quality"]["effective"]["quality_score"],
                        "with_observability": with_observability["data_quality"]["effective"]["quality_score"],
                        "details": {
                            "baseline": without["data_quality"]["baseline"],
                            "without_observability": without["data_quality"]["effective"],
                            "with_observability": with_observability["data_quality"]["effective"],
                        },
                    },
                    "observability": with_observability["observability"],
                    "attack_details": without["attack"],
                    "timing": {
                        "without_observability_seconds": without["timing"]["total_seconds"],
                        "with_observability_seconds": with_observability["timing"]["total_seconds"],
                    },
                }
            )

    report("Consolidando as comparações e preparando o relatório")
    return {
        "kind": "measured_experiment_suite",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at.isoformat(),
        "configuration": request.model_dump(),
        "dataset": {
            "books": int(len(books_df)),
            "ratings_snapshot": int(len(ratings_df)),
        },
        "models": len(MODEL_CATALOG),
        "attacks": len(ATTACK_CATALOG),
        "comparisons_count": len(comparisons),
        "scenario_runs": total_scenarios,
        "comparisons": comparisons,
        "total_seconds": round(time.perf_counter() - wall_started, 3),
        "method": {
            "pairing": "mesma seed, coorte, intensidade e top-k nos dois modos",
            "database_mutated": False,
            "shared_preprocessing": True,
            "baseline_evaluations": len(MODEL_CATALOG),
            "vectorized_content_tags": True,
            "raw_attack_retained_without_observability": True,
        },
    }
