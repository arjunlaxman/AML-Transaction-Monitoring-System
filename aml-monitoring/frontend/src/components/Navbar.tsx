import { Link, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../api/client'

const NAV = [
  { to: '/',        label: 'Overview',       icon: '◈' },
  { to: '/graph',   label: 'Graph Explorer', icon: '⬡' },
  { to: '/metrics', label: 'Model Metrics',  icon: '◎' },
]

export default function Navbar() {
  const { pathname } = useLocation()
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    api.getHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
  }, [])

  return (
    <nav
      style={{
        background: 'rgba(12,18,32,0.85)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid var(--border)',
      }}
      className="sticky top-0 z-50 w-full"
    >
      <div className="max-w-[1400px] mx-auto px-6 py-0 flex items-center justify-between h-14">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div
            style={{
              background: 'linear-gradient(135deg, #6366f1, #818cf8)',
              boxShadow: '0 0 12px rgba(99,102,241,0.4)',
            }}
            className="w-8 h-8 rounded-lg flex items-center justify-center"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 1L14 4.5V11.5L8 15L2 11.5V4.5L8 1Z" stroke="white" strokeWidth="1.5" fill="none"/>
              <path d="M8 5L11 6.5V9.5L8 11L5 9.5V6.5L8 5Z" fill="white" fillOpacity="0.8"/>
            </svg>
          </div>
          <div>
            <div
              style={{ fontFamily: 'Syne, sans-serif', fontWeight: 700, fontSize: '15px', letterSpacing: '-0.02em' }}
              className="text-white leading-none"
            >
              AML Monitor
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', letterSpacing: '0.06em' }}>
              TRANSACTION INTELLIGENCE
            </div>
          </div>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          {NAV.map(({ to, label, icon }) => {
            const active = pathname === to
            return (
              <Link
                key={to}
                to={to}
                style={{
                  fontFamily: 'Syne, sans-serif',
                  fontSize: '13px',
                  fontWeight: active ? 600 : 500,
                  color: active ? 'white' : 'var(--text-muted)',
                  background: active ? 'var(--accent-dim)' : 'transparent',
                  border: `1px solid ${active ? 'rgba(99,102,241,0.3)' : 'transparent'}`,
                  borderRadius: '8px',
                  padding: '6px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.15s',
                  textDecoration: 'none',
                }}
                onMouseEnter={e => {
                  if (!active) {
                    (e.currentTarget as HTMLElement).style.color = 'white'
                    ;(e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'
                  }
                }}
                onMouseLeave={e => {
                  if (!active) {
                    (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)'
                    ;(e.currentTarget as HTMLElement).style.background = 'transparent'
                  }
                }}
              >
                <span style={{ fontSize: '11px', opacity: 0.7 }}>{icon}</span>
                {label}
              </Link>
            )
          })}
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full pulse-dot ${
              online === null ? 'bg-gray-500' :
              online ? 'bg-emerald-400' : 'bg-red-500'
            }`}
          />
          <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
            {online === null ? 'connecting' : online ? 'api online' : 'api offline'}
          </span>
        </div>

      </div>
    </nav>
  )
}
