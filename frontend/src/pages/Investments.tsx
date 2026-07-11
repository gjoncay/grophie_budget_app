import { useEffect, useState } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { api, type Holding, type InvestmentTransaction, type Performance } from '../api'

// Fixed hue order by asset class — color follows the entity's identity,
// never its rank, so a given type always gets the same color regardless
// of which types are present or how the allocation sorts.
const TYPE_COLORS: Record<string, string> = {
  equity: '#7C93C0',
  etf: '#6B8F71',
  mutual_fund: '#E08D6C',
  fixed_income: '#9B7EBD',
  cash: '#C9A227',
  derivative: '#4E7D96',
  other: '#999999',
}

function colorForType(type: string) {
  return TYPE_COLORS[type] ?? TYPE_COLORS.other
}

function formatMoney(amount: number | null) {
  if (amount === null) return '—'
  return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

function formatPct(pct: number | null) {
  if (pct === null) return '—'
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${(pct * 100).toFixed(1)}%`
}

export default function Investments() {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [performance, setPerformance] = useState<Performance | null>(null)
  const [activity, setActivity] = useState<InvestmentTransaction[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.holdings(), api.performance(), api.investmentTransactions()])
      .then(([h, p, a]) => {
        setHoldings(h)
        setPerformance(p)
        setActivity(a)
      })
      .catch((e) => setError(e.message))
  }, [])

  const allocationData = performance
    ? Object.entries(performance.allocation).map(([type, value]) => ({ type, value }))
    : []

  return (
    <div>
      <h1>Investments</h1>
      {error && <p style={{ color: '#C1584A' }}>{error}</p>}

      {holdings.length === 0 ? (
        <p>No investment accounts connected yet.</p>
      ) : (
        <>
          {performance && (
            <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#888' }}>Total value</div>
                <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{formatMoney(performance.total_value)}</div>
                <div style={{ color: (performance.total_gain_loss ?? 0) >= 0 ? '#6B8F71' : '#C1584A' }}>
                  {formatMoney(performance.total_gain_loss)} ({formatPct(
                    performance.total_cost_basis
                      ? (performance.total_gain_loss ?? 0) / performance.total_cost_basis
                      : null,
                  )})
                </div>
              </div>
              <ResponsiveContainer width={220} height={180}>
                <PieChart>
                  <Pie
                    data={allocationData}
                    dataKey="value"
                    nameKey="type"
                    innerRadius={40}
                    outerRadius={70}
                  >
                    {allocationData.map((entry) => (
                      <Cell key={entry.type} fill={colorForType(entry.type)} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatMoney(Number(value))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          <h2>Holdings</h2>
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Account</th>
                <th>Qty</th>
                <th>Cost basis</th>
                <th>Value</th>
                <th>Gain/Loss</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h) => (
                <tr key={`${h.account_id}-${h.security_id}`}>
                  <td>{h.ticker_symbol ?? '—'}</td>
                  <td>{h.name}</td>
                  <td>{h.account_name}</td>
                  <td>{h.quantity}</td>
                  <td>{formatMoney(h.cost_basis)}</td>
                  <td>{formatMoney(h.value)}</td>
                  <td style={{ color: (h.gain_loss ?? 0) >= 0 ? '#6B8F71' : '#C1584A' }}>
                    {formatMoney(h.gain_loss)} ({formatPct(h.gain_loss_pct)})
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <h2>Activity</h2>
          {activity.length === 0 ? (
            <p>No investment transactions yet.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Security</th>
                  <th>Quantity</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {activity.map((t) => (
                  <tr key={t.id}>
                    <td>{t.date}</td>
                    <td>{t.type}</td>
                    <td>{t.ticker_symbol ?? t.security_name ?? t.name}</td>
                    <td>{t.quantity ?? '—'}</td>
                    <td>{formatMoney(t.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}
