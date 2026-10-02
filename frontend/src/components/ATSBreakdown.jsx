import { Card, Disclosure, Meter, Pill, scoreTone } from './ui.jsx'

/**
 * Component-by-component ATS breakdown.
 *
 * Every row shows points earned, points available, the reason and the literal
 * evidence, so the headline score can be recomputed by hand from this table.
 */
export default function ATSBreakdown({ ats }) {
  return (
    <Card
      title="ATS Score Breakdown"
      subtitle={ats.methodology}
      action={
        <Pill tone="accent">
          {ats.score} / {ats.max_score}
        </Pill>
      }
    >
      <ul className="space-y-2.5">
        {ats.components.map((component) => {
          const tone = scoreTone(component.score, component.max_score)
          const full = component.score === component.max_score
          return (
            <li key={component.id} className="rounded-lg border border-ink-700/60 bg-ink-850/50 p-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-xs font-medium text-slate-200">{component.component}</h3>
                <span className={`shrink-0 text-xs font-semibold tabular-nums ${tone.text}`}>
                  {component.score}
                  <span className="text-slate-600"> / {component.max_score}</span>
                </span>
              </div>
              <Meter value={component.score} max={component.max_score} className="mt-2" />
              <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{component.reason}</p>

              {component.evidence?.length > 0 && (
                <div className="mt-2">
                  <Disclosure summary="Evidence used" count={component.evidence.length}>
                    <ul className="space-y-1">
                      {component.evidence.map((item, i) => (
                        <li key={i} className="flex gap-2 text-[11px] leading-relaxed text-slate-400">
                          <span className="mt-[5px] h-1 w-1 shrink-0 rounded-full bg-accent-400" />
                          <span className="min-w-0">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </Disclosure>
                </div>
              )}

              {!full && component.evidence?.length === 0 && (
                <p className="mt-2 text-[11px] text-slate-600">No evidence found for this component.</p>
              )}
            </li>
          )
        })}
      </ul>

      <div className="mt-5 rounded-lg border border-ink-700/60 bg-ink-850/50 p-4">
        <h3 className="text-sm font-semibold text-slate-100">Where the points went</h3>
        <p className="mt-1 text-xs text-slate-400">
          The headline score is the sum of these ten components — nothing else is added.
        </p>

        {/* Laid out as discrete terms rather than one long run-on line, which
            was unreadable at the previous size. */}
        <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-2">
          {ats.components.map((component, index) => (
            <span key={component.id} className="flex items-center gap-2">
              {index > 0 && <span className="text-sm text-slate-600">+</span>}
              <span className="inline-flex items-baseline gap-1.5 rounded-md border border-ink-600 bg-ink-800 px-2 py-1">
                <span className="text-xs text-slate-300">{component.component}</span>
                <span className="text-sm font-semibold tabular-nums text-slate-100">
                  {component.score}
                </span>
              </span>
            </span>
          ))}
          <span className="text-sm text-slate-500">=</span>
          <span className="inline-flex items-baseline gap-1 rounded-md border border-accent-400/40 bg-accent-500/15 px-2.5 py-1">
            <span className="text-base font-bold tabular-nums text-accent-300">{ats.score}</span>
            <span className="text-xs text-slate-400">/ {ats.max_score}</span>
          </span>
        </div>

        {ats.biggest_opportunities?.length > 0 && (
          <div className="mt-4 border-t border-ink-700/70 pt-3">
            <h4 className="text-xs font-semibold text-slate-200">
              Where you can gain the most
            </h4>
            <ul className="mt-2 space-y-1.5">
              {ats.biggest_opportunities.map((opportunity) => (
                <li key={opportunity.component} className="flex items-center gap-2.5">
                  <Pill tone="warn">+{opportunity.points_available}</Pill>
                  <span className="min-w-0 text-xs text-slate-300">{opportunity.component}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  )
}
