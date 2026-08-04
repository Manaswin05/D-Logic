---
title: AI Traffic Moderator
emoji: 🚦
colorFrom: red
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">

# 🚦 AI Traffic Moderator

**Intelligent, real-time traffic signal control powered by computer vision and unsupervised learning.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-FF6F00?logo=ultralytics&logoColor=white)](https://github.com/ultralytics/ultralytics)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Educational-brightgreen)](#license)

[Live Demo](https://huggingface.co/spaces/Manaswin2005/ai-traffic-moderator) · [Documentation](Docs/INDEX.md) · [Report Bug](https://github.com/Manaswin05/AI-Traffic-Moderator/issues) · [Request Feature](https://github.com/Manaswin05/AI-Traffic-Moderator/issues)

</div>

---

## 📖 Overview

AI Traffic Moderator is a full-stack application that replaces static, timer-based traffic lights with an adaptive, AI-driven system. It captures a live video feed, detects vehicles in real time using **YOLOv8**, classifies traffic density with a self-learning **K-Means clustering** model, and dynamically adjusts signal timing — all visualized through a modern React dashboard.

### Key Highlights

- **Computer Vision Pipeline** — YOLOv8 nano model processes video frames to detect and classify cars, motorcycles, buses, and trucks.
- **Adaptive Signal Logic** — A K-Means model continuously learns from observed traffic patterns, replacing hard-coded thresholds with data-driven density classification (LOW / MEDIUM / HIGH).
- **Full-Stack Dashboard** — React 18 frontend with live video streaming, real-time analytics charts, interactive map view, and traffic signal visualization.
- **Cloud-Ready** — Containerized with Docker; deployable to Render, Hugging Face Spaces, or any cloud platform.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        React Frontend (Vite)                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │  Dashboard  │  │ Analytics  │  │  Map View  │  │  Sidebar  │ │
│  │ Live Feed   │  │ Chart.js   │  │  Leaflet   │  │ Navigation│ │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘  └───────────┘ │
└─────────┼───────────────┼───────────────┼───────────────────────┘
          │  HTTP / MJPEG │  Polling      │
          ▼               ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Flask Backend (Gunicorn)                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   /video_feed    │  │ /traffic_status │  │  /model_info    │ │
│  │   MJPEG Stream   │  │  JSON API       │  │  K-Means Stats  │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           ▼                    ▼                     ▼          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │            Core Processing Pipeline                         ││
│  │  Video Capture → YOLOv8 Detection → K-Means Classification ││
│  │                                   → Signal State Machine    ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎯 **Real-time Vehicle Detection** | YOLOv8 detects cars, motorcycles, buses, and trucks with bounding-box overlays |
| 🤖 **K-Means Traffic Classification** | Unsupervised model that self-trains on observed density, replacing static rules |
| 🚦 **Adaptive Signal Control** | Green/yellow/red timing adjusts dynamically based on AI-classified density |
| 📊 **Live Analytics** | Chart.js graphs tracking vehicle counts over time with 5-second polling |
| 🗺️ **Interactive Map** | Leaflet-powered camera location visualization with OpenStreetMap tiles |
| 📹 **MJPEG Video Stream** | Low-latency annotated video feed served directly to the browser |
| 🔄 **Source Switching** | Toggle between webcam and demo video via the dashboard |
| 🐳 **Docker Deployment** | Single-command containerized deployment for cloud platforms |

---

## 🛠️ Tech Stack

<table>
<tr>
<td><b>Frontend</b></td>
<td><b>Backend</b></td>
<td><b>AI / ML</b></td>
<td><b>DevOps</b></td>
</tr>
<tr>
<td>

- React 18
- Vite 5
- React Router 6
- Chart.js / react-chartjs-2
- React Leaflet
- Axios
- Lenis (smooth scroll)
- Three.js

</td>
<td>

- Flask 3.0
- Flask-CORS
- Gunicorn
- OpenCV (headless)

</td>
<td>

- YOLOv8 (Ultralytics)
- PyTorch (CPU)
- scikit-learn (K-Means)
- NumPy

</td>
<td>

- Docker
- Render
- Hugging Face Spaces
- Concurrently (dev)

</td>
</tr>
</table>

---

## 📋 Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.8 or higher |
| Node.js | 16 or higher |
| npm | 8 or higher |
| Git | Any recent version |
| Webcam | Optional — demo video included |

---

## 🚀 Getting Started

### 1 · Clone the repository

```bash
git clone https://github.com/Manaswin05/AI-Traffic-Moderator.git
cd AI-Traffic-Moderator
```

### 2 · Install dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies
npm install
```

### 3 · Run the application

The `dev` script launches **both** the Flask backend and Vite dev server concurrently:

```bash
npm run dev
```

| Service | URL |
|---|---|
| Frontend (Vite) | `http://localhost:3000` |
| Backend (Flask) | `http://localhost:5000` |

> **Note:** Use any username/password on the login screen — authentication is in demo mode.

---

## 🐳 Docker Deployment

```bash
# Build the production frontend first
npm run build

# Build and run the Docker image
docker build -t ai-traffic-moderator .
docker run -p 7860:7860 ai-traffic-moderator
```

The application will be available at `http://localhost:7860`.

See [Docs/RENDER_DEPLOYMENT.md](Docs/RENDER_DEPLOYMENT.md) and [Docs/HF_DOCKER_DEPLOYMENT.md](Docs/HF_DOCKER_DEPLOYMENT.md) for cloud deployment guides.

---

## 📁 Project Structure

```
AI-Traffic-Moderator/
├── src/                            # React frontend source
│   ├── components/
│   │   ├── Sidebar.jsx             # Navigation sidebar
│   │   └── Topbar.jsx              # Top navigation bar
│   ├── pages/
│   │   ├── Dashboard.jsx/.css      # Main dashboard with live feed
│   │   ├── Analytics.jsx/.css      # Real-time analytics charts
│   │   └── MapView.jsx/.css        # Interactive map view
│   ├── App.jsx                     # Root component & routing
│   ├── main.jsx                    # Application entry point
│   └── index.css                   # Global styles
├── models/
│   ├── yolov8n.pt                  # YOLOv8 nano model weights
│   └── traffic_kmeans.pkl          # Persisted K-Means model (auto-generated)
├── Docs/                           # Extended documentation
│   ├── INDEX.md                    # Documentation index
│   ├── KMEANS_README.md            # K-Means system deep-dive
│   ├── RENDER_DEPLOYMENT.md        # Render deployment guide
│   ├── HF_DOCKER_DEPLOYMENT.md     # Hugging Face Spaces guide
│   └── ...                         # Additional references
├── Wireless type/                  # Wireless sensor integration (future)
├── app.py                          # Flask backend & AI pipeline
├── Dockerfile                      # Container configuration
├── render.yaml                     # Render deployment manifest
├── requirements.txt                # Python dependencies
├── package.json                    # Node.js dependencies & scripts
├── vite.config.js                  # Vite build configuration
└── demo_traffic.mp4                # Demo video for testing
```

---

## 🧠 How It Works

### Detection → Classification → Control

```
Video Frame ──► YOLOv8 ──► Vehicle Count ──► K-Means ──► Density Label ──► Signal Logic
                 │                              │              │
                 ▼                              ▼              ▼
          Bounding Boxes              Cluster Assignment   GREEN / YELLOW / RED
          + Class Labels              (0, 1, or 2)         + Adaptive Timing
```

1. **Video Capture** — Reads frames from a webcam or demo video file (with automatic looping).
2. **Vehicle Detection** — YOLOv8 nano processes each frame, filtering for COCO vehicle classes (car, motorcycle, bus, truck).
3. **K-Means Classification** — Vehicle counts are fed into a K-Means model (k=3) that clusters traffic into LOW, MEDIUM, and HIGH density. The model self-trains periodically as it collects real data.
4. **Signal State Machine** — Traffic light timing adapts based on the classified density:

   | Density | Signal Behavior |
   |---|---|
   | **LOW** | Shorter red cycles (10s) |
   | **MEDIUM** | Yellow transition phase (8s) |
   | **HIGH** | Extended green cycles (20s) |

5. **Real-time Streaming** — Annotated frames are encoded as MJPEG and streamed to the frontend; traffic state is exposed via a JSON API polled every 5 seconds.

---

## 🔌 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/video_feed` | `GET` | MJPEG video stream with detection overlays |
| `/traffic_status` | `GET` | Current signal state, vehicle count, density, and model info |
| `/model_info` | `GET` | Detailed K-Means model statistics |
| `/train_model` | `POST` | Manually trigger K-Means retraining |
| `/set_video_source` | `POST` | Switch between `webcam` and `video` sources |

**Example response** — `GET /traffic_status`:

```json
{
  "traffic_light": "green",
  "vehicle_count": 14,
  "traffic_density": "HIGH",
  "cluster": 2,
  "model_trained": true,
  "samples_collected": 185,
  "cluster_centers": [3.2, 9.8, 19.5]
}
```

---

## ⚙️ Configuration

### Backend (`app.py`)

```python
# Camera / video source (env variable or default)
VIDEO_SOURCE = os.environ.get("VIDEO_SOURCE", "demo_traffic.mp4")

# Detected vehicle classes (COCO IDs)
VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

# K-Means parameters
MIN_SAMPLES    = 20     # Minimum data before first training
RETRAIN_INTERVAL = 150  # Samples between retraining cycles
MAX_DATA_SIZE  = 200    # Rolling window size
```

### Frontend (`vite.config.js`)

```javascript
server: {
  port: 3000,
  proxy: {
    '/video_feed': 'http://localhost:5000',
    '/traffic_status': 'http://localhost:5000',
    '/set_video_source': 'http://localhost:5000'
  }
}
```

---

## 🐛 Troubleshooting

<details>
<summary><b>PyTorch model loading error</b></summary>

If you see `_pickle.UnpicklingError` with PyTorch ≥ 2.6, the codebase already includes a monkey-patch that sets `weights_only=False`. No action needed — this is handled automatically in `app.py`.

</details>

<details>
<summary><b>Camera not detected</b></summary>

- Ensure no other application is using the webcam.
- Verify camera permissions in your OS settings.
- Try a different camera index: set `VIDEO_SOURCE` env variable or modify `cv2.VideoCapture(index)` in `app.py`.
- On cloud deployments, the system automatically falls back to the demo video.

</details>

<details>
<summary><b>Port already in use</b></summary>

- **Frontend:** Change the port in `vite.config.js` under `server.port`.
- **Backend:** Change the port in `app.py`: `app.run(port=5001)`.

</details>

<details>
<summary><b>High memory usage on free-tier hosting</b></summary>

The K-Means system is optimized for 512 MB environments (Render free tier). It uses a bounded `deque` of 200 samples (~1.6 KB) and CPU-only PyTorch. See [Docs/MEMORY_COMPARISON.md](Docs/MEMORY_COMPARISON.md) for details.

</details>

---

## 🗺️ Roadmap

- [ ] Multi-camera intersection management
- [ ] Emergency vehicle priority override
- [ ] Historical data analytics and reporting
- [ ] Mobile companion app
- [ ] Wireless sensor integration (see [`Wireless type/`](Wireless%20type/))
- [ ] Multi-intersection coordination

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch — `git checkout -b feature/your-feature`
3. **Commit** your changes — `git commit -m "Add your feature"`
4. **Push** to the branch — `git push origin feature/your-feature`
5. **Open** a Pull Request

---

## 📚 Documentation

Extended documentation is available in the [`Docs/`](Docs/) directory:

| Document | Description |
|---|---|
| [INDEX.md](Docs/INDEX.md) | Documentation index and navigation |
| [KMEANS_README.md](Docs/KMEANS_README.md) | K-Means classification system deep-dive |
| [KMEANS_SUMMARY.md](Docs/KMEANS_SUMMARY.md) | K-Means implementation summary |
| [RENDER_DEPLOYMENT.md](Docs/RENDER_DEPLOYMENT.md) | Render deployment guide |
| [HF_DOCKER_DEPLOYMENT.md](Docs/HF_DOCKER_DEPLOYMENT.md) | Hugging Face Spaces deployment |
| [MEMORY_COMPARISON.md](Docs/MEMORY_COMPARISON.md) | Memory optimization analysis |
| [YOLO_MODEL_FAQ.md](Docs/YOLO_MODEL_FAQ.md) | YOLOv8 model FAQ |

---

## 📝 License

This project is intended for **educational and research purposes**.

---

## 👤 Author

**Manaswin Sripatnala**

[![GitHub](https://img.shields.io/badge/GitHub-Manaswin05-181717?logo=github)](https://github.com/Manaswin05)

---

## 🙏 Acknowledgments

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — Real-time object detection
- [OpenCV](https://opencv.org/) — Computer vision and video processing
- [scikit-learn](https://scikit-learn.org/) — K-Means clustering
- [React](https://react.dev/) — Frontend UI framework
- [Flask](https://flask.palletsprojects.com/) — Backend web framework
- [Chart.js](https://www.chartjs.org/) — Data visualization
- [Leaflet](https://leafletjs.com/) — Interactive maps

---

<div align="center">

⭐ **Star this repo if you found it useful!** ⭐

</div>
