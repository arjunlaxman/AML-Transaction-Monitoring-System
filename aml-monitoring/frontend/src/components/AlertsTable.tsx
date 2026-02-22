import { Alert } from '../api/client'
import { Link } from 'react-router-dom'

interface Props { alerts: Alert[] }

function riskConfig(score: number) {
  if (score >= 0.75) return { label: 'CRITICAL', color: 'var(--danger)', bg: 'var(--danger-dim)', border: 'rgba(244,63,94,0.25)' }
  if (score >= 0.60) return { label: 'HIGH',     color: '#fb923c',       bg: 'rgba(251,146,60,0.1)',  border: 'rgba(251,146,60,0.25)' }
  if (score >= 0.50) return { label: 'MEDIUM',   color: 'var(--warn)',   bg: 'var(--warn-dim)',        border: 'rgba(245,158,11,0.25)' }
  return               { label: 'LOW',     color: 'var(--ok)',    bg: 'var(--success-dim)',    border: 'rgba(16,185,129,0.25)' }
}

const PATTERN_ICONS: Record<string, string> = {
  smurfing: '◈',
  layering: '⬡',
  circular: '◎',
  mixed:    '⬢',
}

export default function AlertsTable({ alerts }: Props) {
  if (!alerts.length) {
    return (
      <div style={{ padding: '60px 0', textAlign: 'center' }}>
        <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.3 }}>⬡</div>
        <div style={{ color: 'var(--text-dim)', fontSize: 14 }}>No alerts yet.</div>
        <div style={{ color: 'var(--text-dim)', fontSize: 12, marginTop: 4 }}>Run the demo to generate data.</div>
      </div>
    )
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>Alert ID</th>
            <th>Entity</th>
            <th>Cluster / Pattern</th>
            <th>Risk Score</th>
            <th>Level</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a, i) => {
            const rc = riskConfig(a.score)
            const patternType = a.cluster_id?.includes('SMURF') ? 'smurfing'
                              : a.cluster_id?.includes('LAYER') ? 'layering'
                              : a.cluster_id?.includes('CIRC')  ? 'circular' : 'mixed'
            return (
              <tr key={a.id} style={{ animationDelay: `${i * 20}ms` }} className="stat-number">
                <td>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent)', fontSize: 12, fontWeight: 600 }}>
                    {a.id}
                  </span>
                </td>
                <td>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--text)', fontSize: 12 }}>
                    {a.entity_id}
                  </span>
                </td>
                <td>
                  {a.cluster_id ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 12, opacity: 0.6 }}>{PATTERN_ICONS[patternType]}</span>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--text-muted)' }}>
                        {a.cluster_id.slice(0, 16)}
                      </span>
                    </div>
                  ) : (
                    <span style={{ color: 'var(--text-dim)', fontSize: 12 }}>—</span>
                  )}
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 60 }}>
                      <div className="risk-bar-track">
                        <div className="risk-bar-fill" style={{
                          width: `${a.score * 100}%`,
                          background: a.score >= 0.75
                            ? 'linear-gradient(90deg, #f43f5e, #fb7185)'
                            : a.score >= 0.5
                            ? 'linear-gradient(90deg, #f59e0b, #fcd34d)'
                            : 'linear-gradient(90deg, #10b981, #34d399)',
                        }} />
                      </div>
                    </div>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: rc.color, fontWeight: 600 }}>
                      {(a.score * 100).toFixed(1)}%
                    </span>
                  </div>
                </td>
                <td>
                  <span className="badge" style={{ background: rc.bg, color: rc.color, border: `1px solid ${rc.border}` }}>
                    {rc.label}
                  </span>
                </td>
                <td>
                  <span className={`badge ${a.status === 'open' ? 'badge-danger' : 'badge-neutral'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${a.status === 'open' ? 'pulse-dot bg-red-400' : 'bg-gray-500'}`} />
                    {a.status.toUpperCase()}
                  </span>
                </td>
                <td>
                  <Link
                    to={`/cases/${a.id}`}
                    style={{
                      fontSize: 12,
                      color: 'var(--accent)',
                      textDecoration: 'none',
                      fontWeight: 500,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '4px 10px',
                      border: '1px solid rgba(99,102,241,0.2)',
                      borderRadius: 6,
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--accent-dim)' }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                  >
                    View Case →
                  </Link>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
