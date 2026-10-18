from flask import Flask, render_template, Response, jsonify, send_from_directory, request
from flask_cors import CORS
import time
import os
import json
import random
import math
import hashlib
import hmac
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional
import networkx as nx
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical
from scipy.spatial import KDTree as ScipyKDTree
import numpy as np

# ── ECC imports (SECP256K1 via cryptography library) ──────────────────────────
from cryptography.hazmat.primitives.asymmetric.ec import (
    generate_private_key, SECP256K1, ECDH,
    EllipticCurvePublicKey
)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# ── Serve React build in production ───────────────────────────────────────────
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'dist')
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')
CORS(app)

# =============================================================================
# ECC P2P SECURE COMMUNICATION LAYER
# =============================================================================
# Each agent owns an ECC key pair on SECP256K1.
# When two agents come within communication range they perform an in-memory
# ECDH handshake → derive a 256-bit AES-GCM shared secret via HKDF-SHA256.
# All subsequent telemetry exchanges are:
#   1. Signed  with the sender's EC private key (ECDSA / SHA-256)
#   2. Encrypted with the per-pair AES-GCM key
#   3. Verified on receipt
# The shared secret is cached so the handshake only runs once per pair.
# =============================================================================

class AgentECCIdentity:
    """ECC identity for one agent: key pair + ECDH session cache."""

    CURVE = SECP256K1()

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._private_key = generate_private_key(self.CURVE, default_backend())
        self.public_key: EllipticCurvePublicKey = self._private_key.public_key()
        # peer_id -> AES-GCM key (bytes)
        self._session_keys: Dict[str, bytes] = {}

    # ── Public key serialisation (sent over the simulated channel) ────────────
    def public_key_bytes(self) -> bytes:
        """Uncompressed SEC1 public key bytes (65 bytes on SECP256K1)."""
        return self.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint
        )

    @staticmethod
    def public_key_from_bytes(raw: bytes) -> EllipticCurvePublicKey:
        return ec.EllipticCurvePublicKey.from_encoded_point(SECP256K1(), raw)

    # ── ECDH handshake ────────────────────────────────────────────────────────
    def derive_shared_secret(self, peer_id: str, peer_pub_bytes: bytes) -> bytes:
        """ECDH + HKDF → 32-byte AES key. Cached after first call."""
        if peer_id in self._session_keys:
            return self._session_keys[peer_id]

        peer_pub = ec.EllipticCurvePublicKey.from_encoded_point(SECP256K1(), peer_pub_bytes)
        raw_secret = self._private_key.exchange(ECDH(), peer_pub)

        # HKDF-SHA256 to stretch to a proper AES-256 key
        aes_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=f"{self.agent_id}:{peer_id}".encode(),
            backend=default_backend()
        ).derive(raw_secret)

        self._session_keys[peer_id] = aes_key
        return aes_key

    def invalidate_session(self, peer_id: str):
        """Drop cached session key when agents leave comm range."""
        self._session_keys.pop(peer_id, None)

    # ── Sign ──────────────────────────────────────────────────────────────────
    def sign(self, payload: bytes) -> bytes:
        """ECDSA-SHA256 signature over payload."""
        return self._private_key.sign(payload, ec.ECDSA(hashes.SHA256()))

    # ── Verify ────────────────────────────────────────────────────────────────
    @staticmethod
    def verify(public_key: EllipticCurvePublicKey, payload: bytes, signature: bytes) -> bool:
        try:
            public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False


class P2PSecureChannel:
    """
    Simulated P2P channel between two agents using ECC.

    Flow per message:
      sender  → sign(payload) → encrypt(payload, aes_key) → wire
      receiver → decrypt(ciphertext, aes_key) → verify(signature) → accept/reject
    """

    def __init__(self):
        # agent_id -> AgentECCIdentity
        self._identities: Dict[str, AgentECCIdentity] = {}
        # (sender_id, receiver_id) -> list of recent verified messages (capped at 20)
        self._message_log: Dict[Tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=20))
        # Total stats
        self.total_handshakes = 0
        self.total_messages = 0
        self.total_verified = 0
        self.total_failed = 0

    # ── Identity management ───────────────────────────────────────────────────
    def register_agent(self, agent_id: str) -> AgentECCIdentity:
        if agent_id not in self._identities:
            self._identities[agent_id] = AgentECCIdentity(agent_id)
        return self._identities[agent_id]

    def deregister_agent(self, agent_id: str):
        self._identities.pop(agent_id, None)

    def get_public_key_hex(self, agent_id: str) -> Optional[str]:
        """Return hex-encoded public key for UI display."""
        if agent_id in self._identities:
            return self._identities[agent_id].public_key_bytes().hex()
        return None

    # ── Handshake ─────────────────────────────────────────────────────────────
    def handshake(self, agent_a: str, agent_b: str) -> bool:
        """
        Mutual ECDH handshake between two agents.
        Both agents derive the same shared AES key (ECDH property).
        Returns True if handshake succeeded.
        """
        if agent_a not in self._identities or agent_b not in self._identities:
            return False

        id_a = self._identities[agent_a]
        id_b = self._identities[agent_b]

        # Each side derives the shared key using the other's public key bytes
        id_a.derive_shared_secret(agent_b, id_b.public_key_bytes())
        id_b.derive_shared_secret(agent_a, id_a.public_key_bytes())

        self.total_handshakes += 1
        return True

    # ── Send ──────────────────────────────────────────────────────────────────
    def send_message(self, sender_id: str, receiver_id: str, payload: dict) -> Optional[dict]:
        """
        Encrypt + sign a telemetry payload from sender to receiver.
        Returns the wire-format envelope (for logging/display).
        """
        if sender_id not in self._identities or receiver_id not in self._identities:
            return None

        id_sender = self._identities[sender_id]

        # Ensure session key exists (auto-handshake if needed)
        if receiver_id not in id_sender._session_keys:
            self.handshake(sender_id, receiver_id)

        aes_key = id_sender._session_keys[receiver_id]
        raw_payload = json.dumps(payload).encode()

        # Sign BEFORE encrypting so the receiver can verify after decrypt
        signature = id_sender.sign(raw_payload)

        # AES-256-GCM encrypt: nonce is 12 random bytes
        nonce = os.urandom(12)
        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(nonce, raw_payload, None)

        envelope = {
            'from': sender_id,
            'to': receiver_id,
            'nonce': nonce.hex(),
            'ciphertext': ciphertext.hex(),
            'signature': signature.hex(),
            'pubkey': id_sender.public_key_bytes().hex(),
            'ts': time.time()
        }

        self.total_messages += 1
        return envelope

    # ── Receive ───────────────────────────────────────────────────────────────
    def receive_message(self, receiver_id: str, envelope: dict) -> Optional[dict]:
        """
        Decrypt + verify an envelope. Returns the plaintext payload dict,
        or None if tampered / verification fails.
        """
        if receiver_id not in self._identities:
            return None

        id_receiver = self._identities[receiver_id]
        sender_id = envelope['from']

        # Ensure session key exists
        if sender_id not in id_receiver._session_keys:
            sender_pub_bytes = bytes.fromhex(envelope['pubkey'])
            id_receiver.derive_shared_secret(sender_id, sender_pub_bytes)

        aes_key = id_receiver._session_keys[sender_id]

        try:
            nonce = bytes.fromhex(envelope['nonce'])
            ciphertext = bytes.fromhex(envelope['ciphertext'])
            aesgcm = AESGCM(aes_key)
            raw_payload = aesgcm.decrypt(nonce, ciphertext, None)
        except Exception:
            self.total_failed += 1
            return None

        # Verify signature using sender's public key from the envelope
        sender_pub = ec.EllipticCurvePublicKey.from_encoded_point(
            SECP256K1(), bytes.fromhex(envelope['pubkey'])
        )
        if not AgentECCIdentity.verify(sender_pub, raw_payload, bytes.fromhex(envelope['signature'])):
            self.total_failed += 1
            return None

        payload = json.loads(raw_payload)
        self.total_verified += 1
        self._message_log[(sender_id, receiver_id)].append({
            'payload': payload,
            'ts': envelope['ts']
        })
        return payload

    # ── Convenience: simulate one secure telemetry exchange ───────────────────
    def exchange_telemetry(self, sender_id: str, receiver_id: str,
                           agent_state: dict) -> dict:
        """
        High-level helper: pack agent state, send, receive, verify.
        Returns a result dict with verification status and decrypted data.
        """
        envelope = self.send_message(sender_id, receiver_id, agent_state)
        if envelope is None:
            return {'verified': False, 'reason': 'identities_missing'}

        decrypted = self.receive_message(receiver_id, envelope)
        if decrypted is None:
            return {'verified': False, 'reason': 'decryption_or_sig_failed'}

        return {
            'verified': True,
            'from': sender_id,
            'to': receiver_id,
            'data': decrypted,
            'pubkey_from': envelope['pubkey'][:16] + '…'   # truncated for display
        }

    def get_stats(self) -> dict:
        return {
            'total_handshakes': self.total_handshakes,
            'total_messages': self.total_messages,
            'total_verified': self.total_verified,
            'total_failed': self.total_failed,
            'registered_agents': list(self._identities.keys())
        }


# Global P2P channel instance (shared across the simulation)
p2p_channel = P2PSecureChannel()

# =============================================================================
# BLOCKCHAIN AUDIT LEDGER
# =============================================================================
# Immutable event ledger using SHA-256 hash chains.
# Each significant simulation event (agent failure, task reallocation, routing
# decision) is recorded as a block with: timestamp, event data, prev_hash, nonce.
# Provides tamper-evident audit trail for research reproducibility.
# =============================================================================

class Block:
    """Single block in the blockchain."""
    
    def __init__(self, index: int, timestamp: float, data: dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """SHA-256 hash of block contents."""
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = 2):
        """Proof-of-work: find nonce such that hash starts with 'difficulty' zeros."""
        target = '0' * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> dict:
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash
        }


class Blockchain:
    """Immutable blockchain ledger for simulation events."""
    
    def __init__(self, difficulty: int = 2):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_transactions: List[dict] = []
        # Create genesis block
        self._create_genesis_block()
    
    def _create_genesis_block(self):
        """Initialize blockchain with genesis block."""
        genesis = Block(0, time.time(), {
            'event': 'GENESIS',
            'message': 'D-LOGIC Blockchain Initialized',
            'version': '1.0'
        }, '0')
        genesis.mine_block(self.difficulty)
        self.chain.append(genesis)
    
    def get_latest_block(self) -> Block:
        return self.chain[-1]
    
    def add_block(self, data: dict):
        """Add a new block with mining (proof-of-work)."""
        latest = self.get_latest_block()
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data=data,
            previous_hash=latest.hash
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
    
    def is_chain_valid(self) -> bool:
        """Verify blockchain integrity."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            
            # Verify hash
            if current.hash != current.calculate_hash():
                return False
            
            # Verify chain link
            if current.previous_hash != previous.hash:
                return False
            
            # Verify proof-of-work
            if not current.hash.startswith('0' * self.difficulty):
                return False
        
        return True
    
    def get_chain_summary(self) -> dict:
        """Summary stats for the blockchain."""
        return {
            'length': len(self.chain),
            'latest_hash': self.get_latest_block().hash,
            'is_valid': self.is_chain_valid(),
            'difficulty': self.difficulty,
            'total_events': sum(1 for b in self.chain if b.index > 0)
        }
    
    def get_recent_blocks(self, count: int = 10) -> List[dict]:
        """Get most recent blocks."""
        return [b.to_dict() for b in self.chain[-count:]]


# Global blockchain instance
blockchain = Blockchain(difficulty=2)

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
    """Algorithm 1: Spatial Range Search using scipy.spatial.KDTree (O(n log n))"""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.communication_radius = 100.0
        # Internal scipy KD-Tree + ordered id list; rebuilt on every position change
        self._kd_tree: Optional[ScipyKDTree] = None
        self._kd_ids: List[str] = []   # index i → agent_id

    # ── Index management ─────────────────────────────────────────────────────
    def add_agent(self, agent: Agent):
        self.agents[agent.id] = agent
        self.rebuild_spatial_index()

    def remove_agent(self, agent_id: str):
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.rebuild_spatial_index()

    def rebuild_spatial_index(self):
        """Rebuild the KD-Tree from current agent positions."""
        if not self.agents:
            self._kd_tree = None
            self._kd_ids = []
            return
        self._kd_ids = list(self.agents.keys())
        positions = np.array([self.agents[aid].position for aid in self._kd_ids])
        self._kd_tree = ScipyKDTree(positions)

    # ── Neighbor query ────────────────────────────────────────────────────────
    def find_neighbors(self, agent_id: str) -> List[str]:
        """O(log n) range query via scipy KD-Tree."""
        if agent_id not in self.agents or self._kd_tree is None:
            return []
        pos = np.array(self.agents[agent_id].position)
        # query_ball_point returns indices of all points within radius
        indices = self._kd_tree.query_ball_point(pos, self.communication_radius)
        return [self._kd_ids[i] for i in indices if self._kd_ids[i] != agent_id]

    def update_agent_neighbors(self):
        """Rebuild KD-Tree once then batch-query all agents."""
        self.rebuild_spatial_index()
        for agent_id in self.agents:
            self.agents[agent_id].neighbors = self.find_neighbors(agent_id)

    def get_local_neighborhood_info(self, agent_id: str) -> Dict:
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
            'avg_speed': 0.0,
            'congestion_metric': 0.0
        }

        if neighbors:
            speeds = []
            for neighbor_id in neighbors:
                neighbor = self.agents[neighbor_id]
                dist = math.sqrt(
                    (agent.position[0] - neighbor.position[0]) ** 2 +
                    (agent.position[1] - neighbor.position[1]) ** 2
                )
                neighborhood_info['neighbors'].append({
                    'id': neighbor_id,
                    'position': neighbor.position,
                    'speed': neighbor.speed,
                    'status': neighbor.status,
                    'distance': dist
                })
                speeds.append(neighbor.speed)
            neighborhood_info['avg_speed'] = sum(speeds) / len(speeds)
            neighborhood_info['congestion_metric'] = max(0.0, (len(neighbors) - 3) / 10.0)

        return neighborhood_info

class SimpleGNN(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)
        
    def forward(self, node_features, adj_matrix):
        aggregated = torch.matmul(adj_matrix, node_features)
        out = self.linear(aggregated)
        return F.relu(out)

class MAPPONetwork(nn.Module):
    def __init__(self, node_dim=3, hidden_dim=32, num_actions=3):
        super().__init__()
        self.gnn = SimpleGNN(node_dim, hidden_dim)
        
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_actions)
        )
        
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
    def forward(self, node_features, adj_matrix):
        x = self.gnn(node_features, adj_matrix)
        agent_repr = x[0] 
        action_logits = self.actor(agent_repr)
        value = self.critic(agent_repr)
        return action_logits, value

class GNNMAPPORouter:
    """Algorithm 2: GNN-Coupled MAPPO for Decentralized Routing"""
    
    def __init__(self):
        self.road_network = nx.Graph()
        self.traffic_states = {}  # intersection_id -> TrafficState
        self.global_reward_history = deque(maxlen=1000)
        
        # ── GPU/CPU device selection ──────────────────────────────────────────
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"[GNN-MAPPO] Using device: {self.device}")
        if torch.cuda.is_available():
            print(f"[GNN-MAPPO] GPU: {torch.cuda.get_device_name(0)}")
            print(f"[GNN-MAPPO] GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        
        # Centralized PyTorch MAPPO Model (moved to GPU if available)
        self.policy_net = MAPPONetwork(node_dim=3, hidden_dim=32, num_actions=3).to(self.device)
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=0.001)
        self.gamma = 0.99
        self.clip_ratio = 0.2
        
        # Experience buffer for all agents
        self.memory = []
        self.agent_policies = {}  # agent_id -> policy parameters
        
    def initialize_road_network(self):
        """Initialize road network topology"""
        import random
        import math
        
        # Create a distributed network for simulation
        # Create a distributed network in a heptagon shape (7 nodes)
        num_intersections = 7
        intersections = []
        
        # Center of simulation area
        cx, cy = 300, 300
        radius = 200
        
        for i in range(num_intersections):
            angle = (i * 2 * math.pi) / num_intersections
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            
            intersection_id = f'N{i}'
            intersections.append((intersection_id, (x, y)))
            
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
            
        # Generate ring connections (each connects to 2 neighbors)
        connections = []
        for i in range(num_intersections):
            j = (i + 1) % num_intersections
            conn = (f'N{i}', f'N{j}')
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
        node_features = local_graph.get('node_features', [])
        
        if not node_features:
            return {
                'action_type': 'maintain_course',
                'target_position': None,
                'route': [],
                'priority': 1.0,
                'confidence': 1.0
            }
            
        padded_features = []
        for f in node_features:
            arr = list(f)
            while len(arr) < 3:
                arr.append(0.0)
            padded_features.append(arr[:3])
            
        x = torch.tensor(padded_features, dtype=torch.float32).to(self.device)
        n_nodes = x.size(0)
        
        adj = torch.eye(n_nodes).to(self.device)
        node_ids = [n['id'] for n in local_graph['nodes']]
        node_idx = {n_id: i for i, n_id in enumerate(node_ids)}
        
        for edge in local_graph.get('edges', []):
            if edge['source'] in node_idx and edge['target'] in node_idx:
                s_idx = node_idx[edge['source']]
                t_idx = node_idx[edge['target']]
                weight = edge['features'][1] if len(edge['features']) > 1 else 1.0
                adj[s_idx, t_idx] = weight
                adj[t_idx, s_idx] = weight
                
        action_logits, value = self.policy_net(x, adj)
        dist = Categorical(logits=action_logits)
        
        action_idx = dist.sample()
        log_prob = dist.log_prob(action_idx)
        
        actions = ['maintain_course', 'reroute', 'optimize_speed']
        chosen_action = actions[action_idx.item()]
        
        decision = {
            'action_type': chosen_action,
            'target_position': None,
            'route': [],
            'priority': 1.0,
            'confidence': float(torch.exp(log_prob).item()),
            '_tensor_state': (x, adj),
            '_action_idx': action_idx,
            '_log_prob': log_prob,
            '_value': value
        }
        
        if chosen_action == 'reroute':
            decision['priority'] = 2.0
            decision['target_position'] = self.find_least_congested_intersection()
        elif chosen_action == 'optimize_speed':
            decision['priority'] = 1.5
            
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
    
    def update_policy_with_reward(self, agent_id: str, reward: float, decision: Dict = None):
        """Update agent policy based on reward feedback"""
        if decision and '_tensor_state' in decision:
            self.memory.append({
                'log_prob': decision['_log_prob'],
                'value': decision['_value'],
                'reward': reward
            })
            
        if len(self.memory) >= 32:
            self.optimizer.zero_grad()
            policy_loss = 0
            value_loss = 0
            
            for experience in self.memory:
                log_prob = experience['log_prob']
                value = experience['value']
                r = experience['reward']
                
                advantage = r - value.item()
                policy_loss -= log_prob * advantage
                value_loss += F.mse_loss(value, torch.tensor([r], dtype=torch.float32).to(self.device))
                
            loss = (policy_loss + 0.5 * value_loss) / len(self.memory)
            loss.backward()
            self.optimizer.step()
            self.memory.clear()

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
            policy['exploration_rate'] = max(0.05, policy['exploration_rate'] * 0.95)
        else:
            policy['exploration_rate'] = min(0.3, policy['exploration_rate'] * 1.05)
        
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
        
        for i in range(1, 5):
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
            # Register ECC identity for every agent
            p2p_channel.register_agent(agent.id)
            self.log_event('SYSTEM', f'Agent {agent.id} initialized - Task: {agent.task}', 'info')
            
        self.simulation_state['total_agents'] = len(demo_agents)
    
    def log_event(self, source: str, message: str, event_type: str = 'info', agent_id: str = None, target_id: str = None):
        """Log simulation events to memory and blockchain (for critical events)."""
        event = {
            'timestamp': time.time(),
            'step': self.simulation_state['step'],
            'source': source,
            'message': message,
            'type': event_type,
            'agent_id': agent_id,
            'target_id': target_id
        }
        self.event_log.append(event)
        
        # ── Write critical events to blockchain ───────────────────────────────
        # Error, success, and communication events are immutably recorded
        if event_type in ['error', 'success', 'communication']:
            blockchain_data = {
                'event_type': event_type,
                'source': source,
                'message': message,
                'step': self.simulation_state['step'],
                'agent_id': agent_id,
                'target_id': target_id
            }
            blockchain.add_block(blockchain_data)
    
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
            # ── ECC P2P Secure Telemetry Exchange ─────────────────────────
            # When this agent has neighbors, perform signed+encrypted telemetry
            # exchange with each new neighbor (handshake on first contact) and
            # log the verification result. Throttled to avoid log spam.
            if len(agent.neighbors) > 0:
                for neighbor_id in agent.neighbors:
                    # One-shot handshake per new pair (cached internally)
                    pair_key = (agent_id, neighbor_id)
                    pair_key_rev = (neighbor_id, agent_id)
                    handshake_done = (
                        neighbor_id in p2p_channel._identities.get(agent_id, AgentECCIdentity(agent_id))._session_keys
                        if agent_id in p2p_channel._identities else False
                    )
                    if not handshake_done:
                        p2p_channel.handshake(agent_id, neighbor_id)
                        self.log_event(
                            agent_id,
                            f'🔐 ECC Handshake: ECDH key exchange with {neighbor_id} — shared AES-256 session established',
                            'communication', agent_id, neighbor_id
                        )

                # Periodic secure telemetry broadcast (every 5 steps, only to first neighbor)
                if self.simulation_state['step'] % 5 == 0 and neighborhood_info['congestion_metric'] > 0:
                    neighbor_id = agent.neighbors[0]
                    telemetry = {
                        'agent_id': agent_id,
                        'position': list(agent.position),
                        'speed': round(agent.speed, 2),
                        'battery': round(agent.battery, 1),
                        'status': agent.status,
                        'congestion': round(neighborhood_info['congestion_metric'], 3),
                        'step': self.simulation_state['step']
                    }
                    result = p2p_channel.exchange_telemetry(agent_id, neighbor_id, telemetry)
                    if result['verified']:
                        self.log_event(
                            agent_id,
                            f'📡 ECC P2P → {neighbor_id}: signed telemetry verified ✓ '
                            f'(pubkey …{result["pubkey_from"]})',
                            'communication', agent_id, neighbor_id
                        )
                    else:
                        self.log_event(
                            agent_id,
                            f'⚠️ ECC P2P → {neighbor_id}: telemetry verification FAILED ({result.get("reason","")})',
                            'error', agent_id, neighbor_id
                        )
            
            # 2. MAPPO Routing Decisions (Only log when behavior actually changes significantly)
            if decision['action_type'] == 'reroute' and agent.status != 'moving':
                self.log_event(agent_id, f'MAPPO: Executing reroute to avoid high traffic (priority: {decision["priority"]})', 'alert', agent_id)
            elif decision['action_type'] == 'optimize_speed' and agent.speed < 20 and self.simulation_state['step'] % 10 == 0:
                self.log_event(agent_id, f'MAPPO: Accelerating in low-traffic zone', 'success', agent_id)
                
            # Assign nearby warehouse as target if no target exists
            if not decision.get('target_position') and agent.route:
                decision['target_position'] = agent.route[0]
                
            if not decision.get('target_position'):
                closest = None
                min_d = float('inf')
                for intersection_id, state in self.mappo_router.traffic_states.items():
                    d = math.sqrt((agent.position[0] - state.position[0])**2 + (agent.position[1] - state.position[1])**2)
                    if d > 20 and d < min_d:
                        min_d = d
                        closest = state.position
                if closest:
                    decision['target_position'] = closest
                    agent.route = [closest]
                    agent.status = 'moving'
            
            # Execute decision and calculate reward
            reward = self.execute_agent_decision(agent_id, decision)
            
            # Update policy with reward
            self.mappo_router.update_policy_with_reward(agent_id, reward, decision)
            
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
        
        # Ensure sleep is outside the lock so API requests don't block
        time.sleep(1.0)

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
            
            # Include ECC public key and active sessions
            ecc_info = {
                'public_key_hex': p2p_channel.get_public_key_hex(agent_id),
                'active_sessions': []
            }
            if agent_id in p2p_channel._identities:
                identity = p2p_channel._identities[agent_id]
                ecc_info['active_sessions'] = list(identity._session_keys.keys())
            
            return jsonify({
                'agent': agent.to_dict(),
                'neighborhood_info': neighborhood_info,
                'local_graph': local_graph,
                'policy': dlogic_sim.mappo_router.agent_policies.get(agent_id, {}),
                'ecc': ecc_info
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
        p2p_channel.register_agent(agent_id)
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
            p2p_channel.deregister_agent(agent_id)
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
                
                # Update edge weights (distances) for connected roads
                # networkx edges view allows us to iterate connected edges
                if hasattr(dlogic_sim.mappo_router.road_network, 'edges'):
                    for u, v, edge_data in list(dlogic_sim.mappo_router.road_network.edges(intersection_id, data=True)):
                        other_node = v if u == intersection_id else u
                        other_pos = dlogic_sim.mappo_router.road_network.nodes[other_node]['pos']
                        new_dist = math.sqrt((position[0] - other_pos[0])**2 + (position[1] - other_pos[1])**2)
                        dlogic_sim.mappo_router.road_network[u][v]['weight'] = new_dist
                        
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

@app.route('/p2p_status')
def p2p_status():
    """Get ECC P2P communication status and statistics"""
    with simulation_lock:
        stats = p2p_channel.get_stats()
        
        # Build per-agent detail
        agent_ecc_details = []
        for agent_id in dlogic_sim.spatial_search.agents.keys():
            pubkey_hex = p2p_channel.get_public_key_hex(agent_id)
            active_sessions = []
            if agent_id in p2p_channel._identities:
                identity = p2p_channel._identities[agent_id]
                active_sessions = list(identity._session_keys.keys())
            
            agent_ecc_details.append({
                'agent_id': agent_id,
                'public_key': pubkey_hex[:32] + '...' if pubkey_hex else None,  # truncated
                'active_sessions': active_sessions,
                'session_count': len(active_sessions)
            })
        
        return jsonify({
            'stats': stats,
            'agents': agent_ecc_details,
            'description': 'ECC SECP256K1 + ECDH + AES-256-GCM secure P2P channel'
        })

@app.route('/blockchain_status')
def blockchain_status():
    """Get blockchain ledger status and recent blocks"""
    with simulation_lock:
        return jsonify({
            'summary': blockchain.get_chain_summary(),
            'recent_blocks': blockchain.get_recent_blocks(20),
            'description': 'SHA-256 immutable audit ledger with proof-of-work'
        })

@app.route('/blockchain_verify')
def blockchain_verify():
    """Verify blockchain integrity"""
    with simulation_lock:
        is_valid = blockchain.is_chain_valid()
        return jsonify({
            'is_valid': is_valid,
            'chain_length': len(blockchain.chain),
            'message': 'Blockchain integrity verified ✓' if is_valid else 'Blockchain compromised ✗'
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