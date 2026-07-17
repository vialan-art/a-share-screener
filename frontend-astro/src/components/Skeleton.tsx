import { motion } from 'framer-motion'

interface SkeletonProps {
  className?: string
  lines?: number
  height?: string
}

export function SkeletonLine({ className = '', width = '100%' }: { className?: string; width?: string }) {
  return (
    <div
      className={`h-4 rounded-lg bg-slate-800/60 animate-pulse ${className}`}
      style={{ width }}
    />
  )
}

export function SkeletonCard({ className = '', height = 'h-32' }: { className?: string; height?: string }) {
  return (
    <div className={`glass-card rounded-2xl p-6 ${height} ${className}`}>
      <SkeletonLine width="40%" className="mb-3" />
      <SkeletonLine width="70%" className="mb-2" />
      <SkeletonLine width="55%" />
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 border-b border-slate-800">
        <SkeletonLine width="30%" />
      </div>
      <div className="p-4 space-y-4">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-4">
            {Array.from({ length: cols }).map((_, j) => (
              <SkeletonLine key={j} width={`${100 / cols}%`} className="h-3" />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} height="h-28" />
      ))}
    </div>
  )
}

export default function Skeleton({ lines = 3, height = 'h-40', className = '' }: SkeletonProps) {
  return (
    <div className={`glass-card rounded-2xl p-6 ${height} ${className}`}>
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <SkeletonLine key={i} width={`${85 - i * 15}%`} />
        ))}
      </div>
    </div>
  )
}
