export default function PageLoading() {
  return (
    <div role="status" aria-label="Loading page" className="mx-auto max-w-7xl p-5 md:p-8 animate-pulse motion-reduce:animate-none">
      <div className="mb-7 space-y-3">
        <div className="h-7 w-44 rounded-lg bg-[var(--color-surface-hover)]" />
        <div className="h-4 w-64 max-w-full rounded bg-[var(--color-surface-hover)]" />
      </div>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="h-28 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60" />
        ))}
      </div>
      <div className="h-72 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/60" />
    </div>
  )
}
