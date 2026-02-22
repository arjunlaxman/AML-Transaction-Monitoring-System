/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['DM Sans', 'system-ui', 'sans-serif'],
        display: ['Syne', 'sans-serif'],
        mono:    ['JetBrains Mono', 'monospace'],
      },
      colors: {
        bg:       '#070b14',
        surface:  '#0c1220',
        's2':     '#111827',
        's3':     '#182034',
        border:   '#1e2d45',
        'border-l': '#243350',
        accent:   '#6366f1',
        danger:   '#f43f5e',
        warn:     '#f59e0b',
        ok:       '#10b981',
      },
      animation: {
        'fade-in':     'fadeSlideIn 0.3s ease both',
        'count-up':    'countUp 0.4s ease both',
        'pulse-slow':  'pulse 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
