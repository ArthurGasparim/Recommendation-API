from sqlmodel import Field, Session, SQLModel, create_engine, select
class Books(SQLModel,table=True):
    id:int | None = Field(default=None,primary_key=True)
    book_id: int = Field(index=True)
    original_title: str = Field(index=True)
    authors:str = Field(index=True)
    average_rating:float = Field(index=True)

class books_tags(SQLModel,table=True):
    goodreads_book_id:int = Field(primary_key=True)
    tag_id:int = Field(primary_key=True)
    count:int=Field(index=True)

class ratings(SQLModel,table=True):
    book_id:int =  Field(primary_key=True)
    user_id:int = Field(primary_key=True)
    rating:int = Field(index=True)

class tags(SQLModel,table=True):
    tag_id:int = Field(primary_key=True)
    tag_name:str = Field(index=True)

class to_read(SQLModel,table=True):
    book_id:int =  Field(primary_key=True)
    user_id:int = Field(primary_key=True)
    
class user(SQLModel,table=True):
    id:int = Field(primary_key=True)
    name:str = Field(index=True)

Postgres_db_name = "bookstore_db"
host = "localhost"
port = "5432"
username = "postgres"
password = "postgres123"

Postgres_url =f"postgresql://{username}:{password}@{host}:{port}/{Postgres_db_name}"


engine = create_engine(Postgres_url, echo=True)

def get_session():
    with Session(engine) as session:
        yield session




def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

create_db_and_tables()