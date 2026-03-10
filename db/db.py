from sqlmodel import Field, Session, SQLModel, create_engine, select
import os

class Books(SQLModel,table=True):
    id:int | None = Field(default=None,primary_key=True)
    good_id: int = Field(index=True)
    title: str|None = Field(index=True)
    authors:str = Field(index=True)
    average_rating:float = Field(index=True)
    image_url: str = Field(index=True, default="")

class books_tags(SQLModel,table=True):
    goodreads_book_id:int = Field(primary_key=True)
    tag_id:int = Field(primary_key=True)
    count:int=Field(index=True)

class ratings(SQLModel,table=True):
    book_id:int =  Field(primary_key=True)
    user_id:int = Field(primary_key=True)
    rating:int = Field(index=True)

class tags(SQLModel,table=True):
    tag_id:int | None = Field(default=None,primary_key=True)
    tag_name:str = Field(index=True)

class to_read(SQLModel,table=True):
    book_id:int =  Field(primary_key=True)
    user_id:int = Field(primary_key=True)
    
class user(SQLModel,table=True):
    id:int = Field(primary_key=True)
    name:str = Field(index=True)

postgres_db_name = "bookstore_db"
host = "localhost"
port = "5432"
username = "postgres"
password = "postgres123"

local_url = f"postgresql://{username}:{password}@{host}:{port}/{postgres_db_name}"

# Pega a URL do Kubernetes, se não existir, usa a local
database_url = os.getenv("DATABASE_URL", local_url)

engine = create_engine(database_url)



def get_session():
    with Session(engine) as session:
        yield session




def create_db_and_tables():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    
  

