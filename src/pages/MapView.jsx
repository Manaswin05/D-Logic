import React, { useState, useEffect, useRef } from 'react'
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
const createAgentIcon = (color, status, heading = 0) => {
  const truckSvg = `
    <svg width="24" height="40" viewBox="0 0 24 40" xmlns="http://www.w3.org/2000/svg" style="transform: rotate(${heading}deg); transform-origin: center; filter: drop-shadow(0px 4px 4px rgba(0,0,0,0.4));">
      <!-- cargo -->
      <rect x="2" y="14" width="20" height="24" rx="2" fill="#d4a373"/>
      <rect x="4" y="16" width="16" height="20" rx="1" fill="#e6ccb2"/>
      <!-- cab -->
      <path d="M2,14 L22,14 L20,2 L4,2 Z" fill="#ffffff"/>
      <path d="M4,13 L20,13 L18,4 L6,4 Z" fill="#f8fafc"/>
      <!-- windshield -->
      <path d="M3,12 L21,12 L19,8 L5,8 Z" fill="#1e293b"/>
      <!-- status dot -->
      <circle cx="12" cy="26" r="5" fill="${color}" stroke="#fff" stroke-width="2"/>
    </svg>
  `;

  return L.divIcon({
    className: 'custom-agent-marker',
    html: truckSvg,
    iconSize: [24, 40],
    iconAnchor: [12, 20],
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
  const centerPosition = [18.5204, 73.8567] // Pune City Center
  const [simulationData, setSimulationData] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [isBottomBarOpen, setIsBottomBarOpen] = useState(false)
  const [isLegendOpen, setIsLegendOpen] = useState(false)
  const agentHeadings = useRef({})

  const mapSimToLatLng = (x, y) => {
    // Map simulation space to cover entire Pune city (~25km x 25km area)
    const lat = 18.5204 + (y / 600) * 0.25 - 0.125
    const lng = 73.8567 + (x / 600) * 0.25 - 0.125
    return [lat, lng]
  }

  const mapLatLngToSim = (lat, lng) => {
    // Reverse mapping: convert lat/lng back to simulation x,y
    const y = ((lat - 18.5204 + 0.125) / 0.25) * 600
    const x = ((lng - 73.8567 + 0.125) / 0.25) * 600
    return [x, y]
  }

  const handleAgentDragEnd = async (agentId, e) => {
    const { lat, lng } = e.target.getLatLng()
    const [x, y] = mapLatLngToSim(lat, lng)
    try {
      await axios.post('/update_agent_position', { agent_id: agentId, position: [x, y] })
    } catch (err) {
      console.error('Failed to update agent position:', err)
    }
  }

  const handleIntersectionDragEnd = async (intersectionId, e) => {
    const { lat, lng } = e.target.getLatLng()
    const [x, y] = mapLatLngToSim(lat, lng)
    try {
      await axios.post('/update_intersection_position', { intersection_id: intersectionId, position: [x, y] })
    } catch (err) {
      console.error('Failed to update intersection position:', err)
    }
  }

  const handleRemoveAgent = async (agentId) => {
    try {
      await axios.delete(`/remove_agent/${agentId}`)
    } catch (err) {
      console.error('Failed to remove agent:', err)
    }
  }

  const handleRemoveIntersection = async (intersectionId) => {
    try {
      await axios.delete(`/remove_intersection/${intersectionId}`)
    } catch (err) {
      console.error('Failed to remove intersection:', err)
    }
  }

  useEffect(() => {
    let timeoutId;
    let isMounted = true;
    let hasData = false;

    const fetchSimulationData = async () => {
      try {
        const response = await axios.get('/simulation_data')
        if (isMounted) {
          setSimulationData(response.data)
          hasData = true;
          timeoutId = setTimeout(fetchSimulationData, 2500)
        }
      } catch (error) {
        console.error('Error fetching simulation data:', error)
        if (isMounted) {
          // If we haven't loaded data yet (backend still starting), retry quickly
          timeoutId = setTimeout(fetchSimulationData, hasData ? 2500 : 250)
        }
      }
    }

    fetchSimulationData()
    return () => {
      isMounted = false;
      clearTimeout(timeoutId)
    }
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
      case 'green': return '#10b981'
      case 'yellow': return '#f59e0b'
      case 'red': return '#ef4444'
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
      <div className="data-card map-panel" style={{ position: 'relative' }}>
        {/* Top Right Controls (Legend + System Toggle) */}
        <div className="map-legend-container">
          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            {/* System Info Toggle Button */}
            {(!isBottomBarOpen && !selectedAgent) && (
              <button 
                className="map-legend-toggle"
                style={{background: 'var(--surface)', color: 'var(--t-primary)'}}
                onClick={() => setIsBottomBarOpen(true)}
              >
                <span className="material-symbols-outlined" style={{color: '#10b981'}}>hub</span>
              </button>
            )}

            {/* Legend Toggle Button */}
            <button className="map-legend-toggle" onClick={() => setIsLegendOpen(!isLegendOpen)}>
              <span className="material-symbols-outlined">
                {isLegendOpen ? 'close' : 'map'}
              </span>
              {!isLegendOpen && <span style={{fontSize: '12px', fontWeight: 'bold'}}>Legend</span>}
            </button>
          </div>
          
          {isLegendOpen && (
            <div className="map-legend-popup">
              <div className="legend-item">
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
              <div className="legend-item">
                <div className="legend-dot" style={{ backgroundColor: '#ef4444', boxShadow: '0 0 8px #ef4444' }}></div>
                <span style={{ color: '#ef4444', fontWeight: 'bold' }}>Failed</span>
              </div>
              <div className="legend-item" style={{marginTop: '8px'}}>
                <span style={{ fontSize: '11px', color: '#888', marginRight: '8px', fontWeight: '600', letterSpacing: '0.5px' }}>NODES:</span>
                <div className="legend-dot" style={{ backgroundColor: 'transparent', border: '2px solid #10b981', borderRadius: '2px', transform: 'rotate(45deg)' }}></div>
                <span>Clear</span>
              </div>
              <div className="legend-item">
                <div className="legend-dot" style={{ backgroundColor: 'transparent', border: '2px solid #ef4444', borderRadius: '2px', transform: 'rotate(45deg)' }}></div>
                <span>Congested</span>
              </div>
            </div>
          )}
        </div>

        <div className="map-inner">
          <MapContainer center={position} zoom={12} style={{ height: '100%', width: '100%' }}>
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
                  draggable={true}
                  eventHandlers={{
                    dragend: (e) => handleIntersectionDragEnd(intersection.intersection_id, e),
                    contextmenu: (e) => {
                      e.originalEvent.preventDefault()
                      handleRemoveIntersection(intersection.intersection_id)
                    }
                  }}
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
                      <div style={{ marginTop: '8px', fontSize: '10px', color: '#888' }}>Drag to move · Right-click to remove</div>
                      {intersection.congestion_level === 'HIGH' && (
                        <div className="popup-alert">
                          ⚠️ <strong>Why congested?</strong><br/>
                          {intersection.vehicle_count} agents occupy this local sector. MAPPO is actively dynamically rerouting traffic around this node.
                        </div>
                      )}
                      
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveIntersection(intersection.intersection_id);
                        }}
                        style={{
                          marginTop: '12px', width: '100%', background: '#ef4444', color: '#fff', 
                          border: 'none', padding: '6px', borderRadius: '4px', cursor: 'pointer', 
                          fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px'
                        }}
                      >
                        <span className="material-symbols-outlined" style={{fontSize: '14px'}}>delete</span>
                        Remove Warehouse
                      </button>
                    </div>
                  </Popup>
                </Marker>
              )
            })}

            {/* Render agents */}
            {simulationData.agents.map((agent) => {
              const [lat, lng] = mapSimToLatLng(agent.position[0], agent.position[1])
              const color = getStatusColor(agent.status)
              
              // Calculate heading for truck rotation
              let heading = agentHeadings.current[agent.id]?.heading || 0
              const prevPos = agentHeadings.current[agent.id]?.pos
              
              if (prevPos && (prevPos[0] !== lat || prevPos[1] !== lng)) {
                // dy is North/South (lat), dx is East/West (lng)
                // Math.atan2(dx, dy) gives 0 for North, 90 for East
                const dy = lat - prevPos[0]
                const dx = lng - prevPos[1]
                heading = Math.atan2(dx, dy) * (180 / Math.PI)
                agentHeadings.current[agent.id] = { pos: [lat, lng], heading }
              } else if (!prevPos) {
                agentHeadings.current[agent.id] = { pos: [lat, lng], heading: 0 }
              }
              
              return (
                <React.Fragment key={agent.id}>
                  {/* Agent marker */}
                  <Marker
                    position={[lat, lng]}
                    icon={createAgentIcon(color, agent.status, heading)}
                    draggable={true}
                    eventHandlers={{
                      click: () => setSelectedAgent(agent.id),
                      dragend: (e) => handleAgentDragEnd(agent.id, e),
                      contextmenu: (e) => {
                        e.originalEvent.preventDefault()
                        handleRemoveAgent(agent.id)
                      }
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
                        <div style={{ marginTop: '8px', fontSize: '10px', color: '#888' }}>Drag to move · Right-click to remove</div>
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

      {/* Selected Agent or System Info Panel */}
      {(isBottomBarOpen || selectedAgent) && (
        <div className="map-agent-info" style={{ maxHeight: '40vh', overflowY: 'auto', paddingTop: '12px' }}>
          {/* Universal Collapse Handle */}
          <div style={{display: 'flex', justifyContent: 'center', marginBottom: '8px'}}>
            <button 
              style={{
                background: 'rgba(255, 255, 255, 0.1)', 
                border: 'none', 
                borderRadius: '50%', 
                width: '32px', 
                height: '32px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                cursor: 'pointer',
                color: 'var(--t-variant)'
              }}
              onClick={() => {
                setIsBottomBarOpen(false);
                if (selectedAgent) setSelectedAgent(null);
              }}
            >
              <span className="material-symbols-outlined">keyboard_arrow_down</span>
            </button>
          </div>
        {selectedAgent ? (
          simulationData.agents.filter(a => a.id === selectedAgent).map(agent => (
            <div key={agent.id} className="bs-content" style={{paddingTop: '0'}}>
              {/* Location Timeline */}
              <div className="bs-timeline">
                <div className="bs-timeline-line"></div>
                <div className="bs-location-row">
                  <span className="bs-dot green"></span>
                  <span className="bs-location-text">Origin Sector A2</span>
                </div>
                <div className="bs-location-row">
                  <span className="bs-dot red"></span>
                  <span className="bs-location-text">Destination Sector {agent.task.split(' ').pop()}</span>
                </div>
                <div className="bs-now-btn">
                  <span className="material-symbols-outlined">schedule</span>
                  <span>Now</span>
                </div>
              </div>

              {/* Agent Card */}
              <div className="bs-agent-card">
                <div className="bs-agent-icon">
                  <span className="material-symbols-outlined">smart_toy</span>
                </div>
                <div className="bs-agent-details">
                  <span className="bs-agent-name">{agent.id}</span>
                  <span className="bs-agent-desc">Autonomous Delivery Pod</span>
                </div>
                <div className="bs-agent-stats">
                  <span className="material-symbols-outlined">battery_charging_full</span>
                  <span>{agent.battery.toFixed(0)}%</span>
                </div>
              </div>

              {/* Action Tabs */}
              <div className="bs-action-tabs">
                <div className="bs-tab">
                  <span className="material-symbols-outlined" style={{color: '#10b981'}}>route</span>
                  <span>Route</span>
                </div>
                <div className="bs-tab">
                  <span className="material-symbols-outlined" style={{color: '#3b82f6'}}>list_alt</span>
                  <span>Logs</span>
                </div>
                <div className="bs-tab" onClick={async () => {
                  await handleRemoveAgent(agent.id);
                  setSelectedAgent(null);
                }}>
                  <span className="material-symbols-outlined" style={{color: '#ef4444'}}>delete</span>
                  <span>Remove Agent</span>
                </div>
              </div>

              {/* Primary Action */}
              <button className="bs-primary-btn" onClick={() => setSelectedAgent(null)}>
                Dispatch {agent.id}
              </button>
            </div>
          ))
        ) : (
          <div className="bs-content" style={{paddingTop: '0'}}>
            {/* System Card */}
            <div className="bs-agent-card" style={{position: 'relative'}}>
              <div className="bs-agent-icon" style={{background: 'rgba(16, 185, 129, 0.1)'}}>
                <span className="material-symbols-outlined" style={{color: '#10b981'}}>hub</span>
              </div>
              <div className="bs-agent-details">
                <span className="bs-agent-name">Multi-Agent Control</span>
                <span className="bs-agent-desc">System Performance</span>
              </div>
              <div className="bs-agent-stats" style={{flexDirection: 'row', alignItems: 'center', gap: '6px', marginRight: '24px'}}>
                <span className="material-symbols-outlined" style={{color: '#10b981'}}>speed</span>
                <span style={{fontSize: '16px'}}>{(simulationData.simulation_state.system_performance * 100).toFixed(0)}%</span>
              </div>
            </div>

            {/* Action Tabs - Stats */}
            <div className="bs-action-tabs" style={{ padding: '12px 0' }}>
              <div className="bs-tab" style={{flexDirection: 'column', alignItems: 'flex-start', gap: '4px', cursor: 'default'}}>
                <span style={{fontSize: '11px', color: 'var(--t-variant)', fontWeight: '600', textTransform: 'uppercase'}}>Active Agents</span>
                <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                  <span className="material-symbols-outlined" style={{fontSize: '18px', color: '#10b981'}}>smart_toy</span>
                  <span style={{color: '#10b981', fontSize: '16px', fontWeight: 'bold'}}>{simulationData.simulation_state.total_agents}</span>
                </div>
              </div>
              <div className="bs-tab" style={{flexDirection: 'column', alignItems: 'flex-start', gap: '4px', cursor: 'default'}}>
                <span style={{fontSize: '11px', color: 'var(--t-variant)', fontWeight: '600', textTransform: 'uppercase'}}>Current Step</span>
                <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                  <span className="material-symbols-outlined" style={{fontSize: '18px', color: '#3b82f6'}}>step</span>
                  <span style={{color: '#3b82f6', fontSize: '16px', fontWeight: 'bold'}}>{simulationData.simulation_state.step}</span>
                </div>
              </div>
              <div className="bs-tab" onClick={async () => {
                try {
                  await axios.post('/reset_simulation')
                  agentHeadings.current = {}
                  setSelectedAgent(null)
                  // Optionally re-fetch immediately so UI responds faster
                  const response = await axios.get('/simulation_data')
                  setSimulationData(response.data)
                } catch (err) {
                  console.error('Failed to reset:', err)
                }
              }} style={{flexDirection: 'column', alignItems: 'center', gap: '4px'}}>
                <span className="material-symbols-outlined" style={{color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', padding: '6px', borderRadius: '50%'}}>restart_alt</span>
                <span style={{fontSize: '11px', color: '#ef4444'}}>Reset</span>
              </div>
            </div>

            {/* Primary Action */}
            <button className="bs-primary-btn" onClick={async () => {
              try {
                await axios.post('/add_agent', {})
              } catch (err) {
                console.error('Failed to add agent:', err)
              }
            }}>
              Add New Agent
            </button>
          </div>
        )}
      </div>
      )}
    </>
  )
}

export default MapView
