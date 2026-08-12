import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
    BookTag,
    Books,
    ModelRevision,
    Rating,
    Tag,
    ToRead,
    User,
    UserCredential,
    engine,
    get_session,
)
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
    with Session(engine) as session:
        _model_revision(session)
        session.commit()
    refresh_recommendation_state(application)
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
    authors: str = PydanticField(min_length=1, max_length=500)
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


@app.post("/admin/load-test-data")
def load_test_data(session: SessionDep, principal: AdminPrincipal):
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

    # O dataset Goodbooks contém chaves compostas repetidas. A tabela de
    # avaliações representa apenas uma nota por usuário/livro; consolidamos as
    # notas conflitantes pela média e mantemos a escala inteira de 1 a 5. Para
    # tags, o maior contador evita duplicar artificialmente a frequência.
    ratings_df = (
        ratings_df.groupby(["book_id", "user_id"], as_index=False, sort=False)[
            "rating"
        ]
        .mean()
        .assign(rating=lambda frame: frame["rating"].round().clip(1, 5).astype(int))
    )
    book_tags_df = book_tags_df.groupby(
        ["goodreads_book_id", "tag_id"], as_index=False, sort=False
    )["count"].max()

    # Usa a mesma sessão para garantir uma única transação também nos testes SQLite.
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
    refresh_recommendation_state(app)
    return {
        "status": "loaded",
        "books": len(books_df),
        "ratings": len(ratings_df),
        "tags": len(tags_df),
        "book_tags": len(book_tags_df),
        "to_read": len(to_read_df),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
