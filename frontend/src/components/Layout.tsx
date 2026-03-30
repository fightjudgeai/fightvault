import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  CalendarDays,
  Users,
  Swords,
  FileText,
  Download,
  Menu,
  X,
  ChevronDown,
} from 'lucide-react'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/events', label: 'Events', icon: CalendarDays },
  { to: '/fighters', label: 'Fighters', icon: Users },
  { to: '/matchmaking', label: 'Matchmaking', icon: Swords },
  { to: '/reports', label: 'Intel Reports', icon: FileText },
  { to: '/exports', label: 'Media Exports', icon: Download },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 flex w-60 flex-col bg-card border-r border-border transition-transform duration-200 lg:static lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-14 px-5 border-b border-border shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded bg-accent flex items-center justify-center shrink-0">
              <span className="text-black text-xs font-bold leading-none">FJ</span>
            </div>
            <div>
              <p className="text-text-primary text-sm font-semibold leading-none">
                Fight Judge AI
              </p>
              <p className="text-text-muted text-[10px] mt-0.5 leading-none tracking-wide uppercase">
                PromoterOS
              </p>
            </div>
          </div>
          <button
            className="lg:hidden text-text-muted hover:text-text-primary"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={16} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors relative group',
                  isActive
                    ? 'text-text-primary bg-surface font-medium'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface',
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent rounded-r" />
                  )}
                  <Icon
                    size={16}
                    className={clsx(
                      'shrink-0',
                      isActive ? 'text-accent' : 'text-text-muted group-hover:text-text-secondary',
                    )}
                  />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border shrink-0">
          <p className="text-text-muted text-[10px] uppercase tracking-wider">
            v0.1.0 — Beta
          </p>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-14 flex items-center justify-between px-5 border-b border-border bg-card shrink-0">
          <button
            className="lg:hidden text-text-muted hover:text-text-primary"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>

          <div className="hidden lg:block">
            <p className="text-text-muted text-sm">
              <span className="text-text-secondary font-medium">PromoterOS</span>
            </p>
          </div>

          {/* User menu placeholder */}
          <button className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors">
            <div className="w-7 h-7 rounded-full bg-zinc-700 flex items-center justify-center text-xs font-medium text-text-primary">
              P
            </div>
            <span className="hidden sm:block">Promoter</span>
            <ChevronDown size={14} />
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-5 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
