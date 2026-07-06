import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { ArrowRight } from 'lucide-react'

export default function EditorialHero() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, amount: 0.3 })

  return (
    <section
      ref={ref}
      className="relative min-h-[88vh] flex flex-col justify-center py-20 -mx-6 lg:-mx-10 px-6 lg:px-10"
    >
      <div className="relative z-10 max-w-4xl">
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className="editorial-label mb-8 text-slate-400"
        >
          QUANTITATIVE SCREENER
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 40 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 1.2, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="font-display text-[clamp(3rem,9vw,7rem)] leading-[0.95] tracking-tight text-slate-50"
        >
          Filter
          <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-200 via-slate-200 to-violet-200">
            the worth
          </span>
          keeping
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.9, delay: 0.35 }}
          className="mt-8 max-w-lg text-slate-400 text-base leading-relaxed font-light"
        >
          Quality, valuation, stability and momentum. A data-driven tool for screening and tracking A-shares.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.9, delay: 0.5 }}
          className="mt-10 flex flex-col sm:flex-row items-start sm:items-center gap-5"
        >
          <a
            href="/screener/"
            className="btn-primary inline-flex items-center gap-2 group"
          >
            Open Screener
            <ArrowRight size={16} strokeWidth={1.5} className="group-hover:translate-x-0.5 transition-transform" />
          </a>

          <a
            href="/portfolio/"
            className="text-sm text-slate-400 hover:text-cyan-300 transition-colors duration-300 underline underline-offset-4 decoration-slate-700 hover:decoration-cyan-400/40"
          >
            View Portfolio
          </a>
        </motion.div>
      </div>

      <motion.div
        initial={{ scaleX: 0 }}
        animate={isInView ? { scaleX: 1 } : {}}
        transition={{ duration: 1.4, delay: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="absolute bottom-8 left-6 right-6 lg:left-10 lg:right-10 origin-left"
      >
        <div className="h-px bg-gradient-to-r from-slate-700/50 via-slate-600/30 to-transparent" />
        <div className="flex justify-between items-center mt-4 text-[10px] tracking-[0.2em] uppercase text-slate-600"
        >
          <span>Pizarro ©2026</span>
          <span className="flex items-center gap-2">
            Scroll
            <span className="w-4 h-px bg-cyan-400/40" />
          </span>
        </div>
      </motion.div>
    </section>
  )
}
