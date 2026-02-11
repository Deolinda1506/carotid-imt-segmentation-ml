import io
from PIL import Image
import torch
import torchvision.transforms as T
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from pydantic import BaseModel
import numpy as np

# --- U-Net Model Definition (matches training setup) ---

class DoubleConv(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.double_conv = torch.nn.Sequential(
            torch.nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            torch.nn.BatchNorm2d(out_channels),
            torch.nn.ReLU(inplace=True),
            torch.nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            torch.nn.BatchNorm2d(out_channels),
            torch.nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)

class EncoderBlock(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.maxpool = torch.nn.MaxPool2d(kernel_size=2)
        self.double_conv = DoubleConv(in_channels, out_channels)

    def forward(self, x):
        x = self.maxpool(x)
        x = self.double_conv(x)
        return x

class DecoderBlock(torch.nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.up = torch.nn.ConvTranspose2d(in_channels, out_channels, kernel_size=2, stride=2)
        self.double_conv = DoubleConv(in_channels, out_channels)

    def forward(self, x, skip):
        x = self.up(x)
        if x.shape[-2:] != skip.shape[-2:]:
            diff_y = skip.size(2) - x.size(2)
            diff_x = skip.size(3) - x.size(3)
            x = torch.nn.functional.pad(x, [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2])
        x = torch.cat([skip, x], dim=1)
        return self.double_conv(x)

class UNet(torch.nn.Module):
    def __init__(self, in_channels=3, out_channels=1, base_channels=8):
        super().__init__()
        self.inc = DoubleConv(in_channels, base_channels)
        self.down1 = EncoderBlock(base_channels, base_channels * 2)
        self.down2 = EncoderBlock(base_channels * 2, base_channels * 4)
        self.down3 = EncoderBlock(base_channels * 4, base_channels * 8)
        self.down4 = EncoderBlock(base_channels * 8, base_channels * 16)
        self.up1 = DecoderBlock(base_channels * 16, base_channels * 8)
        self.up2 = DecoderBlock(base_channels * 8, base_channels * 4)
        self.up3 = DecoderBlock(base_channels * 4, base_channels * 2)
        self.up4 = DecoderBlock(base_channels * 2, base_channels)
        self.outc = torch.nn.Conv2d(base_channels, out_channels, kernel_size=1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        return self.outc(x)

# --- FastAPI Application Setup ---

app = FastAPI()

# Configuration (must match training)
IMG_SIZE = 128 # The size used during training
IMG_MEAN = [0.485, 0.456, 0.406]
IMG_STD = [0.229, 0.224, 0.225]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = UNet(in_channels=3, out_channels=1, base_channels=8).to(DEVICE)

try:
    # Ensure the model file is accessible in the deployment environment
    model_path = "/workspaces/carotid-imt-segmentation-ml/ML/models/unet_model.pth"
    model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    model.eval()
    print(f"Model loaded successfully from {model_path}")
except FileNotFoundError:
    raise RuntimeError(f"Model file not found at {model_path}. Please ensure it's available.")
except Exception as e:
    raise RuntimeError(f"Error loading model: {e}")

# Preprocessing transformation pipeline
preprocess = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.ToTensor(),
    T.Normalize(mean=IMG_MEAN, std=IMG_STD)
])

@app.get("/health")
async def health_check():
    return {"status": "ok", "model_loaded": True if model else False}

@app.get("/")
async def root():
    return {
        "message": "Carotid IMT Segmentation API is running.",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/predict/")
async def predict_segmentation(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    try:
        # Read image
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Preprocess image
        input_tensor = preprocess(image).unsqueeze(0).to(DEVICE) # Add batch dimension

        # Perform inference
        with torch.no_grad():
            outputs = model(input_tensor)
            # Apply sigmoid to logits to get probabilities, then binarize
            probabilities = torch.sigmoid(outputs)
            predicted_mask = (probabilities > 0.5).float().squeeze().cpu().numpy()

        # Convert mask to a format suitable for response (e.g., list or base64 encoded image)
        # For simplicity, returning as a list of lists (pixel values)
        # In a real application, you might encode it as a PNG/JPEG or base64 string
        return {"filename": file.filename, "predicted_mask_shape": predicted_mask.shape, "predicted_mask": predicted_mask.tolist()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

def predict_mask_from_image(image: Image.Image) -> np.ndarray:
    input_tensor = preprocess(image).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        outputs = model(input_tensor)
        probabilities = torch.sigmoid(outputs)
        predicted_mask = (probabilities > 0.5).float().squeeze().cpu().numpy()
    return predicted_mask

@app.post("/predict-mask/")
async def predict_mask_png(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        resized_image = image.resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR)
        predicted_mask = predict_mask_from_image(resized_image)
        mask_image = Image.fromarray((predicted_mask * 255).astype(np.uint8), mode="L")

        output = io.BytesIO()
        mask_image.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

@app.post("/predict-overlay/")
async def predict_overlay_png(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        resized_image = image.resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR)
        predicted_mask = predict_mask_from_image(resized_image)

        mask_image = Image.fromarray((predicted_mask * 255).astype(np.uint8), mode="L")
        alpha = mask_image.point(lambda p: 120 if p > 0 else 0)

        # Blend a red mask onto the resized image for quick visual inspection.
        overlay = Image.new("RGBA", resized_image.size, (255, 0, 0, 0))
        overlay.putalpha(alpha)
        combined = Image.alpha_composite(resized_image.convert("RGBA"), overlay)

        output = io.BytesIO()
        combined.save(output, format="PNG")
        return Response(content=output.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
