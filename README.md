[README.md](https://github.com/user-attachments/files/30220989/README.md)
# StressKey

An automated music intervention solution based on real-time keyboard dynamics and stress prediction.

StressKey detects psychological stress from natural typing rhythm (dwell time and flight time between keystrokes) and automatically recommends calming music — with no camera, wearable, or microphone required.

**FYP Author:** Beh Swee Shen (TP068561) — BSc (Hons) Computer Science, Data Analytics
**Asia Pacific University of Technology and Innovation**

---

## Project Structure

```
StressKey/                     Python backend (ML model, keyboard monitor, desktop app, API server)
stresskey-web/                 React web frontend
```

## Requirements

- Python 3.10+
- Node.js 18+ and npm
- Windows 10/11 (the desktop app and keyboard monitor use Windows-compatible libraries; pynput also supports macOS/Linux)

## Setup

### 1. Backend (Python)

```bash
cd StressKey
pip install -r ../requirements.txt
```

### 2. Frontend (Web)

```bash
cd stresskey-web
npm install
```

## Running the System

You need **two terminals running at the same time**.

**Terminal 1 — Backend server:**
```bash
cd StressKey
python server.py
```
Wait until you see `Uvicorn running on http://0.0.0.0:8000` with no errors.

**Terminal 2 — Web frontend:**
```bash
cd stresskey-web
npm run dev
```
Then open **http://localhost:5173** in your browser.

### Alternative: Desktop app only (no web frontend needed)

```bash
cd StressKey
python gui_app.py
```

## Re-training the Model

The pre-trained model (`StressKey/stress_model.pkl`) is already included. To retrain and re-compare all four classifiers (Random Forest, SVM, KNN, Extra Trees) from scratch:

```bash
cd StressKey
python StressKey_model_comparison.py
```

This regenerates `stress_model.pkl` along with comparison charts (`model_comparison_bar.png`, `model_confusion_matrices.png`, etc.) and the results table (`model_comparison_results.csv`).

## Dataset

`StressKey/Master_Dataset_Augmented_5k.csv` — derived from the EmoSurv: Typing Biometrics dataset (IEEE DataPort), filtered to Free Text typing instances (2,482 observations across five emotional states: Stressed, Angry, Neutral, Happy, Calm).

## Key Results

| Model | Test Accuracy | F1-Score |
|---|---|---|
| Random Forest | 96.58% | 96.55% |
| SVM | 88.73% | 88.66% |
| KNN | 97.59% | 97.58% |
| **Extra Trees (deployed)** | **97.99%** | **97.97%** |

## Privacy Note

The keyboard monitor (`keyboard_monitor.py`) captures only keystroke **timing** (press/release timestamps) — it never records, stores, or transmits which key was pressed. No typed content, passwords, or messages are ever captured.
