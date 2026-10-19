import json
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import pandas as pd
import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field as PydanticField, SecretStr, field_validator
from sqlalchemy import func, text
from sqlmodel import SQLModel, Session, delete, select

from auth import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from db.db import (
    AdminJob,
    BookTag,
    Books,
    ModelRevision,
    Rating,
    Tag,
    ToRead,
    User,
    UserCredential,
    apply_compatible_schema_migrations,
    engine,
    get_session,
)
from experiments.real_runner import (
    RealExperimentRequest,
    RealExperimentSuiteRequest,
    real_experiment_catalog,
    run_real_experiment,
    run_real_experiment_suite,
)
from experiments.suite_report import build_suite_workbook
from experiments.simulator import (
    SimulationRequest,
    run_simulation,
    simulation_catalog,
)
from recommender import (
    attach_tags_to_books,
    build_collaborative_model,
    create_useful_book_dataframe,
    get_recommendation_item_based,
    get_recommendation_item_basedUsu,
    get_recommendation_user_based,
)


BASE_DIR = Path(__file__).resolve().parent
MODEL_REVISION_ID = 1
model_refresh_lock = threading.Lock()
data_load_lock = threading.Lock()
experiment_lock = threading.Lock()

ADMIN_JOBS_TOTAL = Counter(
    "recommendation_admin_jobs_total",
    "Quantidade de tarefas administrativas finalizadas.",
    ["kind", "status"],
)
EXPERIMENT_DURATION = Histogram(
    "recommendation_experiment_duration_seconds",
    "Duração das execuções medidas do laboratório.",
    ["attack_type", "observability", "model"],
)
EXPERIMENT_NDCG = Gauge(
    "recommendation_experiment_ndcg_at_k",
    "Último NDCG medido por configuração do laboratório.",
    ["attack_type", "observability", "model"],
)
EXPERIMENT_LATENCY_P95 = Gauge(
    "recommendation_experiment_latency_p95_milliseconds",
    "Última latência p95 medida pelo laboratório.",
    ["attack_type", "observability", "model"],
)
EXPERIMENT_DATA_QUALITY = Gauge(
    "recommendation_experiment_data_quality_ratio",
    "Qualidade efetiva dos dados na última execução medida.",
    ["attack_type", "observability"],
)
DATASET_RECORDS = Gauge(
    "recommendation_dataset_records",
    "Quantidade de registros carregados por entidade.",
    ["entity"],
)


def _configured_admin_ids() -> set[int]:
    configured = os.getenv("ADMIN_USER_IDS", "")
    try:
        return {int(value.strip()) for value in configured.split(",") if value.strip()}
    except ValueError as exc:
        raise RuntimeError("ADMIN_USER_IDS deve conter somente IDs inteiros") from exc


ADMIN_USER_IDS = _configured_admin_ids()


def _model_revision(session: Session) -> ModelRevision:
    revision = session.get(ModelRevision, MODEL_REVISION_ID)
    if revision is None:
        revision = ModelRevision(id=MODEL_REVISION_ID, revision=0)
        session.add(revision)
        session.flush()
    return revision


def mark_recommendation_model_changed(session: Session) -> None:
    revision = _model_revision(session)
    revision.revision += 1
    session.add(revision)


def refresh_recommendation_state(application: FastAPI) -> None:
    """Reconstrói o snapshot e o modelo colaborativo a partir do banco."""
    with model_refresh_lock:
        for _ in range(5):
            with Session(engine) as session:
                revision_before = _model_revision(session).revision
                session.commit()
            with engine.connect() as connection:
                books_df = pd.read_sql(select(Books), connection)
                book_tags_df = pd.read_sql(select(BookTag), connection)
                ratings_df = pd.read_sql(select(Rating), connection)
                to_read_df = pd.read_sql(select(ToRead), connection)
            with Session(engine) as session:
                revision_after = _model_revision(session).revision
                session.commit()
            if revision_before == revision_after:
                current_revision = revision_after
                break
        else:
            raise RuntimeError(
                "Não foi possível obter snapshot estável para o recomendador"
            )

        books_df = attach_tags_to_books(books_df, book_tags_df)
        if not ratings_df.empty and not books_df.empty:
            ratings_df = ratings_df[
                ratings_df["book_id"].isin(books_df["id"])
            ].copy()
        collaborative_model = build_collaborative_model(ratings_df)

        application.state.books_df = books_df
        application.state.book_tags_df = book_tags_df
        application.state.ratings_df = ratings_df
        application.state.to_read_df = to_read_df
        application.state.collaborative_model = collaborative_model
        application.state.model_revision = current_revision
        application.state.model_loaded_at = datetime.now(timezone.utc).isoformat()


def ensure_recommendation_state_current(application: FastAPI) -> None:
    with Session(engine) as session:
        database_revision = _model_revision(session).revision
        session.commit()
    loaded_revision = getattr(application.state, "model_revision", -1)
    if database_revision != loaded_revision:
        try:
            refresh_recommendation_state(application)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Modelo em atualização; tente novamente",
            ) from exc


@asynccontextmanager
async def lifespan(application: FastAPI):
    SQLModel.metadata.create_all(engine)
    apply_compatible_schema_migrations()
    with Session(engine) as session:
        _model_revision(session)
        session.commit()
    refresh_recommendation_state(application)
    with Session(engine) as session:
        _dataset_counts(session)
    yield


app = FastAPI(title="Recommendation API", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, include_in_schema=False)

frontend_urls = [
    value.strip()
    for value in os.getenv(
        "FRONTEND_URLS",
        (
            "http://localhost:3000,http://localhost:5000,"
            "http://127.0.0.1:3000,http://127.0.0.1:5000"
        ),
    ).split(",")
    if value.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_urls,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

SessionDep = Annotated[Session, Depends(get_session)]
security = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    user_id: int
    is_admin: bool


class UserAuthRequest(BaseModel):
    id: int = PydanticField(gt=0)
    name: str = PydanticField(min_length=1, max_length=120)
    password: SecretStr = PydanticField(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O nome não pode ser vazio")
        return normalized


class BookRequest(BaseModel):
    id: int | None = PydanticField(default=None, gt=0)
    good_id: int = PydanticField(gt=0)
    title: str = PydanticField(min_length=1, max_length=500)
    authors: str = PydanticField(min_length=1, max_length=2000)
    average_rating: float = PydanticField(ge=0, le=5)
    image_url: str = PydanticField(default="", max_length=2048)

    @field_validator("title", "authors")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O campo não pode ser vazio")
        return normalized


class RatingRequest(BaseModel):
    book_id: int = PydanticField(gt=0)
    user_id: int = PydanticField(gt=0)
    rating: int = PydanticField(ge=1, le=5)


class TagRequest(BaseModel):
    book_id: int = PydanticField(gt=0)
    tag_name: str = PydanticField(min_length=1, max_length=100)

    @field_validator("tag_name")
    @classmethod
    def normalize_tag(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("A tag não pode ser vazia")
        return normalized


class ReadRequest(BaseModel):
    book_id: int = PydanticField(gt=0)
    value: bool
    # Aceito temporariamente para compatibilidade; o ID confiável vem do token.
    id: int | None = PydanticField(default=None, gt=0)


def get_current_principal(
    session: SessionDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação Bearer obrigatória",
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    user = session.get(User, payload.user_id)
    credential = session.get(UserCredential, payload.user_id)
    if user is None or credential is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário do token não existe",
        )
    return Principal(user_id=user.id, is_admin=credential.is_admin)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def require_admin(principal: CurrentPrincipal) -> Principal:
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão administrativa obrigatória",
        )
    return principal


AdminPrincipal = Annotated[Principal, Depends(require_admin)]


def _authorize_user(principal: Principal, requested_user_id: int) -> None:
    if not principal.is_admin and principal.user_id != requested_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não é permitido acessar dados de outro usuário",
        )


def _ordered_books(session: Session, book_ids: list[int]) -> list[Books]:
    if not book_ids:
        return []
    records = session.exec(select(Books).where(Books.id.in_(book_ids))).all()
    by_id = {book.id: book for book in records}
    return [by_id[book_id] for book_id in book_ids if book_id in by_id]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _json_loads(value: str | None):
    return json.loads(value) if value else None


def _job_payload(job: AdminJob, *, include_result: bool = True) -> dict:
    payload = {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "requested_by": job.requested_by,
        "request": _json_loads(job.request_json),
        "error": job.error_message,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
    if include_result:
        payload["result"] = _json_loads(job.result_json)
    return payload


def _create_job(
    session: Session,
    *,
    kind: str,
    requested_by: int,
    request_payload: dict,
    message: str,
) -> AdminJob:
    exclusive_kinds = (
        ["load_test_data", "real_experiment", "real_experiment_suite"]
        if kind in {"load_test_data", "real_experiment", "real_experiment_suite"}
        else [kind]
    )
    active = session.exec(
        select(AdminJob).where(
            AdminJob.kind.in_(exclusive_kinds),
            AdminJob.status.in_(["queued", "running"]),
        )
    ).first()
    if active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Já existe uma tarefa deste tipo em execução",
                "job_id": active.id,
            },
        )
    job = AdminJob(
        id=str(uuid4()),
        kind=kind,
        requested_by=requested_by,
        request_json=_json_dumps(request_payload),
        message=message,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _update_job(
    job_id: str,
    *,
    status_value: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    with Session(engine) as session:
        job = session.get(AdminJob, job_id)
        if job is None:
            return
        if status_value is not None:
            job.status = status_value
            if status_value == "running" and job.started_at is None:
                job.started_at = _utcnow()
            if status_value in {"completed", "failed"}:
                job.completed_at = _utcnow()
        if progress is not None:
            job.progress = max(0, min(100, progress))
        if message is not None:
            job.message = message
        if result is not None:
            job.result_json = _json_dumps(result)
        if error is not None:
            job.error_message = error[:2000]
        session.add(job)
        session.commit()


def _dataset_counts(session: Session) -> dict[str, int]:
    counts = {
        "books": int(session.exec(select(func.count()).select_from(Books)).one()),
        "ratings": int(session.exec(select(func.count()).select_from(Rating)).one()),
        "tags": int(session.exec(select(func.count()).select_from(Tag)).one()),
        "book_tags": int(session.exec(select(func.count()).select_from(BookTag)).one()),
        "to_read": int(session.exec(select(func.count()).select_from(ToRead)).one()),
    }
    for entity, count in counts.items():
        DATASET_RECORDS.labels(entity=entity).set(count)
    return counts


def _run_real_experiment_job(job_id: str, request_payload: dict) -> None:
    _update_job(
        job_id,
        status_value="running",
        progress=5,
        message="Copiando o snapshot do banco para o ambiente controlado",
    )
    request = RealExperimentRequest.model_validate(request_payload)
    observability_label = "enabled" if request.with_observability else "disabled"
    try:
        with experiment_lock:
            books_df = app.state.books_df.copy(deep=True)
            ratings_df = app.state.ratings_df.copy(deep=True)
            to_read_df = app.state.to_read_df.copy(deep=True)
            _update_job(
                job_id,
                progress=20,
                message="Executando baseline, ataque e avaliação das recomendações",
            )
            result = run_real_experiment(
                request=request,
                books_df=books_df,
                ratings_df=ratings_df,
                to_read_df=to_read_df,
            )
            result["run_id"] = job_id
        metrics = result["measured"]
        labels = {
            "attack_type": request.attack_type,
            "observability": observability_label,
            "model": request.model,
        }
        EXPERIMENT_DURATION.labels(**labels).observe(result["timing"]["total_seconds"])
        EXPERIMENT_NDCG.labels(**labels).set(metrics["ndcg_at_k"])
        EXPERIMENT_LATENCY_P95.labels(**labels).set(metrics["latency_p95_ms"])
        EXPERIMENT_DATA_QUALITY.labels(
            attack_type=request.attack_type,
            observability=observability_label,
        ).set(result["data_quality"]["effective"]["quality_score"])
        ADMIN_JOBS_TOTAL.labels(kind="real_experiment", status="completed").inc()
        _update_job(
            job_id,
            status_value="completed",
            progress=100,
            message="Experimento medido concluído",
            result=result,
        )
    except Exception as exc:  # pragma: no cover - proteção do worker
        ADMIN_JOBS_TOTAL.labels(kind="real_experiment", status="failed").inc()
        _update_job(
            job_id,
            status_value="failed",
            progress=100,
            message="O experimento falhou",
            error=str(exc),
        )


def _run_real_experiment_suite_job(job_id: str, request_payload: dict) -> None:
    _update_job(
        job_id,
        status_value="running",
        progress=2,
        message="Preparando a bateria completa de experimentos",
    )
    request = RealExperimentSuiteRequest.model_validate(request_payload)

    def report(completed: int, total: int, message: str) -> None:
        progress = 5 + int((completed / max(1, total)) * 90)
        _update_job(job_id, progress=progress, message=message)

    try:
        with experiment_lock:
            books_df = app.state.books_df.copy(deep=True)
            ratings_df = app.state.ratings_df.copy(deep=True)
            to_read_df = app.state.to_read_df.copy(deep=True)
            result = run_real_experiment_suite(
                request=request,
                books_df=books_df,
                ratings_df=ratings_df,
                to_read_df=to_read_df,
                progress_callback=report,
            )
            result["suite_id"] = job_id

        for comparison in result["comparisons"]:
            for key, observability_label in (
                ("without_observability", "disabled"),
                ("with_observability", "enabled"),
            ):
                labels = {
                    "attack_type": comparison["attack"],
                    "observability": observability_label,
                    "model": comparison["model"],
                }
                measured = comparison[key]
                duration_key = f"{key}_seconds"
                EXPERIMENT_DURATION.labels(**labels).observe(
                    comparison["timing"][duration_key]
                )
                EXPERIMENT_NDCG.labels(**labels).set(measured["ndcg_at_k"])
                EXPERIMENT_LATENCY_P95.labels(**labels).set(
                    measured["latency_p95_ms"]
                )
                EXPERIMENT_DATA_QUALITY.labels(
                    attack_type=comparison["attack"],
                    observability=observability_label,
                ).set(comparison["data_quality"][key])

        ADMIN_JOBS_TOTAL.labels(
            kind="real_experiment_suite", status="completed"
        ).inc()
        _update_job(
            job_id,
            status_value="completed",
            progress=100,
            message="Bateria completa concluída; planilha disponível",
            result=result,
        )
    except Exception as exc:  # pragma: no cover - proteção do worker
        ADMIN_JOBS_TOTAL.labels(kind="real_experiment_suite", status="failed").inc()
        _update_job(
            job_id,
            status_value="failed",
            progress=100,
            message="A bateria completa de experimentos falhou",
            error=str(exc),
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(session: SessionDep):
    session.exec(select(1)).one()
    return {"status": "ready"}


@app.post("/createUser")
def create_or_login_user(request: UserAuthRequest, session: SessionDep):
    existing_user = session.get(User, request.id)
    credential = session.get(UserCredential, request.id)
    password = request.password.get_secret_value()

    if existing_user is None:
        salt, password_hash = hash_password(password)
        existing_user = User(id=request.id, name=request.name)
        credential = UserCredential(
            user_id=request.id,
            password_salt=salt,
            password_hash=password_hash,
            is_admin=request.id in ADMIN_USER_IDS,
        )
        session.add(existing_user)
        session.add(credential)
        action = "created"
    else:
        if credential is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Conta legada sem senha. Recrie o ambiente de desenvolvimento "
                    "ou migre a credencial por procedimento administrativo."
                ),
            )
        if not verify_password(
            password, credential.password_salt, credential.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas",
            )
        action = "logged_in"

    session.commit()
    token = create_access_token(existing_user.id, credential.is_admin)
    return {
        "alert": "Usuário criado" if action == "created" else "Login realizado",
        "user": {"id": existing_user.id, "name": existing_user.name},
        "status": action,
        "access_token": token,
        "token_type": "bearer",
        "is_admin": credential.is_admin,
    }


@app.get("/all")
def read_books(
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Books]:
    return session.exec(select(Books).offset(offset).limit(limit)).all()


@app.get("/getBook/{book_id}")
def get_book(book_id: int, session: SessionDep) -> Books:
    if book_id <= 0:
        raise HTTPException(status_code=422, detail="ID de livro inválido")
    book = session.get(Books, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return book


@app.get("/RecIB/{book_id}")
def recommend_by_book(book_id: int, session: SessionDep):
    ensure_recommendation_state_current(app)
    try:
        ids = get_recommendation_item_based(book_id, app.state.books_df)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _ordered_books(session, ids)


@app.get("/RecIBUsu/{user_id}")
def recommend_content_for_user(
    user_id: int, session: SessionDep, principal: CurrentPrincipal
):
    _authorize_user(principal, user_id)
    ensure_recommendation_state_current(app)
    ids = get_recommendation_item_basedUsu(
        user_id=user_id,
        books_df=app.state.books_df,
        ratings_df=app.state.ratings_df,
        to_read_df=app.state.to_read_df,
    )
    return _ordered_books(session, ids)


@app.get("/RecUB/{user_id}")
def recommend_collaborative_for_user(
    user_id: int, session: SessionDep, principal: CurrentPrincipal
):
    _authorize_user(principal, user_id)
    ensure_recommendation_state_current(app)
    ids = get_recommendation_user_based(
        user_id=user_id,
        books_df=app.state.books_df,
        ratings_df=app.state.ratings_df,
        collaborative_model=app.state.collaborative_model,
    )
    return _ordered_books(session, ids)


@app.get("/recommendations/status")
def recommendation_status(session: SessionDep, principal: CurrentPrincipal):
    database_revision = _model_revision(session).revision
    return {
        "loaded_revision": app.state.model_revision,
        "database_revision": database_revision,
        "is_stale": database_revision != app.state.model_revision,
        "loaded_at": app.state.model_loaded_at,
        "books": len(app.state.books_df),
        "ratings": len(app.state.ratings_df),
    }


@app.post("/admin/recommendations/rebuild")
def rebuild_recommendations(principal: AdminPrincipal):
    refresh_recommendation_state(app)
    return {
        "status": "rebuilt",
        "revision": app.state.model_revision,
        "loaded_at": app.state.model_loaded_at,
    }


@app.get("/admin/experiments/catalog")
def get_experiment_catalog(principal: AdminPrincipal):
    """Retorna modelos, ataques, métricas e cenário inicial do simulador."""
    return simulation_catalog()


@app.post("/admin/experiments/simulate")
def simulate_experiment(request: SimulationRequest, principal: AdminPrincipal):
    """Executa uma simulação exploratória determinística, sem alterar o banco."""
    return run_simulation(request)


@app.post("/createBook")
def create_book(
    request: BookRequest, session: SessionDep, principal: AdminPrincipal
):
    if request.id is not None and session.get(Books, request.id) is not None:
        raise HTTPException(status_code=409, detail="Livro já existe")
    book = Books(**request.model_dump())
    session.add(book)
    mark_recommendation_model_changed(session)
    session.commit()
    session.refresh(book)
    return {"alert": "Livro criado", "book": book, "status": "created"}


@app.post("/rating")
def submit_rating(
    request: RatingRequest, session: SessionDep, principal: CurrentPrincipal
):
    _authorize_user(principal, request.user_id)
    if session.get(Books, request.book_id) is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    statement = select(Rating).where(
        Rating.book_id == request.book_id, Rating.user_id == request.user_id
    )
    rating = session.exec(statement).first()
    if rating is None:
        rating = Rating(**request.model_dump())
        session.add(rating)
    else:
        rating.rating = request.rating
        session.add(rating)
    mark_recommendation_model_changed(session)
    session.commit()
    session.refresh(rating)
    return rating


@app.post("/tag")
def submit_tag(
    request: TagRequest, session: SessionDep, principal: CurrentPrincipal
):
    book = session.get(Books, request.book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")

    statement = select(Tag).where(
        func.lower(Tag.tag_name) == request.tag_name.lower()
    )
    tag = session.exec(statement).first()
    if tag is None:
        tag = Tag(tag_name=request.tag_name)
        session.add(tag)
        session.flush()

    relation = session.get(BookTag, (book.good_id, tag.tag_id))
    if relation is None:
        relation = BookTag(
            goodreads_book_id=book.good_id, tag_id=tag.tag_id, count=1
        )
    else:
        relation.count += 1
    session.add(relation)
    mark_recommendation_model_changed(session)
    session.commit()
    return {"message": "Tag adicionada", "tag_id": tag.tag_id}


@app.post("/read")
def update_to_read(
    request: ReadRequest, session: SessionDep, principal: CurrentPrincipal
):
    if request.id is not None and request.id != principal.user_id:
        raise HTTPException(
            status_code=403, detail="O ID enviado não corresponde ao token"
        )
    if session.get(Books, request.book_id) is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    key = (request.book_id, principal.user_id)
    record = session.get(ToRead, key)
    if request.value and record is None:
        session.add(ToRead(book_id=request.book_id, user_id=principal.user_id))
    elif not request.value and record is not None:
        session.delete(record)
    mark_recommendation_model_changed(session)
    session.commit()
    return {"message": "Lista de leitura atualizada"}


@app.delete("/admin/data")
def clear_data(session: SessionDep, principal: AdminPrincipal):
    for model in (Rating, ToRead, BookTag, Tag, Books):
        session.exec(delete(model))
    mark_recommendation_model_changed(session)
    session.commit()
    refresh_recommendation_state(app)
    return {"status": "cleared"}


def _load_test_data_records(progress_callback=None) -> dict:
    def report(progress: int, message: str) -> None:
        if progress_callback is not None:
            progress_callback(progress, message)

    with data_load_lock:
        report(5, "Lendo os CSVs empacotados na imagem da API")
        data_dir = BASE_DIR / "data"
        books_source = pd.read_csv(data_dir / "books.csv")
        ratings_df = pd.read_csv(data_dir / "ratings.csv")
        tags_df = pd.read_csv(data_dir / "tags.csv")
        to_read_df = pd.read_csv(data_dir / "to_read.csv")
        book_tags_df = pd.read_csv(data_dir / "book_tags.csv")
        books_df = create_useful_book_dataframe(books_source)
        valid_book_ids = set(books_df["id"].astype(int))
        ratings_df = ratings_df[ratings_df["book_id"].isin(valid_book_ids)]
        to_read_df = to_read_df[to_read_df["book_id"].isin(valid_book_ids)]

        report(25, "Validando domínios e consolidando chaves repetidas")
        # O Goodbooks contém chaves compostas repetidas. A tabela representa
        # apenas uma nota por usuário/livro; conflitos são consolidados pela média.
        ratings_df = (
            ratings_df.groupby(
                ["book_id", "user_id"], as_index=False, sort=False
            )["rating"]
            .mean()
            .assign(
                rating=lambda frame: frame["rating"].round().clip(1, 5).astype(int)
            )
        )
        book_tags_df = book_tags_df.groupby(
            ["goodreads_book_id", "tag_id"], as_index=False, sort=False
        )["count"].max()

        report(45, "Gravando o snapshot validado em uma única transação")
        with Session(engine) as session:
            connection = session.connection()
            for model in (Rating, ToRead, BookTag, Tag, Books):
                session.exec(delete(model))
            books_df.to_sql("books", con=connection, if_exists="append", index=False)
            tags_df.to_sql("tags", con=connection, if_exists="append", index=False)
            book_tags_df.to_sql(
                "books_tags", con=connection, if_exists="append", index=False
            )
            ratings_df.to_sql(
                "ratings", con=connection, if_exists="append", index=False
            )
            to_read_df.to_sql(
                "to_read", con=connection, if_exists="append", index=False
            )
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence('tags', 'tag_id'), "
                        "coalesce(max(tag_id), 0) + 1, false) FROM tags"
                    )
                )
                connection.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence('books', 'id'), "
                        "coalesce(max(id), 0) + 1, false) FROM books"
                    )
                )
            mark_recommendation_model_changed(session)
            session.commit()

        report(90, "Reconstruindo o snapshot dos recomendadores")
        refresh_recommendation_state(app)
        result = {
            "status": "loaded",
            "books": len(books_df),
            "ratings": len(ratings_df),
            "tags": len(tags_df),
            "book_tags": len(book_tags_df),
            "to_read": len(to_read_df),
        }
        for entity, count in result.items():
            if entity != "status":
                DATASET_RECORDS.labels(entity=entity).set(count)
        return result


def _load_test_data_job(job_id: str) -> None:
    _update_job(
        job_id,
        status_value="running",
        progress=1,
        message="Iniciando carga controlada dos CSVs",
    )
    try:
        result = _load_test_data_records(
            lambda progress, message: _update_job(
                job_id, progress=progress, message=message
            )
        )
        ADMIN_JOBS_TOTAL.labels(kind="load_test_data", status="completed").inc()
        _update_job(
            job_id,
            status_value="completed",
            progress=100,
            message="Dados carregados e recomendadores reconstruídos",
            result=result,
        )
    except Exception as exc:  # pragma: no cover - proteção do worker
        ADMIN_JOBS_TOTAL.labels(kind="load_test_data", status="failed").inc()
        _update_job(
            job_id,
            status_value="failed",
            progress=100,
            message="A carga dos CSVs falhou; a transação foi revertida",
            error=str(exc),
        )


@app.post("/admin/load-test-data")
def load_test_data(principal: AdminPrincipal):
    """Compatibilidade com clientes antigos; aguarda a carga terminar."""
    return _load_test_data_records()


@app.post("/admin/data/load", status_code=status.HTTP_202_ACCEPTED)
def enqueue_test_data_load(
    background_tasks: BackgroundTasks,
    session: SessionDep,
    principal: AdminPrincipal,
):
    job = _create_job(
        session,
        kind="load_test_data",
        requested_by=principal.user_id,
        request_payload={"source": "bundled_goodbooks_csv"},
        message="Carga dos CSVs adicionada à fila",
    )
    background_tasks.add_task(_load_test_data_job, job.id)
    return _job_payload(job)


@app.get("/admin/jobs/{job_id}")
def get_admin_job(job_id: str, session: SessionDep, principal: AdminPrincipal):
    job = session.get(AdminJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tarefa administrativa não encontrada")
    return _job_payload(job)


@app.get("/admin/experiments/real/catalog")
def get_real_experiment_catalog(principal: AdminPrincipal):
    return real_experiment_catalog()


@app.post(
    "/admin/experiments/real/run", status_code=status.HTTP_202_ACCEPTED
)
def enqueue_real_experiment(
    request: RealExperimentRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    principal: AdminPrincipal,
):
    # Outra réplica pode ter concluído a carga dos CSVs. A revisão persistida
    # garante que esta réplica leia o snapshot mais recente antes de validar e
    # copiar os dados do experimento.
    ensure_recommendation_state_current(app)
    if len(app.state.books_df) == 0 or len(app.state.ratings_df) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carregue os CSVs antes de executar um ataque real",
        )
    job = _create_job(
        session,
        kind="real_experiment",
        requested_by=principal.user_id,
        request_payload=request.model_dump(),
        message="Experimento real adicionado à fila",
    )
    background_tasks.add_task(
        _run_real_experiment_job, job.id, request.model_dump()
    )
    return _job_payload(job)


@app.post(
    "/admin/experiments/real/suite", status_code=status.HTTP_202_ACCEPTED
)
def enqueue_real_experiment_suite(
    request: RealExperimentSuiteRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    principal: AdminPrincipal,
):
    """Executa sequencialmente todos os modelos, ataques e modos de defesa."""

    ensure_recommendation_state_current(app)
    if len(app.state.books_df) == 0 or len(app.state.ratings_df) == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Carregue os CSVs antes de executar a bateria completa",
        )
    job = _create_job(
        session,
        kind="real_experiment_suite",
        requested_by=principal.user_id,
        request_payload=request.model_dump(),
        message="Bateria completa adicionada à fila",
    )
    background_tasks.add_task(
        _run_real_experiment_suite_job, job.id, request.model_dump()
    )
    return _job_payload(job)


@app.get("/admin/experiments/real/suite/{job_id}/xlsx")
def download_real_experiment_suite(
    job_id: str,
    session: SessionDep,
    principal: AdminPrincipal,
):
    """Gera a planilha a partir do resultado persistido, sem depender do pod."""

    job = session.get(AdminJob, job_id)
    if job is None or job.kind != "real_experiment_suite":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bateria de experimentos não encontrada",
        )
    if job.status != "completed" or not job.result_json:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A planilha ficará disponível quando a bateria for concluída",
        )
    workbook = build_suite_workbook(_json_loads(job.result_json))
    filename = f"comparacao-observabilidade-{job.id}.xlsx"
    return StreamingResponse(
        workbook,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/admin/experiments/real/metrics")
def get_real_experiment_metrics(
    session: SessionDep,
    principal: AdminPrincipal,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    jobs = session.exec(
        select(AdminJob)
        .where(AdminJob.kind == "real_experiment")
        .order_by(AdminJob.created_at.desc())
        .limit(limit)
    ).all()
    completed = session.exec(
        select(AdminJob)
        .where(
            AdminJob.kind == "real_experiment",
            AdminJob.status == "completed",
            AdminJob.result_json.is_not(None),
        )
        .order_by(AdminJob.completed_at.desc())
    ).first()
    completed_suite = session.exec(
        select(AdminJob)
        .where(
            AdminJob.kind == "real_experiment_suite",
            AdminJob.status == "completed",
            AdminJob.result_json.is_not(None),
        )
        .order_by(AdminJob.completed_at.desc())
    ).first()
    latest_suite = None
    if completed_suite is not None:
        suite_result = _json_loads(completed_suite.result_json)
        latest_suite = {
            **_job_payload(completed_suite, include_result=False),
            "download_url": (
                f"/admin/experiments/real/suite/{completed_suite.id}/xlsx"
            ),
            "summary": {
                "models": suite_result["models"],
                "attacks": suite_result["attacks"],
                "comparisons": suite_result["comparisons_count"],
                "scenario_runs": suite_result["scenario_runs"],
                "total_seconds": suite_result["total_seconds"],
            },
        }
    return {
        "kind": "measured_metrics",
        "measured_at": _utcnow().isoformat(),
        "dataset": _dataset_counts(session),
        "latest": _json_loads(completed.result_json) if completed else None,
        "latest_suite": latest_suite,
        "runs": [_job_payload(job, include_result=False) for job in jobs],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
