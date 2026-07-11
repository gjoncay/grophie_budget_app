import { useCallback, useEffect, useState } from 'react'
import { api, type Category, type Transaction } from '../api'

function formatMoney(amount: number) {
  const sign = amount < 0 ? '+' : ''
  return sign + Math.abs(amount).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
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
      <input
        placeholder="Search merchant or description…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {error && <p style={{ color: '#C1584A' }}>{error}</p>}

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
