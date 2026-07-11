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

export type Holding = {
  account_id: number
  account_name: string
  security_id: number
  ticker_symbol: string | null
  name: string | null
  security_type: string | null
  quantity: number
  cost_basis: number | null
  value: number | null
  gain_loss: number | null
  gain_loss_pct: number | null
  as_of: string
}

export type Performance = {
  allocation: Record<string, number>
  total_value: number
  total_cost_basis: number
  total_gain_loss: number | null
}

export type InvestmentTransaction = {
  id: number
  account_id: number
  account_name: string
  security_name: string | null
  ticker_symbol: string | null
  date: string
  type: string
  quantity: number | null
  price: number | null
  amount: number
  name: string | null
}

export type SpendingSummary = {
  month: string
  total_spending: number
  by_category: { category_id: number | null; category_name: string; amount: number }[]
}

export type SpendingTrendPoint = { month: string; total: number }

export type BudgetTarget = {
  id: number
  category_id: number
  category_name: string
  month: string | null
  target_amount: number
  active: boolean
}

export type BudgetProgress = {
  id: number
  category_id: number
  category_name: string
  target_amount: number
  actual_amount: number
  pct_used: number | null
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
  holdings: () => request<Holding[]>('/api/investments/holdings'),
  performance: () => request<Performance>('/api/investments/performance'),
  investmentTransactions: () => request<InvestmentTransaction[]>('/api/investments/transactions'),
  spendingSummary: (month?: string) =>
    request<SpendingSummary>(`/api/spending/summary${month ? `?month=${month}` : ''}`),
  spendingTrend: (months = 6) => request<SpendingTrendPoint[]>(`/api/spending/trend?months=${months}`),
  budgetTargets: () => request<BudgetTarget[]>('/api/budget-targets'),
  createBudgetTarget: (category_id: number, target_amount: number) =>
    request<BudgetTarget>('/api/budget-targets', {
      method: 'POST',
      body: JSON.stringify({ category_id, target_amount }),
    }),
  updateBudgetTarget: (id: number, target_amount: number) =>
    request<BudgetTarget>(`/api/budget-targets/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ target_amount }),
    }),
  budgetProgress: (month?: string) =>
    request<BudgetProgress[]>(`/api/budget-targets/progress${month ? `?month=${month}` : ''}`),
}
