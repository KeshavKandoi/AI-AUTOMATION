interface LegalSectionProps {
  number: string
  title: string
  children: React.ReactNode
}

export default function LegalSection({ number, title, children }: LegalSectionProps) {
  return (
    <section>
      <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold text-[var(--color-text-primary)] mb-3">
        {number}. {title}
      </h2>
      <div className="flex flex-col gap-3">{children}</div>
    </section>
  )
}
