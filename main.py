from fastapi import FastAPI,Depends
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from db.db import engine,user as User,get_session,Session
from typing import Annotated


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
def response_root():
    return {"message" : "Testing FastApi"}


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
    

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)