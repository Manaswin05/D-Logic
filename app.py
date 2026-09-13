from flask import Flask, render_template, Response, jsonify, send_from_directory, request
from flask_cors import CORS
import time
import os
import json
import random
import math
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
import networkx as nx

# Serve React build in production
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'dist')
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')
CORS(app)

# ============================================
# D-LOGIC: Decentralized Multi-Agent System
# ============================================

@dataclass
class Agent:
    """AI Agent representation for D-LOGIC system"""
    id: str
    position: Tuple[float, float]  # (x, y) coordinates
    speed: float
    battery: float
    task: str
    status: str  # 'idle', 'moving', 'executing'
    route: List[Tuple[float, float]]
    neighbors: List[str]
    last_update: float
    
    def to_dict(self):
        return asdict(self)

@dataclass  
class TrafficState:
    """Traffic intersection state"""
    intersection_id: str
    position: Tuple[float, float]
    signal: str  # 'red', 'yellow', 'green'
    timer: int
    vehicle_count: int
    congestion_level: str  # 'LOW', 'MEDIUM', 'HIGH'
    connected_roads: List[str]

class KDTreeSpatialSearch:
    """Algorithm 1: Spatial Range Search for Agent Neighbor Discovery"""
    
    def __init__(self):
        self.agents = {}  # id -> Agent
        self.communication_radius = 100.0  # meters
        
    def add_agent(self, agent: Agent):
        """Add agent to the spatial index"""
        self.agents[agent.id] = agent
        
    def remove_agent(self, agent_id: str):
        """Remove agent from the spatial index"""
        if agent_id in self.agents:
            del self.agents[agent_id]
    
    def rebuild_spatial_index(self):
        """No-op: neighbor search is done on-the-fly to save memory"""
        pass
    
    def find_neighbors(self, agent_id: str) -> List[str]:
        """Find neighboring agents within communication radius using simple distance check"""
        if agent_id not in self.agents:
            return []
            
        agent = self.agents[agent_id]
        r2 = self.communication_radius ** 2
        neighbors = []
        
        for other_id, other in self.agents.items():
            if other_id == agent_id:
                continue
            dx = agent.position[0] - other.position[0]
            dy = agent.position[1] - other.position[1]
            if dx*dx + dy*dy <= r2:
                neighbors.append(other_id)
                
        return neighbors
    
    def update_agent_neighbors(self):
        """Update neighbor lists for all agents"""
        for agent_id in self.agents:
            neighbors = self.find_neighbors(agent_id)
            self.agents[agent_id].neighbors = neighbors
    
    def get_local_neighborhood_info(self, agent_id: str) -> Dict:
        """Get local neighborhood information for decision making"""
        if agent_id not in self.agents:
            return {}
            
        agent = self.agents[agent_id]
        neighbors = self.find_neighbors(agent_id)
        
        neighborhood_info = {
            'agent_id': agent_id,
            'position': agent.position,
            'neighbor_count': len(neighbors),
            'neighbors': [],
            'local_density': len(neighbors) / (math.pi * self.communication_radius ** 2),
            'avg_speed': 0,
            'congestion_metric': 0
        }
        
        if neighbors:
            speeds = []
            for neighbor_id in neighbors:
                neighbor = self.agents[neighbor_id]
                neighborhood_info['neighbors'].append({
                    'id': neighbor_id,
                    'position': neighbor.position,
                    'speed': neighbor.speed,
                    'status': neighbor.status,
                    'distance': math.sqrt(
                        (agent.position[0] - neighbor.position[0]) ** 2 +
                        (agent.position[1] - neighbor.position[1]) ** 2
                    )
                })
                speeds.append(neighbor.speed)
            
            neighborhood_info['avg_speed'] = sum(speeds) / len(speeds)
            neighborhood_info['congestion_metric'] = max(0, (len(neighbors) - 3) / 10)  # Normalized congestion
        
        return neighborhood_info

class GNNMAPPORouter:
    """Algorithm 2: GNN-Coupled MAPPO for Decentralized Routing"""
    
    def __init__(self):
        self.road_network = nx.Graph()
        self.traffic_states = {}  # intersection_id -> TrafficState
        self.agent_policies = {}  # agent_id -> policy parameters
        self.global_reward_history = deque(maxlen=1000)
        self.learning_rate = 0.01
        
    def initialize_road_network(self):
        """Initialize road network topology"""
        import random
        import math
        
        # Create a distributed network for simulation
        random.seed(1337)  # Consistent layout
        num_intersections = 7
        intersections = []
        points = []
        
        for i in range(num_intersections):
            angle = random.uniform(0, 2 * math.pi)
            r = math.sqrt(random.uniform(0.1, 1.0)) * 250
            x = 300 + r * math.cos(angle)
            y = 300 + (r * 0.8) * math.sin(angle)
            
            intersection_id = f'N{i}'
            intersections.append((intersection_id, (x, y)))
            points.append([x, y])
            
        # Add intersection nodes
        for intersection_id, pos in intersections:
            self.road_network.add_node(intersection_id, pos=pos)
            self.traffic_states[intersection_id] = TrafficState(
                intersection_id=intersection_id,
                position=pos,
                signal='green',
                timer=30,
                vehicle_count=0,
                congestion_level='LOW',
                connected_roads=[]
            )
            
        # Generate road connections using nearest-neighbor edges (no scipy needed)
        connections = []
        for i in range(len(points)):
            # Connect each node to its 2-3 nearest neighbors
            dists = []
            for j in range(len(points)):
                if i == j:
                    continue
                d = math.sqrt((points[i][0]-points[j][0])**2 + (points[i][1]-points[j][1])**2)
                dists.append((d, j))
            dists.sort()
            for _, j in dists[:3]:
                edge = tuple(sorted([i, j]))
                conn = (f'N{edge[0]}', f'N{edge[1]}')
                if conn not in connections:
                    connections.append(conn)
            

        
        for start, end in connections:
            distance = math.sqrt(
                (self.road_network.nodes[start]['pos'][0] - self.road_network.nodes[end]['pos'][0]) ** 2 +
                (self.road_network.nodes[start]['pos'][1] - self.road_network.nodes[end]['pos'][1]) ** 2
            )
            self.road_network.add_edge(start, end, weight=distance)
    
    def construct_local_graph(self, agent_id: str, neighborhood_info: Dict) -> Dict:
        """Construct local graph representation for GNN processing"""
        graph_features = {
            'nodes': [],
            'edges': [],
            'node_features': [],
            'edge_features': []
        }
        
        # Add agent node
        agent_node = {
            'id': agent_id,
            'type': 'agent',
            'position': neighborhood_info['position'],
            'features': [
                neighborhood_info.get('local_density', 0),
                neighborhood_info.get('avg_speed', 0),
                neighborhood_info.get('congestion_metric', 0)
            ]
        }
        
        graph_features['nodes'].append(agent_node)
        graph_features['node_features'].append(agent_node['features'])
        
        # Add neighbor nodes
        for neighbor in neighborhood_info.get('neighbors', []):
            neighbor_node = {
                'id': neighbor['id'],
                'type': 'neighbor',
                'position': neighbor['position'],
                'features': [
                    neighbor['speed'],
                    neighbor['distance'],
                    1.0 if neighbor['status'] == 'moving' else 0.0
                ]
            }
            
            graph_features['nodes'].append(neighbor_node)
            graph_features['node_features'].append(neighbor_node['features'])
            
            # Add edge between agent and neighbor
            edge = {
                'source': agent_id,
                'target': neighbor['id'],
                'features': [neighbor['distance'], 1.0]  # distance, connection_strength
            }
            
            graph_features['edges'].append(edge)
            graph_features['edge_features'].append(edge['features'])
        
        # Add traffic intersection nodes if in range
        for intersection_id, traffic_state in self.traffic_states.items():
            distance = math.sqrt(
                (neighborhood_info['position'][0] - traffic_state.position[0]) ** 2 +
                (neighborhood_info['position'][1] - traffic_state.position[1]) ** 2
            )
            
            if distance <= 150:  # Within sensing range
                traffic_node = {
                    'id': intersection_id,
                    'type': 'intersection',
                    'position': traffic_state.position,
                    'features': [
                        traffic_state.vehicle_count / 20,  # Normalized count
                        1.0 if traffic_state.signal == 'green' else 0.0,
                        distance / 150  # Normalized distance
                    ]
                }
                
                graph_features['nodes'].append(traffic_node)
                graph_features['node_features'].append(traffic_node['features'])
                
                # Add edge to intersection
                edge = {
                    'source': agent_id,
                    'target': intersection_id,
                    'features': [distance, 0.5]  # distance, traffic_connection
                }
                
                graph_features['edges'].append(edge)
                graph_features['edge_features'].append(edge['features'])
        
        return graph_features
    
    def mappo_policy_decision(self, agent_id: str, local_graph: Dict) -> Dict:
        """MAPPO policy for routing and task allocation decisions"""
        # Simplified MAPPO decision logic
        # In real implementation, this would use neural network policies
        
        decision = {
            'action_type': 'move',
            'target_position': None,
            'route': [],
            'priority': 1.0,
            'confidence': 0.8
        }
        
        # Analyze local graph for decision making
        node_features = local_graph.get('node_features', [])
        
        if len(node_features) > 1:
            # Calculate average congestion in neighborhood
            first_features = [f[0] for f in node_features if len(f) > 0]
            avg_congestion = sum(first_features) / len(first_features) if first_features else 0
            
            # Decision logic based on congestion
            if avg_congestion > 0.7:  # High congestion
                decision['action_type'] = 'reroute'
                decision['priority'] = 2.0
                # Find alternative path
                target_intersection = self.find_least_congested_intersection()
                decision['target_position'] = target_intersection
                
            elif avg_congestion < 0.3:  # Low congestion
                decision['action_type'] = 'optimize_speed'
                decision['priority'] = 1.5
                
            else:  # Medium congestion
                decision['action_type'] = 'maintain_course'
                decision['priority'] = 1.0
        
        return decision
    
    def find_least_congested_intersection(self) -> Tuple[float, float]:
        """Find intersection with lowest congestion"""
        min_congestion = float('inf')
        best_intersection = (300, 300)  # Default center
        
        for intersection_id, state in self.traffic_states.items():
            congestion_score = state.vehicle_count + (0 if state.signal == 'green' else 5)
            
            if congestion_score < min_congestion:
                min_congestion = congestion_score
                best_intersection = state.position
                
        return best_intersection
    
    def update_policy_with_reward(self, agent_id: str, reward: float):
        """Update agent policy based on reward feedback"""
        if agent_id not in self.agent_policies:
            self.agent_policies[agent_id] = {
                'exploration_rate': 0.1,
                'performance_history': deque(maxlen=100),
                'average_reward': 0.0
            }
        
        policy = self.agent_policies[agent_id]
        policy['performance_history'].append(reward)
        
        if len(policy['performance_history']) > 0:
            policy['average_reward'] = sum(policy['performance_history']) / len(policy['performance_history'])
            
        # Adjust exploration rate based on performance
        if policy['average_reward'] > 0.7:
            policy['exploration_rate'] = max(0.05, policy['exploration_rate'] * 0.95)  # Reduce exploration
        else:
            policy['exploration_rate'] = min(0.3, policy['exploration_rate'] * 1.05)   # Increase exploration
        
        self.global_reward_history.append(reward)

class DLOGICSimulation:
    """Main D-LOGIC simulation coordinator"""
    
    def __init__(self):
        self.spatial_search = KDTreeSpatialSearch()
        self.mappo_router = GNNMAPPORouter()
        self.simulation_state = {
            'running': False,
            'step': 0,
            'total_agents': 0,
            'active_tasks': 0,
            'system_performance': 0.0,
            'communication_events': 0
        }
        self.event_log = deque(maxlen=50)  # Store last 50 events (reduced for memory)
        
        # Initialize systems
        self.mappo_router.initialize_road_network()
        self.initialize_demo_agents()
        
    def initialize_demo_agents(self):
        """Initialize demo agents for simulation"""
        import random
        import math
        random.seed(42)
        demo_agents = []
        tasks = ['delivery', 'patrol', 'rescue', 'transport', 'monitor']
        statuses = ['moving', 'idle', 'executing']
        
        for i in range(1, 21):
            agent_id = f'AGENT_{i:03d}'
            
            # Generate agents in a similar organic shape as the road network
            angle = random.uniform(0, 2 * math.pi)
            r = math.sqrt(random.uniform(0.1, 1.0)) * 240
            x = 300 + r * math.cos(angle)
            y = 300 + (r * 0.8) * math.sin(angle)
            
            speed = random.uniform(20, 50)
            battery = random.uniform(60, 100)
            task = random.choice(tasks)
            status = random.choice(statuses)
            
            demo_agents.append(
                Agent(agent_id, (x, y), speed, battery, task, status, [], [], time.time())
            )
        
        for agent in demo_agents:
            self.spatial_search.add_agent(agent)
            self.log_event('SYSTEM', f'Agent {agent.id} initialized - Task: {agent.task}', 'info')
            
        self.simulation_state['total_agents'] = len(demo_agents)
    
    def log_event(self, source: str, message: str, event_type: str = 'info', agent_id: str = None, target_id: str = None):
        """Log simulation events"""
        event = {
            'timestamp': time.time(),
            'step': self.simulation_state['step'],
            'source': source,
            'message': message,
            'type': event_type,  # 'info', 'communication', 'alert', 'success', 'warning', 'error'
            'agent_id': agent_id,
            'target_id': target_id
        }
        self.event_log.append(event)
    
    def simulation_step(self):
        """Execute one simulation step"""
        self.simulation_state['step'] += 1
        
        # Step 1: Update spatial index and find neighbors
        self.spatial_search.update_agent_neighbors()
        
        # Step 2: Process each agent
        decisions_made = 0
        performance_sum = 0
        
        for agent_id, agent in self.spatial_search.agents.items():
            # Check for hardware failure (0.2% chance per tick for active agents)
            if agent.status in ['executing', 'moving'] and random.random() < 0.002:
                agent.status = 'failed'
                agent.speed = 0
                self.log_event(agent_id, f'🚨 CRITICAL: Hardware failure detected on {agent_id}. Agent immobilized.', 'error', agent_id)
                
                # Self-healing: KD-Tree search for nearest idle agent
                nearest_idle = None
                min_dist = float('inf')
                for other_id, other_agent in self.spatial_search.agents.items():
                    if other_agent.status == 'idle' and other_id != agent_id:
                        dist = math.sqrt((agent.position[0]-other_agent.position[0])**2 + (agent.position[1]-other_agent.position[1])**2)
                        if dist < min_dist:
                            min_dist = dist
                            nearest_idle = other_agent
                
                if nearest_idle:
                    nearest_idle.status = 'moving'
                    nearest_idle.task = agent.task
                    agent.task = 'Awaiting Recovery'
                    self.log_event('SYSTEM', f'🔄 SELF-HEALING: Reallocated task from {agent_id} to {nearest_idle.id}', 'success', agent_id, nearest_idle.id)
                else:
                    self.log_event('SYSTEM', f'⚠️ SELF-HEALING PENDING: No idle agents available for {agent_id}', 'warning', agent_id)

            if agent.status == 'failed':
                continue # Skip routing and movement if failed

            # Get neighborhood information (Algorithm 1)
            neighborhood_info = self.spatial_search.get_local_neighborhood_info(agent_id)
            
            # Construct local graph for GNN
            local_graph = self.mappo_router.construct_local_graph(agent_id, neighborhood_info)
            
            # Make routing decision using MAPPO (Algorithm 2)  
            decision = self.mappo_router.mappo_policy_decision(agent_id, local_graph)
            
            # Deterministic logging based on actual state changes
            # 1. P2P communication (Only if congestion > 0.6 and has neighbors, throttled by step)
            if len(agent.neighbors) > 0 and neighborhood_info['congestion_metric'] > 0.6:
                if self.simulation_state['step'] % max(5, int(100/len(agent.neighbors))) == 0:
                    neighbor_id = agent.neighbors[0]
                    self.log_event(agent_id, f'P2P: Coordinating congestion avoidance with {neighbor_id}', 'communication', agent_id, neighbor_id)
            
            # 2. MAPPO Routing Decisions (Only log when behavior actually changes significantly)
            if decision['action_type'] == 'reroute' and agent.status != 'moving':
                self.log_event(agent_id, f'MAPPO: Executing reroute to avoid high traffic (priority: {decision["priority"]})', 'alert', agent_id)
            elif decision['action_type'] == 'optimize_speed' and agent.speed < 20 and self.simulation_state['step'] % 10 == 0:
                self.log_event(agent_id, f'MAPPO: Accelerating in low-traffic zone', 'success', agent_id)
            
            # Execute decision and calculate reward
            reward = self.execute_agent_decision(agent_id, decision)
            
            # Update policy with reward
            self.mappo_router.update_policy_with_reward(agent_id, reward)
            
            decisions_made += 1
            performance_sum += reward
            
            # Update agent position (simplified movement)
            self.update_agent_position(agent_id, decision)
            
            # Check for low battery deterministically (triggers exactly when crossing 20%)
            if agent.battery < 20 and (agent.battery + 0.1) >= 20:
                self.log_event(agent_id, f'⚠️ Battery Critical: {agent.battery:.1f}% - Initiating RTB (Return to Base)', 'warning', agent_id)
        
        # Check for agents that reached a warehouse (intersection) and remove them
        agents_to_remove = []
        for agent_id, agent in self.spatial_search.agents.items():
            for intersection_id, state in self.mappo_router.traffic_states.items():
                dist = math.sqrt(
                    (agent.position[0] - state.position[0]) ** 2 +
                    (agent.position[1] - state.position[1]) ** 2
                )
                if dist < 15:  # Within 15 units of a warehouse
                    agents_to_remove.append(agent_id)
                    self.log_event(agent_id, f'📦 {agent_id} arrived at warehouse {intersection_id}. Task "{agent.task}" complete. Agent deallocated.', 'success', agent_id)
                    break
        
        for agent_id in agents_to_remove:
            self.spatial_search.remove_agent(agent_id)
        
        self.simulation_state['total_agents'] = len(self.spatial_search.agents)
        
        # Update simulation metrics
        if decisions_made > 0:
            self.simulation_state['system_performance'] = performance_sum / decisions_made
        
        self.simulation_state['communication_events'] = sum(
            len(agent.neighbors) for agent in self.spatial_search.agents.values()
        )
        
        # Update traffic states
        self.update_traffic_intersections()
        
        # Log system-wide events occasionally
        if self.simulation_state['step'] % 20 == 0:
            self.log_event('SYSTEM', f'System health check - Performance: {self.simulation_state["system_performance"]:.2f}', 'info')
        
    def execute_agent_decision(self, agent_id: str, decision: Dict) -> float:
        """Execute agent decision and return reward"""
        agent = self.spatial_search.agents[agent_id]
        reward = 0.5  # Base reward
        
        if decision['action_type'] == 'reroute':
            # Reward for avoiding congestion
            reward = 0.8
            agent.status = 'moving'
            
        elif decision['action_type'] == 'optimize_speed':
            # Reward for efficiency
            reward = 0.7
            agent.speed = min(40.0, agent.speed * 1.1)
            
        elif decision['action_type'] == 'maintain_course':
            # Neutral reward
            reward = 0.6
            
        # Penalize high battery usage
        if agent.battery < 20:
            reward *= 0.5
            
        # Bonus for task completion
        if agent.status == 'executing':
            reward += 0.2
            
        return min(1.0, max(0.0, reward))
    
    def update_agent_position(self, agent_id: str, decision: Dict):
        """Update agent position based on decision"""
        agent = self.spatial_search.agents[agent_id]
        
        # Simple movement simulation
        if decision.get('target_position'):
            target_x, target_y = decision['target_position']
            current_x, current_y = agent.position
            
            # Move towards target
            dx = target_x - current_x
            dy = target_y - current_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 0:
                move_distance = agent.speed * 0.1  # Scale factor for simulation
                
                if distance > move_distance:
                    # Move towards target
                    agent.position = (
                        current_x + (dx / distance) * move_distance,
                        current_y + (dy / distance) * move_distance
                    )
                else:
                    # Reached target
                    if agent.status != 'idle':
                        self.log_event(agent_id, f'✓ Target destination reached for task: {agent.task}', 'success', agent_id)
                    agent.position = (target_x, target_y)
                    agent.status = 'idle'
        else:
            # Random small movement
            angle = random.uniform(0, 2 * math.pi)
            move_distance = agent.speed * 0.05
            
            agent.position = (
                agent.position[0] + math.cos(angle) * move_distance,
                agent.position[1] + math.sin(angle) * move_distance
            )
        
        # Keep within bounds (600x600 simulation area)
        agent.position = (
            max(50, min(550, agent.position[0])),
            max(50, min(550, agent.position[1]))
        )
        
        # Update battery (simple depletion)
        agent.battery = max(0, agent.battery - 0.1)
        
        # Rebuild spatial index after position changes
        self.spatial_search.rebuild_spatial_index()
    
    def update_traffic_intersections(self):
        """Update traffic intersection states"""
        for intersection_id, state in self.mappo_router.traffic_states.items():
            # Count nearby agents
            nearby_count = 0
            for agent in self.spatial_search.agents.values():
                distance = math.sqrt(
                    (agent.position[0] - state.position[0]) ** 2 +
                    (agent.position[1] - state.position[1]) ** 2
                )
                if distance <= 50:  # Within intersection range
                    nearby_count += 1
            
            state.vehicle_count = nearby_count
            
            # Update congestion level
            if nearby_count >= 3:
                state.congestion_level = 'HIGH'
            elif nearby_count >= 2:
                state.congestion_level = 'MEDIUM'
            else:
                state.congestion_level = 'LOW'
            
            # Simple traffic light logic
            current_time = time.time()
            if not hasattr(state, '_last_change'):
                state._last_change = current_time
            
            if current_time - state._last_change >= state.timer:
                if state.signal == 'green':
                    state.signal = 'yellow'
                    state.timer = 5
                elif state.signal == 'yellow':
                    state.signal = 'red'
                    state.timer = 15 if state.congestion_level == 'HIGH' else 10
                else:  # red
                    state.signal = 'green'
                    state.timer = 25 if state.congestion_level == 'HIGH' else 20
                
                state._last_change = current_time
    
    def get_simulation_data(self) -> Dict:
        """Get current simulation state for frontend"""
        agents_data = []
        for agent in self.spatial_search.agents.values():
            agent_data = agent.to_dict()
            agent_data['neighborhood_info'] = self.spatial_search.get_local_neighborhood_info(agent.id)
            agents_data.append(agent_data)
        
        intersections_data = []
        for intersection_id, state in self.mappo_router.traffic_states.items():
            intersections_data.append(asdict(state))
        
        # Convert event log to list with formatted timestamps
        events_list = []
        for event in list(self.event_log):
            events_list.append({
                'timestamp': time.strftime('%H:%M:%S', time.localtime(event['timestamp'])),
                'step': event['step'],
                'source': event['source'],
                'message': event['message'],
                'type': event['type'],
                'agent_id': event['agent_id'],
                'target_id': event['target_id']
            })
        
        return {
            'simulation_state': self.simulation_state,
            'agents': agents_data,
            'intersections': intersections_data,
            'network_topology': {
                'nodes': [
                    {'id': node_id, 'position': data['pos']}
                    for node_id, data in self.mappo_router.road_network.nodes(data=True)
                ],
                'edges': [
                    {'source': u, 'target': v, 'weight': data['weight']}
                    for u, v, data in self.mappo_router.road_network.edges(data=True)
                ]
            },
            'performance_metrics': {
                'avg_system_performance': self.simulation_state['system_performance'],
                'communication_efficiency': self.simulation_state['communication_events'] / max(1, self.simulation_state['total_agents']),
                'global_reward_avg': sum(self.mappo_router.global_reward_history) / max(1, len(self.mappo_router.global_reward_history)) if self.mappo_router.global_reward_history else 0
            },
            'event_log': events_list  # Include event log in response
        }

# Initialize D-LOGIC simulation
dlogic_sim = DLOGICSimulation()

# Simulation thread
simulation_thread = None
simulation_lock = threading.Lock()

def run_simulation():
    """Background simulation loop"""
    while True:
        with simulation_lock:
            if dlogic_sim.simulation_state['running']:
                dlogic_sim.simulation_step()
        time.sleep(1.0)  # 1 step per second (reduced CPU usage for free tier)

# Start simulation thread
simulation_thread = threading.Thread(target=run_simulation, daemon=True)
simulation_thread.start()

# Video feed removed to save ~80MB RAM (cv2 no longer imported)
# The React frontend renders everything via the /simulation_data JSON API

# ---------------------------
# Flask Routes
# ---------------------------
@app.route('/video_feed')
def video_feed():
    """Legacy video feed endpoint - no longer used"""
    return jsonify({'message': 'Video feed deprecated. Use /simulation_data API instead.'})

@app.route('/simulation_control', methods=['POST'])
def simulation_control():
    """Start/stop simulation"""
    data = request.json
    action = data.get('action', 'toggle')
    
    with simulation_lock:
        if action == 'start':
            dlogic_sim.simulation_state['running'] = True
        elif action == 'stop':
            dlogic_sim.simulation_state['running'] = False
        elif action == 'toggle':
            dlogic_sim.simulation_state['running'] = not dlogic_sim.simulation_state['running']
    
    return jsonify({
        'status': 'success',
        'running': dlogic_sim.simulation_state['running'],
        'message': f"Simulation {'started' if dlogic_sim.simulation_state['running'] else 'stopped'}"
    })

@app.route('/simulation_data')
def simulation_data():
    """Get current simulation data"""
    with simulation_lock:
        data = dlogic_sim.get_simulation_data()
    return jsonify(data)

@app.route('/agent_details/<agent_id>')
def agent_details(agent_id):
    """Get detailed information about a specific agent"""
    with simulation_lock:
        if agent_id in dlogic_sim.spatial_search.agents:
            agent = dlogic_sim.spatial_search.agents[agent_id]
            neighborhood_info = dlogic_sim.spatial_search.get_local_neighborhood_info(agent_id)
            local_graph = dlogic_sim.mappo_router.construct_local_graph(agent_id, neighborhood_info)
            
            return jsonify({
                'agent': agent.to_dict(),
                'neighborhood_info': neighborhood_info,
                'local_graph': local_graph,
                'policy': dlogic_sim.mappo_router.agent_policies.get(agent_id, {})
            })
    
    return jsonify({'error': 'Agent not found'}), 404

@app.route('/add_agent', methods=['POST'])
def add_agent():
    """Add a new agent to the simulation"""
    data = request.json
    
    agent_id = data.get('id', f'AGENT_{random.randint(100, 999)}')
    position = data.get('position', (random.uniform(50, 550), random.uniform(50, 550)))
    speed = data.get('speed', random.uniform(20, 40))
    battery = data.get('battery', random.uniform(70, 100))
    task = data.get('task', random.choice(['delivery', 'patrol', 'rescue', 'transport', 'monitor']))
    
    new_agent = Agent(agent_id, position, speed, battery, task, 'idle', [], [], time.time())
    
    with simulation_lock:
        dlogic_sim.spatial_search.add_agent(new_agent)
        dlogic_sim.simulation_state['total_agents'] = len(dlogic_sim.spatial_search.agents)
    
    return jsonify({
        'status': 'success',
        'message': f'Agent {agent_id} added successfully',
        'agent': new_agent.to_dict()
    })
@app.route('/remove_agent/<agent_id>', methods=['DELETE'])
def remove_agent(agent_id):
    """Remove an agent from the simulation"""
    with simulation_lock:
        if agent_id in dlogic_sim.spatial_search.agents:
            dlogic_sim.spatial_search.remove_agent(agent_id)
            dlogic_sim.simulation_state['total_agents'] = len(dlogic_sim.spatial_search.agents)
            return jsonify({
                'status': 'success',
                'message': f'Agent {agent_id} removed successfully'
            })
    
    return jsonify({'error': 'Agent not found'}), 404

@app.route('/update_agent_position', methods=['POST'])
def update_agent_position_route():
    """Update an agent's position (for drag-drop)"""
    data = request.json
    agent_id = data.get('agent_id')
    position = data.get('position')  # [x, y] in simulation co-ords
    
    if not agent_id or not position:
        return jsonify({'error': 'agent_id and position required'}), 400
    
    with simulation_lock:
        if agent_id in dlogic_sim.spatial_search.agents:
            dlogic_sim.spatial_search.agents[agent_id].position = tuple(position)
            return jsonify({'status': 'success', 'message': f'{agent_id} moved'})
    
    return jsonify({'error': 'Agent not found'}), 404

@app.route('/update_intersection_position', methods=['POST'])
def update_intersection_position():
    """Update an intersection's position (for drag-drop)"""
    data = request.json
    intersection_id = data.get('intersection_id')
    position = data.get('position')  # [x, y] in simulation coords
    
    if not intersection_id or not position:
        return jsonify({'error': 'intersection_id and position required'}), 400
    
    with simulation_lock:
        if intersection_id in dlogic_sim.mappo_router.traffic_states:
            dlogic_sim.mappo_router.traffic_states[intersection_id].position = tuple(position)
            if intersection_id in dlogic_sim.mappo_router.road_network.nodes:
                dlogic_sim.mappo_router.road_network.nodes[intersection_id]['pos'] = tuple(position)
            return jsonify({'status': 'success', 'message': f'{intersection_id} moved'})
    
    return jsonify({'error': 'Intersection not found'}), 404

@app.route('/remove_intersection/<intersection_id>', methods=['DELETE'])
def remove_intersection(intersection_id):
    """Remove an intersection from the simulation"""
    with simulation_lock:
        if intersection_id in dlogic_sim.mappo_router.traffic_states:
            del dlogic_sim.mappo_router.traffic_states[intersection_id]
            if intersection_id in dlogic_sim.mappo_router.road_network.nodes:
                dlogic_sim.mappo_router.road_network.remove_node(intersection_id)
            return jsonify({'status': 'success', 'message': f'{intersection_id} removed'})
    
    return jsonify({'error': 'Intersection not found'}), 404

@app.route('/reset_simulation', methods=['POST'])
def reset_simulation():
    """Reset simulation to default state"""
    global dlogic_sim
    with simulation_lock:
        dlogic_sim = DLOGICSimulation()
        dlogic_sim.simulation_state['running'] = True
    return jsonify({
        'status': 'success',
        'message': 'Simulation reset to default state'
    })

@app.route('/traffic_status')
def traffic_status():
    """Legacy route for compatibility with existing frontend"""
    with simulation_lock:
        data = dlogic_sim.get_simulation_data()
        
        # Convert to legacy format
        return jsonify({
            'traffic_light': 'green',  # Default
            'vehicle_count': len(dlogic_sim.spatial_search.agents),
            'traffic_density': 'MEDIUM',  # Default
            'cluster': 1,
            'model_trained': True,
            'samples_collected': data['simulation_state']['step'],
            'cluster_centers': [1.0, 2.0, 3.0]
        })

@app.route('/algorithms_info')
def algorithms_info():
    """Get information about the implemented algorithms"""
    return jsonify({
        'algorithm_1': {
            'name': 'KD-Tree Spatial Range Search for Agent Neighbor Discovery',
            'purpose': 'Efficiently identify nearby AI agents within a predefined spatial radius',
            'steps': [
                'TraCI obtains current position of every AI agent from SUMO simulation',
                'The position of all agents are inserted into a KD-Tree spatial index',
                'For each agent, spatial range search is performed using current position and predefined communication radius',
                'The KD-Tree returns agents located within the specified radius',
                'The identified neighboring agents\' states are collected',
                'Agent combines its own state with neighboring-agent information to form local observation'
            ]
        },
        'algorithm_2': {
            'name': 'GNN-Coupled MAPPO for Decentralized Routing',
            'purpose': 'Enable AI agents to make decentralized routing and task-reallocation decisions',
            'steps': [
                'Each agent constructs its local graph using own state, neighboring agents, and relevant road/traffic information',
                'Node & edge features such as position, battery, distance, congestion, and task information are provided to the GNN',
                'The GNN performs message passing between connected nodes to learn relationships between agents and tasks',
                'The resulting graph representation is passed to the MAPPO policy network',
                'MAPPO outputs the agent\'s next decision, such as selecting a route, taking/reallocating a task, repositioning, or waiting',
                'The selected action is executed in SUMO, and the resulting reward is used to update the MAPPO policy during training'
            ]
        }
    })

# Serve React frontend for all non-API routes (SPA support)
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.errorhandler(404)
def not_found(e):
    # If a route is not found (e.g. /map, /dashboard), serve the React index.html
    # so that React Router can handle the client-side routing.
    return app.send_static_file('index.html')
# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("D-LOGIC: Decentralized Multi-Agent Traffic Control System")
    print("=" * 60)
    print("Algorithm 1: KD-Tree Spatial Range Search for Agent Neighbor Discovery")
    print("Algorithm 2: GNN-Coupled MAPPO for Decentralized Routing")
    print("=" * 60)
    print("Flask server: http://localhost:5000")
    print("Simulation status: Ready to start")
    print("=" * 60)

    # Start simulation automatically
    dlogic_sim.simulation_state['running'] = True

    try:
        app.run(debug=False, threaded=True, host='0.0.0.0', port=5000)
    finally:
        print("D-LOGIC simulation shutdown complete.")