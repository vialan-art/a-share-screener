import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface DissolveCardProps {
  children: React.ReactNode
  className?: string
  enableCrows?: boolean
  enableFoam?: boolean
  enableFog?: boolean
  enablePixel?: boolean
}

interface Particle {
  id: number
  x: number
  y: number
  size: number
  delay: number
  duration: number
}

interface Crow {
  id: number
  startX: number
  startY: number
  endX: number
  endY: number
  scale: number
}

function CrowIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
    >
      <path d="M20.5 11c-1.5 0-2.8.8-3.5 2-.4-.8-1.2-1.3-2-1.3-1.1 0-2.1.8-2.3 1.9-.3-.1-.7-.2-1-.2-1.7 0-3 1.3-3 3v.5c-1.1.4-2 1.3-2.4 2.5l-.8-.3c-.3-.1-.6 0-.7.3-.1.3 0 .6.3.7l1.5.6c.2.1.4 0 .6-.1.5-.9 1.3-1.6 2.3-2 .3-.1.4-.4.4-.7 0-1.1.9-2 2-2 .3 0 .6.1.9.2.3.1.6 0 .7-.2.2-.8.9-1.4 1.7-1.4.7 0 1.3.4 1.6 1 .1.3.5.4.8.3.7-.3 1.4-.4 2.1-.4 1.1 0 2.1.3 3 1 .2.2.5.2.7 0 .2-.2.2-.5 0-.7-.5-.5-1.1-.9-1.7-1.1.4-.7 1.1-1.1 1.9-1.1.3 0 .5-.2.5-.5s-.2-.5-.5-.5z" />
    </svg>
  )
}

export default function DissolveCard({
  children,
  className = '',
  enableCrows = true,
  enableFoam = true,
  enableFog = true,
  enablePixel = true,
}: DissolveCardProps) {
  const [particles, setParticles] = useState<Particle[]>([])
  const [crows, setCrows] = useState<Crow[]>([])
  const [fogKey, setFogKey] = useState(0)
  const [pixelKey, setPixelKey] = useState(0)
  const cardRef = useRef<HTMLDivElement>(null)
  const idCounter = useRef(0)

  const spawnEffects = useCallback(() => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()

    if (enableFoam) {
      const newParticles: Particle[] = Array.from({ length: 7 }, (_, i) => ({
        id: idCounter.current++,
        x: 15 + Math.random() * 70,
        y: 70 + Math.random() * 25,
        size: 3 + Math.random() * 8,
        delay: i * 0.05,
        duration: 0.8 + Math.random() * 0.5,
      }))
      setParticles(newParticles)
      setTimeout(() => setParticles([]), 1600)
    }

    if (enableCrows) {
      const newCrows: Crow[] = Array.from({ length: 2 + Math.floor(Math.random() * 2) }, (_, i) => {
        const side = Math.random() > 0.5 ? 'left' : 'right'
        return {
          id: idCounter.current++,
          startX: side === 'left' ? 5 + Math.random() * 15 : 80 + Math.random() * 10,
          startY: 10 + Math.random() * 40,
          endX: side === 'left' ? 50 + Math.random() * 30 : 20 + Math.random() * 20,
          endY: -30 - Math.random() * 20,
          scale: 0.6 + Math.random() * 0.4,
        }
      })
      setCrows(newCrows)
      setTimeout(() => setCrows([]), 1200)
    }

    if (enableFog) {
      setFogKey((k) => k + 1)
    }

    if (enablePixel) {
      setPixelKey((k) => k + 1)
    }
  }, [enableCrows, enableFoam, enableFog, enablePixel])

  return (
    <div
      ref={cardRef}
      className={`relative overflow-hidden ${className}`}
      onMouseLeave={spawnEffects}
    >
      {children}

      <AnimatePresence>
        {particles.map((p) => (
          <motion.div
            key={p.id}
            className="absolute rounded-full pointer-events-none"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
              background: 'radial-gradient(circle at 30% 30%, rgba(255,255,255,0.7), rgba(92, 225, 230, 0.25) 45%, transparent 75%)',
              boxShadow: 'inset 0 0 5px rgba(255,255,255,0.4)',
            }}
            initial={{ opacity: 0, y: 8, scale: 0.8 }}
            animate={{
              opacity: [0, 0.6, 0],
              y: [0, -18 - Math.random() * 12, -40 - Math.random() * 20],
              scale: [0.8, 1.1, 1.4],
            }}
            exit={{ opacity: 0 }}
            transition={{
              duration: p.duration,
              delay: p.delay,
              ease: [0.22, 1, 0.36, 1],
            }}
          />
        ))}
      </AnimatePresence>

      <AnimatePresence>
        {crows.map((crow) => (
          <motion.div
            key={crow.id}
            className="absolute pointer-events-none text-slate-300/40"
            style={{
              left: `${crow.startX}%`,
              top: `${crow.startY}%`,
              width: 24 * crow.scale,
              height: 24 * crow.scale,
            }}
            initial={{ opacity: 0, x: 0, y: 0, rotate: 0 }}
            animate={{
              opacity: [0, 0.7, 0],
              x: crow.endX - crow.startX,
              y: crow.endY,
              rotate: crow.endX > 0 ? 15 : -15,
            }}
            exit={{ opacity: 0 }}
            transition={{
              duration: 1,
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            <CrowIcon className="w-full h-full" />
          </motion.div>
        ))}
      </AnimatePresence>

      {enableFog && (
        <motion.div
          key={fogKey}
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'linear-gradient(to top, rgba(200, 200, 215, 0.12) 0%, rgba(200, 200, 215, 0.04) 40%, transparent 100%)',
            filter: 'blur(24px)',
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.8, 0] }}
          transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
        />
      )}

      {enablePixel && (
        <motion.div
          key={pixelKey}
          className="absolute inset-0 pointer-events-none bg-slate-950/10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
            `,
            backgroundSize: '8px 8px',
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.4, 0] }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        />
      )}
    </div>
  )
}
