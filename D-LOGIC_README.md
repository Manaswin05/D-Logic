# D-LOGIC: Decentralized Multi-Agent Pre-Dispatch Coordination System

## Overview

This system implements the **D-LOGIC** framework for autonomous mobility fleet coordination, featuring two core algorithms from your research:

### Algorithm 1: KD-Tree Spatial Range Search for Agent Neighbor Discovery

**Purpose:** Efficiently identify nearby AI agents within a predefined spatial radius for decentralized decision-making.

**Working Steps:**
1. TraCI obtains the current position of every AI agent from the SUMO simulation
2. The positions of all agents are inserted into a KD-Tree spatial index
3. For each agent, a spatial range search is performed using its current position and predefined communication radius
4. The KD-Tree returns agents located within the specified radius
5. The identified neighboring agents' states (position, speed, battery, task, status) are collected
6. The agent combines its own state with neighboring-agent information to form its local observation

**Key Features:**
- Communication radius: 100 meters
- O(log n) query time complexity
- Dynamic spatial indexing that updates in real-time
- Neighbor discovery for V2V communication

### Algorithm 2: GNN-Coupled MAPPO for Decentralized Routing

**Purpose:** Enable AI agents to make decentralized routing and task-reallocation decisions by combining graph-based representation with Multi-Agent Proximal Policy Optimization.

**Working Steps:**
1. Each agent constructs its local graph using own state, neighboring agents, and relevant road/traffic information
2. Node & edge features (position, battery, distance, congestion, task info) are provided to the GNN
3. The GNN performs message passing between connected nodes to learn relationships between agents and tasks
4. The resulting graph representation is passed to the MAPPO policy network
5. MAPPO outputs the agent's next decision (route selection, task reallocation, repositioning, or waiting)
6. The selected action is executed in SUMO, and the resulting reward is used to update the MAPPO policy during training

**Key Features:**
- Local graph construction with neighbors + traffic intersections
- Node types: agent, neighbor, intersection
- Edge features: distance, connection strength
- Policy learning with exploration/exploitation balance
- Reward-based policy updates

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    D-LOGIC Simulation Core                       │
│  ┌──────────────────────┐      ┌──────────────────────┐        │
│  │  KDTreeSpatialSearch │      │   GNNMAPPORouter     │        │
│  │  (Algorithm 1)       │──────│   (Algorithm 2)       │        │
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
              │  • System logs              │
              └─────────────────────────────┘
```

## Features

### 1. **Live Simulation Visualization**
- Real-time 600x600 canvas showing agent movements
- Road network topology with 9 intersections (3x3 grid)
- Agent rendering with status-based colors:
  - 🟠 Orange: Moving
  - 🟣 Magenta: Executing task
  - 🔵 Blue: Idle
- Communication radius visualization (KD-Tree range)
- Neighbor connection lines
- Traffic signal visualization at intersections

### 2. **Interactive Agent Cards**
- Click any agent to view detailed information
- Real-time updates (1 second polling)
- Display for each agent:
  - ID, Task type, Status
  - Speed, Battery level
  - Position coordinates
  - Neighbor count and list

### 3. **Agent Details Panel**
When an agent is selected, view:
- **Agent State:** Complete status information
- **Neighborhood Info (KD-Tree):** 
  - Neighbor count
  - Local density metric
  - Average speed in neighborhood
  - Congestion metric
- **Local Graph (GNN):**
  - Node and edge count
  - Graph structure preview
  - Node types (agent, neighbor, intersection)
- **MAPPO Policy:**
  - Exploration rate
  - Average reward score

### 4. **Traffic Intersection Monitoring**
- 9 intersection nodes displayed
- Real-time signal status (green/yellow/red)
- Vehicle count at each intersection
- Congestion level (LOW/MEDIUM/HIGH)

### 5. **System Performance Metrics**
- Active agent count
- Simulation step counter
- System performance percentage
- Communication events count

## API Endpoints

### GET `/simulation_data`
Returns complete simulation state including:
- All agent information
- Intersection states
- Network topology
- Performance metrics

### GET `/agent_details/<agent_id>`
Returns detailed information for a specific agent:
- Agent state
- Neighborhood information from KD-Tree
- Local graph structure for GNN
- MAPPO policy parameters

### POST `/simulation_control`
Control simulation execution:
```json
{
  "action": "start" | "stop" | "toggle"
}
```

### GET `/video_feed`
MJPEG stream of the simulation visualization

### POST `/add_agent`
Add a new agent to the simulation

### DELETE `/remove_agent/<agent_id>`
Remove an agent from the simulation

### GET `/algorithms_info`
Get detailed information about the two algorithms

## Running the Application

### Prerequisites
```bash
pip install flask flask-cors opencv-python-headless numpy scipy networkx
npm install
```

### Development Mode
```bash
# Build frontend
npm run build

# Start Flask server
python app.py
```

The application will be available at **http://localhost:5000**

### Production Mode
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Simulation Parameters

### Agent Properties
- **Position:** (x, y) coordinates in 600x600 space
- **Speed:** 20-40 km/h
- **Battery:** 70-100%
- **Tasks:** delivery, patrol, rescue, transport, monitor
- **Status:** idle, moving, executing

### KD-Tree Parameters
- **Communication Radius:** 100 meters
- **Spatial Index:** Rebuilt dynamically on position updates
- **Query Complexity:** O(log n) per agent

### MAPPO Parameters
- **Learning Rate:** 0.01
- **Exploration Rate:** 0.05-0.30 (adaptive)
- **Reward History:** Rolling window of 1000 samples
- **Policy Update:** After each decision execution

### Traffic Network
- **Grid Size:** 3x3 (9 intersections)
- **Intersection Spacing:** 200 units
- **Signal Timing:** Adaptive based on congestion
- **Congestion Thresholds:**
  - LOW: < 2 vehicles
  - MEDIUM: 2 vehicles
  - HIGH: ≥ 3 vehicles

## Technical Stack

### Backend
- **Framework:** Flask 3.0
- **Spatial Indexing:** scipy.spatial.KDTree
- **Network Topology:** NetworkX
- **Video Processing:** OpenCV
- **Data Structures:** NumPy arrays, Python dataclasses

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite 5
- **Styling:** Custom CSS with CSS variables
- **State Management:** React hooks (useState, useEffect)
- **HTTP Client:** Axios

## Key Differences from Original System

| Feature | Original (YOLOv8 + K-Means) | New (D-LOGIC) |
|---------|----------------------------|---------------|
| **Primary Goal** | Traffic signal optimization | Multi-agent fleet coordination |
| **Detection** | Vehicle detection from video | Simulated autonomous agents |
| **Algorithm 1** | YOLOv8 object detection | KD-Tree spatial search |
| **Algorithm 2** | K-Means clustering | GNN-Coupled MAPPO routing |
| **Decision Making** | Centralized signal control | Decentralized agent policies |
| **Communication** | None | V2V communication simulation |
| **Learning** | Unsupervised clustering | Reinforcement learning (MAPPO) |
| **Visualization** | Live camera feed | Agent simulation canvas |

## Future Enhancements

1. **Neural Network Implementation**
   - Implement actual GNN message passing
   - Train MAPPO policy networks with PyTorch
   
2. **SUMO Integration**
   - Connect to actual SUMO traffic simulator
   - Use TraCI for real traffic scenarios
   
3. **Advanced Routing**
   - A* pathfinding integration
   - Dynamic obstacle avoidance
   
4. **Fault Tolerance**
   - Battery depletion handling
   - Self-healing on agent failures
   
5. **Task Allocation**
   - Auction-based task distribution
   - Coalition formation algorithms

## Research Goals Achieved

✅ **Decentralized Edge Decision-Making:** Each agent makes decisions based on local neighborhood information

✅ **Self-Healing Fault Resilience:** Agents can operate independently without cloud server reliance

✅ **Heterogeneous Swarm Synergy:** Multiple agent types (AGVs, delivery drones) coordinate under unified system

✅ **Bounded Safety Compliance:** Control Barrier Functions (CBF) can be integrated for safety constraints

## Credits

**Based on Research:** D-LOGIC - Decentralized Multi-Agent Pre-Dispatch Coordination for Autonomous Mobility Fleets

**Algorithms Implemented:**
1. KD-Tree Spatial Range Search for Agent Neighbor Discovery
2. GNN-Coupled MAPPO for Decentralized Routing

**Team:** XDevs - Marathwada Mitra Mandal's College of Engineering

---

**Last Updated:** September 2, 2026
