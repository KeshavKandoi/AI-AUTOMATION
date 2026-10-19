import { useState } from 'react'
import type { CSSProperties, MouseEvent, ReactNode } from 'react'

export default function MagicBentoTile({ children, className = '' }: { children: ReactNode; className?: string }) {
  const [ripple, setRipple] = useState<{ x: number; y: number; key: number } | null>(null)

  function move(event: MouseEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    event.currentTarget.style.setProperty('--bento-x', `${event.clientX - bounds.left}px`)
    event.currentTarget.style.setProperty('--bento-y', `${event.clientY - bounds.top}px`)
  }

  function click(event: MouseEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    setRipple({ x: event.clientX - bounds.left, y: event.clientY - bounds.top, key: Date.now() })
  }

  return (
    <div className={`magic-bento-tile ${className}`} onMouseMove={move} onClick={click}>
      {children}
      {ripple && <span key={ripple.key} className="magic-bento-ripple" style={{ '--ripple-x': `${ripple.x}px`, '--ripple-y': `${ripple.y}px` } as CSSProperties} aria-hidden="true" />}
    </div>
  )
}
