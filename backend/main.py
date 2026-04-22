from pathlib import Path

from fastapi import FastAPI
from contextlib import asynccontextmanager

import gdown

MODEL_URL = "https://drive.google.com/file/d/1RBmVFYECQxnO6ITS4mbf9hKOvSB-LcVp/view?usp=sharing"
MODEL_PATH = Path(__file__).resolve().parent / "model.pth"


def ensure_model_downloaded() -> None:
    if MODEL_PATH.exists():
        return

    gdown.download(MODEL_URL, str(MODEL_PATH), quiet=False)

    if not MODEL_PATH.exists():
        raise RuntimeError("No se pudo descargar el modelo.")

# Check if the model is already downloaded when starting the app
@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_model_downloaded()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Hello World"}
