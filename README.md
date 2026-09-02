<div align="center">

# 🚗 D-LOGIC

**Decentralized Multi-Agent Pre-Dispatch Coordination System for Autonomous Mobility Fleets**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![NetworkX](https://img.shields.io/badge/NetworkX-Graph-orange)](https://networkx.org/)
[![SciPy](https://img.shields.io/badge/SciPy-KDTree-blue)](https://scipy.org/)
[![License](https://img.shields.io/badge/License-Educational-brightgreen)](#license)

[Documentation](D-LOGIC_README.md) · [User Guide](USER_GUIDE.md) · [Report Bug](https://github.com/Manaswin05/D-Logic/issues) · [Request Feature](https://github.com/Manaswin05/D-Logic/issues)

</div>

---

## 📖 Overview

D-LOGIC is a cutting-edge simulation and visualization platform for **decentralized multi-agent coordination** in autonomous mobility systems. Built on research from XDevs at Marathwada Mitra Mandal's College of Engineering, this system demonstrates how autonomous vehicles can make intelligent, coordinated decisions without centralized control.

Unlike traditional centralized traffic management systems, D-LOGIC enables each agent (autonomous vehicle) to make independent routing and task allocation decisions by combining:
- **Spatial awareness** through efficient neighbor discovery
- **Graph-based reasoning** for understanding local traffic patterns  
- **Reinforcement learning** for adaptive policy optimization

### Key Highlights

- **KD-Tree Spatial Search** — O(log n) neighbor discovery within communication radius for efficient V2V coordination
- **GNN-Coupled MAPPO** — Graph Neural Network representation combined with Multi-Agent Proximal Policy Optimization for decentralized routing decisions
- **Real-time Simulation** — Live visualization of autonomous agent movements, traffic patterns, and inter-agent communication
- **Interactive Dashboard** — React-based interface for monitoring agent states, neighborhood information, policy decisions, and system performance
- **Self-Healing Architecture** — Fault-resilient system with automatic task reallocation when agents fail

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    D-LOGIC Simulation Core                       │
│  ┌──────────────────────┐      ┌──────────────────────┐        │
│  │  KDTreeSpatialSearch │      │   GNNMAPPORouter     │        │
│  │   (Algorithm 1)      │──────│    (Algorithm 2)      │        │
│  │                      │      │                      │        │
│  │ • Spatial indexing   │      │ • Local graph        │        │
│  │ • Neighbor discovery │      │ • GNN processing     │        │
│  │ • Range queries      │      │ • MAPPO decisions    │        │
│  │ • O(log n) lookup    │      │ • Policy learning    │        │
│  └──────────────────────┘      └──────────────────────┘        │
│                 │                          │                     │
│                 └──────────┬───────────────┘                     │
│                            ▼                                     │
│                  ┌──────────────────┐                           │
│                  │ DLOGICSimulation │                           │
│                  │                  │                           │
│                  │ • Agent manager  │                           │
│                  │ • Step execution │                           │
│                  │ • Traffic states │                           │
│                  │ • Road network   │                           │
│                  └──────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │      Flask REST API         │
              │                             │
              │  /simulation_data          │
              │  /agent_details/<id>       │
              │  /simulation_control       │
              │  /video_feed (MJPEG)       │
              └─────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │   React Frontend (Vite)     │
              │                             │
              │  • Live simulation view     │
              │  • Agent status cards       │
              │  • Interactive selection    │
              │  • KD-Tree visualization    │
              │  • Traffic intersections    │
              │  • System event logs        │
              └─────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌐 **Decentralized Decision Making** | Each agent makes routing decisions based on local neighborhood information without central coordination |
| 🗺️ **KD-Tree Spatial Search** | Efficient O(log n) neighbor discovery within 100m communication radius for V2V coordination |
| 🧠 **GNN-MAPPO Routing** | Graph Neural Network representation with Multi-Agent PPO for intelligent path planning |
| 🚗 **Multi-Agent Simulation** | 5 autonomous agents with different tasks (delivery, patrol, rescue, transport, monitor) |
| 📊 **Real-time Visualization** | Live simulation canvas showing agent movements, road network, and traffic signals |
| 🔗 **V2V Communication** | Visual representation of agent-to-agent communication links based on proximity |
| 🚦 **Adaptive Traffic Signals** | 9-intersection traffic network with adaptive signal timing based on congestion |
| 📈 **Performance Metrics** | System-wide performance tracking, communication events, and reward scores |
| 🔍 **Interactive Agent Details** | Click any agent to view KD-Tree neighborhood info, local graph structure, and MAPPO policy |
| 🛡️ **Self-Healing System** | Automatic task reallocation when agents experience hardware failures |
| 📝 **Event Logging** | Timestamped system events including P2P communication, routing decisions, and state changes |

---

## 🧠 Core Algorithms

### Algorithm 1: KD-Tree Spatial Range Search for Agent Neighbor Discovery

**Purpose:** Efficiently identify nearby AI agents within a predefined spatial radius for decentralized decision-making.

**Process:**
1. All agent positions are inserted into a KD-Tree spatial index
2. For each agent, perform spatial range search using its position and 100m communication radius
3. KD-Tree returns agents within the specified radius in O(log n) time
4. Collect neighboring agents' states (position, speed, battery, task, status)
5. Agent combines own state with neighbor information for local observation
6. Calculate local density, average speed, and congestion metrics

**Benefits:**
- O(log n) query complexity vs. O(n) brute force
- Dynamic spatial indexing that updates in real-time
- Enables scalable V2V communication simulation
- Foundation for decentralized coordination

### Algorithm 2: GNN-Coupled MAPPO for Decentralized Routing

**Purpose:** Enable AI agents to make decentralized routing and task-reallocation decisions using graph-based representation with Multi-Agent Proximal Policy Optimization.

**Process:**
1. Each agent constructs local graph using own state, neighbors (from KD-Tree), and nearby intersections
2. Node features include position, battery, distance, congestion, and task information
3. Edge features capture distance and connection strength between entities
4. GNN performs message passing to learn relationships (simplified in current implementation)
5. MAPPO policy network processes graph representation
6. Policy outputs next decision: reroute, optimize_speed, or maintain_course
7. Action execution in simulation generates reward signal
8. Policy updates based on reward with adaptive exploration rate

**Benefits:**
- Decentralized decision-making with local information only
- Graph structure captures spatial and relational context
- Reward-based learning improves coordination over time
- Adaptive exploration balances optimization and discovery

---

## 🛠️ Tech Stack

<table>
<tr>
<td><b>Backend</b></td>
<td><b>Frontend</b></td>
<td><b>Algorithms</b></td>
<td><b>Visualization</b></td>
</tr>
<tr>
<td>

- Flask 3.0
- Flask-CORS
- Python 3.11

</td>
<td>

- React 18
- Vite 5
- Axios
- React Router 6

</td>
<td>

- SciPy (KD-Tree)
- NetworkX (Graphs)
- NumPy
- Dataclasses

</td>
<td>

- OpenCV (Canvas)
- Custom CSS
- Real-time MJPEG
- Interactive UI

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
| pip | Latest version |

---

## 🚀 Getting Started

### 1 · Clone the repository

```bash
git clone https://github.com/Manaswin05/D-Logic.git
cd D-Logic
```

### 2 · Install dependencies

```bash
# Python dependencies
pip install flask flask-cors opencv-python-headless numpy scipy networkx

# Node.js dependencies
npm install
```

### 3 · Build the frontend

```bash
npm run build
```

### 4 · Run the application

```bash
python app.py
```

The application will be available at **http://localhost:5000**

### Alternative: Development Mode with Hot Reload

```bash
# Runs Flask backend and Vite dev server concurrently
npm run dev
```

| Service | URL |
|---|---|
| Frontend (Vite) | `http://localhost:3000` |
| Backend (Flask) | `http://localhost:5000` |

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
D-Logic/
├── src/                            # React frontend source
│   ├── components/
│   │   ├── Sidebar.jsx/.css        # Navigation sidebar
│   │   └── Topbar.jsx/.css         # Top navigation bar
│   ├── pages/
│   │   ├── Dashboard.jsx/.css      # Main simulation dashboard
│   │   ├── Analytics.jsx/.css      # Performance analytics
│   │   └── MapView.jsx/.css        # Map visualization
│   ├── App.jsx                     # Root component & routing
│   ├── main.jsx                    # Application entry point
│   └── index.css                   # Global styles
├── models/                         # Pre-trained models (if needed)
├── Docs/                           # Extended documentation
│   ├── INDEX.md                    # Documentation index
│   ├── KMEANS_README.md            # Legacy K-Means docs
│   ├── RENDER_DEPLOYMENT.md        # Deployment guides
│   └── ...                         # Additional references
├── public/                         # Static assets
├── dist/                           # Built frontend (generated)
├── app.py                          # Flask backend & D-LOGIC core
├── D-LOGIC_README.md               # Detailed system documentation
├── USER_GUIDE.md                   # User interface guide
├── IMPLEMENTATION_SUMMARY.md       # Implementation details
├── MAPVIEW_ALGORITHMS.md           # Algorithm documentation
├── requirements.txt                # Python dependencies
├── package.json                    # Node.js dependencies
├── vite.config.js                  # Vite build configuration
└── README.md                       # This file
```

---

## 🎯 How It Works

### Simulation Flow

```
Agent Position Update → KD-Tree Rebuild → Neighbor Discovery → Local Graph Construction
                                               │                        │
                                               ▼                        ▼
                                    Neighborhood Metrics      GNN Feature Extraction
                                               │                        │
                                               └───────┬────────────────┘
                                                       ▼
                                              MAPPO Policy Decision
                                                       │
                                                       ▼
                                           Execute Action → Calculate Reward
                                                       │
                                                       ▼
                                              Update Policy Parameters
```

### Agent Decision-Making Process

1. **Spatial Indexing (Algorithm 1)**
   - Agent positions are inserted into KD-Tree
   - Each agent queries tree for neighbors within 100m radius
   - Local density, average speed, and congestion computed

2. **Graph Construction (Algorithm 2)**
   - Build local graph with 3 node types:
     - **Agent node:** Self-state with local metrics
     - **Neighbor nodes:** States of nearby agents from KD-Tree
     - **Intersection nodes:** Traffic signals within 150m
   - Create edges with distance and connection features

3. **MAPPO Decision**
   - Process graph representation (simplified GNN in current version)
   - Policy network outputs action:
     - **Reroute:** Find less congested path (high congestion)
     - **Optimize Speed:** Accelerate in clear areas (low congestion)
     - **Maintain Course:** Continue current trajectory (medium congestion)

4. **Reward Calculation**
   - Base reward + bonuses for task completion
   - Penalties for high battery usage
   - Congestion avoidance bonuses

5. **Policy Update**
   - Adjust exploration rate based on average reward
   - High performance → reduce exploration (exploit)
   - Low performance → increase exploration (explore)

### Traffic Management

- **9-intersection grid network** (3×3 layout, 200-unit spacing)
- **Adaptive signal timing** based on vehicle count:
  - LOW (< 2 vehicles): Standard timing
  - MEDIUM (2 vehicles): Yellow phase priority
  - HIGH (≥ 3 vehicles): Extended green + longer red
- **Real-time congestion tracking** per intersection

---

## 🔌 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/simulation_data` | `GET` | Complete simulation state (agents, intersections, network, metrics, event log) |
| `/agent_details/<agent_id>` | `GET` | Detailed agent info with KD-Tree neighborhood, local graph, and MAPPO policy |
| `/simulation_control` | `POST` | Control simulation: `{"action": "start" \| "stop" \| "toggle"}` |
| `/video_feed` | `GET` | MJPEG stream of real-time simulation visualization |
| `/add_agent` | `POST` | Add new agent to simulation dynamically |
| `/remove_agent/<agent_id>` | `DELETE` | Remove agent from simulation |
| `/algorithms_info` | `GET` | Detailed documentation of KD-Tree and GNN-MAPPO algorithms |
| `/` | `GET` | Serve React frontend (production build) |

### Example: Get Agent Details

**Request:**
```bash
GET http://localhost:5000/agent_details/AGENT_001
```

**Response:**
```json
{
  "agent_state": {
    "id": "AGENT_001",
    "position": [150.5, 220.3],
    "speed": 28.5,
    "battery": 85.2,
    "task": "delivery",
    "status": "moving",
    "neighbors": ["AGENT_002", "AGENT_005"]
  },
  "neighborhood_info": {
    "neighbor_count": 2,
    "local_density": 0.00006366,
    "avg_speed": 26.7,
    "congestion_metric": 0.0
  },
  "local_graph": {
    "nodes": 5,
    "edges": 4,
    "node_types": ["agent", "neighbor", "neighbor", "intersection", "intersection"]
  },
  "mappo_policy": {
    "exploration_rate": 0.12,
    "average_reward": 0.68,
    "performance_history_size": 45
  }
}
```

---

## ⚙️ Configuration

### Simulation Parameters

**Agent Properties:**
```python
# Agent capabilities
SPEED_RANGE = (20, 40)         # km/h
BATTERY_RANGE = (70, 100)      # percentage
TASKS = ['delivery', 'patrol', 'rescue', 'transport', 'monitor']
STATUS_OPTIONS = ['idle', 'moving', 'executing']
```

**KD-Tree Parameters (Algorithm 1):**
```python
COMMUNICATION_RADIUS = 100.0   # meters - V2V communication range
SPATIAL_DIMENSIONS = 2         # 2D space (x, y coordinates)
REBUILD_ON_UPDATE = True       # Rebuild tree after position changes
```

**MAPPO Parameters (Algorithm 2):**
```python
LEARNING_RATE = 0.01           # Policy update step size
EXPLORATION_RATE = 0.05-0.30   # Adaptive exploration (ε-greedy)
REWARD_HISTORY_SIZE = 1000     # Rolling window for global rewards
PERFORMANCE_HISTORY = 100      # Per-agent reward history
```

**Traffic Network:**
```python
GRID_SIZE = (3, 3)             # 9-intersection grid
INTERSECTION_SPACING = 200     # units between intersections
INTERSECTION_RANGE = 50        # Detection radius around intersection
SENSING_RANGE = 150            # Agent sensing distance
```

**Simulation Area:**
```python
CANVAS_SIZE = (600, 600)       # Pixel dimensions
AGENT_BOUNDS = (50, 550)       # Keep agents within borders
SIMULATION_TICK = 0.5          # Seconds per step (2 Hz)
```

---

## 🎨 User Interface

### Dashboard Features

**System KPIs (Top Row)**
- **Active Agents:** Real-time agent count
- **Simulation Step:** Current iteration number
- **System Performance:** Average reward score (0-100%)
- **Communication Events:** Total V2V message exchanges

**Agent Cards (Left Column)**
- Visual grid of all active agents
- Click to select and view detailed information
- Status color indicators:
  - 🟠 Orange: Moving
  - 🟣 Magenta: Executing task
  - 🔵 Blue: Idle
- Shows: ID, task, speed, battery, neighbors, position

**Live Simulation Canvas**
- Real-time 600×600 visualization
- Road network topology (gray lines)
- Agents with ID labels
- Traffic signals (green/yellow/red)
- Communication radius visualization
- V2V connection lines (cyan)

**Agent Details Panel (Right Column)**
When an agent is selected:
1. **Agent State:** Complete status information
2. **Neighborhood Info (KD-Tree):** Neighbor count, density, avg speed, congestion
3. **Local Graph (GNN):** Node/edge counts, graph structure
4. **MAPPO Policy:** Exploration rate, average reward

**Traffic Intersections Grid**
- 9 intersection cards (A1-C3)
- Real-time signal status with colored indicators
- Vehicle count per intersection
- Congestion level (LOW/MEDIUM/HIGH)

**System Event Log**
- Timestamped events
- P2P communications
- MAPPO routing decisions
- System alerts and state changes
- Color-coded by event type

---

## 🗺️ Roadmap

### Current Implementation ✅
- [x] KD-Tree spatial search with O(log n) neighbor discovery
- [x] GNN-MAPPO routing framework (simplified)
- [x] Multi-agent simulation with 5 autonomous agents
- [x] Real-time visualization and interactive dashboard
- [x] 9-intersection traffic network with adaptive signals
- [x] Self-healing fault tolerance with task reallocation
- [x] Event logging and system monitoring

### Future Enhancements 🚀

**Neural Network Integration**
- [ ] Implement full GNN message passing layers (PyTorch)
- [ ] Train MAPPO policy networks with actual gradients
- [ ] Add attention mechanisms for neighbor importance
- [ ] Experience replay buffer for improved learning

**SUMO Integration**
- [ ] Connect to SUMO traffic simulator via TraCI
- [ ] Import real-world road networks
- [ ] Use actual traffic scenarios and patterns
- [ ] Validate against baseline traffic control

**Advanced Features**
- [ ] Multi-intersection coordination protocols
- [ ] Emergency vehicle priority override
- [ ] Battery-aware routing and charging station integration
- [ ] Dynamic task allocation with auction mechanisms
- [ ] Coalition formation for cooperative tasks

**Visualization & UI**
- [ ] 3D visualization with Three.js
- [ ] Historical performance charts and analytics
- [ ] Heatmaps for traffic density and agent activity
- [ ] Path prediction visualization
- [ ] WebSocket for real-time updates (replace polling)

**Scalability**
- [ ] Support for 100+ agents
- [ ] Distributed simulation across multiple processes
- [ ] Cloud deployment with load balancing
- [ ] Performance benchmarking suite

**Safety & Validation**
- [ ] Control Barrier Functions (CBF) for safety constraints
- [ ] Collision avoidance verification
- [ ] Formal verification of coordination protocols
- [ ] Comparison with centralized baseline

---

## 🤝 Contributing

Contributions are welcome! This project is designed for research and education in multi-agent systems, graph neural networks, and reinforcement learning.

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit** your changes
   ```bash
   git commit -m "Add: brief description of your changes"
   ```
4. **Push** to your branch
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open** a Pull Request with a clear description

### Areas for Contribution

- **Algorithm Implementation:** Full GNN layers, improved MAPPO training
- **Visualization:** Enhanced UI, 3D rendering, better analytics
- **Integration:** SUMO connector, real traffic data sources
- **Testing:** Unit tests, integration tests, performance benchmarks
- **Documentation:** Tutorials, algorithm explanations, deployment guides
- **Research:** New coordination algorithms, safety mechanisms, evaluation metrics

---

## 📚 Documentation

Comprehensive documentation is available in the repository:

| Document | Description |
|---|---|
| [D-LOGIC_README.md](D-LOGIC_README.md) | Detailed system architecture and algorithm documentation |
| [USER_GUIDE.md](USER_GUIDE.md) | Complete user interface guide and interaction tutorial |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Implementation status and technical details |
| [MAPVIEW_ALGORITHMS.md](MAPVIEW_ALGORITHMS.md) | Algorithm specifications and pseudocode |
| [Docs/INDEX.md](Docs/INDEX.md) | Documentation index and navigation |
| [Docs/RENDER_DEPLOYMENT.md](Docs/RENDER_DEPLOYMENT.md) | Cloud deployment guide for Render |

### Quick Links

- **Getting Started:** See [USER_GUIDE.md](USER_GUIDE.md) for interface walkthrough
- **Algorithm Details:** See [D-LOGIC_README.md](D-LOGIC_README.md) for KD-Tree and GNN-MAPPO
- **Development:** See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical stack
- **Research Background:** See [MAPVIEW_ALGORITHMS.md](MAPVIEW_ALGORITHMS.md) for algorithm theory

---

## 🎓 Research Context

### D-LOGIC Framework

This implementation is based on research in **Decentralized Multi-Agent Pre-Dispatch Coordination for Autonomous Mobility Fleets**.

**Research Goals:**
- ✅ **Decentralized Edge Decision-Making:** Each agent makes decisions using only local information
- ✅ **Self-Healing Fault Resilience:** System continues operating when agents fail
- ✅ **Heterogeneous Swarm Synergy:** Multiple agent types coordinate under unified framework
- ✅ **Bounded Safety Compliance:** Safety constraints through local coordination (CBF integration planned)

**Key Innovations:**
1. **Spatial Efficiency:** KD-Tree reduces neighbor search from O(n) to O(log n)
2. **Graph-Based Reasoning:** GNN captures spatial and relational context for routing
3. **Decentralized Learning:** MAPPO enables independent policy learning with global coordination
4. **Scalability:** System scales to large fleets without centralized bottlenecks

**Research Team:** XDevs - Marathwada Mitra Mandal's College of Engineering

### Academic Applications

This platform is suitable for:
- Multi-agent reinforcement learning research
- Graph neural network applications in robotics
- Decentralized coordination algorithm development
- Traffic simulation and optimization studies
- Autonomous vehicle coordination research
- Fault-tolerant distributed systems

---

## 📝 License

This project is intended for **educational and research purposes**.

**Permissions:**
- ✅ Use for academic research and learning
- ✅ Modify and extend for research projects
- ✅ Share with proper attribution

**Restrictions:**
- ❌ Commercial use without permission
- ❌ Redistribution without attribution

For commercial licensing inquiries, please contact the author.

---

## 👤 Author

**Manaswin Sripatnala**

- GitHub: [@Manaswin05](https://github.com/Manaswin05)
- Project: [D-Logic](https://github.com/Manaswin05/D-Logic)

---

## 🙏 Acknowledgments

**Core Technologies:**
- [SciPy](https://scipy.org/) — KD-Tree spatial indexing implementation
- [NetworkX](https://networkx.org/) — Graph data structures and algorithms
- [Flask](https://flask.palletsprojects.com/) — Lightweight web framework
- [React](https://react.dev/) — Modern UI development
- [NumPy](https://numpy.org/) — Numerical computing foundation

**Research Inspiration:**
- Multi-Agent Reinforcement Learning literature
- Graph Neural Networks for robotics
- Decentralized coordination protocols
- SUMO traffic simulation framework

**Special Thanks:**
- XDevs Research Team at Marathwada Mitra Mandal's College of Engineering
- Open source community for foundational libraries
- Contributors and researchers advancing autonomous systems

---

<div align="center">

**⭐ Star this repository if you find it useful for your research or learning! ⭐**

**🔗 [View Live Demo](#) · [Read Documentation](D-LOGIC_README.md) · [Report Issues](https://github.com/Manaswin05/D-Logic/issues)**

---

*D-LOGIC: Advancing autonomous mobility through decentralized intelligence*

</div>
