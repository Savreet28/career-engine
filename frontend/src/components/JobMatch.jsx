import { Card, Meter, Pill, SkillChips, scoreTone } from './ui.jsx'

/** How the match score was composed, plus the matched/missing skill sets. */
export default function JobMatch({ match }) {
  return (
    <Card
      title="Job Match Breakdown"
      subtitle={match.methodology}
      action={<Pill tone="accent">{match.score} / {match.max_score}</Pill>}
    >
      <ul className="space-y-2.5">
        {match.components.map((component) => {
          const tone = scoreTone(component.score, component.max_score)
          return (
            <li key={component.id} className="rounded-lg border border-ink-700/60 bg-ink-850/50 p-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-xs font-medium text-slate-200">{component.component}</h3>
                <span className={`shrink-0 text-xs font-semibold tabular-nums ${tone.text}`}>
                  {component.score}<span className="text-slate-600"> / {component.max_score}</span>
                </span>
              </div>
              <Meter value={component.score} max={component.max_score} className="mt-2" />
              <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{component.reason}</p>
            </li>
          )
        })}
      </ul>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-ink-700/60 bg-ink-850/50 p-3">
          <h3 className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-200">
            Core skills
            <Pill tone="neutral">
              {match.core_skills.matched.length}/{match.core_skills.total}
            </Pill>
          </h3>
          <p className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">Matched</p>
          <SkillChips skills={match.core_skills.matched} tone="good" />
          <p className="mt-2.5 mb-1 text-[10px] uppercase tracking-wide text-slate-500">Missing</p>
          <SkillChips skills={match.core_skills.missing} tone="bad" />
        </div>

        <div className="rounded-lg border border-ink-700/60 bg-ink-850/50 p-3">
          <h3 className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-200">
            Preferred skills
            <Pill tone="neutral">
              {match.preferred_skills.matched.length}/{match.preferred_skills.total}
            </Pill>
          </h3>
          <p className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">Matched</p>
          <SkillChips skills={match.preferred_skills.matched} tone="good" />
          <p className="mt-2.5 mb-1 text-[10px] uppercase tracking-wide text-slate-500">Missing</p>
          <SkillChips skills={match.preferred_skills.missing} tone="warn" limit={14} />
        </div>
      </div>

    </Card>
  )
}
