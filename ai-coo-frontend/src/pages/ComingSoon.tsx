import { motion } from 'framer-motion'
import { Construction } from 'lucide-react'

export default function ComingSoon({ title }: { title: string }) {
  return (
    <div className="h-full flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-center max-w-sm"
      >
        <div className="mx-auto mb-4 h-12 w-12 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center">
          <Construction size={20} className="text-[var(--color-text-faint)]" />
        </div>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--color-text-primary)]">
          {title}
        </h2>
        <p className="mt-1.5 text-sm text-[var(--color-text-muted)]">
          This connects once the backend endpoint exists. The UI shell is ready.
        </p>
      </motion.div>
    </div>
  )
}
