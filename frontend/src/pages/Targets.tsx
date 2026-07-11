import { useEffect, useState } from 'react'
import { api, type BudgetProgress, type Category } from '../api'

function formatMoney(amount: number) {
  return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export default function Targets() {
  const [progress, setProgress] = useState<BudgetProgress[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [categoryId, setCategoryId] = useState<number | ''>('')
  const [amount, setAmount] = useState('')
  const [error, setError] = useState<string | null>(null)

  const reload = () => {
    api.budgetProgress().then(setProgress).catch((e) => setError(e.message))
  }

  useEffect(() => {
    api.categories().then(setCategories).catch((e) => setError(e.message))
    reload()
  }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!categoryId || !amount) return
    setError(null)
    try {
      await api.createBudgetTarget(Number(categoryId), Number(amount))
      setCategoryId('')
      setAmount('')
      reload()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <div>
      <h1>Budget Targets</h1>
      <p>Optional per-category monthly targets — actual vs. target, not full envelope budgeting.</p>
      {error && <p style={{ color: '#C1584A' }}>{error}</p>}

      {progress.length === 0 ? (
        <p>No targets set yet.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxWidth: 480 }}>
          {progress.map((p) => {
            const pct = Math.min(p.pct_used ?? 0, 1)
            const over = (p.pct_used ?? 0) > 1
            return (
              <div key={p.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>{p.category_name}</span>
                  <span>
                    {formatMoney(p.actual_amount)} / {formatMoney(p.target_amount)}
                  </span>
                </div>
                <div style={{ background: '#eee', borderRadius: 999, height: 8 }}>
                  <div
                    style={{
                      background: over ? '#C1584A' : '#6B8F71',
                      width: `${pct * 100}%`,
                      height: 8,
                      borderRadius: 999,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}

      <h2>Add a target</h2>
      <form onSubmit={handleCreate} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <select value={categoryId} onChange={(e) => setCategoryId(Number(e.target.value))}>
          <option value="">Select category…</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Monthly target"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <button type="submit">Add</button>
      </form>
    </div>
  )
}
