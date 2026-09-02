# D-LOGIC User Guide

## Quick Start

1. **Start the server:**
   ```bash
   cd "C:\Users\Manaswin\Desktop\dev\AI-Traffic-Moderator"
   python app.py
   ```

2. **Open your browser:**
   Navigate to **http://localhost:5000**

3. **The simulation will start automatically!**

## Interface Overview

### Top Section: KPI Cards

Four real-time metric cards display:

1. **Active Agents** - Number of autonomous vehicles in the simulation
2. **Simulation Step** - Current iteration count  
3. **System Performance** - Average reward score (0-100%)
4. **Communication Events** - Total agent-to-agent messages

### Left Column: Simulation View & Agent Cards

#### Live Simulation Feed
- Shows real-time visualization of the D-LOGIC system
- **Orange agents** = Moving
- **Magenta agents** = Executing task
- **Blue agents** = Idle
- Green/Yellow/Red circles = Traffic signals at intersections
- Gray lines = Road network
- Thin cyan lines = Agent communication links

#### Agent Cards Grid
Each card shows:
- **Agent ID** (e.g., AGENT_001)
- **Colored status dot** (moving/executing/idle)
- **Task type** (delivery, patrol, rescue, transport, monitor)
- **Speed** in km/h
- **Battery** percentage
- **Neighbor count** (agents within communication range)
- **Position** (x, y coordinates)
- **Connected to** list (neighbor agent IDs)

**💡 TIP:** Click any agent card to view detailed information!

### Right Column: Details & Monitoring

#### Agent Details Panel (when agent selected)

**1. Agent State**
- Complete status information
- Position, speed, battery, task, status

**2. Neighborhood Info (Algorithm 1: KD-Tree)**
- **Neighbor Count:** How many agents are within 100m communication radius
- **Local Density:** Agents per square meter in neighborhood
- **Avg Speed:** Average speed of all neighbors
- **Congestion:** Congestion metric (0-100%)

This section demonstrates **Algorithm 1** in action - the KD-Tree spatial search finds all neighbors efficiently!

**3. Local Graph (Algorithm 2: GNN)**
- **Nodes:** Total nodes in the agent's local graph
- **Edges:** Total edges connecting the nodes
- **Node List:** Shows agent, neighbor, and intersection nodes

This section demonstrates **Algorithm 2** - the GNN uses this graph to make routing decisions!

**4. MAPPO Policy**
- **Exploration Rate:** How often the agent explores new strategies (5-30%)
- **Avg Reward:** Agent's performance score over time

#### Traffic Intersections Panel
Shows all 9 intersections (A1-A3, B1-B3, C1-C3):
- **Signal color indicator** (green/yellow/red light)
- **Vehicle count** at intersection
- **Congestion level** (LOW/MEDIUM/HIGH with color coding)

#### System Logs
- Timestamped events
- Simulation state changes
- Agent selections
- System messages

## Understanding the Algorithms

### Algorithm 1: KD-Tree Spatial Search

**What you see:**
- When you select an agent, the "Neighborhood Info" section shows:
  - How many neighbors were found
  - Local density around the agent
  - Average speed in the neighborhood
  - Congestion metric

**What's happening behind the scenes:**
1. All agent positions are inserted into a KD-Tree spatial index
2. For the selected agent, a range search queries the KD-Tree
3. The KD-Tree returns all agents within 100m radius
4. Statistics are computed from the neighbors
5. This information is used for decentralized decision-making

**Why it's efficient:**
- Traditional: Check distance to every agent = O(n)
- KD-Tree: Spatial search = O(log n)
- For 100 agents: ~100x faster!

### Algorithm 2: GNN-Coupled MAPPO

**What you see:**
- When you select an agent, the "Local Graph" section shows:
  - Node count (includes agent + neighbors + nearby intersections)
  - Edge count (connections between nodes)
  - Node type preview

**What's happening behind the scenes:**
1. **Graph Construction:**
   - Agent creates a local graph of its environment
   - Nodes: self, neighbors (from KD-Tree), nearby intersections
   - Edges: connections with distance and strength features

2. **GNN Processing (Simplified in this demo):**
   - Node features: density, speed, distance, congestion
   - Edge features: distance, connection type
   - In full implementation: message passing between nodes

3. **MAPPO Decision:**
   - Graph representation → policy network
   - Output: action (reroute/optimize_speed/maintain_course)
   - Agent's decision affects its movement

4. **Policy Learning:**
   - Action executed → reward calculated
   - Policy updated based on reward
   - Exploration rate adapts to performance

## Interactive Features

### Selecting an Agent
1. **Click** any agent card in the grid
2. The card will **highlight with green border**
3. The **Agent Details Panel** appears on the right
4. View all KD-Tree and GNN information
5. **Click again** to deselect

### Controlling the Simulation
- **Pause/Start button** in the top-right corner
- Click to toggle simulation execution
- Useful for:
  - Examining specific states
  - Taking screenshots
  - Analyzing agent behavior

### Monitoring Performance
Watch the KPI cards at the top:
- **System Performance** should stay above 50%
- **Communication Events** increases with more neighbors
- **Simulation Step** counts iterations

## What Each Agent Does

### Agent Tasks
- **delivery** - Transport packages/goods
- **patrol** - Monitor area security
- **rescue** - Emergency response
- **transport** - Passenger/cargo transport
- **monitor** - Surveillance and data collection

### Agent Status
- **idle** - Waiting for task assignment
- **moving** - Traveling to destination
- **executing** - Performing assigned task

### Agent Behavior
Each agent:
1. Uses **KD-Tree** to find neighbors
2. Constructs **local graph** with neighbors + intersections
3. **MAPPO policy** decides next action:
   - **Reroute** if congestion is high
   - **Optimize speed** if congestion is low
   - **Maintain course** if congestion is medium
4. Executes action and receives reward
5. Updates policy based on reward

## Understanding the Visualization

### Simulation Canvas Elements

**Agents (circles with ID labels):**
- 🟠 Orange = Moving
- 🟣 Magenta = Executing task
- 🔵 Blue = Idle
- White outline on all agents
- ID number below agent

**Road Network (gray lines):**
- Grid of 9 intersections
- Horizontal and vertical roads
- 200-unit spacing between intersections

**Traffic Signals (larger circles at intersections):**
- 🟢 Green = Go
- 🟡 Yellow = Caution  
- 🔴 Red = Stop
- Intersection ID labels (A1, A2, B1, etc.)
- Vehicle count below intersection

**Communication Links (cyan lines):**
- Connect agents within 100m range
- Show KD-Tree neighbor relationships
- Only visible when agents are close

**Communication Radius (gray circle):**
- Shows 100m radius around AGENT_001
- Visualizes the KD-Tree search range
- Only shown for first agent (to reduce clutter)

## Troubleshooting

### Simulation not updating?
- Check if simulation is paused (button should say "Start")
- Click the Start button to resume

### No agent details showing?
- Make sure you clicked an agent card
- Selected card should have green border
- Try clicking another agent

### Performance issues?
- Normal behavior: ~2 simulation steps per second
- Browser may slow down with many tabs open
- Try closing other applications

### Server not starting?
```bash
# Check if port 5000 is already in use
# Windows:
netstat -ano | findstr :5000

# If occupied, kill the process or change port in app.py
```

## Advanced Usage

### Adding Agents (via API)
```bash
curl -X POST http://localhost:5000/add_agent -H "Content-Type: application/json" -d "{\"id\":\"AGENT_006\",\"position\":[300,300],\"speed\":30,\"battery\":90,\"task\":\"delivery\"}"
```

### Viewing Algorithm Info
Navigate to: **http://localhost:5000/algorithms_info**

### Getting Simulation Data (JSON)
Navigate to: **http://localhost:5000/simulation_data**

### Checking Specific Agent
Navigate to: **http://localhost:5000/agent_details/AGENT_001**

## Tips for Demonstration

1. **Show Algorithm 1:**
   - Select an agent
   - Point to "Neighborhood Info" section
   - Explain KD-Tree finds neighbors efficiently
   - Show neighbor count and density metrics

2. **Show Algorithm 2:**
   - Keep agent selected
   - Point to "Local Graph" section
   - Explain GNN builds graph from neighbors
   - Show node and edge counts
   - Point to MAPPO policy section
   - Explain reward-based learning

3. **Show Decentralization:**
   - Select different agents
   - Show each has different neighbor counts
   - Explain each agent makes own decisions
   - Show how decisions affect movement

4. **Show Traffic Management:**
   - Point to intersections panel
   - Show congestion levels
   - Explain how signals adapt
   - Show vehicle counts updating

5. **Show System Performance:**
   - Watch KPI cards update
   - Show communication events increasing
   - Explain performance metrics

## Keyboard Shortcuts

Currently none implemented. Feature suggestion for future:
- `Space` - Pause/Resume simulation
- `1-5` - Select agents 1-5 quickly
- `Esc` - Deselect agent
- `R` - Reset simulation

---

**Need Help?** Check the D-LOGIC_README.md for technical details!
