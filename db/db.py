import os
from datetime import datetime, timezone
from urllib.parse import quote_plus

from sqlalchemy import Column, Text, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Session, SQLModel, create_engine


class Books(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    good_id: int = Field(index=True)
    title: str | None = Field(default=None, index=True, max_length=500)
    # O Goodbooks possui coletâneas com listas de autores superiores a 500
    # caracteres. Text preserva o dado original sem truncamento.
    authors: str = Field(sa_column=Column(Text, nullable=False))
    average_rating: float = Field(index=True, ge=0, le=5)
    image_url: str = Field(default="", max_length=2048)


class BookTag(SQLModel, table=True):
    __tablename__ = "books_tags"

    goodreads_book_id: int = Field(primary_key=True)
    tag_id: int = Field(primary_key=True)
    count: int = Field(default=1, ge=0, index=True)


class Rating(SQLModel, table=True):
    __tablename__ = "ratings"

    book_id: int = Field(primary_key=True, foreign_key="books.id")
    # Usuários do dataset são implícitos e não possuem cadastro na tabela user.
    user_id: int = Field(primary_key=True)
    rating: int = Field(index=True, ge=1, le=5)


class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    tag_id: int | None = Field(default=None, primary_key=True)
    tag_name: str = Field(index=True, min_length=1, max_length=100)


class ToRead(SQLModel, table=True):
    __tablename__ = "to_read"

    book_id: int = Field(primary_key=True, foreign_key="books.id")
    user_id: int = Field(primary_key=True)


class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=120)


class UserCredential(SQLModel, table=True):
    __tablename__ = "user_credentials"

    user_id: int = Field(primary_key=True, foreign_key="user.id")
    password_salt: str
    password_hash: str
    is_admin: bool = Field(default=False, index=True)


class ModelRevision(SQLModel, table=True):
    __tablename__ = "model_revision"

    id: int = Field(default=1, primary_key=True)
    revision: int = Field(default=0, ge=0)


class AdminJob(SQLModel, table=True):
    """Tarefa administrativa persistida e visível entre réplicas da API."""

    __tablename__ = "admin_jobs"

    id: str = Field(primary_key=True, max_length=36)
    kind: str = Field(index=True, max_length=50)
    status: str = Field(default="queued", index=True, max_length=20)
    progress: int = Field(default=0, ge=0, le=100)
    message: str = Field(default="Tarefa aguardando execução", max_length=500)
    requested_by: int = Field(index=True)
    request_json: str = Field(sa_column=Column(Text, nullable=False))
    result_json: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    error_message: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


def _database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url

    postgres_host = os.getenv("POSTGRES_HOST")
    if postgres_host:
        required = {
            "POSTGRES_USER": os.getenv("POSTGRES_USER"),
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "POSTGRES_DB": os.getenv("POSTGRES_DB"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Variáveis obrigatórias do PostgreSQL ausentes: " + ", ".join(missing)
            )
        postgres_port = os.getenv("POSTGRES_PORT", "5432")
        username = quote_plus(required["POSTGRES_USER"] or "")
        password = quote_plus(required["POSTGRES_PASSWORD"] or "")
        database = quote_plus(required["POSTGRES_DB"] or "")
        return (
            f"postgresql://{username}:{password}@{postgres_host}:"
            f"{postgres_port}/{database}"
        )

    sqlite_path = os.getenv("SQLITE_DATABASE_PATH", "./recommendation.db")
    return f"sqlite:///{sqlite_path}"


database_url = _database_url()
engine_options: dict = {"pool_pre_ping": True}
if database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
    if database_url in {"sqlite://", "sqlite:///:memory:"}:
        engine_options["poolclass"] = StaticPool

engine = create_engine(database_url, **engine_options)


def apply_compatible_schema_migrations() -> None:
    """Aplica ajustes idempotentes ainda não cobertos por create_all()."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE books ALTER COLUMN authors TYPE TEXT"))


def get_session():
    with Session(engine) as session:
        yield session


# Aliases mantidos para não quebrar imports antigos durante a transição.
books_tags = BookTag
ratings = Rating
tags = Tag
to_read = ToRead
user = User
