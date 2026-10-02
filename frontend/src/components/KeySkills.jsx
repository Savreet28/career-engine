import { Card, Pill, SourceBadge } from './ui.jsx'

const MAX_PER_LIST = 5

/**
 * The overview's condensed skill view.
 *
 * The full skill-by-skill table lives under the Job Match tab. Here we show
 * only what a student would act on first: the core requirements they are
 * missing, and the core requirements they can most strongly evidence.
 */
export default function KeySkills({ match }) {
  const rows = match.skill_breakdown

  // Gaps: core requirements with no evidence. Rank by how strongly the job
  // descriptions asked for them, so the top of the list is the most demanded.
  const gaps = rows
    .filter((r) => r.required && !r.matched)
    .sort((a, b) => (b.retrieval_similarity ?? 0) - (a.retrieval_similarity ?? 0))
    .slice(0, MAX_PER_LIST)

  // Strengths: core requirements that are evidenced. A skill backed by both
  // the resume and GitHub is stronger than one backed by the resume alone.
  const strengths = rows
    .filter((r) => r.required && r.matched)
    .sort((a, b) => {
      const weight = (r) => r.sources.length
      return weight(b) - weight(a) ||
        (b.retrieval_similarity ?? 0) - (a.retrieval_similarity ?? 0)
    })
    .slice(0, MAX_PER_LIST)

  return (
    <Card
      title="Key skills for this role"
      subtitle="The few that matter most, drawn from the role's core requirements."
      action={
        <Pill tone="neutral">
          {match.core_skills.matched.length}/{match.core_skills.total} core
        </Pill>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <SkillColumn
          title="Focus on these first"
          caption="Core requirements with no evidence in your resume or on GitHub."
          rows={gaps}
          tone="bad"
          empty="Every core requirement is evidenced. Nothing critical is missing."
        />
        <SkillColumn
          title="Your strongest matches"
          caption="Core requirements you can already evidence."
          rows={strengths}
          tone="good"
          empty="No core requirements are evidenced yet."
        />
      </div>
    </Card>
  )
}

function SkillColumn({ title, caption, rows, tone, empty }) {
  return (
    <div className="rounded-lg border border-ink-700/60 bg-ink-850/50 p-3">
      <h3 className="text-xs font-medium text-slate-200">{title}</h3>
      <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{caption}</p>

      {rows.length ? (
        <ul className="mt-2.5 space-y-2">
          {rows.map((row) => (
            <li key={row.skill} className="flex items-start justify-between gap-2 border-b border-ink-800 pb-2 last:border-0 last:pb-0">
              <div className="min-w-0">
                <p className="text-xs font-medium text-slate-100">{row.skill}</p>
                {row.job_description_evidence?.[0] && (
                  <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-slate-500">
                    {row.job_description_evidence[0]}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 flex-wrap justify-end gap-1">
                {row.sources.length
                  ? row.sources.map((s) => <SourceBadge key={s} source={s} />)
                  : <Pill tone={tone}>Missing</Pill>}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-[11px] text-slate-500">{empty}</p>
      )}
    </div>
  )
}
