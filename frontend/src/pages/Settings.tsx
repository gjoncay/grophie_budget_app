import { useEffect, useState } from 'react'
import { api, type BackupStatus, type PlaidItem } from '../api'

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
}

export default function Settings() {
  const [items, setItems] = useState<PlaidItem[]>([])
  const [backupStatus, setBackupStatus] = useState<BackupStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const reload = () => {
    api.plaidItems().then(setItems).catch(() => {})
    api.backupStatus().then(setBackupStatus).catch(() => {})
  }

  useEffect(reload, [])

  async function handleSyncAll() {
    setBusy(true)
    setMessage(null)
    try {
      for (const item of items) {
        await api.syncItem(item.id)
      }
      setMessage('Sync complete.')
      reload()
    } catch (e) {
      setMessage((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function handleBackupNow() {
    setBusy(true)
    setMessage(null)
    try {
      await api.runBackup()
      setMessage('Backup created.')
      reload()
    } catch (e) {
      setMessage((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1>Settings</h1>
      {message && <p className="text-muted">{message}</p>}

      <h2>Connected institutions</h2>
      <div className="card">
        {items.length === 0 ? (
          <p>None yet — connect an account from the Accounts page.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Institution</th>
                <th>Status</th>
                <th>Last synced</th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.id}>
                  <td>{i.institution_name}</td>
                  <td>{i.status}</td>
                  <td>{i.last_synced_at ? formatDate(i.last_synced_at) : 'never'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {items.length > 0 && (
          <button onClick={handleSyncAll} disabled={busy} style={{ marginTop: '0.75rem' }}>
            {busy ? 'Syncing…' : 'Sync all now'}
          </button>
        )}
      </div>

      <h2>Backups</h2>
      <div className="card">
        <p className="text-muted">
          A rolling 30-day local backup runs daily. Copy the backups/ folder somewhere off this
          device periodically — a single laptop is a single point of failure for real financial
          data.
        </p>
        <p>
          Last backup: {backupStatus?.last_backup_at ? formatDate(backupStatus.last_backup_at) : 'never'}
          {' · '}
          {backupStatus?.backups.length ?? 0} kept
        </p>
        <button onClick={handleBackupNow} disabled={busy}>
          {busy ? 'Working…' : 'Back up now'}
        </button>
      </div>
    </div>
  )
}
