from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from db.db import engine
app = FastAPI()



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

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)