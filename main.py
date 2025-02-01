
import uuid

from dotenv import load_dotenv

from src.routes.routes import router

load_dotenv()

import uvicorn

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ATC-Drive project")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
@app.get("/")
def root():
    return "ATC-Drive Service is running."
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        reload=True
    )
