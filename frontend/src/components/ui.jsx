/**
 * ui.jsx
 * ======
 * Small presentational primitives shared across the dashboard. Keeping them in
 * one place is what makes every panel look like part of the same product.
 */

/** Standard panel: heading, optional subtitle/action, bordered body. */
export function Card({ title, subtitle, action, children, className = '' }) {
  return (
    <section
      className={`rounded-xl border border-ink-700/70 bg-ink-900/70 backdrop-blur-sm shadow-lg shadow-black/20 ${className}`}
    >
      {(title || action) && (
        <header className="flex items-start justify-between gap-4 border-b border-ink-700/70 px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold tracking-wide text-slate-100">{title}</h2>}
            {subtitle && <p className="mt-1 text-xs leading-relaxed text-slate-400">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="px-5 py-4">{children}</div>
    </section>
  )
}

/** Colour scale used everywhere a score is shown, so colour means one thing. */
export function scoreTone(value, max = 100) {
  const pct = max ? (value / max) * 100 : 0
  if (pct >= 80) return { text: 'text-good-400', bg: 'bg-good-400', ring: 'stroke-good-400', label: 'strong' }
  if (pct >= 60) return { text: 'text-accent-300', bg: 'bg-accent-400', ring: 'stroke-accent-400', label: 'good' }
  if (pct >= 40) return { text: 'text-warn-400', bg: 'bg-warn-400', ring: 'stroke-warn-400', label: 'moderate' }
  return { text: 'text-bad-400', bg: 'bg-bad-400', ring: 'stroke-bad-400', label: 'weak' }
}

/** Horizontal progress bar with an accessible value. */
export function Meter({ value, max, tone, className = '' }) {
  const pct = max ? Math.max(0, Math.min(100, (value / max) * 100)) : 0
  const colour = tone || scoreTone(value, max).bg
  return (
    <div
      className={`h-1.5 w-full overflow-hidden rounded-full bg-ink-700 ${className}`}
      role="meter"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
    >
      <div className={`h-full rounded-full ${colour} transition-[width] duration-500`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function Pill({ children, tone = 'neutral', title }) {
  const tones = {
    neutral: 'border-ink-600 bg-ink-800 text-slate-300',
    good: 'border-good-400/40 bg-good-400/10 text-good-400',
    warn: 'border-warn-400/40 bg-warn-400/10 text-warn-400',
    bad: 'border-bad-400/40 bg-bad-400/10 text-bad-400',
    accent: 'border-accent-400/40 bg-accent-400/10 text-accent-300',
  }
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

/** Labels which evidence source backs a skill: resume, GitHub, or both. */
export function SourceBadge({ source }) {
  const map = {
    resume: { label: 'Resume', tone: 'accent' },
    github: { label: 'GitHub', tone: 'good' },
  }
  const item = map[source] || { label: source, tone: 'neutral' }
  return <Pill tone={item.tone}>{item.label}</Pill>
}

export function EmptyState({ children }) {
  return <p className="py-4 text-center text-xs text-slate-500">{children}</p>
}

/** Definition-list row used by the insight panels. */
export function Field({ label, value, mono = false }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-ink-800 py-1.5 last:border-0">
      <dt className="shrink-0 text-xs text-slate-400">{label}</dt>
      <dd className={`min-w-0 truncate text-right text-xs text-slate-200 ${mono ? 'font-mono' : ''}`}>
        {value || <span className="text-slate-600">not detected</span>}
      </dd>
    </div>
  )
}

/** Collapsible block, used for long evidence lists. */
export function Disclosure({ summary, children, count }) {
  return (
    <details className="group rounded-lg border border-ink-700/70 bg-ink-850/60 open:bg-ink-850">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-xs font-medium text-slate-300 hover:text-slate-100">
        <span>{summary}</span>
        <span className="flex items-center gap-2">
          {count !== undefined && <span className="text-slate-500">{count}</span>}
          <svg className="h-3.5 w-3.5 transition-transform group-open:rotate-180" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
          </svg>
        </span>
      </summary>
      <div className="border-t border-ink-700/70 px-3 py-2.5">{children}</div>
    </details>
  )
}

export function SkillChips({ skills, tone = 'neutral', limit }) {
  if (!skills?.length) return <EmptyState>None</EmptyState>
  const shown = limit ? skills.slice(0, limit) : skills
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((s) => (
        <Pill key={s} tone={tone}>{s}</Pill>
      ))}
      {limit && skills.length > limit && (
        <Pill tone="neutral">+{skills.length - limit} more</Pill>
      )}
    </div>
  )
}
