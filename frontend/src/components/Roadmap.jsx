import { Card, Pill } from './ui.jsx'

/**
 * Objective 3: the gap list turned into an ordered learning plan.
 *
 * Steps are ordered by a prerequisite graph and by how strongly the retrieved
 * job descriptions demanded each skill. There are deliberately no time
 * estimates — nothing in the analysis supports one.
 */
export default function Roadmap({ roadmap }) {
  const { phases, headline, methodology, hidden_prerequisites: hidden, omitted_steps: omitted } = roadmap

  if (!phases?.length) {
    return (
      <Card title="Your learning roadmap" subtitle="Ordered by what unlocks what.">
        <p className="py-4 text-center text-xs text-slate-400">{headline}</p>
      </Card>
    )
  }

  return (
    <Card
      title="Your learning roadmap"
      subtitle="Ordered by what unlocks what, then by how strongly employers asked for it."
      action={<Pill tone="accent">{roadmap.total_steps} steps</Pill>}
    >
      <p className="mb-4 text-xs leading-relaxed text-slate-300">{headline}</p>

      {hidden?.length > 0 && (
        <div className="mb-4 rounded-lg border border-warn-400/25 bg-warn-400/5 px-3 py-2.5">
          <p className="text-[11px] leading-relaxed text-slate-300">
            <span className="font-medium text-warn-400">Assumed knowledge:</span>{' '}
            the job descriptions never listed {hidden.join(', ')}, but the skills
            you are missing depend on them. They lead the plan.
          </p>
        </div>
      )}

      <div className="space-y-5">
        {phases.map((phase, phaseIndex) => (
          <section key={phase.id}>
            <h3 className="text-sm font-semibold text-slate-100">{phase.title}</h3>
            <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{phase.why}</p>

            <ol className="mt-2.5 space-y-2">
              {phase.steps.map((step, stepIndex) => (
                <li
                  key={step.skill}
                  className="rounded-lg border border-ink-700/60 bg-ink-850/50 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-accent-500/20 text-[10px] font-semibold text-accent-300">
                      {stepIndex + 1}
                    </span>
                    <h4 className="text-xs font-semibold text-slate-100">{step.skill}</h4>
                    <Pill tone={step.requirement_level === 'core' ? 'accent' : 'neutral'}>
                      {step.requirement_level === 'prerequisite'
                        ? 'assumed knowledge'
                        : step.requirement_level}
                    </Pill>
                    {/* "Ready now" means nothing at all stands in the way. A
                        step whose blockers are earlier in this plan is not
                        ready yet, it is simply sequenced — saying otherwise
                        contradicted the "After X" line below it. */}
                    {step.blockers_outside_plan?.length > 0 ? (
                      <Pill tone="warn">blocked</Pill>
                    ) : step.blockers_covered_earlier?.length > 0 ? (
                      <Pill tone="neutral">
                        after step{step.blockers_covered_earlier.length > 1 ? 's' : ''}{' '}
                        {step.blockers_covered_earlier.map((b) => b.skill).join(', ')}
                      </Pill>
                    ) : (
                      <Pill tone="good">ready now</Pill>
                    )}
                  </div>

                  <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{step.why}</p>

                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
                    {step.blockers_outside_plan?.length > 0 && (
                      <span className="text-warn-400">
                        Needs {step.blockers_outside_plan.join(', ')} first
                      </span>
                    )}
                    {step.unlocks?.length > 0 && (
                      <span className="text-slate-500">
                        Unlocks {step.unlocks.join(', ')}
                      </span>
                    )}
                    {step.docs && (
                      <a
                        href={step.docs}
                        target="_blank"
                        rel="noreferrer"
                        className="text-accent-300 underline-offset-2 hover:underline"
                      >
                        Official docs
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ol>

            {phaseIndex < phases.length - 1 && (
              <div className="mt-3 border-b border-dashed border-ink-700" />
            )}
          </section>
        ))}
      </div>

      {omitted > 0 && (
        <p className="mt-4 text-[11px] text-slate-500">
          {omitted} further gap{omitted === 1 ? '' : 's'} were left off to keep the plan
          workable. They appear once these are closed.
        </p>
      )}

      <p className="mt-4 border-t border-ink-800 pt-3 text-[11px] leading-relaxed text-slate-500">
        {methodology}
      </p>
    </Card>
  )
}
