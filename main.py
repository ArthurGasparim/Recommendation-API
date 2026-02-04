from fastapi import FastAPI,Depends,Query
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from db.db import engine,user as User,Books,get_session,Session
from typing import Annotated
from sqlmodel import select


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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)