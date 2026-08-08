from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello from TravelDoris"}

@app.post("/trip")
def create_trip():
    return {"message": "Planning a trip"}