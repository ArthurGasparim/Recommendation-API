from sqlmodel import Field, Session, SQLModel, create_engine, select
class Book(SQLModel,table=True):
    id:int | None = Field(default=None,primary_key=True)
    name: str = Field(index=True)

Postgres_db_name = "bookstore_db"
host = "localhost"
port = "5432"
username = "postgres"
password = "postgres123"

Postgres_url =f"postgresql://{username}:{password}@{host}:{port}/{Postgres_db_name}"


engine = create_engine(Postgres_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
