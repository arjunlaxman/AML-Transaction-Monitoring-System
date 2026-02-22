import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Overview from './pages/Overview'
import GraphExplorer from './pages/GraphExplorer'
import CaseDetail from './pages/CaseDetail'
import ModelMetrics from './pages/ModelMetrics'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 w-full max-w-[1400px] mx-auto px-6 py-8">
        <Routes>
          <Route path="/"              element={<Overview />} />
          <Route path="/graph"         element={<GraphExplorer />} />
          <Route path="/cases/:caseId" element={<CaseDetail />} />
          <Route path="/metrics"       element={<ModelMetrics />} />
        </Routes>
      </main>
    </div>
  )
}
