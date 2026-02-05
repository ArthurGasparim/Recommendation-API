from fastapi import FastAPI,Depends,Query
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from db.db import engine,to_read as ToRead, books_tags as BooksTags,user as User,Books,ratings as Rating,tags as Tags , get_session,Session
from typing import Annotated
from sqlmodel import select,delete
from pydantic import BaseModel
from recommender import create_useful_book_dataframe, get_recommendation_item_based,get_recommendation_user_based
import pandas as pd
from sqlalchemy import text
app = FastAPI()

SessionDep = Annotated[Session, Depends(get_session)]




origins = [
    "http://localhost:3000",
    "https://localhost:5000"
]



app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True, # Allows cookies to be included in cross-origin requests
    allow_methods=["*"],    # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],    # Allows all headers
)

@app.get("/")
def loadData(session:SessionDep):
    global tags_df, to_read_df, books_tags_df, books_df, ratings_df
    with session.bind.connect() as conn:
        tags_df = pd.read_sql(select(Tags), conn)
        to_read_df = pd.read_sql(select(ToRead), conn)
        books_tags_df = pd.read_sql(select(BooksTags), conn)
        books_df = pd.read_sql(select(Books), conn)
        ratings_df = pd.read_sql(select(Rating), conn)
        books_merge_tags =  pd.merge(books_df,books_tags_df,left_on='good_id', right_on='goodreads_book_id', how='inner')
        tags_final = books_merge_tags.groupby('id')['tag_id'].agg(list)
        books_df = pd.merge(books_df,tags_final,on='id',how='inner')
        books_df = books_df.drop(columns=["good_id"])
    return {"status": "ok"}

@app.get("/clearTables")
def clearTables(session:SessionDep):
    statement = delete(Books)
    session.exec(statement)
    session.commit()
    statement = delete(BooksTags)
    session.exec(statement)
    session.commit()
    statement = delete(Tags)
    session.exec(statement)
    session.commit()
    statement = delete(Rating)
    session.exec(statement)
    session.commit()
    statement = delete(ToRead)
    session.exec(statement)
    session.commit()


@app.get("/loadTest")
def loadTest():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE ratings, tags, to_read, books_tags, books RESTART IDENTITY CASCADE"))
    booksDirty_df_test = pd.read_csv("data/books.csv")
    ratings_df_test = pd.read_csv("data/ratings.csv")
    tags_df_test = pd.read_csv("data/tags.csv")
    to_read_df_test = pd.read_csv("data/to_read.csv")
    books_tags_df_test = pd.read_csv("data/book_tags.csv")
    books_df_test = create_useful_book_dataframe(booksDirty_df_test,tags_df_test,books_tags_df_test)
    ratings_df_test = ratings_df_test.loc[ratings_df_test["book_id"].isin(books_df_test['id'])]
    ratings_df_test.to_sql('ratings',con=engine,if_exists='replace', index=False)
    tags_df_test.to_sql('tags',con=engine,if_exists='append', index=False)
    to_read_df_test.to_sql('to_read',con=engine,if_exists='append', index=False)
    books_tags_df_test.to_sql(
    'books_tags',
    con=engine,
    if_exists='replace',
    index=False
    )
    books_df_test.to_sql("books",con=engine,if_exists='append', index=False)
    return {"status": "ok"}

@app.get("/RecIB/{id}")
def getRecIB(id:int,session:SessionDep):
    ids = get_recommendation_item_based(user_id=id,books_df=books_df,ratings_df=ratings_df,to_read_df=to_read_df)
    statement = select(Books).where(Books.id.in_(ids))
    books = session.exec(statement=statement).all()
    return books

@app.get("/RecUB/{id}")
def getRecIB(id:int,session:SessionDep):
    print(ratings_df)
    ids = get_recommendation_user_based(user_id=id,books_df=books_df,ratings_df=ratings_df)
    ids = ids.astype(int).tolist()   
    statement = select(Books).where(Books.id.in_(ids))
    books = session.exec(statement=statement).all()
    return books

@app.get("/all")
def read_books(session:SessionDep,offset:int=0,limit:Annotated[int, Query(le=100)] = 100,
) -> list[Books]:
    books=session.exec(select(Books).offset(offset).limit(limit)).all()
    return books


@app.post("/createUser")
def createUser(user: User,session:SessionDep):
    user1 = session.get(User, user.id)
    if not user1:
        session.add(user)
        session.commit()
        session.refresh(user)
        return {
            "alert": "User successfully created",
            "user": user,
            "status": "created"
        }
    else:
        return {
            "alert": "Login Successful",
            "user": user1,
            "status": "logged_in"
        }
    
@app.post("/createBook")
def createBook(book:Books,session:SessionDep):
    book1 = session.get(Books, book.id)
    if not book1:
        session.add(book)
        session.commit()
        session.refresh(book)
        return {
            "alert": "Book successfully created",
            "book": book,
            "status": "created"
        }
    else:
        return {
            "alert": "Book already exists",
            "book": book1,
            "status": "exists"
        }

@app.get("/getBook/{book_id}")
def getBook(book_id:int,session:SessionDep)->Books:
    book = session.get(Books,book_id)
    return book



@app.post("/rating")
def submitRating(column: Rating,session:SessionDep):
    statement = select(Rating).where(Rating.book_id == column.book_id, Rating.user_id == column.user_id)
    rate = session.exec(statement=statement).first()
    if(not rate):
        rate = column
        session.add(rate)
    else:
        rate.rating = column.rating
    session.commit()
    session.refresh(rate)
    return rate

class TagRequest(BaseModel):
    book_id: int
    tag_name: str

@app.post("/tag")
def submitTag(tag:TagRequest,session:SessionDep):
    statement = select(Tags).where(Tags.tag_name == f"{tag.tag_name}")
    tag1 = session.exec(statement=statement).first()
    if(not tag1):
        session.add(Tags(tag_name=tag.tag_name))
        session.flush()
    tag1 = session.exec(statement=statement).first()
    statement = select(BooksTags).where(BooksTags.tag_id == tag1.tag_id, BooksTags.goodreads_book_id == tag.book_id)
    tag_book1 = session.exec(statement=statement).first()
    if(not tag_book1):
        session.add(BooksTags(goodreads_book_id=tag.book_id,tag_id=tag1.tag_id,count=1))
    else:
        tag_book1.count += 1
    session.commit()
    return {"message":"Sucessifully added"}

class ReadRequest(BaseModel):
    book_id: int
    value: bool
    id: int

@app.post("/read")
def toRead(data: ReadRequest,session:SessionDep):
    statement = select(ToRead).where(ToRead.book_id == data.book_id, ToRead.user_id == data.id)
    toread = session.exec(statement).first()
    if(not data.value):
        if(toread):
            session.delete(toread)
    else:
        if(not toread):
            newData = ToRead(book_id=data.book_id,user_id=data.id)
            session.add(newData)
    session.commit()

    return {"message":"Succes"}



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)