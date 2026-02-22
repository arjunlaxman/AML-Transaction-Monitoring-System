import { useEffect, useState, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, Cluster, Subgraph, GraphNode } from '../api/client'

const PATTERN_COLORS: Record<string, string> = {
  smurfing: '#f43f5e',
  layering: '#f59e0b',
  circular: '#6366f1',
  mixed:    '#a78bfa',
}
const PATTERN_ICONS: Record<string, string> = {
  smurfing: '◈',
  layering: '⬡',
  circular: '◎',
  mixed:    '⬢',
}

// ── Force Graph with lazy load ───────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ForceGraph2D({ graphData, onNodeClick }: { graphData: any; onNodeClick: (n: GraphNode) => void }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [FG, setFG] = useState<any>(null)

  useEffect(() => {
    import('react-force-graph-2d').then(m => setFG(() => m.default))
  }, [])

  if (!FG) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-dim)', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontSize: 32, opacity: 0.2 }}>⬡</div>
      <div style={{ fontSize: 13 }}>Loading graph engine…</div>
    </div>
  )

  return (
    <FG
      graphData={graphData}
      backgroundColor="#070b14"
      nodeColor={(n: { color: string }) => n.color}
      nodeVal={(n: { val: number }) => n.val}
      nodeLabel={(n: { id: string; risk_pct: string }) => `${n.id}  ·  ${n.risk_pct}`}
      linkColor={(l: { color: string }) => l.color}
      linkWidth={(l: { width: number }) => l.width}
      linkDirectionalArrowLength={5}
      linkDirectionalArrowRelPos={0.85}
      linkDirectionalArrowColor={(l: { color: string }) => l.color}
      onNodeClick={onNodeClick}
      nodeCanvasObject={(
        node: { x?: number; y?: number; color: string; val: number; is_suspicious: boolean },
        ctx: CanvasRenderingContext2D,
        globalScale: number
      ) => {
        const x = node.x ?? 0, y = node.y ?? 0
        const r = Math.max(3, (node.val ?? 3) * 1.2)
        if (node.is_suspicious) {
          ctx.beginPath()
          ctx.arc(x, y, r + 4, 0, 2 * Math.PI)
          ctx.fillStyle = node.color + '22'
          ctx.fill()
        }
        ctx.beginPath()
        ctx.arc(x, y, r, 0, 2 * Math.PI)
        ctx.fillStyle = node.color
        ctx.shadowColor = node.is_suspicious ? node.color : 'transparent'
        ctx.shadowBlur = node.is_suspicious ? 8 : 0
        ctx.fill()
        ctx.shadowBlur = 0
      }}
    />
  )
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function GraphExplorer() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [clusters, setClusters]         = useState<Cluster[]>([])
  const [selectedId, setSelectedId]     = useState<string | null>(searchParams.get('cluster'))
  const [subgraph, setSubgraph]         = useState<Subgraph | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [loading, setLoading]           = useState(false)

  // Load cluster list
  useEffect(() => {
    api.getTopClusters(30).then(setClusters).catch(() => {})
  }, [])

  const loadCluster = useCallback(async (id: string) => {
    setLoading(true)
    setSelectedNode(null)
    setSelectedId(id)
    setSearchParams({ cluster: id })
    try {
      const sg = await api.getClusterGraph(id)
      setSubgraph(sg)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [setSearchParams])

  // Auto-load cluster from URL param on mount
  useEffect(() => {
    const param = searchParams.get('cluster')
    if (param && !subgraph && !loading) {
      loadCluster(param)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Build graph data for force-graph
  const graphData = subgraph ? {
    nodes: subgraph.nodes.map(n => ({
      ...n,
      color: n.is_suspicious
        ? `hsl(${350 - n.risk_score * 30}, 90%, ${50 + n.risk_score * 15}%)`
        : '#1e3a5f',
      val:  n.is_suspicious ? 5 + n.risk_score * 8 : 3,
      risk_pct: `${(n.risk_score * 100).toFixed(1)}%`,
    })),
    links: subgraph.edges.map(e => ({
      source: e.source,
      target: e.target,
      color: e.is_suspicious ? 'rgba(244,63,94,0.7)' : 'rgba(99,102,241,0.25)',
      width: e.is_suspicious ? 2 : 1,
      amount: e.amount,
    })),
  } : { nodes: [], links: [] }

  const selectedCluster = clusters.find(c => c.id === selectedId)

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div>
        <h1 style={{ fontFamily: 'Syne, sans-serif', fontWeight: 800, fontSize: 32, letterSpacing: '-0.03em', color: 'white', marginBottom: 6 }}>
          Graph Explorer
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
          Visualize suspicious entity clusters and their transaction networks.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 16, height: 640 }}>

        {/* ── Cluster list panel ── */}
        <div
          className="card"
          style={{ width: 240, flexShrink: 0, overflowY: 'auto', padding: 16 }}
        >
          <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: 12 }}>
            Suspicious Clusters
          </div>

          {clusters.length === 0 && (
            <div style={{ color: 'var(--text-dim)', fontSize: 12, lineHeight: 1.6, padding: '8px 0' }}>
              Run demo first to generate clusters.
            </div>
          )}

          {clusters.map(c => {
            const pattern = c.pattern_type
            const pcolor  = PATTERN_COLORS[pattern] ?? 'var(--accent)'
            const active  = c.id === selectedId
            return (
              <button
                key={c.id}
                onClick={() => loadCluster(c.id)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '10px 12px',
                  borderRadius: 8,
                  marginBottom: 6,
                  background: active ? 'var(--accent-dim)' : 'var(--surface-2)',
                  border: `1px solid ${active ? 'rgba(99,102,241,0.4)' : 'var(--border)'}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 13, color: pcolor, fontWeight: 700 }}>
                    {PATTERN_ICONS[pattern]} {pattern}
                  </span>
                  <span style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 11,
                    fontWeight: 700,
                    color: c.suspicion_score > 0.75 ? 'var(--danger)' : 'var(--warn)',
                  }}>
                    {(c.suspicion_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: 'var(--text-dim)', marginBottom: 2 }}>
                  {c.id.slice(0, 18)}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                  {c.size} entities
                </div>
              </button>
            )
          })}
        </div>

        {/* ── Graph canvas ── */}
        <div
          className="card"
          style={{ flex: 1, position: 'relative', overflow: 'hidden' }}
        >
          {loading && (
            <div style={{
              position: 'absolute', inset: 0, zIndex: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(7,11,20,0.7)', backdropFilter: 'blur(4px)',
            }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, marginBottom: 8, opacity: 0.4, animation: 'spin 2s linear infinite' }}>⬡</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading graph…</div>
              </div>
            </div>
          )}

          {!subgraph && !loading && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 64, opacity: 0.06 }}>⬡</div>
              <div style={{ color: 'var(--text-dim)', fontSize: 14 }}>Select a cluster to visualize</div>
            </div>
          )}

          {subgraph && !loading && (
            <ForceGraph2D graphData={graphData} onNodeClick={n => setSelectedNode(n as GraphNode)} />
          )}

          {/* Cluster stats overlay */}
          {selectedCluster && (
            <div style={{
              position: 'absolute', top: 16, left: 16,
              background: 'rgba(12,18,32,0.85)', backdropFilter: 'blur(8px)',
              border: '1px solid var(--border)', borderRadius: 10,
              padding: '12px 16px', minWidth: 200,
            }}>
              <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: 13, color: 'white', marginBottom: 8 }}>
                {PATTERN_ICONS[selectedCluster.pattern_type]} {selectedCluster.pattern_type.toUpperCase()}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
                {[
                  ['Score', `${(selectedCluster.suspicion_score * 100).toFixed(1)}%`],
                  ['Entities', selectedCluster.size],
                ].map(([k, v]) => (
                  <div key={k as string}>
                    <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{k}</div>
                    <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Node detail panel ── */}
        {selectedNode && (
          <div
            className="card page-enter"
            style={{ width: 220, flexShrink: 0, padding: 16, height: 'fit-content', alignSelf: 'flex-start' }}
          >
            <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: 14 }}>
              Node Detail
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                { label: 'Entity ID',   value: selectedNode.id,          mono: true,  color: 'var(--accent)' },
                { label: 'Type',        value: selectedNode.entity_type,               color: 'var(--text)' },
                { label: 'Country',     value: selectedNode.country,                   color: 'var(--text)' },
                { label: 'Cluster',     value: selectedNode.cluster_id ?? '—',  mono: true, color: 'var(--text-muted)' },
              ].map(({ label, value, mono, color }) => (
                <div key={label}>
                  <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>
                    {label}
                  </div>
                  <div style={{ fontSize: 12, color, fontFamily: mono ? 'JetBrains Mono, monospace' : undefined, fontWeight: 500, wordBreak: 'break-all' }}>
                    {value}
                  </div>
                </div>
              ))}
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                  Risk Score
                </div>
                <div style={{ marginBottom: 4 }}>
                  <div className="risk-bar-track">
                    <div className="risk-bar-fill" style={{
                      width: `${selectedNode.risk_score * 100}%`,
                      background: selectedNode.risk_score > 0.75
                        ? 'linear-gradient(90deg, #f43f5e, #fb7185)'
                        : selectedNode.risk_score > 0.5
                        ? 'linear-gradient(90deg, #f59e0b, #fcd34d)'
                        : 'linear-gradient(90deg, #10b981, #34d399)',
                    }} />
                  </div>
                </div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, fontSize: 16, color: selectedNode.risk_score > 0.75 ? 'var(--danger)' : selectedNode.risk_score > 0.5 ? 'var(--warn)' : 'var(--ok)' }}>
                  {(selectedNode.risk_score * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <span className={`badge ${selectedNode.is_suspicious ? 'badge-danger' : 'badge-success'}`}>
                  {selectedNode.is_suspicious ? '⚠ Suspicious' : '✓ Normal'}
                </span>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '0 4px' }}>
        {[
          { color: '#f43f5e', label: 'High-risk entity (suspicious)' },
          { color: '#1e3a5f', label: 'Normal entity' },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-dim)' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}88` }} />
            {label}
          </div>
        ))}
        {[
          { color: 'rgba(244,63,94,0.7)', label: 'Suspicious transaction', w: 20 },
          { color: 'rgba(99,102,241,0.4)',  label: 'Normal transaction',    w: 20 },
        ].map(({ color, label, w }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-dim)' }}>
            <div style={{ width: w, height: 2, background: color }} />
            {label}
          </div>
        ))}
      </div>

    </div>
  )
}
