import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
} from 'recharts'
import './Dashboard.css'

const COLORS = ['#22c55e','#3b82f6','#f59e0b','#8b5cf6','#06b6d4',
                 '#f97316','#ec4899','#a3e635','#facc15','#34d399']

function Dashboard() {
  const navigate = useNavigate()
  const [simulationData, setSimulationData] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [agentDetails, setAgentDetails] = useState(null)
  const [simulationRunning, setSimulationRunning] = useState(true)
  const [perfHistory, setPerfHistory] = useState([])
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
          const data = response.data
          setSimulationData(data)
          hasData = true;

          // Build performance history for chart
          setPerfHistory(prev => {
            const entry = {
              step: data.simulation_state?.step ?? 0,
              performance: parseFloat(((data.simulation_state?.system_performance ?? 0) * 100).toFixed(1)),
              agents: data.simulation_state?.total_agents ?? 0,
              commEvents: data.simulation_state?.communication_events ?? 0,
            }
            const next = [...prev, entry]
            return next.length > 60 ? next.slice(-60) : next
          })

          timeoutId = setTimeout(fetchSimulationData, 1000)
        }
      } catch (error) {
        console.error('Error fetching simulation data:', error)
        if (isMounted) {
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
      case 'moving': return '#f59e0b' 
      case 'executing': return '#8b5cf6' 
      case 'idle': return '#3b82f6' 
      case 'failed': return '#ef4444' 
      default: return '#6b7280'
    }
  }

  const getSignalColor = (signal) => {
    switch(signal) {
      case 'green': return '#10b981' 
      case 'yellow': return '#f59e0b' 
      case 'red': return '#ef4444' 
      default: return '#6b7280'
    }
  }

  const statusDist = {}
  if (simulationData) {
    simulationData.agents.forEach(a => {
      statusDist[a.status] = (statusDist[a.status] || 0) + 1
    })
  }
  const statusChartData = Object.entries(statusDist).map(([status, count]) => ({
    status: status.charAt(0).toUpperCase() + status.slice(1), count,
  }))

  if (!simulationData) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Initializing D-LOGIC Simulation...</p>
      </div>
    )
  }

  return (
    <div style={{ zoom: 0.9, display: 'flex', flexDirection: 'column', flex: 1, height: '100%' }}>
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



      <div className="dash-main">
        <div className="dash-left">
          <div className="data-card cam-panel" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="cam-header">
              <div className="cam-header-left">
                <span className="material-symbols-outlined">terminal</span>
                <span className="cam-header-label">Command Line</span>
              </div>
              <span className="cam-badge">
                <span className="pulse-dot" />
                AWAITING COMMAND
              </span>
            </div>
            <div className="cam-feed" style={{ display: 'flex', flexDirection: 'column', backgroundColor: '#0a0a0a', padding: '15px', paddingTop: '60px', paddingBottom: '30px', flex: 1, borderTop: '1px solid #222' }}>
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


        </div>

      </div>
    </div>
  )
}

export default Dashboard
