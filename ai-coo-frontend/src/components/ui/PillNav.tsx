import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

const LINKS = [
  { id: 'features', label: 'Features' },
  { id: 'how-it-works', label: 'How it works' },
  { id: 'google-data', label: 'Google data use' },
]

export default function PillNav() {
  const [active, setActive] = useState(LINKS[0].id)
  const reduceMotion = useReducedMotion()

  useEffect(() => {
    const sections = LINKS.map(({ id }) => document.getElementById(id)).filter(
      (section): section is HTMLElement => section !== null,
    )
    if (!sections.length) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
        if (visible) setActive(visible.target.id)
      },
      { rootMargin: '-20% 0px -65% 0px', threshold: [0, 0.2, 0.5, 0.8] },
    )

    sections.forEach((section) => observer.observe(section))
    return () => observer.disconnect()
  }, [])

  return (
    <nav
      aria-label="Homepage sections"
      className="flex max-w-full items-center gap-1 overflow-x-auto rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/75 p-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      {LINKS.map(({ id, label }) => {
        const selected = active === id
        return (
          <a
            key={id}
            href={`#${id}`}
            aria-current={selected ? 'location' : undefined}
            onClick={() => setActive(id)}
            className={`group relative isolate shrink-0 overflow-hidden rounded-full py-2 pl-6 pr-3.5 text-xs font-medium transition-colors sm:pr-4 sm:text-sm ${selected ? 'text-[var(--color-void)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'}`}
          >
            {selected && (
              <motion.span
                layoutId="home-pill-active"
                className="absolute inset-0 -z-10 rounded-full bg-[var(--color-signal)]"
                transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 360, damping: 32 }}
              />
            )}
            {selected && (
              <motion.span
                layoutId="home-pill-dot"
                aria-hidden="true"
                className="absolute left-3 top-1/2 h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-[var(--color-void)]"
                transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 360, damping: 32 }}
              />
            )}
            {!selected && (
              <motion.span
                aria-hidden="true"
                className="absolute inset-0 -z-10 rounded-full bg-[var(--color-signal-dim)]"
                initial={{ y: '105%' }}
                whileHover={{ y: 0 }}
                transition={reduceMotion ? { duration: 0 } : { duration: 0.2, ease: 'easeOut' }}
              />
            )}
            <span className="relative block h-5 overflow-hidden leading-5">
              <span className="block transition-transform duration-200 group-hover:-translate-y-5 motion-reduce:transition-none">{label}</span>
              <span aria-hidden="true" className="absolute inset-x-0 top-full transition-transform duration-200 group-hover:-translate-y-5 motion-reduce:transition-none">{label}</span>
            </span>
          </a>
        )
      })}
    </nav>
  )
}
