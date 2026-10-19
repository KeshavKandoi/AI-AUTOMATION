import { Link, useLocation } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'

const LINKS = [
  { path: '/', label: 'Home' },
  { path: '/features', label: 'Features' },
  { path: '/how-it-works', label: 'How to use' },
  { path: '/connections', label: 'Integrations' },
]

export default function PillNav() {
  const { pathname } = useLocation()
  const reduceMotion = useReducedMotion()

  return (
    <nav
      aria-label="About WorkForge"
      className="flex max-w-full items-center gap-1 overflow-x-auto rounded-full border border-border bg-surface/75 p-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      {LINKS.map(({ path, label }) => {
        const selected = pathname === path
        return (
          <Link
            key={path}
            to={path}
            aria-current={selected ? 'page' : undefined}
            className={`group relative isolate shrink-0 overflow-hidden rounded-full py-2 pl-6 pr-3.5 font-medium transition-colors sm:pr-4 ${path === '/how-it-works' ? 'text-[11px] sm:text-xs' : 'text-xs sm:text-sm'} ${selected ? 'text-void' : 'text-text-muted hover:text-text-primary'}`}
          >
            {selected && (
              <motion.span
                layoutId="home-pill-active"
                className="absolute inset-0 -z-10 rounded-full bg-signal"
                transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 360, damping: 32 }}
              />
            )}
            {selected && (
              <motion.span
                layoutId="home-pill-dot"
                aria-hidden="true"
                className="absolute left-3 top-1/2 h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-void"
                transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 360, damping: 32 }}
              />
            )}
            {!selected && (
              <motion.span
                aria-hidden="true"
                className="absolute inset-0 -z-10 rounded-full bg-signal-dim"
                initial={{ y: '105%' }}
                whileHover={{ y: 0 }}
                transition={reduceMotion ? { duration: 0 } : { duration: 0.2, ease: 'easeOut' }}
              />
            )}
            <span className="relative block h-5 overflow-hidden leading-5">
              <span className="block transition-transform duration-200 group-hover:-translate-y-5 motion-reduce:transition-none">{label}</span>
              <span aria-hidden="true" className="absolute inset-x-0 top-full transition-transform duration-200 group-hover:-translate-y-5 motion-reduce:transition-none">{label}</span>
            </span>
          </Link>
        )
      })}
    </nav>
  )
}
