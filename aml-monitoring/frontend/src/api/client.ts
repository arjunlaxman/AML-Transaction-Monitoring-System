/**
 * API client.
 *
 * Uses the /api prefix which is:
 *   - Dev:  proxied by Vite to http://localhost:8000  (vite.config.ts)
 *   - Prod: proxied by nginx to http://api:8000       (nginx.conf)
 *
 * No build-time env vars needed — works anywhere without rebuilding.
 */
import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 360_000,   // 6 min — covers full-mode training
})

// ─── Types ─────────────────────────────────────────────────────────────────

export interface Stats {
  total_entities: number
  total_transactions: number
  total_alerts: number
  open_alerts: number
  total_clusters: number
  gnn_precision: number
  gnn_recall: number
  gnn_f1: number
  gnn_roc_auc: number
  has_model: boolean
}

export interface Alert {
  id: string
  entity_id: string
  cluster_id: string | null
  score: number
  narrative: string
  shap_values: Record<string, number>
  status: string
  created_at: string
}

export interface AlertsResponse {
  total: number
  items: Alert[]
}

export interface Cluster {
  id: string
  entity_ids: string[]
  size: number
  suspicion_score: number
  pattern_type: string
  created_at: string
}

export interface Entity {
  id: string
  entity_type: string
  country: string
  is_suspicious: boolean
  cluster_id: string | null
  risk_score: number
  features: Record<string, number>
}

export interface Transaction {
  id: string
  src_entity_id: string
  dst_entity_id: string
  amount: number
  timestamp: string
  channel: string
  country: string
  risk_flags: string[]
  is_suspicious: boolean
}

export interface CaseDetail {
  alert: Alert
  entity: Entity
  cluster: Cluster | null
  transactions: Transaction[]
  narrative: string
  shap_values: Record<string, number>
}

export interface GraphNode {
  id: string
  entity_type: string
  country: string
  risk_score: number
  is_suspicious: boolean
  cluster_id: string | null
}

export interface GraphEdge {
  source: string
  target: string
  amount: number
  channel: string
  is_suspicious: boolean
}

export interface Subgraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
  cluster_id: string
}

export interface Metrics {
  mode: string
  gnn: Record<string, number>
  rule_based: Record<string, number>
  logistic_regression: Record<string, number>
  pr_curve: { precision: number[]; recall: number[] } | null
  created_at: string
}

export interface JobResponse {
  status: string
  message: string
  detail: Record<string, unknown>
}

// ─── API functions ──────────────────────────────────────────────────────────

export const api = {
  getHealth:       ()                           => http.get('/health').then(r => r.data),
  getStats:        ()                           => http.get<Stats>('/stats').then(r => r.data),
  getAlerts:       (limit = 50, offset = 0)    => http.get<AlertsResponse>('/alerts', { params: { limit, offset } }).then(r => r.data),
  getTopClusters:  (limit = 10)               => http.get<Cluster[]>('/clusters/top', { params: { limit } }).then(r => r.data),
  getCase:         (id: string)                => http.get<CaseDetail>(`/cases/${id}`).then(r => r.data),
  getClusterGraph: (id: string)               => http.get<Subgraph>(`/graph/cluster/${id}`).then(r => r.data),
  getMetrics:      ()                          => http.get<Metrics>('/metrics').then(r => r.data),
  runGenerate:     (size: 'demo' | 'full')     => http.post<JobResponse>('/generate', null, { params: { size } }).then(r => r.data),
  runTrain:        (mode: 'demo' | 'full')     => http.post<JobResponse>('/train', null, { params: { mode } }).then(r => r.data),
}
