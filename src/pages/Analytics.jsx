import React, { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import './Analytics.css'

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

  const isVisibleRef = useRef(!document.hidden)

  // ─── Stable polling callback ───
  const poll = useCallback(async () => {
    // Skip network request if tab is hidden
    if (!isVisibleRef.current) return

    try {
      const simulationResponse = await axios.get('/simulation_data')
      const simData = simulationResponse.data
      
      const t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      
      // Update simulation metrics
      if (simData) {
        setSimulationMetrics(simData)
        
        // Update simulation event logs if available
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
        
        // Create performance log entry
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
    } catch (_) { /* network error */ }
  }, [])

  // ─── Lifecycle: poll + visibility ───
  useEffect(() => {
    const handleVisibility = () => {
      isVisibleRef.current = !document.hidden
      if (!document.hidden) poll()
    }
    document.addEventListener('visibilitychange', handleVisibility)

    poll()
    const id = setInterval(poll, POLL_INTERVAL_MS)
    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [poll])

  return (
    <>
      {/* Header */}
      <div className="analytics-header">
        <div>
          <h2 className="analytics-title">D-LOGIC Analytics</h2>
          <p className="analytics-subtitle">System Performance & Algorithm Metrics</p>
        </div>
      </div>

      {/* D-LOGIC Performance Metrics */}
      {simulationMetrics ? (
        <>
          <div className="an-grid-full">
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

          {/* Performance Update Logs */}
          <div className="an-grid-full">
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
          <div className="an-grid-full">
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
