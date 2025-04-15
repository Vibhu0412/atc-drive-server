
import uuid

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware

from src.routes.routes import router

load_dotenv()

import uvicorn

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ATC-Drive project")

app.add_middleware(
    CORSMiddleware,
    # BaseHTTPMiddleware,
    # dispatch=lambda request, call_next: call_next(request),
    allow_origins=[
            "http://93.127.137.160",
            "http://ec2-93.127.137.160.ap-south-1.compute.amazonaws.com",
            "http://localhost:9000",
            "http://127.0.0.1:9000",
            "http://93.127.137.160:9000",
            "http://93.127.137.160:8000",
            "http://localhost:63342",
            "http://93.127.137.160",
            "http://93.127.137.160:9000"
        ],
        allow_methods=["*"],
        allow_headers=["*"]
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
