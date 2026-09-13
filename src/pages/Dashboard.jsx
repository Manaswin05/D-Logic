import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import './Dashboard.css'

function Dashboard() {
  const navigate = useNavigate()
  const [simulationData, setSimulationData] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [agentDetails, setAgentDetails] = useState(null)
  const [simulationRunning, setSimulationRunning] = useState(true)
  const [logs, setLogs] = useState([
    { time: new Date().toLocaleTimeString(), msg: 'D-LOGIC system initialized', type: 'primary' }
  ])

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
          timeoutId = setTimeout(fetchSimulationData, 1000)
        }
      } catch (error) {
        console.error('Error fetching simulation data:', error)
        if (isMounted) {
          // Retry quickly if we are still waiting for initial load
          timeoutId = setTimeout(fetchSimulationData, hasData ? 1000 : 250)
        }
      }
    }

    fetchSimulationData()
    return () => {
      isMounted = false;
      clearTimeout(timeoutId)
    }
  }, [])

  useEffect(() => {
    if (selectedAgent) {
      const fetchAgentDetails = async () => {
        try {
          const response = await axios.get(`/agent_details/${selectedAgent}`)
          setAgentDetails(response.data)
        } catch (error) {
          console.error('Error fetching agent details:', error)
        }
      }
      fetchAgentDetails()
      const interval = setInterval(fetchAgentDetails, 3000)
      return () => clearInterval(interval)
    }
  }, [selectedAgent])

  const toggleSimulation = async () => {
    try {
      const response = await axios.post('/simulation_control', { action: 'toggle' })
      setSimulationRunning(response.data.running)
      
      const t = new Date().toLocaleTimeString()
      setLogs(prev => [
        { time: t, msg: response.data.message, type: 'primary' },
        ...prev.slice(0, 29)
      ])
    } catch (error) {
      console.error('Error toggling simulation:', error)
    }
  }

  const handleAgentClick = (agentId) => {
    setSelectedAgent(agentId === selectedAgent ? null : agentId)
    
    const t = new Date().toLocaleTimeString()
    setLogs(prev => [
      { time: t, msg: `Selected agent: ${agentId}`, type: 'info' },
      ...prev.slice(0, 29)
    ])
  }

  const [terminalHistory, setTerminalHistory] = useState([
    { type: 'cmd', text: '$ system_ctl start d-logic-core' },
    { type: 'info', text: '[OK] Multi-Agent System Initialized.' },
    { type: 'info', text: '[OK] KD-Tree Spatial Search Active.' },
    { type: 'info', text: '[OK] GNN-MAPPO Neural Network Online.' },
    { type: 'dim', text: '-- Awaiting new pre-dispatch commands --' }
  ])
  const [cmdInput, setCmdInput] = useState('')
  const terminalRef = useRef(null)

  // Scroll terminal to bottom when history changes
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [terminalHistory])

  const handleCommandSubmit = async () => {
    if (!cmdInput.trim()) return
    const cmd = cmdInput.trim()
    const lowerCmd = cmd.toLowerCase()
    
    setTerminalHistory(prev => [...prev, { type: 'cmd', text: `$ ${cmd}` }])
    setCmdInput('')

    if (lowerCmd.includes('add') && (lowerCmd.includes('agent') || lowerCmd.includes('attribute') || lowerCmd.includes('attibute'))) {
      setTerminalHistory(prev => [...prev, { type: 'info', text: '> Initiating new agent deployment...' }])
      try {
        const response = await axios.post('/add_agent', {})
        if (response.data.status === 'success') {
          setTerminalHistory(prev => [...prev, { type: 'success', text: `[SUCCESS] Deployed ${response.data.agent.id} into the mesh network.` }])
        }
      } catch (err) {
        setTerminalHistory(prev => [...prev, { type: 'error', text: '[ERROR] Communication failure with deployment server.' }])
      }
    } else if (lowerCmd.startsWith('remove agent')) {
      const parts = cmd.split(' ');
      let agentId = parts.length > 2 ? parts[2] : null;
      
      if (!agentId && simulationData && simulationData.agents.length > 0) {
        agentId = simulationData.agents[simulationData.agents.length - 1].id;
      }
      
      if (agentId) {
        setTerminalHistory(prev => [...prev, { type: 'info', text: `> Initiating removal of ${agentId}...` }])
        try {
          const response = await axios.delete(`/remove_agent/${agentId}`)
          if (response.data.status === 'success') {
            setTerminalHistory(prev => [...prev, { type: 'success', text: `[SUCCESS] ${agentId} removed.` }])
          }
        } catch (err) {
          setTerminalHistory(prev => [...prev, { type: 'error', text: `[ERROR] Failed to remove ${agentId}. Check if it exists.` }])
        }
      } else {
        setTerminalHistory(prev => [...prev, { type: 'error', text: '[ERROR] No agents available to remove.' }])
      }
    } else if (lowerCmd === 'clear') {
      setTerminalHistory([])
    } else {
      setTerminalHistory(prev => [...prev, { type: 'error', text: `Command not recognized: ${cmd}. Try "add agent" or "remove agent [ID]".` }])
    }
  }

  const getStatusColor = (status) => {
    switch(status) {
      case 'moving': return '#f59e0b' // amber
      case 'executing': return '#8b5cf6' // purple
      case 'idle': return '#3b82f6' // blue
      case 'failed': return '#ef4444' // red
      default: return '#6b7280'
    }
  }

  const getSignalColor = (signal) => {
    switch(signal) {
      case 'green': return '#10b981' // emerald
      case 'yellow': return '#f59e0b' // amber
      case 'red': return '#ef4444' // red
      default: return '#6b7280'
    }
  }

  if (!simulationData) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Initializing D-LOGIC Simulation...</p>
      </div>
    )
  }

  return (
    <>
      {/* Header */}
      <div className="dash-header">
        <div>
          <h2 className="dash-title">D-LOGIC Multi-Agent System</h2>
          <p className="dash-subtitle">Decentralized Pre-Dispatch Coordination for Autonomous Mobility Fleets</p>
        </div>
        <div style={{display: 'flex', gap: '12px', alignItems: 'center'}}>
          <button className="sim-control-btn" style={{background: '#10b981', color: '#fff'}} onClick={() => navigate('/map')}>
            <span className="material-symbols-outlined">map</span>
            Open Maps
          </button>
          <button className="sim-control-btn" onClick={toggleSimulation}>
            <span className="material-symbols-outlined">
              {simulationRunning ? 'pause' : 'play_arrow'}
            </span>
            {simulationRunning ? 'Pause' : 'Start'} Simulation
          </button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="kpi-grid">
        <div className="data-card kpi-card">
          <span className="kpi-label">Active Agents</span>
          <span className="kpi-value">{simulationData.simulation_state.total_agents}</span>
          <span className="kpi-meta">Autonomous vehicles</span>
        </div>

        <div className="data-card kpi-card">
          <span className="kpi-label">Simulation Step</span>
          <span className="kpi-value">{simulationData.simulation_state.step}</span>
          <span className="kpi-meta">Current iteration</span>
        </div>

        <div className="data-card kpi-card">
          <span className="kpi-label">System Performance</span>
          <span className="kpi-value">{(simulationData.simulation_state.system_performance * 100).toFixed(1)}%</span>
          <span className="kpi-meta">Average reward score</span>
        </div>

        <div className="data-card kpi-card">
          <span className="kpi-label">Communication Events</span>
          <span className="kpi-value">{simulationData.simulation_state.communication_events}</span>
          <span className="kpi-meta">Agent-to-agent messages</span>
        </div>
      </div>

      {/* Main grid */}
      <div className="dash-main">

        {/* Left column — Video Feed */}
        <div className="dash-left">
          <div className="data-card cam-panel" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="cam-header">
              <div className="cam-header-left">
                <span className="material-symbols-outlined">terminal</span>
                <span className="cam-header-label">Activity Status</span>
              </div>
              <span className="cam-badge">
                <span className="pulse-dot" />
                AWAITING COMMAND
              </span>
            </div>
            <div className="cam-feed" style={{ display: 'flex', flexDirection: 'column', backgroundColor: '#0a0a0a', padding: '15px', height: '100%', borderTop: '1px solid #222' }}>
              <div ref={terminalRef} style={{ flex: 1, overflowY: 'auto', fontFamily: 'JetBrains Mono', fontSize: '13px', textAlign: 'left', lineHeight: '1.6' }}>
                {terminalHistory.map((line, idx) => (
                  <div key={idx} style={{ 
                    color: line.type === 'cmd' ? '#22c55e' : 
                           line.type === 'dim' ? '#8e9192' : 
                           line.type === 'error' ? '#ef4444' : 
                           line.type === 'success' ? '#3b82f6' : '#a78bfa',
                    marginTop: line.type === 'cmd' && idx > 0 ? '10px' : '0'
                  }}>
                    {line.text}
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', marginTop: '10px', borderTop: '1px solid #333', paddingTop: '15px', alignItems: 'center' }}>
                <span style={{ color: '#22c55e', marginRight: '10px', fontFamily: 'JetBrains Mono', fontWeight: 'bold' }}>$</span>
                <input 
                  type="text" 
                  value={cmdInput}
                  onChange={(e) => setCmdInput(e.target.value)}
                  placeholder='Type "add agent" or "add another attribute"...' 
                  style={{ flex: 1, backgroundColor: 'transparent', border: 'none', color: '#fff', outline: 'none', fontFamily: 'JetBrains Mono', fontSize: '13px' }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleCommandSubmit()
                  }}
                />
                <button 
                  onClick={handleCommandSubmit}
                  style={{ backgroundColor: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontFamily: 'JetBrains Mono', fontSize: '12px' }}>
                  Execute
                </button>
              </div>
            </div>
          </div>

          {/* Agent Cards */}
          <div className="agent-grid">
            {simulationData.agents.map((agent) => (
              <div 
                key={agent.id} 
                className={`agent-card ${selectedAgent === agent.id ? 'selected' : ''}`}
                onClick={() => handleAgentClick(agent.id)}
              >
                <div className="agent-card-header">
                  <span className="agent-id">{agent.id}</span>
                  <span 
                    className="agent-status-dot" 
                    style={{ backgroundColor: getStatusColor(agent.status) }}
                  />
                </div>
                <div className="agent-card-body">
                  <div className="agent-stat">
                    <span className="agent-stat-label">Task</span>
                    <span className="agent-stat-value">{agent.task}</span>
                  </div>
                  <div className="agent-stat">
                    <span className="agent-stat-label">Status</span>
                    <span className="agent-stat-value">{agent.status}</span>
                  </div>
                  <div className="agent-stat">
                    <span className="agent-stat-label">Speed</span>
                    <span className="agent-stat-value">{agent.speed.toFixed(1)} km/h</span>
                  </div>
                  <div className="agent-stat">
                    <span className="agent-stat-label">Battery</span>
                    <span className="agent-stat-value">{agent.battery.toFixed(0)}%</span>
                  </div>
                  <div className="agent-stat">
                    <span className="agent-stat-label">Neighbors</span>
                    <span className="agent-stat-value">{agent.neighbors.length}</span>
                  </div>
                  <div className="agent-stat">
                    <span className="agent-stat-label">Position</span>
                    <span className="agent-stat-value">
                      ({agent.position[0].toFixed(0)}, {agent.position[1].toFixed(0)})
                    </span>
                  </div>
                </div>
                {agent.neighbors.length > 0 && (
                  <div className="agent-neighbors">
                    <span className="agent-neighbors-label">Connected to:</span>
                    <span className="agent-neighbors-list">
                      {agent.neighbors.join(', ')}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right column */}
        <div className="dash-right">
          
          {/* Selected Agent Details */}
          {selectedAgent && agentDetails && (
            <div className="data-card agent-details-panel">
              <div className="panel-header">
                <span className="panel-header-text">Agent Details: {selectedAgent}</span>
                <button 
                  className="close-btn" 
                  onClick={() => setSelectedAgent(null)}
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>
              
              <div className="agent-details-content">
                <div className="detail-section">
                  <h4>Agent State</h4>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="detail-label">ID</span>
                      <span className="detail-value">{agentDetails.agent.id}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Status</span>
                      <span className="detail-value" style={{ color: getStatusColor(agentDetails.agent.status) }}>
                        {agentDetails.agent.status}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Task</span>
                      <span className="detail-value">{agentDetails.agent.task}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Speed</span>
                      <span className="detail-value">{agentDetails.agent.speed.toFixed(2)} km/h</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Battery</span>
                      <span className="detail-value">{agentDetails.agent.battery.toFixed(1)}%</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Position</span>
                      <span className="detail-value">
                        ({agentDetails.agent.position[0].toFixed(1)}, {agentDetails.agent.position[1].toFixed(1)})
                      </span>
                    </div>
                  </div>
                </div>

                <div className="detail-section">
                  <h4>Neighborhood Info (KD-Tree)</h4>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="detail-label">Neighbor Count</span>
                      <span className="detail-value">{agentDetails.neighborhood_info.neighbor_count}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Local Density</span>
                      <span className="detail-value">{(agentDetails.neighborhood_info.local_density * 1000).toFixed(3)}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Avg Speed</span>
                      <span className="detail-value">{agentDetails.neighborhood_info.avg_speed.toFixed(2)} km/h</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Congestion</span>
                      <span className="detail-value">{(agentDetails.neighborhood_info.congestion_metric * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>

                <div className="detail-section">
                  <h4>Local Graph (GNN)</h4>
                  <div className="graph-info">
                    <div className="graph-stat">
                      <span className="graph-stat-label">Nodes</span>
                      <span className="graph-stat-value">{agentDetails.local_graph.nodes.length}</span>
                    </div>
                    <div className="graph-stat">
                      <span className="graph-stat-label">Edges</span>
                      <span className="graph-stat-value">{agentDetails.local_graph.edges.length}</span>
                    </div>
                  </div>
                  
                  {agentDetails.local_graph.nodes.length > 0 && (
                    <div className="graph-nodes-list">
                      {agentDetails.local_graph.nodes.slice(0, 5).map((node, idx) => (
                        <div key={idx} className="graph-node-item">
                          <span className="node-type">{node.type}</span>
                          <span className="node-id">{node.id}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {agentDetails.policy && (
                  <div className="detail-section">
                    <h4>MAPPO Policy</h4>
                    <div className="detail-grid">
                      <div className="detail-item">
                        <span className="detail-label">Exploration Rate</span>
                        <span className="detail-value">
                          {(agentDetails.policy.exploration_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Avg Reward</span>
                        <span className="detail-value">
                          {(agentDetails.policy.average_reward * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Traffic Intersections */}
          <div className="data-card intersections-panel">
            <div className="panel-header">
              <span className="panel-header-text">Traffic Intersections</span>
              <span className="panel-count">{simulationData.intersections.length} nodes</span>
            </div>
            
            <div className="intersections-grid">
              {simulationData.intersections.map((intersection) => (
                <div key={intersection.intersection_id} className="intersection-card">
                  <div className="intersection-header">
                    <span className="intersection-id">{intersection.intersection_id}</span>
                    <span 
                      className="signal-light" 
                      style={{ backgroundColor: getSignalColor(intersection.signal) }}
                    />
                  </div>
                  <div className="intersection-stats">
                    <div className="intersection-stat">
                      <span className="stat-label">Vehicles</span>
                      <span className="stat-value">{intersection.vehicle_count}</span>
                    </div>
                    <div className="intersection-stat">
                      <span className="stat-label">Congestion</span>
                      <span className={`stat-value congestion-${intersection.congestion_level.toLowerCase()}`}>
                        {intersection.congestion_level}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* System Logs */}
          <div className="data-card logs-panel">
            <div className="panel-header">
              <span className="panel-header-text">System Logs</span>
              <span className="panel-count">Last {logs.length} entries</span>
            </div>
            <div className="logs-list">
              {logs.map((entry, i) => (
                <div key={i} className={`log-entry${i > 0 ? ' dim' : ''}`}>
                  <span className="log-time">{entry.time}</span>
                  <span className={`log-msg${entry.type === 'error' ? ' error' : entry.type === 'primary' ? ' primary' : ''}`}>
                    {entry.msg}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default Dashboard
