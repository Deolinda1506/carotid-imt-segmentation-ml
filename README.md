# StrokeLink – Carotid IMT Segmentation & Triage

## 1. Description

StrokeLink is an Edge‑AI healthcare solution designed to bridge the **“treatment vacuum”** in rural clinical settings.  
It enables Community Health Workers (CHWs) to perform **carotid artery ultrasound screenings** and quantify **Intima‑Media Thickness (IMT)** directly on device, flagging individuals at elevated risk of ischemic stroke and generating digital referrals.

This repository contains:

- **ML**: carotid ultrasound segmentation models (U‑Net / ViT variants) and IMT measurement logic.
- **api**: a FastAPI backend for referrals and data synchronization.
- **app**: a Flutter mobile app (StrokeLink) that guides CHWs through scan → analysis → triage → referral.

### Dataset – Common Carotid Artery Ultrasound Images (Momot 2022)

This project uses the **Common Carotid Artery Ultrasound Images** dataset by **Agata Momot** (`Mendeley Data, V1, 2022, DOI: 10.17632/d4xt63mgjm.1`).  
Key characteristics of the dataset ([link](https://data.mendeley.com/datasets/d4xt63mgjm/1)):

- **Modality**: B‑mode ultrasound of the common carotid artery acquired on a Mindray UMT‑500Plus with an L13‑3s linear probe.
- **Subjects**: 11 individuals, each examined at least once on the left and right sides (vascular and carotid modalities).
- **Images**: 2,200 PNG images (≈100 frames per subject) at **709 × 749 × 3** resolution.
- **Labels**: Corresponding expert masks for each image (matching filenames), created by a technician and verified by an expert.
- **Intended use**: Carotid artery **segmentation** and **geometry / IMT measurement** and evaluation.
- **License**: **CC BY 4.0** – please cite:  
  *Momot, Agata (2022), “Common Carotid Artery Ultrasound Images”, Mendeley Data, V1, doi: 10.17632/d4xt63mgjm.1.*

The focus is on **functionality and workflow demonstration**, not long research exposition.

---

## 2. GitHub Repository

- Main repo: `https://github.com/Deolinda1506/carotid-imt-segmentation-ml`

---

## 3. Environment & Project Setup

The project has three main parts. You can use them independently or together.

### 3.1 Clone the repository

```bash
git clone https://github.com/Deolinda1506/carotid-imt-segmentation-ml.git
cd carotid-imt-segmentation-ml
```

Repository structure (high level):

- `ML/` – notebooks + trained models for carotid IMT segmentation.
- `api/` – FastAPI backend service.
- `app/` – StrokeLink Flutter client app.

---

### 3.2 ML Environment (Notebooks & Offline Experiments)

**Prerequisites**

- Python 3.10+ (3.11 recommended)
- `pip` or `conda`
- Jupyter Notebook or VS Code with Jupyter extension

**Option A – `venv` + `pip`**

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Option B – `conda`**

```bash
conda create -n carotid-imt python=3.11 -y
conda activate carotid-imt
pip install -r requirements.txt
```

> The root `requirements.txt` includes Jupyter, NumPy, OpenCV, PyTorch, Torchvision, and plotting utilities needed for experiments.

**Run the main notebook**

```bash
jupyter notebook ML/Carotid_Ultrasound_IMT_Model.ipynb
```

This notebook:

- Loads carotid ultrasound frames.
- Trains/evaluates U‑Net / ViT‑style segmentation models.
- Extracts IMT measurements from masks.
- Prepares models for deployment (TorchScript / ONNX / TFLite INT8).

---

### 3.3 Backend API (FastAPI Referral Service) – `api/`

The `api` folder exposes a FastAPI service that will:

- Accept IMT values and metadata from the mobile app.
- Create digital referrals for high‑risk patients.
- Provide hooks for hospital‑side dashboards or EMR systems.

**Setup**

```bash
cd api
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Run the server**

```bash
uvicorn main:app --reload
```

Default URL: `http://127.0.0.1:8000`

You can then wire the Flutter app’s **“Confirm & Notify Hospital”** button to call this API.

---

### 3.4 Flutter Mobile App – `app/` (StrokeLink)

The Flutter client implements the clinical workflow:

1. Secure Login (Firebase‑ready, AES‑256 session handling planned).
2. Dashboard – quick actions + activity stats.
3. Live Scan – guidance overlay + capture button.
4. AI Analysis – Edge‑AI processing state.
5. Results – IMT value + risk level.
6. Referral – digital referral to neurology.
7. Profile – user identity, scan history, local encryption status.

**Requirements**

- Flutter SDK (stable channel)
- Android Studio / Xcode (for mobile builds) or Chrome (for web)

**Setup**

```bash
cd app
flutter pub get
```

**Run on Chrome (web demo)**

```bash
flutter run -d chrome
```

**Run on Android / iOS**

```bash
flutter devices          # list devices
flutter run -d <device> # e.g., an Android emulator ID
```

> On web, camera/gallery are mocked; on mobile, these can be backed by `image_picker` or platform camera APIs and connected to the Edge‑AI pipeline.

---

## 4. Designs

### 4.1 Figma Mockups

High‑contrast, clinical UI optimized for outdoor/field use, including:

- Login and secure authentication.
- Diagnostic Dashboard with quick actions and activity stats.
- Live Scan with AI guidance.
- Analysis & Results with IMT quantification and risk badges.
- Referral summary and next‑steps card.
- User Profile & Settings.

Add your Figma link here:

**Figma**: <https://www.figma.com/design/fY1l0i5WnqkdSSMTBRJeky/Untitled?node-id=0-1&t=DAaDF5kbsBtMCFkX-1>

---

## 5. Deployment Plan

### 5.1 ML / Edge‑AI

- Consolidate trained segmentation model weights from `ML/models/`.
- Export:
  - TorchScript or ONNX for server‑side inference, and/or
  - TensorFlow Lite INT8 for on‑device inference.
- Integrate TFLite model with Flutter (via `tflite_flutter` or native bridge):
  - Preprocess input ultrasound frame.
  - Run segmentation to obtain lumen/intima/adventitia masks.
  - Compute IMT (in mm) from pixel spacing and mask geometry.

### 5.2 FastAPI Backend

- Extend `api/main.py` endpoints to:
  - Receive IMT + risk status + metadata (patient ID, GPS, timestamp).
  - Store referrals in a database (e.g., PostgreSQL).
  - Optionally notify hospital systems (email, webhook, FHIR, etc.).
- Containerize with Docker:

```bash
docker build -t stroklink-api ./api
docker run -p 8000:8000 stroklink-api
```

### 5.3 Flutter App

- Configure API base URL and environment variables.
- Implement secure storage (AES‑256) for:
  - Auth tokens.
  - Cached scans and IMT measurements (if needed offline).
- Build releases:

```bash
cd app
flutter build apk        # Android
flutter build ios        # iOS
flutter build web        # Web
```

### 5.4 Monitoring & Logging

- Log:
  - Volume of scans and referrals.
  - Distribution of IMT values and risk categories.
  - API response times and failures.
- Add dashboards and alerts as needed for production.

---

## 6. Demo Links

### 6.1 Video Demo (5–10 minutes)

- **Video link**: <https://drive.google.com/file/d/1OG1TUGSOI66jcxSKlduEaioTrM61OVVC/view?usp=sharing>

### 6.2 UI / UX Designs (Figma)

- **Figma file**: <https://www.figma.com/design/fY1l0i5WnqkdSSMTBRJeky/Untitled?node-id=0-1&t=DAaDF5kbsBtMCFkX-1>


---

## 7. Code Files & Structure

- **Root**
  - `README.md` – this document.
  - `requirements.txt` – base Python dependencies for ML experiments.

- **ML/**
  - `Carotid_Ultrasound_IMT_Model.ipynb` – main research notebook.
  - `models/` – trained U‑Net / ViT checkpoints for carotid IMT segmentation.

- **api/**
  - `main.py` – FastAPI app (referral API, health checks, etc.).
  - `requirements.txt` – backend requirements.

- **app/**
  - `lib/main.dart` – StrokeLink Flutter app (UI, navigation, state).
  - `pubspec.yaml` – Flutter dependencies.
  - Platform folders: `android/`, `ios/`, `web/`, `macos/`, `linux/`, `windows/`.
Please note that the Flutter app and FastAPI backend are still under development.

