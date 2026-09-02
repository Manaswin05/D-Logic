from flask import Flask, render_template, Response, jsonify, send_from_directory, request
from flask_cors import CORS
import cv2
import time
import numpy as np
import os
import json
import random
import math
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
from scipy.spatial import KDTree
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
    """Algorithm 1: KD-Tree Spatial Range Search for Agent Neighbor Discovery"""
    
    def __init__(self):
        self.agents = {}  # id -> Agent
        self.kd_tree = None
        self.agent_positions = []
        self.agent_ids = []
        self.communication_radius = 100.0  # meters
        
    def add_agent(self, agent: Agent):
        """Add agent to the spatial index"""
        self.agents[agent.id] = agent
        self.rebuild_spatial_index()
        
    def remove_agent(self, agent_id: str):
        """Remove agent from the spatial index"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.rebuild_spatial_index()
    
    def rebuild_spatial_index(self):
        """Rebuild KD-Tree spatial index"""
        if not self.agents:
            self.kd_tree = None
            return
            
        positions = []
        ids = []
        
        for agent_id, agent in self.agents.items():
            positions.append(agent.position)
            ids.append(agent_id)
            
        self.agent_positions = np.array(positions)
        self.agent_ids = ids
        
        if len(positions) > 0:
            self.kd_tree = KDTree(self.agent_positions)
    
    def find_neighbors(self, agent_id: str) -> List[str]:
        """Find neighboring agents within communication radius"""
        if not self.kd_tree or agent_id not in self.agents:
            return []
            
        agent = self.agents[agent_id]
        
        # Query KD-Tree for neighbors within communication radius
        neighbor_indices = self.kd_tree.query_ball_point(
            agent.position, 
            self.communication_radius
        )
        
        # Convert indices to agent IDs, excluding self
        neighbors = []
        for idx in neighbor_indices:
            neighbor_id = self.agent_ids[idx]
            if neighbor_id != agent_id:
                neighbors.append(neighbor_id)
                
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
        # Create a simple grid network for simulation
        intersections = [
            ('A1', (100, 100)), ('A2', (300, 100)), ('A3', (500, 100)),
            ('B1', (100, 300)), ('B2', (300, 300)), ('B3', (500, 300)),
            ('C1', (100, 500)), ('C2', (300, 500)), ('C3', (500, 500))
        ]
        
        # Add intersection nodes
        for intersection_id, pos in intersections:
            self.road_network.add_node(intersection_id, pos=pos)
            
            # Initialize traffic state
            self.traffic_states[intersection_id] = TrafficState(
                intersection_id=intersection_id,
                position=pos,
                signal='green',
                timer=30,
                vehicle_count=0,
                congestion_level='LOW',
                connected_roads=[]
            )
        
        # Add road connections (edges)
        connections = [
            ('A1', 'A2'), ('A2', 'A3'),
            ('B1', 'B2'), ('B2', 'B3'),
            ('C1', 'C2'), ('C2', 'C3'),
            ('A1', 'B1'), ('A2', 'B2'), ('A3', 'B3'),
            ('B1', 'C1'), ('B2', 'C2'), ('B3', 'C3')
        ]
        
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
        node_features = np.array(local_graph.get('node_features', []))
        
        if len(node_features) > 1:
            # Calculate average congestion in neighborhood
            avg_congestion = np.mean(node_features[:, 0]) if node_features.shape[1] > 0 else 0
            
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
        
        # Initialize systems
        self.mappo_router.initialize_road_network()
        self.initialize_demo_agents()
        
    def initialize_demo_agents(self):
        """Initialize demo agents for simulation"""
        demo_agents = [
            Agent('AGENT_001', (150, 150), 25.0, 85.0, 'delivery', 'moving', [], [], time.time()),
            Agent('AGENT_002', (350, 250), 30.0, 92.0, 'patrol', 'idle', [], [], time.time()),
            Agent('AGENT_003', (450, 180), 20.0, 78.0, 'rescue', 'executing', [], [], time.time()),
            Agent('AGENT_004', (250, 400), 35.0, 88.0, 'transport', 'moving', [], [], time.time()),
            Agent('AGENT_005', (180, 320), 28.0, 95.0, 'monitor', 'idle', [], [], time.time())
        ]
        
        for agent in demo_agents:
            self.spatial_search.add_agent(agent)
            
        self.simulation_state['total_agents'] = len(demo_agents)
    
    def simulation_step(self):
        """Execute one simulation step"""
        self.simulation_state['step'] += 1
        
        # Step 1: Update spatial index and find neighbors
        self.spatial_search.update_agent_neighbors()
        
        # Step 2: Process each agent
        decisions_made = 0
        performance_sum = 0
        
        for agent_id, agent in self.spatial_search.agents.items():
            # Get neighborhood information (Algorithm 1)
            neighborhood_info = self.spatial_search.get_local_neighborhood_info(agent_id)
            
            # Construct local graph for GNN
            local_graph = self.mappo_router.construct_local_graph(agent_id, neighborhood_info)
            
            # Make routing decision using MAPPO (Algorithm 2)  
            decision = self.mappo_router.mappo_policy_decision(agent_id, local_graph)
            
            # Execute decision and calculate reward
            reward = self.execute_agent_decision(agent_id, decision)
            
            # Update policy with reward
            self.mappo_router.update_policy_with_reward(agent_id, reward)
            
            decisions_made += 1
            performance_sum += reward
            
            # Update agent position (simplified movement)
            self.update_agent_position(agent_id, decision)
        
        # Update simulation metrics
        if decisions_made > 0:
            self.simulation_state['system_performance'] = performance_sum / decisions_made
        
        self.simulation_state['communication_events'] = sum(
            len(agent.neighbors) for agent in self.spatial_search.agents.values()
        )
        
        # Update traffic states
        self.update_traffic_intersections()
        
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
            }
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
        time.sleep(0.5)  # 2 steps per second

# Start simulation thread
simulation_thread = threading.Thread(target=run_simulation, daemon=True)
simulation_thread.start()

# ---------------------------
# Visualization Frame Generation
# ---------------------------
def generate_simulation_frame():
    """Generate visualization frame for the D-LOGIC simulation"""
    frame = np.zeros((600, 600, 3), dtype=np.uint8)
    
    # Draw background grid
    for i in range(0, 600, 50):
        cv2.line(frame, (i, 0), (i, 600), (30, 30, 30), 1)
        cv2.line(frame, (0, i), (600, i), (30, 30, 30), 1)
    
    # Draw road network
    for edge in dlogic_sim.mappo_router.road_network.edges():
        start_pos = dlogic_sim.mappo_router.road_network.nodes[edge[0]]['pos']
        end_pos = dlogic_sim.mappo_router.road_network.nodes[edge[1]]['pos']
        cv2.line(frame, 
                (int(start_pos[0]), int(start_pos[1])), 
                (int(end_pos[0]), int(end_pos[1])), 
                (100, 100, 100), 3)
    
    # Draw traffic intersections
    for intersection_id, state in dlogic_sim.mappo_router.traffic_states.items():
        x, y = int(state.position[0]), int(state.position[1])
        
        # Color based on signal
        if state.signal == 'green':
            color = (0, 255, 0)
        elif state.signal == 'yellow':
            color = (0, 255, 255)
        else:  # red
            color = (0, 0, 255)
        
        cv2.circle(frame, (x, y), 15, color, -1)
        cv2.putText(frame, intersection_id, (x-10, y-20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, f"V:{state.vehicle_count}", (x-15, y+30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)
    
    # Draw agents
    for agent in dlogic_sim.spatial_search.agents.values():
        x, y = int(agent.position[0]), int(agent.position[1])
        
        # Color based on status
        if agent.status == 'moving':
            color = (255, 100, 0)  # Orange
        elif agent.status == 'executing':
            color = (255, 0, 255)  # Magenta
        else:  # idle
            color = (0, 100, 255)  # Blue
        
        # Draw agent
        cv2.circle(frame, (x, y), 8, color, -1)
        cv2.circle(frame, (x, y), 8, (255, 255, 255), 1)
        
        # Draw agent ID
        cv2.putText(frame, agent.id.split('_')[1], (x-8, y-12), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        
        # Draw communication radius (for first agent only, to avoid clutter)
        if agent.id == 'AGENT_001':
            cv2.circle(frame, (x, y), int(dlogic_sim.spatial_search.communication_radius), 
                      (100, 100, 100), 1)
        
        # Draw neighbor connections
        for neighbor_id in agent.neighbors:
            if neighbor_id in dlogic_sim.spatial_search.agents:
                neighbor = dlogic_sim.spatial_search.agents[neighbor_id]
                neighbor_x, neighbor_y = int(neighbor.position[0]), int(neighbor.position[1])
                cv2.line(frame, (x, y), (neighbor_x, neighbor_y), (0, 150, 150), 1)
    
    # Add simulation info overlay
    info_y = 30
    cv2.putText(frame, f"D-LOGIC Multi-Agent System", (10, info_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    info_y += 30
    cv2.putText(frame, f"Step: {dlogic_sim.simulation_state['step']}", (10, info_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    info_y += 25
    cv2.putText(frame, f"Agents: {dlogic_sim.simulation_state['total_agents']}", (10, info_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    info_y += 25
    cv2.putText(frame, f"Performance: {dlogic_sim.simulation_state['system_performance']:.2f}", (10, info_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    info_y += 25
    cv2.putText(frame, f"Comm Events: {dlogic_sim.simulation_state['communication_events']}", (10, info_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    # Algorithm info
    info_y += 40
    cv2.putText(frame, "Algorithm 1: KD-Tree Spatial Search", (10, info_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
    
    info_y += 20
    cv2.putText(frame, "Algorithm 2: GNN-MAPPO Routing", (10, info_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
    
    return frame

def process_simulation_frames():
    """Generate frames for the simulation visualization"""
    while True:
        frame = generate_simulation_frame()
        
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        time.sleep(0.1)  # 10 FPS
# ---------------------------
# Flask Routes
# ---------------------------
@app.route('/video_feed')
def video_feed():
    """Stream simulation visualization"""
    return Response(process_simulation_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

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
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    # If the path is a static file that exists, serve it
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Otherwise serve index.html (React Router handles the rest)
    return send_from_directory(app.static_folder, 'index.html')
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