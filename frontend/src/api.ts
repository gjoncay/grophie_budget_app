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

export type Category = {
  id: number
  name: string
  group: string | null
  parent_category_id: number | null
  is_custom: boolean
}

export type Transaction = {
  id: number
  account_id: number
  account_name: string
  date: string
  amount: number
  merchant_name: string | null
  description: string | null
  category_id: number | null
  category_name: string | null
  pending: boolean
  is_manually_recategorized: boolean
}

export type NetWorthPoint = {
  date: string
  net_worth: number
  total_assets: number
  total_liabilities: number
}

export type AccountsSummary = {
  net_worth: number
  total_assets: number
  total_liabilities: number
  as_of: string | null
  accounts: Account[]
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
  categories: () => request<Category[]>('/api/categories'),
  transactions: (search?: string) =>
    request<Transaction[]>(`/api/transactions${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  recategorize: (transactionId: number, category_id: number, apply_to_future: boolean) =>
    request<Transaction & { rule_created: boolean }>(`/api/transactions/${transactionId}`, {
      method: 'PATCH',
      body: JSON.stringify({ category_id, apply_to_future }),
    }),
  netWorthHistory: () => request<NetWorthPoint[]>('/api/networth/history'),
  accountsSummary: () => request<AccountsSummary>('/api/accounts/summary'),
  insight: () => request<{ message: string }>('/api/insights'),
}
