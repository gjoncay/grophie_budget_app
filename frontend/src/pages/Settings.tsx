import { useEffect, useState } from 'react'
import { api } from '../api'

type PlaidItem = {
  id: number
  institution_name: string
  status: string
  last_synced_at: string | null
}

export default function Settings() {
  const [items, setItems] = useState<PlaidItem[]>([])

  useEffect(() => {
    api.plaidItems().then(setItems).catch(() => {})
  }, [])

  return (
    <div>
      <h1>Settings</h1>
      <h2>Connected institutions</h2>
      {items.length === 0 ? (
        <p>None yet — connect an account from the Accounts page.</p>
      ) : (
        <ul>
          {items.map((i) => (
            <li key={i.id}>
              {i.institution_name} — {i.status}
              {i.last_synced_at ? ` (last synced ${i.last_synced_at})` : ' (never synced)'}
            </li>
          ))}
        </ul>
      )}
      <p>Manual sync, backup status, and other controls land here in later phases.</p>
    </div>
  )
}
