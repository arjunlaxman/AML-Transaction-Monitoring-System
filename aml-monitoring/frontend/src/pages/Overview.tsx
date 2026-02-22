import { useCallback, useEffect, useRef, useState } from 'react'
import { api, Alert, Stats } from '../api/client'
import AlertsTable from '../components/AlertsTable'

// ── Animated counter ────────────────────────────────────────────────────────
function useCountUp(target: number, duration = 800) {
  const [value, setValue] = useState(0)
  const raf = useRef<number>(0)
  useEffect(() => {
    if (!target) { setValue(0); return }
    const start = performance.now()
    const step = (now: number) => {
      const p = Math.min((now - start) / duration, 1)
      const ease = 1 - Math.pow(1 - p, 3)
      setValue(Math.round(ease * target))
      if (p < 1) raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf.current)
  }, [target, duration])
  return value
}

// ── Stat card ───────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string
  value: number
  fmt?: (n: number) => string
  sub?: string
  color?: string
  delay?: number
  icon?: string
}

function StatCard({ label, value, fmt, sub, color = 'var(--accent)', delay = 0, icon }: StatCardProps) {
  const animated = useCountUp(value)
  const display = fmt ? fmt(animated) : animated.toLocaleString()

  return (
    <div
      className="card card-glow page-enter"
      style={{ padding: '20px 24px', animationDelay: `${delay}ms` }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-dim)', fontFamily: 'Syne, sans-serif' }}>
          {label}
        </span>
        {icon && <span style={{ fontSize: 16, opacity: 0.4 }}>{icon}</span>}
      </div>
      <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: '28px', color, letterSpacing: '-0.03em', lineHeight: 1 }}>
        {display}
      </div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

// ── Log line ────────────────────────────────────────────────────────────────
function LogLine({ line, idx }: { line: string; idx: number }) {
  const isErr = line.startsWith('✗')
  const isOk  = line.startsWith('✓') || line.startsWith('✅')
  const isRun = line.startsWith('⏳')
  return (
    <div
      className="page-enter"
      style={{
        animationDelay: `${idx * 80}ms`,
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 12,
        color: isErr ? 'var(--danger)' : isOk ? 'var(--ok)' : isRun ? 'var(--accent)' : 'var(--text-muted)',
        display: 'flex',
        gap: 8,
        padding: '3px 0',
      }}
    >
      <span style={{ color: 'var(--text-dim)', flexShrink: 0 }}>
        {String(idx + 1).padStart(2, '0')}
      </span>
      {line}
    </div>
  )
}

// ── Main page ───────────────────────────────────────────────────────────────
type RunStatus = 'idle' | 'generating' | 'training' | 'done' | 'error'

export default function Overview() {
  const [stats, setStats]  = useState<Stats | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [status, setStatus] = useState<RunStatus>('idle')
  const [log, setLog]       = useState<string[]>([])
  const logRef = useRef<HTMLDivElement>(null)

  const addLog = (line: string) => setLog(p => [...p, line])

  const fetchData = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([api.getStats(), api.getAlerts(30)])
      setStats(s)
      setAlerts(a.items)
    } catch { /* silently ignore on initial load */ }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  const runDemo = async () => {
    setLog([])
    setStatus('generating')
    addLog('⏳ Starting demo pipeline …')
    addLog('⏳ Generating synthetic transaction network (1,000 entities, ~5,000 transactions) …')
    try {
      const gen = await api.runGenerate('demo')
      addLog(`✓ ${gen.message}`)
      setStatus('training')
      addLog('⏳ Training GraphSAGE GNN (60 epochs, weighted cross-entropy for class imbalance) …')
      addLog('⏳ Computing SHAP attributions via XGBoost surrogate …')
      const train = await api.runTrain('demo')
      addLog(`✓ ${train.message}`)
      addLog(`✅ Demo complete — dashboard updated below`)
      setStatus('done')
      await fetchData()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } }; message?: string })
        ?.response?.data?.detail ?? (err as Error)?.message ?? 'Unknown error'
      addLog(`✗ Error: ${msg}`)
      setStatus('error')
    }
  }

  const isRunning = status === 'generating' || status === 'training'

  return (
    <div className="page-enter space-y-8">

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 32, color: 'white', letterSpacing: '-0.03em', marginBottom: 6 }}>
            Transaction Intelligence
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, maxWidth: 480 }}>
            Graph Neural Network–powered AML detection with explainable alerts.
            {stats?.has_model && (
              <span style={{ color: 'var(--ok)', marginLeft: 8 }}>
                ✓ Model active
              </span>
            )}
          </p>
        </div>

        <button
          className="btn-primary"
          onClick={runDemo}
          disabled={isRunning}
        >
          {isRunning ? (
            <>
              <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>◈</span>
              Running…
            </>
          ) : (
            <>
              <span>▶</span>
              Run Demo
            </>
          )}
        </button>
      </div>

      {/* ── Terminal log ── */}
      {log.length > 0 && (
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: '16px 20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 6 }}>
              {['#f43f5e','#f59e0b','#10b981'].map(c => (
                <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c, opacity: 0.7 }} />
              ))}
            </div>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--text-dim)' }}>
              pipeline.log
            </span>
          </div>
          <div ref={logRef} style={{ maxHeight: 160, overflowY: 'auto' }}>
            {log.map((line, i) => <LogLine key={i} line={line} idx={i} />)}
          </div>
        </div>
      )}

      {/* ── Stats grid ── */}
      {stats && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
            <StatCard label="Entities"     value={stats.total_entities}    icon="◈" delay={0} />
            <StatCard label="Transactions" value={stats.total_transactions} icon="⬡" delay={50} />
            <StatCard label="Open Alerts"  value={stats.open_alerts}
              color={stats.open_alerts > 0 ? 'var(--danger)' : 'var(--ok)'}
              sub={stats.open_alerts > 0 ? 'requires investigation' : 'nothing flagged'}
              icon="⚠" delay={100} />
            <StatCard label="Clusters"     value={stats.total_clusters}
              sub="suspicious groups" icon="⬢" delay={150} />
          </div>

          {stats.has_model && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              <StatCard
                label="GNN Precision"
                value={stats.gnn_precision}
                fmt={n => `${(n).toFixed(1)}%`}
                sub="true positives / alerts filed"
                color="var(--accent)" delay={200} icon="◎"
              />
              <StatCard
                label="GNN Recall"
                value={stats.gnn_recall}
                fmt={n => `${(n).toFixed(1)}%`}
                sub="suspicious entities caught"
                color="#818cf8" delay={250} icon="◎"
              />
              <StatCard
                label="GNN F1 Score"
                value={stats.gnn_f1}
                fmt={n => (n / 100).toFixed(3)}
                sub="harmonic precision-recall mean"
                color="var(--ok)" delay={300} icon="◎"
              />
            </div>
          )}
        </>
      )}

      {/* ── Alerts table ── */}
      <div className="card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h2 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 18, color: 'white', marginBottom: 2 }}>
              Recent Alerts
            </h2>
            <p style={{ fontSize: 12, color: 'var(--text-dim)' }}>
              {stats ? `${stats.total_alerts} total · ordered by risk score` : 'Run demo to populate'}
            </p>
          </div>
          {alerts.length > 0 && (
            <span className="badge badge-danger">
              <span className="pulse-dot w-1.5 h-1.5 rounded-full bg-red-400" />
              {alerts.filter(a => a.status === 'open').length} OPEN
            </span>
          )}
        </div>
        <AlertsTable alerts={alerts} />
      </div>

      {/* ── Empty state ── */}
      {!stats?.total_entities && !isRunning && log.length === 0 && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-dim)' }}>
          <div style={{ fontSize: 64, marginBottom: 16, opacity: 0.15 }}>⬡</div>
          <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: 18, color: 'var(--text-muted)', marginBottom: 8 }}>
            No data yet
          </div>
          <div style={{ fontSize: 13, maxWidth: 340, margin: '0 auto', lineHeight: 1.7 }}>
            Click <strong style={{ color: 'var(--accent)' }}>Run Demo</strong> to generate a synthetic transaction
            network and train the GNN model.
          </div>
        </div>
      )}

    </div>
  )
}
