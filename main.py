from fastapi import FastAPI,Depends,Query
from sklearn.metrics.pairwise import cosine_similarity
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from db.db import engine,to_read as ToRead, books_tags as BooksTags,user as User,Books,ratings as Rating,tags as Tags , get_session,Session
from typing import Annotated
from sqlmodel import select,delete
from pydantic import BaseModel
from recommender import create_useful_book_dataframe, get_recommendation_item_based,get_recommendation_user_based,get_recommendation_item_basedUsu
import pandas as pd
from sqlalchemy import text
app = FastAPI()

SessionDep = Annotated[Session, Depends(get_session)]




#Enabling connection between the server and the react server
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


@app.on_event("startup")
def startup_load_data():
    #On loanding the server, gets the db tables and converts them into databases for the recommendations
    with engine.connect() as conn:
        app.state.tags_df = pd.read_sql(select(Tags), conn)
        app.state.to_read_df = pd.read_sql(select(ToRead), conn)
        app.state.books_tags_df = pd.read_sql(select(BooksTags), conn)
        app.state.books_df = pd.read_sql(select(Books), conn)
        app.state.ratings_df = pd.read_sql(select(Rating), conn)
        #Generating the list of tags on final books_df
        books_merge_tags = pd.merge(
            app.state.books_df,
            app.state.books_tags_df,
            left_on="good_id",
            right_on="goodreads_book_id",
            how="inner",
        )
        tags_final = books_merge_tags.groupby("id")["tag_id"].agg(list)
        app.state.books_df = pd.merge( app.state.books_df, tags_final, on="id", how="inner").drop(columns=["good_id"])
        #Also crating the model on the  start of the server
        #Generating the sparce matrix
        app.state.rating_matrix = app.state.ratings_df.pivot_table(index='user_id', columns='book_id', values='rating').fillna(0)
        #Applying th cosine similarity method
        app.state.item_similarity = cosine_similarity(app.state.rating_matrix.T)
        

#Very intuitive, clear all db tables
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
    #Used to load the data tests on the database
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE ratings, tags, to_read, books_tags, books RESTART IDENTITY CASCADE"))
    booksDirty_df_test = pd.read_csv("data/books.csv")
    ratings_df_test = pd.read_csv("data/ratings.csv")
    tags_df_test = pd.read_csv("data/tags.csv")
    to_read_df_test = pd.read_csv("data/to_read.csv")
    books_tags_df_test = pd.read_csv("data/book_tags.csv")
    books_df_test = create_useful_book_dataframe(booksDirty_df_test,tags_df_test,books_tags_df_test)
    ratings_df_test = ratings_df_test.loc[ratings_df_test["book_id"].isin(books_df_test['id'])]
    #ratings_df_test = ratings_df_test[:1000]
    #tags_df_test = tags_df_test[:1000]
    #to_read_df_test = to_read_df_test[:1000]
    #books_tags_df_test = books_tags_df_test[:1000]
    #books_df_test = books_df_test[:100]
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
    #Use this to reload the db value for the auto increment ID based on the values that were just inserted
    with engine.begin() as conn:
        conn.execute(text("SELECT setval(pg_get_serial_sequence('tags', 'tag_id'), coalesce(max(tag_id), 0) + 1, false) FROM tags;"))
        conn.execute(text("SELECT setval(pg_get_serial_sequence('books', 'id'), coalesce(max(id), 0) + 1, false) FROM books;"))
    return {"status": "ok"}

#Gets a User recommendation Item based
@app.get("/RecIBUsu/{id}")
def getRecIB(id: int, session: SessionDep):
    ids = get_recommendation_item_basedUsu(
        user_id=id,
        books_df=app.state.books_df,
        ratings_df=app.state.ratings_df,
        to_read_df=app.state.to_read_df,

    )
    #Selects from the Database the ids that were served
    statement = select(Books).where(Books.id.in_(ids))
    return session.exec(statement).all()

#Gets one book top 5 recommendations
@app.get("/RecIB/{id}")
def getRecIB(id: int, session: SessionDep):
    ids = get_recommendation_item_based(
        book_id=id,
        books_df=app.state.books_df,

    )
     #Selects from the Database the ids that were served
    statement = select(Books).where(Books.id.in_(ids))
    return session.exec(statement).all()


#Uses the modlel saved on the state variable to get the top 5 recommendations for the user
@app.get("/RecUB/{id}")
def getRecUB(id: int, session: SessionDep):
    ids = get_recommendation_user_based(
        user_id=id,
        books_df=app.state.books_df,
        ratings_df=app.state.ratings_df,
        rating_matrix= app.state.rating_matrix,
        item_similarity= app.state.item_similarity
    ).astype(int).tolist()
    statement = select(Books).where(Books.id.in_(ids))
     #Selects from the Database the ids that were served
    return session.exec(statement).all()

#Returns all the books from the database, in the query le  you determine the limit of books, now is set for 100 books
@app.get("/all")
def read_books(session:SessionDep,offset:int=0,limit:Annotated[int, Query(le=100)] = 100,
) -> list[Books]:
    books=session.exec(select(Books).offset(offset).limit(limit)).all()
    return books

#Creates the user that is send by the react server
@app.post("/createUser")
def createUser(user: User,session:SessionDep):
    #Seeing if user already exists
    user1 = session.get(User, user.id)
    if not user1:
        #Creates the user
        session.add(user)
        session.commit()
        session.refresh(user)
        return {
            "alert": "User successfully created",
            "user": user,
            "status": "created"
        }
    else:
        #Logs the user in
        return {
            "alert": "Login Successful",
            "user": user1,
            "status": "logged_in"
        }
    

#Creates the book that is send by the react server
@app.post("/createBook")
def createBook(book:Books,session:SessionDep):
    #Seeing if the boook already exists
    book1 = session.get(Books, book.id)
    if not book1:
        #Creates the new book
        session.add(book)
        session.commit()
        session.refresh(book)
        return {
            "alert": "Book successfully created",
            "book": book,
            "status": "created"
        }
    else:
        #Alerts that the book already exists
        return {
            "alert": "Book already exists",
            "book": book1,
            "status": "exists"
        }

#Gets a single book based on the Id
@app.get("/getBook/{book_id}")
def getBook(book_id:int,session:SessionDep)->Books:
    book = session.get(Books,book_id)
    return book


#Gets a rating send by a user to a Book
@app.post("/rating")
def submitRating(column: Rating,session:SessionDep):
    #Sees if the combination user/book already exists in rating
    statement = select(Rating).where(Rating.book_id == column.book_id, Rating.user_id == column.user_id)
    rate = session.exec(statement=statement).first()
    if(not rate):
        #Creates a new rate based on the column sent by the react server
        rate = column
        session.add(rate)
    else:
        #Changes the rating of the column found for the new rating
        rate.rating = column.rating
    #Commits the db transaction
    session.commit()
    session.refresh(rate)
    return rate

#New class to work with tags and book_tags at the same time
class TagRequest(BaseModel):
    book_id: int
    tag_name: str

#Saves the tag sent by the user 
@app.post("/tag")
def submitTag(tag:TagRequest,session:SessionDep):
    statement = select(Tags).where(Tags.tag_name == tag.tag_name)
    #Searching if the tag already exists
    tag1 = session.exec(statement=statement).first()
    if(not tag1):
        #Creates a new tag
        session.add(Tags(tag_name=tag.tag_name))
        session.flush()
    #Gets the new tag id
    tag1 = session.exec(statement=statement).first()
    #Sees if the book/tag relation already exists
    statement = select(BooksTags).where(BooksTags.tag_id == tag1.tag_id, BooksTags.goodreads_book_id == tag.book_id)
    tag_book1 = session.exec(statement=statement).first()
    if(not tag_book1):
        #Creates a new Book Tag relation with a count of 1
        session.add(BooksTags(goodreads_book_id=tag.book_id,tag_id=tag1.tag_id,count=1))
    else:
        #Changes the already existing Relation count by one
        tag_book1.count += 1
    session.commit()
    return {"message":"Sucessifully added"}

#Creating new class to store the value of the html checkbox
class ReadRequest(BaseModel):
    book_id: int
    value: bool
    id: int

#Saves the to read changes on the checkbox on the html
@app.post("/read")
def toRead(data: ReadRequest,session:SessionDep):
    #Checks if the relation exists
    statement = select(ToRead).where(ToRead.book_id == data.book_id, ToRead.user_id == data.id)
    toread = session.exec(statement).first()
    #if the user checked false on the box
    if(not data.value):
        #if exists, delete the relation
        if(toread):
            session.delete(toread)
    else:
        #if the user checked true on the box
        if(not toread):
            #if it not exists create a new relation, if already exists, there is not need to change
            newData = ToRead(book_id=data.book_id,user_id=data.id)
            session.add(newData)
    session.commit()

    return {"message":"Succes"}


#Running the FastApi Server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)