import { NavLink, Route, Routes } from 'react-router-dom'
import './App.css'
import Accounts from './pages/Accounts'
import Dashboard from './pages/Dashboard'
import Investments from './pages/Investments'
import Settings from './pages/Settings'
import Transactions from './pages/Transactions'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/accounts', label: 'Accounts' },
  { to: '/investments', label: 'Investments' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/settings', label: 'Settings' },
]

function App() {
  return (
    <div className="shell">
      <nav className="nav">
        <span className="brand">Hearth</span>
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/investments" element={<Investments />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
