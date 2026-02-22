import { useEffect, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell, Legend,
} from 'recharts'
import { api, Metrics } from '../api/client'
import { Link } from 'react-router-dom'

const MODELS = [
  { key: 'gnn',                 label: 'GraphSAGE GNN',       color: '#6366f1' },
  { key: 'logistic_regression', label: 'Logistic Regression', color: '#10b981' },
  { key: 'rule_based',          label: 'Rule-Based',          color: '#f59e0b' },
]

function MetricGauge({ label, value, color, delay = 0 }: { label: string; value: number; color: string; delay?: number }) {
  return (
    <div className="page-enter" style={{ animationDelay: `${delay}ms` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'Syne, sans-serif', fontWeight: 600 }}>
          {label}
        </span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color, fontWeight: 700 }}>
          {(value * 100).toFixed(1)}%
        </span>
      </div>
      <div className="risk-bar-track" style={{ height: 6 }}>
        <div
          className="risk-bar-fill"
          style={{
            width: `${value * 100}%`,
            background: `linear-gradient(90deg, ${color}cc, ${color})`,
            height: '100%',
          }}
        />
      </div>
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--surface-2)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '10px 14px' }}>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6, fontFamily: 'Syne, sans-serif', fontWeight: 600 }}>{label}</div>
      {payload.map((p: { name: string; value: number; color: string }) => (
        <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginBottom: 2 }}>
          <div style={{ width: 8, height: 8, borderRadius: 2, background: p.color }} />
          <span style={{ color: 'var(--text-muted)' }}>{p.name}:</span>
          <span style={{ color: 'var(--text)', fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
            {(p.value * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  )
}

export default function ModelMetrics() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]    = useState<string | null>(null)

  useEffect(() => {
    api.getMetrics()
      .then(setMetrics)
      .catch(e => setError(e.response?.data?.detail ?? e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 400 }}>
      <div style={{ color: 'var(--text-dim)', fontSize: 14 }}>Loading metrics…</div>
    </div>
  )

  if (error || !metrics) return (
    <div style={{ textAlign: 'center', padding: '80px 0' }}>
      <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.1 }}>◎</div>
      <div style={{ color: 'var(--text-muted)', fontSize: 16, fontFamily: 'Syne, sans-serif', fontWeight: 600, marginBottom: 8 }}>
        No model metrics yet
      </div>
      <div style={{ color: 'var(--text-dim)', fontSize: 13, marginBottom: 24 }}>
        {error ?? 'Run the demo to train the GNN and generate metrics.'}
      </div>
      <Link to="/" className="btn-primary" style={{ display: 'inline-flex' }}>
        ← Go to Overview
      </Link>
    </div>
  )

  // Comparison bar data
  const compData = ['precision', 'recall', 'f1'].map(m => ({
    metric: m.toUpperCase(),
    'GNN':  metrics.gnn[m] ?? 0,
    'Log Reg': metrics.logistic_regression[m] ?? 0,
    'Rule-Based': metrics.rule_based[m] ?? 0,
  }))

  // PR curve (downsample for performance)
  const prData = metrics.pr_curve
    ? metrics.pr_curve.recall
        .map((r, i) => ({ recall: +r.toFixed(3), precision: +(metrics.pr_curve!.precision[i]).toFixed(3) }))
        .filter((_, i) => i % 4 === 0)
    : []

  // GNN vs best baseline improvement
  const gnnF1   = metrics.gnn.f1 ?? 0
  const bestF1  = Math.max(metrics.rule_based.f1 ?? 0, metrics.logistic_regression.f1 ?? 0)
  const improvement = bestF1 > 0 ? ((gnnF1 - bestF1) / bestF1 * 100) : 0

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 32, letterSpacing: '-0.03em', color: 'white', marginBottom: 6 }}>
            Model Performance
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            {metrics.mode === 'demo' ? 'Demo run' : 'Full run'} ·{' '}
            {new Date(metrics.created_at).toLocaleString()}
            {improvement > 0 && (
              <span style={{ color: 'var(--ok)', marginLeft: 12 }}>
                ✓ GNN outperforms baselines by {improvement.toFixed(1)}% F1
              </span>
            )}
          </p>
        </div>
        {metrics.gnn.roc_auc && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 36, color: 'var(--accent)', letterSpacing: '-0.04em', lineHeight: 1 }}>
              {(metrics.gnn.roc_auc * 100).toFixed(1)}
              <span style={{ fontSize: 16, fontWeight: 500 }}>%</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>GNN ROC-AUC</div>
          </div>
        )}
      </div>

      {/* Per-model metric cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {MODELS.map(({ key, label, color }, mi) => {
          const m = metrics[key as keyof Metrics] as Record<string, number>
          return (
            <div key={key} className="card card-glow page-enter" style={{ padding: 24, animationDelay: `${mi * 80}ms` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}88` }} />
                <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 14, color: 'white' }}>
                  {label}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <MetricGauge label="Precision" value={m.precision ?? 0} color={color} delay={mi * 80 + 100} />
                <MetricGauge label="Recall"    value={m.recall ?? 0}    color={color} delay={mi * 80 + 150} />
                <MetricGauge label="F1 Score"  value={m.f1 ?? 0}        color={color} delay={mi * 80 + 200} />
                {m.roc_auc !== undefined && (
                  <MetricGauge label="ROC-AUC"  value={m.roc_auc}       color={color} delay={mi * 80 + 250} />
                )}
              </div>
              {key === 'gnn' && improvement > 0 && (
                <div style={{
                  marginTop: 16,
                  padding: '8px 12px',
                  background: 'rgba(16,185,129,0.08)',
                  border: '1px solid rgba(16,185,129,0.2)',
                  borderRadius: 8,
                  fontSize: 11,
                  color: 'var(--ok)',
                  fontFamily: 'Syne, sans-serif',
                  fontWeight: 600,
                }}>
                  ↑ {improvement.toFixed(1)}% F1 vs best baseline
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Model comparison bar chart */}
      <div className="card" style={{ padding: 24 }}>
        <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 14, color: 'var(--text)', marginBottom: 4 }}>
          Model Comparison
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20 }}>
          Precision · Recall · F1 across all three models
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={compData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" vertical={false} />
            <XAxis dataKey="metric" tick={{ fill: '#7889a8', fontSize: 12, fontFamily: 'Syne, sans-serif', fontWeight: 600 }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 1]} tickFormatter={v => `${(v * 100).toFixed(0)}%`} tick={{ fill: '#7889a8', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ paddingTop: 16, fontSize: 12, color: 'var(--text-muted)', fontFamily: 'Syne, sans-serif' }}
            />
            {MODELS.map(({ label, color }) => (
              <Bar key={label} dataKey={label === 'GraphSAGE GNN' ? 'GNN' : label === 'Logistic Regression' ? 'Log Reg' : 'Rule-Based'} fill={color} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* PR Curve */}
      {prData.length > 0 && (
        <div className="card" style={{ padding: 24 }}>
          <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 14, color: 'var(--text)', marginBottom: 4 }}>
            Precision-Recall Curve (GNN)
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20 }}>
            Test set · higher area under curve = better performance on imbalanced data
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={prData} margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" />
              <XAxis
                dataKey="recall"
                label={{ value: 'Recall', position: 'insideBottom', offset: -12, fill: '#7889a8', fontSize: 12, fontFamily: 'Syne, sans-serif' }}
                tick={{ fill: '#7889a8', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
                axisLine={false} tickLine={false}
              />
              <YAxis
                domain={[0, 1]}
                label={{ value: 'Precision', angle: -90, position: 'insideLeft', fill: '#7889a8', fontSize: 12, fontFamily: 'Syne, sans-serif', offset: 8 }}
                tick={{ fill: '#7889a8', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
                axisLine={false} tickLine={false}
              />
              <Tooltip
                formatter={(v: number) => [`${(v * 100).toFixed(1)}%`]}
                contentStyle={{ background: 'var(--surface-2)', border: '1px solid var(--border-light)', borderRadius: 8 }}
                labelStyle={{ color: 'var(--text)', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}
              />
              <Line type="monotone" dataKey="precision" stroke="#6366f1" strokeWidth={2.5} dot={false}
                style={{ filter: 'drop-shadow(0 0 6px rgba(99,102,241,0.5))' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Methodology note */}
      <div style={{
        background: 'var(--accent-dim)',
        border: '1px solid rgba(99,102,241,0.2)',
        borderRadius: 12,
        padding: '20px 24px',
      }}>
        <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 13, color: 'var(--accent)', marginBottom: 10 }}>
          ◎ Explainability Methodology
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.7 }}>
          GNN risk scores are explained via an <strong style={{ color: 'var(--text)' }}>XGBoost surrogate model</strong> trained to approximate
          the GNN's output probabilities on node-level features (transaction statistics, centrality measures,
          geographic diversity, entity type). <strong style={{ color: 'var(--text)' }}>SHAP TreeExplainer</strong> decomposes each prediction into
          per-feature contributions without backpropagating through the graph structure — making attributions
          auditor-ready and computationally tractable at scale.
          Class imbalance (~5% suspicious) is handled via <strong style={{ color: 'var(--text)' }}>inverse-frequency class weighting</strong> during
          training and stratified splitting.
        </p>
      </div>

    </div>
  )
}
