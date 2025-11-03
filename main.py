from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def response_root():
    return {"message" : "Testing FastApi"}

