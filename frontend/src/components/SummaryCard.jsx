import { Card, Pill } from './ui.jsx'

/**
 * The scannable summary of an analysis.
 *
 * Three short sections of one-line bullets, assembled by fixed rules in the
 * backend from scores that were already computed. Nothing here is written by a
 * language model, so the wording is deterministic and traceable.
 */
export default function SummaryCard({ summary }) {
  return (
    <Card
      title="Summary"
      subtitle="The short version of everything below."
      action={<Pill tone="neutral" title={summary.note}>Rule-based</Pill>}
    >
      <div className="space-y-5">
        {summary.sections.map((section) => (
          <section key={section.id}>
            <h3 className="text-sm font-semibold text-slate-100">{section.title}</h3>

            {section.ordered ? (
              <ol className="mt-2 space-y-2">
                {section.bullets.map((bullet, index) => (
                  <li key={index} className="flex gap-2.5">
                    <span className="mt-px grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full bg-accent-500/20 text-[10px] font-semibold text-accent-300">
                      {index + 1}
                    </span>
                    <span className="min-w-0 text-xs leading-relaxed text-slate-300">
                      {bullet}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <ul className="mt-2 space-y-1.5">
                {section.bullets.map((bullet, index) => (
                  <li key={index} className="flex gap-2.5">
                    <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-accent-400" />
                    <span className="min-w-0 text-xs leading-relaxed text-slate-300">
                      {bullet}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>

      <p className="mt-5 border-t border-ink-800 pt-3 text-[11px] leading-relaxed text-slate-500">
        {summary.note}
      </p>
    </Card>
  )
}
