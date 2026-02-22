import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'

interface Props {
  shapValues: Record<string, number>
  title?: string
}

const FEATURE_LABELS: Record<string, string> = {
  total_sent:          'Total Sent',
  total_received:      'Total Received',
  num_sent:            'Tx Count (Out)',
  num_received:        'Tx Count (In)',
  avg_sent:            'Avg Sent Amount',
  avg_received:        'Avg Recv Amount',
  max_sent:            'Max Sent',
  max_received:        'Max Received',
  in_out_ratio:        'In/Out Ratio',
  geo_diversity:       'Geo Diversity',
  channel_diversity:   'Channel Diversity',
  unique_counterparties: 'Unique Counterparties',
  burstiness:          'Tx Burstiness',
  risk_flag_count:     'Risk Flags',
  degree_centrality:   'Degree Centrality',
  in_degree_centrality:'In-Degree Centrality',
  entity_type_enc:     'Entity Type',
  country_risk:        'Country Risk',
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{
      background: 'var(--surface-2)',
      border: '1px solid var(--border-light)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 12,
    }}>
      <div style={{ color: 'var(--text)', fontFamily: 'Syne, sans-serif', fontWeight: 600, marginBottom: 4 }}>
        {d.label}
      </div>
      <div style={{ color: d.value >= 0 ? 'var(--danger)' : 'var(--ok)', fontFamily: 'JetBrains Mono, monospace' }}>
        {d.value >= 0 ? '↑ Risk +' : '↓ Risk '}{Math.abs(d.value).toFixed(4)}
      </div>
      <div style={{ color: 'var(--text-dim)', marginTop: 4, fontSize: 11 }}>
        {d.value >= 0 ? 'Increases suspicion score' : 'Reduces suspicion score'}
      </div>
    </div>
  )
}

export default function ShapChart({ shapValues, title }: Props) {
  const data = Object.entries(shapValues)
    .map(([k, v]) => ({ key: k, label: FEATURE_LABELS[k] ?? k.replace(/_/g, ' '), value: v, abs: Math.abs(v) }))
    .sort((a, b) => b.abs - a.abs)
    .slice(0, 10)

  if (!data.length) {
    return (
      <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '40px 0', fontSize: 13 }}>
        No SHAP values available
      </div>
    )
  }

  const maxAbs = Math.max(...data.map(d => d.abs))

  return (
    <div>
      {title && (
        <h3 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: 14, color: 'var(--text)', marginBottom: 20 }}>
          {title}
        </h3>
      )}

      {/* Custom bar viz for crispness */}
      <div className="space-y-2">
        {data.map((d, i) => {
          const pct = (d.abs / maxAbs) * 100
          const isPositive = d.value >= 0
          return (
            <div key={d.key} style={{ animationDelay: `${i * 40}ms` }} className="stat-number">
              <div className="flex items-center justify-between mb-1">
                <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>
                  {d.label}
                </span>
                <span style={{
                  fontSize: 11,
                  fontFamily: 'JetBrains Mono, monospace',
                  color: isPositive ? 'var(--danger)' : 'var(--ok)',
                  fontWeight: 600,
                }}>
                  {isPositive ? '+' : ''}{d.value.toFixed(4)}
                </span>
              </div>
              <div className="risk-bar-track">
                <div
                  className="risk-bar-fill"
                  style={{
                    width: `${pct}%`,
                    background: isPositive
                      ? 'linear-gradient(90deg, #f43f5e, #fb7185)'
                      : 'linear-gradient(90deg, #10b981, #34d399)',
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>

      <div style={{ display: 'flex', gap: 20, marginTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-dim)' }}>
          <div style={{ width: 10, height: 3, background: 'var(--danger)', borderRadius: 2 }} />
          Increases risk
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-dim)' }}>
          <div style={{ width: 10, height: 3, background: 'var(--ok)', borderRadius: 2 }} />
          Reduces risk
        </div>
      </div>
    </div>
  )
}
