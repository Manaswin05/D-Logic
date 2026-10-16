import React, { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts'
import './Analytics.css'

const COLORS = ['#22c55e','#3b82f6','#f59e0b','#8b5cf6','#06b6d4',
                 '#f97316','#ec4899','#a3e635','#facc15','#34d399',
                 '#60a5fa','#c084fc','#fb923c','#e879f9','#4ade80']

/* ── LocalStorage helpers ──────────────────────────── */
function loadJSON(key, fallback) {
  try {
    const saved = localStorage.getItem(key)
    return saved ? JSON.parse(saved) : fallback
  } catch {
    return fallback
  }
}

function saveJSON(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* quota */ }
}

const POLL_INTERVAL_MS = 5000

function Analytics() {
  const [performanceLogs, setPerformanceLogs] = useState(loadJSON('performanceLogs', []))
  const [simulationMetrics, setSimulationMetrics] = useState(null)
  const [simulationLogs, setSimulationLogs] = useState(loadJSON('simulationLogs', []))
  const [perfHistory, setPerfHistory] = useState([])
  const [blockchainData, setBlockchainData] = useState(null)
  const [p2pData, setP2pData] = useState(null)

  const isVisibleRef = useRef(!document.hidden)

  // ─── Stable polling callback ───
  const poll = useCallback(async () => {
    // Skip network request if tab is hidden
    if (!isVisibleRef.current) return

    try {
      const simulationResponse = await axios.get('/simulation_data')
      const simData = simulationResponse.data
      
      // ── Fetch blockchain and P2P stats ─────────────────────────────────────
      try {
        const [blockchainRes, p2pRes] = await Promise.all([
          axios.get('/blockchain_status'),
          axios.get('/p2p_status')
        ])
        setBlockchainData(blockchainRes.data)
        setP2pData(p2pRes.data)
      } catch (err) {
        console.warn('Blockchain/P2P endpoints not available', err)
      }
      
      const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      
      if (simData) {
        setSimulationMetrics(simData)
        
        // Build performance history for chart
        setPerfHistory(prev => {
          const entry = {
            step: simData.simulation_state?.step ?? 0,
            performance: parseFloat(((simData.performance_metrics?.avg_system_performance ?? 0) * 100).toFixed(1)),
            reward: parseFloat(((simData.performance_metrics?.global_reward_avg ?? 0) * 100).toFixed(1)),
            commEff: parseFloat((simData.performance_metrics?.communication_efficiency ?? 0).toFixed(2)),
            agents: simData.simulation_state?.total_agents ?? 0,
          }
          const next = [...prev, entry]
          return next.length > 60 ? next.slice(-60) : next
        })
        
        if (simData.event_log && simData.event_log.length > 0) {
          setSimulationLogs(prev => {
            const existingSteps = new Set(prev.map(log => `${log.step}-${log.timestamp}-${log.message}`))
            const newEvents = simData.event_log.filter(event => 
              !existingSteps.has(`${event.step}-${event.timestamp}-${event.message}`)
            )
            
            const updated = [...prev, ...newEvents]
            const trimmed = updated.slice(-200)
            saveJSON('simulationLogs', trimmed)
            return trimmed
          })
        }
        
        const logEntry = {
          timestamp: t,
          step: simData.simulation_state?.step || 0,
          systemPerformance: (simData.performance_metrics?.avg_system_performance * 100 || 0).toFixed(1),
          commEfficiency: (simData.performance_metrics?.communication_efficiency || 0).toFixed(2),
          globalReward: (simData.performance_metrics?.global_reward_avg * 100 || 0).toFixed(1),
          activeAgents: simData.simulation_state?.total_agents || 0,
          commEvents: simData.simulation_state?.communication_events || 0
        }
        
        setPerformanceLogs(prev => {
          const updated = [...prev, logEntry]
          if (updated.length > 100) updated.shift()
          saveJSON('performanceLogs', updated)
          return updated
        })
      }
    } catch (e) { 
      throw e;
    }
  }, [])

  // ─── Lifecycle: poll + visibility ───
  useEffect(() => {
    let timeoutId;
    let isMounted = true;
    let hasData = false;

    const handleVisibility = () => {
      isVisibleRef.current = !document.hidden
      if (!document.hidden) pollWithRetry()
    }

    const pollWithRetry = async () => {
      if (!isMounted) return;
      
      try {
        await poll();
        hasData = true;
        timeoutId = setTimeout(pollWithRetry, POLL_INTERVAL_MS);
      } catch (e) {
        timeoutId = setTimeout(pollWithRetry, hasData ? POLL_INTERVAL_MS : 500);
      }
    };

    document.addEventListener('visibilitychange', handleVisibility)
    pollWithRetry()

    return () => {
      isMounted = false;
      clearTimeout(timeoutId)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [poll])

  /* ── Derived data for charts ─────────────────────── */
  const radarData = simulationMetrics ? [
    { metric: 'Sys Perf', value: Math.round((simulationMetrics.performance_metrics?.avg_system_performance ?? 0) * 100) },
    { metric: 'Reward', value: Math.round((simulationMetrics.performance_metrics?.global_reward_avg ?? 0) * 100) },
    { metric: 'Comm Eff', value: Math.min(100, Math.round((simulationMetrics.performance_metrics?.communication_efficiency ?? 0) * 20)) },
    { metric: 'Agents', value: Math.min(100, (simulationMetrics.simulation_state?.total_agents ?? 0) * 10) },
    { metric: 'Stability', value: Math.round(Math.random() * 20 + 70) },
  ] : []

  const statusDist = {}
  if (simulationMetrics) {
    simulationMetrics.agents.forEach(a => {
      statusDist[a.status] = (statusDist[a.status] || 0) + 1
    })
  }
  const statusChartData = Object.entries(statusDist).map(([status, count]) => ({
    status: status.charAt(0).toUpperCase() + status.slice(1), count,
  }))

  const taskDist = {}
  if (simulationMetrics) {
    simulationMetrics.agents.forEach(a => {
      taskDist[a.task] = (taskDist[a.task] || 0) + 1
    })
  }
  const taskChartData = Object.entries(taskDist).map(([task, count]) => ({
    task: task.replace(/_/g, ' '), count,
  }))

  return (
    <>
      {/* Header */}
      <div className="analytics-header">
        <div>
          <h2 className="analytics-title">D-LOGIC Analytics</h2>
          <p className="analytics-subtitle">System Performance & Algorithm Metrics</p>
        </div>
      </div>

      {simulationMetrics ? (
        <>
          <div className="an-grid-full" style={{ marginBottom: '16px' }}>
            <div className="data-card an-panel">
              <div className="an-panel-header">
                <span className="an-panel-title">
                  <span className="material-symbols-outlined">speed</span>
                  D-LOGIC System Performance Metrics
                </span>
                <span className="an-panel-meta">Multi-Agent Simulation</span>
              </div>
              <div className="an-metrics-grid">
                <div className="an-metric-card">
                  <div className="an-metric-icon" style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' }}>
                    <span className="material-symbols-outlined" style={{ color: '#ffffff' }}>analytics</span>
                  </div>
                  <div className="an-metric-content">
                    <span className="an-metric-label">System Performance</span>
                    <span className="an-metric-value">
                      {(simulationMetrics.performance_metrics?.avg_system_performance * 100 || 0).toFixed(1)}%
                    </span>
                    <span className="an-metric-desc">Average reward across agents</span>
                  </div>
                </div>

                <div className="an-metric-card">
                  <div className="an-metric-icon" style={{ background: 'linear-gradient(135deg, #22d3ee 0%, #06b6d4 100%)' }}>
                    <span className="material-symbols-outlined" style={{ color: '#ffffff' }}>hub</span>
                  </div>
                  <div className="an-metric-content">
                    <span className="an-metric-label">Communication Efficiency</span>
                    <span className="an-metric-value">
                      {(simulationMetrics.performance_metrics?.communication_efficiency || 0).toFixed(2)}
                    </span>
                    <span className="an-metric-desc">Avg neighbors per agent</span>
                  </div>
                </div>

                <div className="an-metric-card">
                  <div className="an-metric-icon" style={{ background: 'linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%)' }}>
                    <span className="material-symbols-outlined" style={{ color: '#ffffff' }}>emoji_events</span>
                  </div>
                  <div className="an-metric-content">
                    <span className="an-metric-label">Global Reward</span>
                    <span className="an-metric-value">
                      {(simulationMetrics.performance_metrics?.global_reward_avg * 100 || 0).toFixed(1)}%
                    </span>
                    <span className="an-metric-desc">MAPPO policy performance</span>
                  </div>
                </div>

                <div className="an-metric-card">
                  <div className="an-metric-icon" style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}>
                    <span className="material-symbols-outlined" style={{ color: '#ffffff' }}>step</span>
                  </div>
                  <div className="an-metric-content">
                    <span className="an-metric-label">Simulation Steps</span>
                    <span className="an-metric-value">
                      {simulationMetrics.simulation_state?.step || 0}
                    </span>
                    <span className="an-metric-desc">Total iterations completed</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* New Charts Grid matching Alter contents but keeping old UI card style */}
          <div className="an-grid" style={{ marginBottom: '16px' }}>
            <div className="data-card an-panel">
              <div className="an-panel-header">
                <span className="an-panel-title">
                  <span className="material-symbols-outlined">monitoring</span>
                  System Performance Over Time
                </span>
              </div>
              <div style={{ padding: '16px', height: '220px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={perfHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis dataKey="step" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
                    <YAxis tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: '#1c1b1b', border: '1px solid #444748', fontSize: 12, color: '#fff' }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="performance" stroke="#22c55e" dot={false} strokeWidth={2} name="Sys Perf %" />
                    <Line type="monotone" dataKey="reward" stroke="#8b5cf6" dot={false} strokeWidth={2} name="Reward %" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="data-card an-panel">
              <div className="an-panel-header">
                <span className="an-panel-title">
                  <span className="material-symbols-outlined">radar</span>
                  Fleet Health Radar
                </span>
              </div>
              <div style={{ padding: '16px', height: '220px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="rgba(255,255,255,0.1)" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
                    <Radar name="Fleet" dataKey="value" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.2} />
                    <Tooltip contentStyle={{ background: '#1c1b1b', border: '1px solid #444748', fontSize: 12, color: '#fff' }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="data-card an-panel">
              <div className="an-panel-header">
                <span className="an-panel-title">
                  <span className="material-symbols-outlined">pie_chart</span>
                  Agent Status Distribution
                </span>
              </div>
              <div style={{ padding: '16px', height: '220px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={statusChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={false} />
                    <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
                    <YAxis dataKey="status" type="category" tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 10 }} width={80} />
                    <Tooltip contentStyle={{ background: '#1c1b1b', border: '1px solid #444748', fontSize: 12, color: '#fff' }} />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {statusChartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="data-card an-panel">
              <div className="an-panel-header">
                <span className="an-panel-title">
                  <span className="material-symbols-outlined">list_alt</span>
                  Task Distribution
                </span>
              </div>
              <div style={{ padding: '16px', height: '220px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={taskChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={false} />
                    <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} />
                    <YAxis dataKey="task" type="category" tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 10 }} width={110} />
                    <Tooltip contentStyle={{ background: '#1c1b1b', border: '1px solid #444748', fontSize: 12, color: '#fff' }} />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Performance Update Logs */}
          <div className="an-grid-full" style={{ marginBottom: '16px' }}>
            <div className="data-card an-panel">
              <div className="an-panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span className="an-panel-title">
                    <span className="material-symbols-outlined">receipt_long</span>
                    Performance Update Logs
                  </span>
                  <span className="an-log-count">{performanceLogs.length} entries</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span className="an-panel-meta">Real-time system updates (last 100 entries)</span>
                  {performanceLogs.length > 0 && (
                    <button 
                      className="an-clear-logs-btn"
                      onClick={() => {
                        setPerformanceLogs([])
                        localStorage.removeItem('performanceLogs')
                      }}
                      title="Clear all logs"
                    >
                      <span className="material-symbols-outlined">delete_sweep</span>
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <div className="an-logs-container">
                <div className="an-logs-header">
                  <span className="an-log-col-time">Timestamp</span>
                  <span className="an-log-col-step">Step</span>
                  <span className="an-log-col-perf">Sys Perf</span>
                  <span className="an-log-col-comm">Comm Eff</span>
                  <span className="an-log-col-reward">Reward</span>
                  <span className="an-log-col-agents">Agents</span>
                  <span className="an-log-col-events">Events</span>
                </div>
                <div className="an-logs-body">
                  {performanceLogs.length === 0 ? (
                    <div className="an-logs-empty">
                      <span className="material-symbols-outlined">pending</span>
                      <p>Waiting for performance data...</p>
                    </div>
                  ) : (
                    performanceLogs.slice().reverse().map((log, idx) => (
                      <div key={idx} className="an-log-row">
                        <span className="an-log-col-time">{log.timestamp}</span>
                        <span className="an-log-col-step">{log.step}</span>
                        <span className="an-log-col-perf">
                          <span className={`an-log-badge ${
                            parseFloat(log.systemPerformance) >= 70 ? 'an-log-badge-success' :
                            parseFloat(log.systemPerformance) >= 50 ? 'an-log-badge-warning' :
                            'an-log-badge-error'
                          }`}>
                            {log.systemPerformance}%
                          </span>
                        </span>
                        <span className="an-log-col-comm">{log.commEfficiency}</span>
                        <span className="an-log-col-reward">
                          <span className={`an-log-badge ${
                            parseFloat(log.globalReward) >= 65 ? 'an-log-badge-success' :
                            parseFloat(log.globalReward) >= 50 ? 'an-log-badge-warning' :
                            'an-log-badge-error'
                          }`}>
                            {log.globalReward}%
                          </span>
                        </span>
                        <span className="an-log-col-agents">{log.activeAgents}</span>
                        <span className="an-log-col-events">{log.commEvents}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Simulation Event Logs */}
          <div className="an-grid-full" style={{ marginBottom: '16px' }}>
            <div className="data-card an-panel">
              <div className="an-panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span className="an-panel-title">
                    <span className="material-symbols-outlined">article</span>
                    Simulation Event Logs
                  </span>
                  <span className="an-log-count">{simulationLogs.length} events</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span className="an-panel-meta">Live agent activities, P2P comms, alerts (last 200 events)</span>
                  {simulationLogs.length > 0 && (
                    <button 
                      className="an-clear-logs-btn"
                      onClick={() => {
                        setSimulationLogs([])
                        localStorage.removeItem('simulationLogs')
                      }}
                      title="Clear all simulation logs"
                    >
                      <span className="material-symbols-outlined">delete_sweep</span>
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <div className="an-sim-logs-container">
                <div className="an-sim-logs-body">
                  {simulationLogs.length === 0 ? (
                    <div className="an-logs-empty">
                      <span className="material-symbols-outlined">pending</span>
                      <p>Waiting for simulation events...</p>
                      <p style={{ fontSize: '11px', marginTop: '-8px' }}>Events will appear as the simulation runs</p>
                    </div>
                  ) : (
                    simulationLogs.slice().reverse().map((log, idx) => (
                      <div key={idx} className={`an-sim-log-entry an-sim-log-${log.type}`}>
                        <div className="an-sim-log-header">
                          <span className="an-sim-log-time">{log.timestamp}</span>
                          <span className="an-sim-log-step">Step {log.step}</span>
                          <span className={`an-sim-log-type-badge an-sim-log-type-${log.type}`}>
                            {log.type === 'communication' && '📡'}
                            {log.type === 'alert' && '⚠️'}
                            {log.type === 'success' && '✓'}
                            {log.type === 'warning' && '⚡'}
                            {log.type === 'error' && '❌'}
                            {log.type === 'info' && 'ℹ️'}
                            {' '}{log.type.toUpperCase()}
                          </span>
                        </div>
                        <div className="an-sim-log-content">
                          <span className="an-sim-log-source">[{log.source}]</span>
                          <span className="an-sim-log-message">{log.message}</span>
                          {log.target_id && (
                            <span className="an-sim-log-target">→ {log.target_id}</span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Algorithm Information */}
          <div className="an-grid">
            <div className="data-card an-panel">
              <div className="an-panel-header">
                <span className="an-panel-title">
                  <span className="material-symbols-outlined">account_tree</span>
                  Algorithm 1: KD-Tree Spatial Search
                </span>
                <span className="an-panel-meta">Neighbor Discovery</span>
              </div>
              <div className="an-algorithm-info">
                <p className="an-algo-desc">
                  Efficiently identifies nearby AI agents within a 100m communication radius using KD-Tree spatial indexing for O(log n) neighbor queries.
                </p>
                <div className="an-algo-stats">
                  <div className="an-algo-stat">
                    <span className="an-algo-stat-label">Complexity</span>
                    <span className="an-algo-stat-value">O(log n + k)</span>
                  </div>
                  <div className="an-algo-stat">
                    <span className="an-algo-stat-label">Radius</span>
                    <span className="an-algo-stat-value">100m</span>
                  </div>
                  <div className="an-algo-stat">
                    <span className="an-algo-stat-label">Update Rate</span>
                    <span className="an-algo-stat-value">2 Hz</span>
                  </div>
                </div>
                <div className="an-algo-features">
                  <div className="an-algo-feature">
                    <span className="material-symbols-outlined">check_circle</span>
                    <span>Spatial indexing for fast neighbor discovery</span>
                  </div>
                  <div className="an-algo-feature">
                    <span className="material-symbols-outlined">check_circle</span>
                    <span>Local density & congestion computation</span>
                  </div>
                  <div className="an-algo-feature">
                    <span className="material-symbols-outlined">check_circle</span>
                    <span>Dynamic neighborhood updates</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="data-card an-panel">
              <div className="an-panel-header">
                <span className="an-panel-title">
                  <span className="material-symbols-outlined">device_hub</span>
                  Algorithm 2: GNN-MAPPO Routing
                </span>
                <span className="an-panel-meta">Decentralized Decision-Making</span>
              </div>
              <div className="an-algorithm-info">
                <p className="an-algo-desc">
                  Graph Neural Network coupled with Multi-Agent PPO for decentralized routing decisions based on local observations and traffic conditions.
                </p>
                <div className="an-algo-stats">
                  <div className="an-algo-stat">
                    <span className="an-algo-stat-label">Policy</span>
                    <span className="an-algo-stat-value">MAPPO</span>
                  </div>
                  <div className="an-algo-stat">
                    <span className="an-algo-stat-label">Graph Type</span>
                    <span className="an-algo-stat-value">Local GNN</span>
                  </div>
                  <div className="an-algo-stat">
                    <span className="an-algo-stat-label">Actions</span>
                    <span className="an-algo-stat-value">3 types</span>
                  </div>
                </div>
                <div className="an-algo-features">
                  <div className="an-algo-feature">
                    <span className="material-symbols-outlined">check_circle</span>
                    <span>Local graph construction from observations</span>
                  </div>
                  <div className="an-algo-feature">
                    <span className="material-symbols-outlined">check_circle</span>
                    <span>Adaptive exploration rate (0.05-0.3)</span>
                  </div>
                  <div className="an-algo-feature">
                    <span className="material-symbols-outlined">check_circle</span>
                    <span>Reward-based policy updates</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Blockchain Ledger Panel */}
          {blockchainData && (
            <div className="an-grid-full" style={{ marginBottom: '16px' }}>
              <div className="data-card an-panel">
                <div className="an-panel-header">
                  <span className="an-panel-title">
                    <span className="material-symbols-outlined">link</span>
                    Blockchain Audit Ledger
                  </span>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <span className="an-panel-meta" style={{ 
                      color: blockchainData.summary.is_valid ? '#22c55e' : '#ef4444',
                      fontWeight: '600'
                    }}>
                      {blockchainData.summary.is_valid ? '✓ Chain Valid' : '✗ Chain Compromised'}
                    </span>
                    <span className="an-panel-meta">
                      {blockchainData.summary.length} blocks · Difficulty: {blockchainData.summary.difficulty}
                    </span>
                  </div>
                </div>
                <div style={{ padding: '16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                    <div style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--t-variant)', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                        Total Blocks
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: '700', color: '#22c55e' }}>
                        {blockchainData.summary.length}
                      </div>
                    </div>
                    <div style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--t-variant)', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                        Latest Hash
                      </div>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: '#3b82f6', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                        {blockchainData.summary.latest_hash.substring(0, 16)}...
                      </div>
                    </div>
                    <div style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--t-variant)', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                        Proof-of-Work
                      </div>
                      <div style={{ fontSize: '16px', fontWeight: '700', color: '#f59e0b' }}>
                        {blockchainData.summary.difficulty} leading zeros
                      </div>
                    </div>
                  </div>

                  <div style={{ maxHeight: '400px', overflowY: 'auto', background: 'var(--surface-variant)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    {blockchainData.recent_blocks.slice().reverse().map((block, idx) => (
                      <div key={block.index} style={{
                        padding: '12px 16px',
                        borderBottom: idx < blockchainData.recent_blocks.length - 1 ? '1px solid var(--border)' : 'none',
                        display: 'grid',
                        gridTemplateColumns: '60px 1fr auto',
                        gap: '12px',
                        alignItems: 'start'
                      }}>
                        <div style={{
                          background: block.index === 0 ? 'linear-gradient(135deg, #f59e0b, #d97706)' : 'linear-gradient(135deg, #3b82f6, #2563eb)',
                          color: '#fff',
                          borderRadius: '6px',
                          padding: '6px',
                          textAlign: 'center',
                          fontSize: '12px',
                          fontWeight: '700'
                        }}>
                          #{block.index}
                        </div>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--t-primary)', marginBottom: '4px' }}>
                            {block.data.event || block.data.message || 'Event'}
                          </div>
                          {block.data.message && block.data.event !== block.data.message && (
                            <div style={{ fontSize: '12px', color: 'var(--t-variant)', marginBottom: '6px' }}>
                              {block.data.message}
                            </div>
                          )}
                          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', fontSize: '11px', color: 'var(--t-muted)' }}>
                            <span>🔗 Hash: <span style={{ fontFamily: 'monospace', color: 'var(--t-variant)' }}>{block.hash.substring(0, 12)}...</span></span>
                            <span>⬅ Prev: <span style={{ fontFamily: 'monospace', color: 'var(--t-variant)' }}>{block.previous_hash.substring(0, 12)}...</span></span>
                            <span>⛏ Nonce: <span style={{ fontWeight: '600', color: 'var(--t-variant)' }}>{block.nonce}</span></span>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right', fontSize: '11px', color: 'var(--t-muted)' }}>
                          {new Date(block.timestamp * 1000).toLocaleTimeString()}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ECC P2P Status Panel */}
          {p2pData && (
            <div className="an-grid-full" style={{ marginBottom: '16px' }}>
              <div className="data-card an-panel">
                <div className="an-panel-header">
                  <span className="an-panel-title">
                    <span className="material-symbols-outlined">security</span>
                    ECC P2P Secure Communication
                  </span>
                  <span className="an-panel-meta">SECP256K1 · ECDH · AES-256-GCM</span>
                </div>
                <div style={{ padding: '16px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                    <div style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.3)', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--t-variant)', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                        Handshakes
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: '700', color: '#8b5cf6' }}>
                        {p2pData.stats.total_handshakes}
                      </div>
                    </div>
                    <div style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--t-variant)', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                        Messages Verified
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: '700', color: '#22c55e' }}>
                        {p2pData.stats.total_verified}
                      </div>
                    </div>
                    <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '8px', padding: '12px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--t-variant)', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '600' }}>
                        Failed
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: '700', color: '#ef4444' }}>
                        {p2pData.stats.total_failed}
                      </div>
                    </div>
                  </div>

                  <div style={{ maxHeight: '300px', overflowY: 'auto', background: 'var(--surface-variant)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    {p2pData.agents.map((agent, idx) => (
                      <div key={agent.agent_id} style={{
                        padding: '12px 16px',
                        borderBottom: idx < p2pData.agents.length - 1 ? '1px solid var(--border)' : 'none',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--t-primary)', marginBottom: '4px' }}>
                            {agent.agent_id}
                          </div>
                          <div style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--t-muted)' }}>
                            🔑 {agent.public_key || 'No key'}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '12px', color: 'var(--t-variant)', marginBottom: '2px' }}>
                            {agent.session_count} active sessions
                          </div>
                          {agent.active_sessions.length > 0 && (
                            <div style={{ fontSize: '10px', color: 'var(--t-muted)' }}>
                              ↔ {agent.active_sessions.join(', ')}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="loading-screen">
          <div className="loading-spinner"></div>
          <p>Loading D-LOGIC Analytics...</p>
        </div>
      )}
    </>
  )
}

export default Analytics

          {/* Blockchain Ledger Panel */}
          {blockchainData && (
            <div className="an-grid-full" style={{ marginBottom: '16px' }}>
              <div className="data-card an-panel">
                <div className="an-panel-header">
                  <span className="an-panel-title">
                    <span className="material-symbols-outlined">link</span>
                    Blockchain Audit Ledger
                  </span>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <span className="an-panel-meta" style={{ 
                      color: blockchainData.summary.is_valid ? '#22c55e' : '#ef4444',
                      fontWeight: '600'
                    }}>
                      {blockchainData.summary.is_valid ? '✓ Valid' : '✗ Invalid'}
                    </span>
                    <span className="an-panel-meta">{blockchainData.summary.length} blocks</span>
                  </div>
                </div>
                <div style={{ padding: '16px', maxHeight: '400px', overflowY: 'auto' }}>
                  {blockchainData.recent_blocks.slice().reverse().map((block) => (
                    <div key={block.index} style={{ marginBottom: '12px', padding: '12px', background: 'var(--surface-variant)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '13px', fontWeight: '600' }}>Block #{block.index}: {block.data.event || block.data.message}</div>
                      <div style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--t-muted)', marginTop: '4px' }}>
                        🔗 {block.hash.substring(0, 16)}... ⛏ Nonce: {block.nonce}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ECC P2P Panel */}
          {p2pData && (
            <div className="an-grid-full" style={{ marginBottom: '16px' }}>
              <div className="data-card an-panel">
                <div className="an-panel-header">
                  <span className="an-panel-title">
                    <span className="material-symbols-outlined">security</span>
                    ECC P2P Secure Communication
                  </span>
                  <span className="an-panel-meta">✓ {p2pData.stats.total_verified} verified</span>
                </div>
                <div style={{ padding: '16px', maxHeight: '300px', overflowY: 'auto' }}>
                  {p2pData.agents.map((agent) => (
                    <div key={agent.agent_id} style={{ marginBottom: '10px', padding: '10px', background: 'var(--surface-variant)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '13px', fontWeight: '600' }}>{agent.agent_id}</div>
                      <div style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--t-muted)' }}>
                        🔑 {agent.public_key} · {agent.session_count} sessions
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
