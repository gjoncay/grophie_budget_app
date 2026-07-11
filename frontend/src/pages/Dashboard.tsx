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
    <div style={{ background: '#fff', border: '1px solid #ddd', borderRadius: 8, padding: '0.5rem 0.75rem' }}>
      <div style={{ color: '#666', fontSize: '0.8rem' }}>{formatDate(point.date)}</div>
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
      {error && <p style={{ color: '#C1584A' }}>{error}</p>}

      <p
        style={{
          background: '#FBEAE3',
          color: '#8A3F31',
          borderRadius: 999,
          padding: '0.5rem 1rem',
          display: 'inline-block',
        }}
      >
        {insight || 'Loading…'}
      </p>

      <div style={{ fontSize: '2.5rem', fontWeight: 700, margin: '0.5rem 0' }}>
        {summary ? formatMoney(summary.net_worth) : '—'}
      </div>

      {history.length === 0 ? (
        <p>Connect an account to see your net worth trend.</p>
      ) : (
        <>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            {RANGES.map((r) => (
              <button
                key={r.label}
                onClick={() => setRangeDays(r.days)}
                style={{ fontWeight: rangeDays === r.days ? 700 : 400 }}
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
              <CartesianGrid vertical={false} stroke="#eee" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12, fill: '#888' }}
                axisLine={false}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis
                tickFormatter={(v) => formatMoney(v)}
                tick={{ fontSize: 12, fill: '#888' }}
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
          <p style={{ fontSize: '0.8rem', color: '#888' }}>
            Cash and credit balances are reconstructed from transaction history. Investment
            balances only count from the day each account was connected — see the Investments
            page for details.
          </p>
        </>
      )}

      {summary && summary.accounts.length > 0 && (
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '1rem' }}>
          {summary.accounts.map((a) => (
            <div key={a.id} style={{ border: '1px solid #eee', borderRadius: 12, padding: '0.75rem 1rem' }}>
              <div style={{ fontSize: '0.8rem', color: '#888' }}>{a.institution_name}</div>
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
