import { useEffect, useRef } from 'react'

interface SplashParticle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  life: number
  maxLife: number
  color: string
}

const COLORS = ['#ff1680', '#9b5cff', '#38e0d9']

export default function SplashCursor() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d', { alpha: true })
    const finePointer = window.matchMedia('(pointer: fine)').matches
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (!canvas || !context || !finePointer || reducedMotion) return

    const particles: SplashParticle[] = []
    const maxParticles = 100
    let frameId = 0
    let width = 0
    let height = 0
    let lastX = 0
    let lastY = 0
    let hueIndex = 0

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5)
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = Math.round(width * ratio)
      canvas.height = Math.round(height * ratio)
      context.setTransform(ratio, 0, 0, ratio, 0, 0)
    }

    const addParticle = (x: number, y: number, speedX: number, speedY: number, burst = false) => {
      const angle = Math.random() * Math.PI * 2
      const speed = burst ? 0.8 + Math.random() * 4 : 0.2 + Math.random() * 1.1
      const life = burst ? 34 + Math.random() * 24 : 22 + Math.random() * 18

      particles.push({
        x: x + (Math.random() - 0.5) * (burst ? 10 : 4),
        y: y + (Math.random() - 0.5) * (burst ? 10 : 4),
        vx: Math.cos(angle) * speed + speedX * 0.08,
        vy: Math.sin(angle) * speed + speedY * 0.08,
        radius: burst ? 2 + Math.random() * 6 : 2 + Math.random() * 4,
        life,
        maxLife: life,
        color: COLORS[(hueIndex + Math.floor(Math.random() * COLORS.length)) % COLORS.length],
      })

      if (particles.length > maxParticles) particles.splice(0, particles.length - maxParticles)
    }

    const draw = () => {
      frameId = 0
      context.clearRect(0, 0, width, height)
      context.globalCompositeOperation = 'lighter'

      for (let index = particles.length - 1; index >= 0; index -= 1) {
        const particle = particles[index]
        particle.x += particle.vx
        particle.y += particle.vy
        particle.vx *= 0.965
        particle.vy *= 0.965
        particle.life -= 1

        if (particle.life <= 0) {
          particles.splice(index, 1)
          continue
        }

        const fade = particle.life / particle.maxLife
        const radius = particle.radius * (0.55 + fade * 0.65)
        const glow = context.createRadialGradient(particle.x, particle.y, 0, particle.x, particle.y, radius * 3)
        glow.addColorStop(0, `${particle.color}${Math.round(fade * 190).toString(16).padStart(2, '0')}`)
        glow.addColorStop(0.45, `${particle.color}${Math.round(fade * 75).toString(16).padStart(2, '0')}`)
        glow.addColorStop(1, `${particle.color}00`)
        context.fillStyle = glow
        context.beginPath()
        context.arc(particle.x, particle.y, radius * 3, 0, Math.PI * 2)
        context.fill()
      }

      context.globalCompositeOperation = 'source-over'
      if (particles.length) frameId = window.requestAnimationFrame(draw)
    }

    const startAnimation = () => {
      if (!frameId) frameId = window.requestAnimationFrame(draw)
    }

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType === 'touch') return
      const deltaX = event.clientX - lastX
      const deltaY = event.clientY - lastY
      lastX = event.clientX
      lastY = event.clientY

      if (Math.abs(deltaX) + Math.abs(deltaY) > 1) {
        hueIndex = (hueIndex + 1) % COLORS.length
        addParticle(event.clientX, event.clientY, deltaX, deltaY)
        if (Math.random() > 0.45) addParticle(event.clientX, event.clientY, deltaX, deltaY)
        startAnimation()
      }
    }

    const onPointerDown = (event: PointerEvent) => {
      if (event.pointerType === 'touch' || event.button !== 0) return
      for (let index = 0; index < 18; index += 1) {
        addParticle(event.clientX, event.clientY, 0, 0, true)
      }
      startAnimation()
    }

    const onVisibilityChange = () => {
      if (document.hidden) {
        if (frameId) window.cancelAnimationFrame(frameId)
        frameId = 0
      } else if (particles.length) {
        startAnimation()
      }
    }

    resize()
    window.addEventListener('resize', resize, { passive: true })
    window.addEventListener('pointermove', onPointerMove, { passive: true })
    window.addEventListener('pointerdown', onPointerDown, { passive: true })
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      if (frameId) window.cancelAnimationFrame(frameId)
      window.removeEventListener('resize', resize)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [])

  return <canvas ref={canvasRef} aria-hidden="true" className="pointer-events-none fixed inset-0 z-40 h-full w-full mix-blend-screen" />
}
