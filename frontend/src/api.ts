export type Account = {
  id: number
  name: string
  official_name: string | null
  type: string
  subtype: string | null
  mask: string | null
  current_balance: number | null
  available_balance: number | null
  currency: string
  institution_name: string
}

type PlaidItem = {
  id: number
  institution_name: string
  status: string
  last_synced_at: string | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request to ${path} failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  accounts: () => request<Account[]>('/api/accounts'),
  plaidItems: () => request<PlaidItem[]>('/api/plaid/items'),
  createLinkToken: () =>
    request<{ link_token: string }>('/api/plaid/link-token', { method: 'POST' }),
  exchangePublicToken: (public_token: string) =>
    request<{ item_id: number; institution_name: string; accounts_added: number }>(
      '/api/plaid/exchange',
      { method: 'POST', body: JSON.stringify({ public_token }) },
    ),
  removeItem: (itemId: number) =>
    request<{ ok: boolean }>(`/api/plaid/items/${itemId}`, { method: 'DELETE' }),
}
