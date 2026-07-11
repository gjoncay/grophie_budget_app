import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type AccountsSummary, type NetWorthPoint } from '../api'

const RANGES = [
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: 'All', days: null },
] as const

const MOSS = '#6B8F71'

function formatMoney(amount: number) {
  return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function TrendTooltip({ active, payload }: { active?: boolean; payload?: { payload: NetWorthPoint }[] }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <div className="card" style={{ padding: '0.5rem 0.75rem', marginBottom: 0 }}>
      <div className="text-muted">{formatDate(point.date)}</div>
      <div style={{ fontWeight: 600 }}>{formatMoney(point.net_worth)}</div>
    </div>
  )
}

export default function Dashboard() {
  const [history, setHistory] = useState<NetWorthPoint[]>([])
  const [summary, setSummary] = useState<AccountsSummary | null>(null)
  const [insight, setInsight] = useState<string>('')
  const [rangeDays, setRangeDays] = useState<number | null>(90)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.netWorthHistory(), api.accountsSummary(), api.insight()])
      .then(([h, s, i]) => {
        setHistory(h)
        setSummary(s)
        setInsight(i.message)
      })
      .catch((e) => setError(e.message))
  }, [])

  const visibleHistory = useMemo(() => {
    if (rangeDays === null) return history
    return history.slice(-rangeDays)
  }, [history, rangeDays])

  return (
    <div>
      <h1>Dashboard</h1>
      {error && <p className="text-negative">{error}</p>}

      <p className="pill">{insight || 'Loading…'}</p>

      <div className="hero-number">{summary ? formatMoney(summary.net_worth) : '—'}</div>

      {history.length === 0 ? (
        <p>Connect an account to see your net worth trend.</p>
      ) : (
        <div className="card">
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
            {RANGES.map((r) => (
              <button
                key={r.label}
                className={rangeDays === r.days ? '' : 'btn-secondary'}
                onClick={() => setRangeDays(r.days)}
              >
                {r.label}
              </button>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={visibleHistory} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="netWorthFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={MOSS} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={MOSS} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12, fill: 'var(--ink-muted)' }}
                axisLine={false}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis
                tickFormatter={(v) => formatMoney(v)}
                tick={{ fontSize: 12, fill: 'var(--ink-muted)' }}
                axisLine={false}
                tickLine={false}
                width={80}
              />
              <Tooltip content={<TrendTooltip />} />
              <Area
                type="monotone"
                dataKey="net_worth"
                stroke={MOSS}
                strokeWidth={2}
                fill="url(#netWorthFill)"
                activeDot={{ r: 4 }}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
          <p className="text-muted">
            Cash and credit balances are reconstructed from transaction history. Investment
            balances only count from the day each account was connected — see the Investments
            page for details.
          </p>
        </div>
      )}

      {summary && summary.accounts.length > 0 && (
        <div className="card-row">
          {summary.accounts.map((a) => (
            <div key={a.id} className="card" style={{ minWidth: 180 }}>
              <div className="text-muted">{a.institution_name}</div>
              <div>{a.name}</div>
              <div style={{ fontWeight: 600 }}>
                {a.current_balance !== null ? formatMoney(a.current_balance) : '—'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
