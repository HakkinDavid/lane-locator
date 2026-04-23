import base64
import io
from contextlib import asynccontextmanager

import gdown
import numpy as np
import torch
import torchvision.transforms.functional as TF
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from torchvision.models.segmentation import deeplabv3_resnet50

MODEL_URL = "https://drive.google.com/file/d/1qf4zs-kV3zdtd5A3qP0wAt9P4gNZa7OK/view?usp=sharing"
MODEL_PATH = "model.pth"


# Load model and download if not exists before starting the application
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not __import__("os").path.exists(MODEL_PATH):
        gdown.download(MODEL_URL, MODEL_PATH, quiet=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    checkpoint = torch.load(MODEL_PATH, map_location=device)

    model = deeplabv3_resnet50(weights=None, weights_backbone=None, num_classes=1).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    app.state.model = model
    app.state.device = device
    app.state.image_size = int(checkpoint["image_size"])
    app.state.threshold = float(checkpoint["threshold"])
    app.state.mean = list(checkpoint["mean"])
    app.state.std = list(checkpoint["std"])
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/predict")
async def predict(file: UploadFile = File(...), only_mask: bool = False):
    image = Image.open(io.BytesIO(await file.read())).convert("RGB")
    orig_size = image.size

    tensor = TF.normalize(
        TF.to_tensor(TF.resize(image, [app.state.image_size, app.state.image_size])),
        mean=app.state.mean, std=app.state.std,
    ).unsqueeze(0).to(app.state.device)

    with torch.no_grad():
        probs = torch.sigmoid(app.state.model(tensor)["out"])[0, 0].cpu().numpy()

    mask = (probs >= app.state.threshold).astype(np.uint8)
    mask = np.asarray(
        Image.fromarray((mask * 255).astype(np.uint8)).resize(orig_size, Image.NEAREST)
    ) > 0
    
    overlay = None
    
    if only_mask:
        overlay = mask
    else:
        overlay = np.array(image)
        overlay[mask] = (overlay[mask] * 0.5 + np.array([255, 255, 0]) * 0.3).astype(np.uint8)

    buf = io.BytesIO()
    Image.fromarray(overlay).save(buf, format="PNG")

    return {
        "overlay": base64.b64encode(buf.getvalue()).decode(),
    }
