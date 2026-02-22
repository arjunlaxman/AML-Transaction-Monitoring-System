import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, CaseDetail } from '../api/client'
import ShapChart from '../components/ShapChart'

function formatUSD(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n)
}
function formatDate(s: string) {
  return new Date(s).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function InfoRow({ label, value, mono = false, color }: { label: string; value: string | number; mono?: boolean; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: 12, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'Syne, sans-serif', fontWeight: 600 }}>
        {label}
      </span>
      <span style={{
        fontSize: 13,
        fontFamily: mono ? 'JetBrains Mono, monospace' : undefined,
        fontWeight: 600,
        color: color ?? 'var(--text)',
      }}>
        {value}
      </span>
    </div>
  )
}

export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const [detail, setDetail]  = useState<CaseDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]    = useState<string | null>(null)

  useEffect(() => {
    if (!caseId) return
    api.getCase(caseId)
      .then(setDetail)
      .catch(e => setError(e.response?.data?.detail ?? e.message))
      .finally(() => setLoading(false))
  }, [caseId])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 400, flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 40, opacity: 0.2, animation: 'spin 2s linear infinite' }}>◎</div>
      <div style={{ color: 'var(--text-dim)', fontSize: 14 }}>Loading case…</div>
    </div>
  )

  if (error || !detail) return (
    <div style={{ textAlign: 'center', padding: '80px 0' }}>
      <div style={{ color: 'var(--danger)', fontSize: 14, marginBottom: 16 }}>{error ?? 'Case not found'}</div>
      <Link to="/" className="btn-ghost">← Back to Overview</Link>
    </div>
  )

  const { alert, entity, cluster, transactions, narrative, shap_values } = detail
  const score = alert.score
  const riskColor = score >= 0.75 ? 'var(--danger)' : score >= 0.5 ? 'var(--warn)' : 'var(--ok)'
  const riskLabel = score >= 0.75 ? 'CRITICAL' : score >= 0.6 ? 'HIGH' : score >= 0.5 ? 'MEDIUM' : 'LOW'

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* ── Back + header ── */}
      <div>
        <Link
          to="/"
          style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4, marginBottom: 16 }}
        >
          ← Back to Overview
        </Link>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
              <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 28, letterSpacing: '-0.03em', color: 'white' }}>
                Case {alert.id}
              </h1>
              <span className="badge" style={{ background: `${riskColor}18`, color: riskColor, border: `1px solid ${riskColor}44`, fontSize: 12 }}>
                ⚠ {riskLabel}
              </span>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              Entity <span style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent)' }}>{entity.id}</span>
              {' · '}{entity.entity_type} · {entity.country}
              {cluster && (
                <> · <span style={{ color: 'var(--text-dim)' }}>{cluster.pattern_type} pattern</span></>
              )}
            </p>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 40, color: riskColor, lineHeight: 1, letterSpacing: '-0.04em' }}>
              {(score * 100).toFixed(1)}
              <span style={{ fontSize: 18, fontWeight: 500 }}>%</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>GNN suspicion score</div>
          </div>
        </div>
      </div>

      {/* ── Main 2-col ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Narrative */}
        <div className="card" style={{ padding: 24 }}>
          <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 13, color: 'var(--text)', letterSpacing: '-0.01em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: 'var(--accent)' }}>◈</span> Case Narrative
          </div>
          <pre style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            color: 'var(--text-muted)',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.7,
            maxHeight: 420,
            overflowY: 'auto',
          }}>
            {narrative}
          </pre>
        </div>

        {/* SHAP */}
        <div className="card" style={{ padding: 24 }}>
          <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 13, color: 'var(--text)', letterSpacing: '-0.01em', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: '#818cf8' }}>◎</span> Risk Factor Attributions
          </div>
          <ShapChart shapValues={shap_values} />
        </div>
      </div>

      {/* ── 3-col metadata ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>

        {/* Entity */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', marginBottom: 12 }}>
            Entity
          </div>
          <InfoRow label="ID"         value={entity.id}          mono color="var(--accent)" />
          <InfoRow label="Type"       value={entity.entity_type} />
          <InfoRow label="Country"    value={entity.country} />
          <InfoRow label="Suspicious" value={entity.is_suspicious ? 'Yes' : 'No'} color={entity.is_suspicious ? 'var(--danger)' : 'var(--ok)'} />
          <InfoRow label="Risk Score" value={`${(entity.risk_score * 100).toFixed(2)}%`} color={riskColor} />
        </div>

        {/* Cluster */}
        {cluster ? (
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', marginBottom: 12 }}>
              Cluster
            </div>
            <InfoRow label="ID"       value={cluster.id.slice(0, 18)} mono color="var(--accent)" />
            <InfoRow label="Pattern"  value={cluster.pattern_type} />
            <InfoRow label="Size"     value={`${cluster.size} entities`} />
            <InfoRow label="Score"    value={`${(cluster.suspicion_score * 100).toFixed(1)}%`} color="var(--danger)" />
            <div style={{ marginTop: 16 }}>
              <Link
                to={`/graph?cluster=${cluster.id}`}
                className="btn-ghost"
                style={{ width: '100%', justifyContent: 'center', fontSize: 12 }}
              >
                View in Graph Explorer →
              </Link>
            </div>
          </div>
        ) : (
          <div className="card" style={{ padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center', color: 'var(--text-dim)', fontSize: 13 }}>
              <div style={{ fontSize: 24, marginBottom: 6, opacity: 0.3 }}>⬡</div>
              No cluster association
            </div>
          </div>
        )}

        {/* Alert status */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', marginBottom: 12 }}>
            Alert
          </div>
          <InfoRow label="Alert ID"  value={alert.id} mono color="var(--accent)" />
          <InfoRow label="Status"    value={alert.status.toUpperCase()} color={alert.status === 'open' ? 'var(--danger)' : 'var(--text-muted)'} />
          <InfoRow label="Created"   value={formatDate(alert.created_at)} />
        </div>
      </div>

      {/* ── Transactions table ── */}
      <div className="card" style={{ padding: 24 }}>
        <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 14, color: 'var(--text)', marginBottom: 4 }}>
          Key Transactions
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20 }}>
          Top {transactions.length} by amount involving this entity
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>TX ID</th>
                <th>Direction</th>
                <th>Amount</th>
                <th>Channel</th>
                <th>Country</th>
                <th>Date</th>
                <th>Risk Flags</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map(tx => {
                const isSrc = tx.src_entity_id === entity.id
                return (
                  <tr key={tx.id} style={{ background: tx.is_suspicious ? 'rgba(244,63,94,0.03)' : undefined }}>
                    <td>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--text-dim)' }}>
                        {tx.id}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ color: isSrc ? '#fb923c' : 'var(--ok)', fontWeight: 700, fontSize: 12 }}>
                          {isSrc ? '↑' : '↓'}
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{isSrc ? 'OUT' : 'IN'}</span>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: 'var(--text-dim)' }}>
                          {isSrc ? tx.dst_entity_id : tx.src_entity_id}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: tx.amount > 50_000 ? 'var(--warn)' : 'var(--text)', fontWeight: 600 }}>
                        {formatUSD(tx.amount)}
                      </span>
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize', fontSize: 12 }}>{tx.channel}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: 12 }}>{tx.country}</span>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--text-dim)' }}>
                        {formatDate(tx.timestamp)}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {tx.risk_flags.map(f => (
                          <span key={f} className="badge badge-danger" style={{ fontSize: 10 }}>
                            {f.replace(/_/g, ' ')}
                          </span>
                        ))}
                        {!tx.risk_flags.length && <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>—</span>}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  )
}
