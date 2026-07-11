import { useCallback, useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, type Category, type SpendingSummary, type SpendingTrendPoint, type Transaction } from '../api'

const CLAY = '#E08D6C'

function formatMoney(amount: number) {
  const sign = amount < 0 ? '+' : ''
  return sign + Math.abs(amount).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

function formatMonth(month: string) {
  const [year, mon] = month.split('-').map(Number)
  return new Date(year, mon - 1, 1).toLocaleDateString('en-US', { month: 'short' })
}

function SpendingCharts() {
  const [summary, setSummary] = useState<SpendingSummary | null>(null)
  const [trend, setTrend] = useState<SpendingTrendPoint[]>([])

  useEffect(() => {
    api.spendingSummary().then(setSummary).catch(() => {})
    api.spendingTrend(6).then(setTrend).catch(() => {})
  }, [])

  if (!summary || summary.by_category.length === 0) return null

  return (
    <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', margin: '1rem 0' }}>
      <div>
        <h2>This month by category</h2>
        <ResponsiveContainer width={320} height={Math.max(120, summary.by_category.length * 32)}>
          <BarChart data={summary.by_category} layout="vertical" margin={{ left: 16 }}>
            <XAxis type="number" tickFormatter={(v) => formatMoney(v)} tick={{ fontSize: 12, fill: '#888' }} />
            <YAxis
              type="category"
              dataKey="category_name"
              width={120}
              tick={{ fontSize: 12, fill: '#444' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip formatter={(value) => formatMoney(Number(value))} />
            <Bar dataKey="amount" fill={CLAY} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {trend.length > 0 && (
        <div>
          <h2>Last 6 months</h2>
          <ResponsiveContainer width={320} height={180}>
            <BarChart data={trend}>
              <CartesianGrid vertical={false} stroke="#eee" />
              <XAxis dataKey="month" tickFormatter={formatMonth} tick={{ fontSize: 12, fill: '#888' }} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={(v) => formatMoney(v)} tick={{ fontSize: 12, fill: '#888' }} axisLine={false} tickLine={false} width={70} />
              <Tooltip formatter={(value) => formatMoney(Number(value))} labelFormatter={(label) => formatMonth(String(label))} />
              <Bar dataKey="total" fill={CLAY} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [search, setSearch] = useState('')
  const [rememberByRow, setRememberByRow] = useState<Record<number, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [savedRowId, setSavedRowId] = useState<number | null>(null)

  const loadTransactions = useCallback((q: string) => {
    api.transactions(q).then(setTransactions).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    api.categories().then(setCategories).catch((e) => setError(e.message))
    loadTransactions('')
  }, [loadTransactions])

  useEffect(() => {
    const timeout = setTimeout(() => loadTransactions(search), 300)
    return () => clearTimeout(timeout)
  }, [search, loadTransactions])

  async function handleRecategorize(transactionId: number, categoryId: number) {
    setError(null)
    try {
      const remember = rememberByRow[transactionId] ?? true
      const updated = await api.recategorize(transactionId, categoryId, remember)
      setTransactions((prev) => prev.map((t) => (t.id === transactionId ? updated : t)))
      setSavedRowId(transactionId)
      setTimeout(() => setSavedRowId(null), 1500)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div>
      <h1>Transactions</h1>
      {error && <p style={{ color: '#C1584A' }}>{error}</p>}

      <SpendingCharts />

      <input
        placeholder="Search merchant or description…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {transactions.length === 0 ? (
        <p>No transactions yet — connect an account to backfill some.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Merchant</th>
              <th>Account</th>
              <th>Amount</th>
              <th>Category</th>
              <th>Remember?</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((t) => (
              <tr key={t.id}>
                <td>{t.date}</td>
                <td>
                  {t.merchant_name ?? t.description}
                  {t.pending && ' (pending)'}
                </td>
                <td>{t.account_name}</td>
                <td>{formatMoney(t.amount)}</td>
                <td>
                  <select
                    value={t.category_id ?? ''}
                    onChange={(e) => handleRecategorize(t.id, Number(e.target.value))}
                  >
                    <option value="" disabled>
                      Uncategorized
                    </option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  {savedRowId === t.id && ' ✓'}
                </td>
                <td>
                  <input
                    type="checkbox"
                    checked={rememberByRow[t.id] ?? true}
                    onChange={(e) =>
                      setRememberByRow((prev) => ({ ...prev, [t.id]: e.target.checked }))
                    }
                    title="Apply this category to future transactions from this merchant"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
