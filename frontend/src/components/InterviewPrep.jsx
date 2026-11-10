import { Card, Pill } from './ui.jsx'

const GROUP_TONE = { prove: 'good', gaps: 'warn', about_you: 'accent' }

/**
 * Objective 3: the questions this candidate is most likely to face.
 *
 * Selected by skill tag from a curated local bank, filtered to the experience
 * level, ordered by how strongly the job descriptions demanded each skill.
 * Deliberately no model answers — each question states what the interviewer is
 * checking for, so the candidate prepares their own.
 */
export default function InterviewPrep({ prep }) {
  const { groups, headline, methodology, bank_size: bankSize } = prep

  if (!groups?.length) {
    return (
      <Card title="Interview preparation">
        <p className="py-4 text-center text-xs text-slate-400">{headline}</p>
      </Card>
    )
  }

  return (
    <Card
      title="Interview preparation"
      subtitle="The questions you are most likely to be asked, based on your actual skill profile."
      action={<Pill tone="accent">{prep.total_questions} of {bankSize}</Pill>}
    >
      <p className="mb-4 text-xs leading-relaxed text-slate-300">{headline}</p>

      <div className="space-y-5">
        {groups.map((group) => (
          <section key={group.id}>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-100">{group.title}</h3>
              <Pill tone={GROUP_TONE[group.id] || 'neutral'}>
                {group.questions.length}
              </Pill>
            </div>
            <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{group.why}</p>

            <ol className="mt-2.5 space-y-2">
              {group.questions.map((question, index) => (
                <li
                  key={question.id}
                  className="rounded-lg border border-ink-700/60 bg-ink-850/50 p-3"
                >
                  <div className="flex gap-2.5">
                    <span className="mt-px grid h-5 w-5 shrink-0 place-items-center rounded-full bg-ink-700 text-[10px] font-semibold text-slate-300">
                      {index + 1}
                    </span>
                    <p className="min-w-0 text-xs font-medium leading-relaxed text-slate-100">
                      {question.question}
                    </p>
                  </div>

                  <div className="mt-2 ml-7.5 flex flex-wrap items-center gap-1.5">
                    {question.matched_skill && (
                      <Pill tone="accent">{question.matched_skill}</Pill>
                    )}
                    <Pill tone="neutral">{question.kind}</Pill>
                    {question.stretch && (
                      <Pill tone="warn" title="Above your stated level, but it is the only question covering this skill">
                        stretch
                      </Pill>
                    )}
                  </div>

                  <p className="mt-2 ml-7.5 text-[11px] leading-relaxed text-slate-400">
                    <span className="font-medium text-slate-300">
                      What they are checking:
                    </span>{' '}
                    {question.what_they_are_checking}
                  </p>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      <p className="mt-5 border-t border-ink-800 pt-3 text-[11px] leading-relaxed text-slate-500">
        {methodology}
      </p>
    </Card>
  )
}
