import { Card, Meter, Pill, SkillChips } from './ui.jsx'

/**
 * Objective 3: how the candidate ranks across every role, not just the one
 * they picked.
 *
 * Rows are ordered by **core fit** — the share of a role's must-have
 * requirements the candidate can evidence — rather than by the match score.
 * The experience-level adjustment caps a component once the expected coverage
 * is reached, which is correct for a single role but flattens a comparison
 * across six. The match score is still shown, muted, and the note at the
 * bottom explains why the two orderings can disagree.
 */
export default function RoleFit({ recommendations }) {
  const { roles, headline, methodology } = recommendations
  const target = roles.find((r) => r.is_target)

  return (
    <Card
      title="How you fit other roles"
      subtitle="The same matcher, run against all six roles on equal terms."
      action={
        target && <Pill tone="neutral">Your target ranks #{target.rank} of {roles.length}</Pill>
      }
    >
      <p className="mb-4 text-xs leading-relaxed text-slate-300">{headline}</p>

      <ol className="space-y-2.5">
        {roles.map((role) => (
          <li
            key={role.role_id}
            className={`rounded-lg border p-3 ${
              role.is_target
                ? 'border-accent-400/50 bg-accent-500/10'
                : 'border-ink-700/60 bg-ink-850/50'
            }`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded bg-ink-700 text-[10px] font-semibold text-slate-300">
                {role.rank}
              </span>
              <h3 className="text-xs font-semibold text-slate-100">{role.title}</h3>
              {role.is_target && <Pill tone="accent">Your target</Pill>}
              <span className="ml-auto shrink-0 text-xs font-semibold tabular-nums text-slate-100">
                {role.core_matched}
                <span className="text-slate-500">/{role.core_total} core</span>
              </span>
            </div>

            <Meter value={role.core_matched} max={role.core_total} className="mt-2" />

            <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <span className="text-[11px] text-slate-400">
                {Math.round(role.core_coverage * 100)}% of core requirements
              </span>
              <span className="text-[11px] text-slate-500">
                match score {role.score}/{role.max_score}
              </span>
              <span className="text-[11px] text-slate-500">
                preferred {role.preferred_matched}/{role.preferred_total}
              </span>
            </div>

            {role.top_gaps?.length > 0 && (
              <div className="mt-2">
                <p className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">
                  Missing here
                </p>
                <SkillChips skills={role.top_gaps} tone="bad" />
              </div>
            )}
          </li>
        ))}
      </ol>

      <p className="mt-4 border-t border-ink-800 pt-3 text-[11px] leading-relaxed text-slate-500">
        {methodology}
      </p>
    </Card>
  )
}
