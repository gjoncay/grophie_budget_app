import { useCallback, useEffect, useState } from 'react'
import { usePlaidLink } from 'react-plaid-link'
import { api, type Account } from '../api'

function formatMoney(amount: number | null) {
  if (amount === null) return '—'
  return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [linkToken, setLinkToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const loadAccounts = useCallback(() => {
    api.accounts().then(setAccounts).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    loadAccounts()
  }, [loadAccounts])

  const { open, ready } = usePlaidLink({
    token: linkToken,
    onSuccess: async (public_token) => {
      setLoading(true)
      try {
        await api.exchangePublicToken(public_token)
        loadAccounts()
      } catch (e) {
        setError((e as Error).message)
      } finally {
        setLoading(false)
        setLinkToken(null)
      }
    },
    onExit: () => setLinkToken(null),
  })

  useEffect(() => {
    if (linkToken && ready) open()
  }, [linkToken, ready, open])

  async function startConnect() {
    setError(null)
    setLoading(true)
    try {
      const { link_token } = await api.createLinkToken()
      setLinkToken(link_token)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Accounts</h1>
      <button onClick={startConnect} disabled={loading}>
        {loading ? 'Connecting…' : 'Connect an account'}
      </button>
      {error && <p className="text-negative">{error}</p>}

      {accounts.length === 0 ? (
        <p>No accounts connected yet.</p>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Institution</th>
                <th>Account</th>
                <th>Type</th>
                <th>Balance</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((a) => (
                <tr key={a.id}>
                  <td>{a.institution_name}</td>
                  <td>
                    {a.name} {a.mask && `••${a.mask}`}
                  </td>
                  <td>{a.subtype ?? a.type}</td>
                  <td>{formatMoney(a.current_balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
