import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronsLeft, LogOut } from 'lucide-react'
import { navItems } from '@/lib/navigation'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 248 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="h-screen shrink-0 border-r border-[var(--color-border)] bg-[var(--color-surface)]/40 backdrop-blur-xl flex flex-col"
    >
      <div className="flex items-center gap-2 px-4 h-16 border-b border-[var(--color-border)] shrink-0">
        <div className="h-2 w-2 rounded-full bg-[var(--color-signal)] animate-pulse-signal shrink-0" />
        {!collapsed && (
          <span className="font-[family-name:var(--font-display)] text-sm font-semibold text-[var(--color-text-primary)] truncate">
            AI COO
          </span>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-3 px-2 flex flex-col gap-0.5">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                'group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-[var(--color-signal-dim)] text-[var(--color-signal)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)]'
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-[var(--color-signal)]" />
                )}
                <item.icon size={17} className="shrink-0" />
                {!collapsed && (
                  <span className="truncate flex-1">{item.label}</span>
                )}
                {!collapsed && item.comingSoon && (
                  <span className="text-[9px] uppercase tracking-wide text-[var(--color-text-faint)] border border-[var(--color-border)] rounded px-1 py-0.5 shrink-0">
                    Soon
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-[var(--color-border)] p-3 flex flex-col gap-2">
        {!collapsed && user && (
          <div className="px-1.5 flex items-center gap-2 min-w-0">
            <div className="h-7 w-7 rounded-full bg-[var(--color-signal-dim)] text-[var(--color-signal)] flex items-center justify-center text-xs font-medium shrink-0">
              {user.full_name?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-xs text-[var(--color-text-primary)] truncate">{user.full_name}</p>
              <p className="text-[11px] text-[var(--color-text-faint)] truncate">{user.organization_name}</p>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-alert)] hover:bg-[var(--color-alert-dim)] transition-colors"
        >
          <LogOut size={16} className="shrink-0" />
          {!collapsed && 'Sign out'}
        </button>
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-[var(--color-text-faint)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] transition-colors"
        >
          <ChevronsLeft size={16} className={cn('shrink-0 transition-transform', collapsed && 'rotate-180')} />
          {!collapsed && 'Collapse'}
        </button>
      </div>
    </motion.aside>
  )
}
