import React, { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline } from 'react-leaflet'
import axios from 'axios'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import './MapView.css'

delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// Create custom icons for agents
const createAgentIcon = (color, status) => {
  return L.divIcon({
    className: 'custom-agent-marker',
    html: `<div style="background-color: ${color}; width: 16px; height: 16px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 0 12px ${color}, inset 0 0 4px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;">
             <div style="width: 4px; height: 4px; background-color: #fff; border-radius: 50%;"></div>
           </div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  })
}

// Create custom icons for intersections
const createIntersectionIcon = (signalColor) => {
  return L.divIcon({
    className: 'custom-intersection-marker',
    html: `<div style="background-color: #1a1a1a; width: 14px; height: 14px; transform: rotate(45deg); border: 2px solid ${signalColor}; box-shadow: 0 0 8px ${signalColor};"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

function MapView() {
  const centerPosition = [18.5074, 73.8077] // Kothrud, Pune
  const [simulationData, setSimulationData] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)

  const mapSimToLatLng = (x, y) => {
    // Expanded map simulation space to ~3km x 3km area (tripled from original)
    const lat = 18.5074 + (y / 600) * 0.03 - 0.015 // Center around Kothrud
    const lng = 73.8077 + (x / 600) * 0.06 - 0.03
    return [lat, lng]
  }

  useEffect(() => {
    const fetchSimulationData = async () => {
      try {
        const response = await axios.get('/simulation_data')
        setSimulationData(response.data)
      } catch (error) {
        console.error('Error fetching simulation data:', error)
      }
    }

    fetchSimulationData()
    const interval = setInterval(fetchSimulationData, 1000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status) => {
    switch(status) {
      case 'moving': return '#ff6400'
      case 'executing': return '#ff00ff'
      case 'idle': return '#0064ff'
      case 'failed': return '#ef4444'
      default: return '#666'
    }
  }

  const getSignalColor = (signal) => {
    switch(signal) {
      case 'green': return '#00ff00'
      case 'yellow': return '#ffff00'
      case 'red': return '#ff0000'
      default: return '#666'
    }
  }

  if (!simulationData) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading D-LOGIC Map View...</p>
      </div>
    )
  }

  const position = centerPosition


  return (
    <>
      <div className="map-header">
        <div>
          <h2 className="map-title">D-LOGIC Map View</h2>
          <p className="map-subtitle">Multi-Agent System Overlay · Kothrud, Pune</p>
        </div>
        <div className="map-stats">
          <div className="map-stat">
            <span className="map-stat-label">Active Agents</span>
            <span className="map-stat-value">{simulationData.simulation_state.total_agents}</span>
          </div>
          <div className="map-stat">
            <span className="map-stat-label">Step</span>
            <span className="map-stat-value">{simulationData.simulation_state.step}</span>
          </div>
          <div className="map-stat">
            <span className="map-stat-label">Performance</span>
            <span className="map-stat-value">
              {(simulationData.simulation_state.system_performance * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      <div className="data-card map-panel">
        <div className="map-panel-bar">
          <span className="material-symbols-outlined">map</span>
          <span className="map-panel-label">Live Traffic Map with D-LOGIC Agents</span>
          <div className="map-legend">
            <div className="legend-item" style={{ marginRight: '15px' }}>
              <span style={{ fontSize: '11px', color: '#888', marginRight: '8px', fontWeight: '600', letterSpacing: '0.5px' }}>AGENTS:</span>
              <div className="legend-dot" style={{ backgroundColor: '#ff6400', boxShadow: '0 0 8px #ff6400' }}></div>
              <span>Moving</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ backgroundColor: '#ff00ff', boxShadow: '0 0 8px #ff00ff' }}></div>
              <span>Executing</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ backgroundColor: '#0064ff', boxShadow: '0 0 8px #0064ff' }}></div>
              <span>Idle</span>
            </div>
            <div className="legend-item" style={{ marginRight: '20px' }}>
              <div className="legend-dot" style={{ backgroundColor: '#ef4444', boxShadow: '0 0 8px #ef4444' }}></div>
              <span style={{ color: '#ef4444', fontWeight: 'bold' }}>Failed</span>
            </div>
            <div className="legend-item">
              <span style={{ fontSize: '11px', color: '#888', marginRight: '8px', fontWeight: '600', letterSpacing: '0.5px' }}>NODES:</span>
              <div className="legend-dot" style={{ backgroundColor: 'transparent', border: '2px solid #00ff00', borderRadius: '2px', transform: 'rotate(45deg)' }}></div>
              <span>Clear</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ backgroundColor: 'transparent', border: '2px solid #ff0000', borderRadius: '2px', transform: 'rotate(45deg)' }}></div>
              <span>Congested</span>
            </div>
          </div>
        </div>
        <div className="map-inner">
          <MapContainer center={position} zoom={15} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            
            {/* Render traffic intersections */}
            {simulationData.intersections.map((intersection) => {
              const [lat, lng] = mapSimToLatLng(intersection.position[0], intersection.position[1])
              return (
                <Marker
                  key={intersection.intersection_id}
                  position={[lat, lng]}
                  icon={createIntersectionIcon(getSignalColor(intersection.signal))}
                >
                  <Popup>
                    <div className="map-popup">
                      <strong>🚦 {intersection.intersection_id}</strong>
                      <div className="popup-row">
                        <span>Signal:</span>
                        <span style={{ color: getSignalColor(intersection.signal), fontWeight: 'bold' }}>
                          {intersection.signal.toUpperCase()}
                        </span>
                      </div>
                      <div className="popup-row">
                        <span>Vehicles:</span>
                        <span>{intersection.vehicle_count}</span>
                      </div>
                      <div className="popup-row">
                        <span>Congestion:</span>
                        <span className={`congestion-${intersection.congestion_level.toLowerCase()}`}>
                          {intersection.congestion_level}
                        </span>
                      </div>
                      {intersection.congestion_level === 'HIGH' && (
                        <div className="popup-alert">
                          ⚠️ <strong>Why congested?</strong><br/>
                          {intersection.vehicle_count} agents occupy this local sector. MAPPO is actively dynamically rerouting traffic around this node.
                        </div>
                      )}
                    </div>
                  </Popup>
                </Marker>
              )
            })}

            {/* Render agents */}
            {simulationData.agents.map((agent) => {
              const [lat, lng] = mapSimToLatLng(agent.position[0], agent.position[1])
              const color = getStatusColor(agent.status)
              
              return (
                <React.Fragment key={agent.id}>
                  {/* Agent marker */}
                  <Marker
                    position={[lat, lng]}
                    icon={createAgentIcon(color, agent.status)}
                    eventHandlers={{
                      click: () => setSelectedAgent(agent.id)
                    }}
                  >
                    <Popup>
                      <div className="map-popup">
                        <strong>🤖 {agent.id}</strong>
                        <div className="popup-row">
                          <span>Task:</span>
                          <span>{agent.task}</span>
                        </div>
                        <div className="popup-row">
                          <span>Status:</span>
                          <span style={{ color: color, fontWeight: 'bold' }}>
                            {agent.status.toUpperCase()}
                          </span>
                        </div>
                        <div className="popup-row">
                          <span>Speed:</span>
                          <span>{agent.speed.toFixed(1)} km/h</span>
                        </div>
                        <div className="popup-row">
                          <span>Battery:</span>
                          <span>{agent.battery.toFixed(0)}%</span>
                        </div>
                        <div className="popup-row">
                          <span>Neighbors:</span>
                          <span>{agent.neighbors.length}</span>
                        </div>
                        {agent.neighbors.length > 0 && (
                          <div className="popup-neighbors">
                            <small>Connected to: {agent.neighbors.join(', ')}</small>
                          </div>
                        )}
                      </div>
                    </Popup>
                  </Marker>

                  {/* Communication radius circle */}
                  <Circle
                    center={[lat, lng]}
                    radius={100} // 100 meters communication radius
                    pathOptions={{
                      color: color,
                      fillColor: color,
                      fillOpacity: 0.05,
                      weight: 1,
                      opacity: 0.3
                    }}
                  />

                  {/* Draw lines to neighbors */}
                  {agent.neighbors.map((neighborId) => {
                    const neighbor = simulationData.agents.find(a => a.id === neighborId)
                    if (neighbor) {
                      const [neighborLat, neighborLng] = mapSimToLatLng(neighbor.position[0], neighbor.position[1])
                      return (
                        <Polyline
                          key={`${agent.id}-${neighborId}`}
                          positions={[[lat, lng], [neighborLat, neighborLng]]}
                          pathOptions={{
                            color: '#00ffff',
                            weight: 2,
                            opacity: 0.6,
                            className: 'animated-p2p-link'
                          }}
                        />
                      )
                    }
                    return null
                  })}
                </React.Fragment>
              )
            })}

            {/* Draw road network edges */}
            {simulationData.network_topology.edges.map((edge, idx) => {
              const sourceNode = simulationData.network_topology.nodes.find(n => n.id === edge.source)
              const targetNode = simulationData.network_topology.nodes.find(n => n.id === edge.target)
              
              if (sourceNode && targetNode) {
                const [sourceLat, sourceLng] = mapSimToLatLng(sourceNode.position[0], sourceNode.position[1])
                const [targetLat, targetLng] = mapSimToLatLng(targetNode.position[0], targetNode.position[1])
                
                return (
                  <Polyline
                    key={`road-${idx}`}
                    positions={[[sourceLat, sourceLng], [targetLat, targetLng]]}
                    pathOptions={{
                      color: '#4f46e5',
                      weight: 3,
                      opacity: 0.35,
                      lineCap: 'round'
                    }}
                  />
                )
              }
              return null
            })}
          </MapContainer>
        </div>
      </div>

      {/* Selected Agent Info Panel */}
      {selectedAgent && (
        <div className="map-agent-info">
          <div className="map-agent-info-header">
            <span>Selected: {selectedAgent}</span>
            <button onClick={() => setSelectedAgent(null)}>×</button>
          </div>
          <div className="map-agent-info-body">
            {simulationData.agents.filter(a => a.id === selectedAgent).map(agent => (
              <div key={agent.id}>
                <div className="info-row">
                  <span>Task:</span>
                  <span>{agent.task}</span>
                </div>
                <div className="info-row">
                  <span>Status:</span>
                  <span style={{ color: getStatusColor(agent.status) }}>
                    {agent.status}
                  </span>
                </div>
                <div className="info-row">
                  <span>Speed:</span>
                  <span>{agent.speed.toFixed(1)} km/h</span>
                </div>
                <div className="info-row">
                  <span>Battery:</span>
                  <span>{agent.battery.toFixed(0)}%</span>
                </div>
                <div className="info-row">
                  <span>Neighbors:</span>
                  <span>{agent.neighbors.length}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

export default MapView
