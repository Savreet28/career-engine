import { Card, Disclosure, Field, Pill, SkillChips } from './ui.jsx'

/** What the parser actually extracted from the uploaded file. */
export default function ResumeInsights({ resume }) {
  const contact = resume.contact || {}
  const readability = resume.readability || {}
  const byCategory = resume.skills_detail?.by_category || {}

  return (
    <Card
      title="Resume Insights"
      subtitle={`Parsed from ${resume.file?.name} (${resume.file?.type?.toUpperCase()})`}
      action={<Pill tone="accent">{resume.skills.length} skills</Pill>}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h3 className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">Contact detected</h3>
          <dl>
            <Field label="Name" value={contact.name} />
            <Field label="Email" value={contact.email} mono />
            <Field label="Phone" value={contact.phone} mono />
          </dl>
        </div>
        <div>
          <h3 className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">Document signals</h3>
          <dl>
            <Field label="Word count" value={readability.word_count} />
            <Field label="Bullet points" value={readability.bullet_count} />
          </dl>
        </div>
      </div>

      <div className="mt-4">
        <h3 className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">Sections</h3>
        <div className="flex flex-wrap gap-1.5">
          {resume.sections?.map((s) => <Pill key={s} tone="good">{s}</Pill>)}
          {resume.missing_core_sections?.map((s) => (
            <Pill key={s} tone="bad" title="Expected but not found">{s} (missing)</Pill>
          ))}
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <Disclosure summary="Skills by category" count={resume.skills.length}>
          <div className="space-y-2">
            {Object.entries(byCategory).map(([category, skills]) => (
              <div key={category}>
                <p className="mb-1 text-[10px] uppercase tracking-wide text-slate-500">
                  {category} ({skills.length})
                </p>
                <SkillChips skills={skills} tone="accent" />
              </div>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">
            {resume.skills_detail?.declared?.length || 0} appear in an explicit skills
            section; the rest were found in project and experience text.
          </p>
        </Disclosure>

        <EntryList title="Projects" entries={resume.projects} />
        <EntryList title="Experience" entries={resume.experience} />
        <EntryList title="Education" entries={resume.education} plain />
        <EntryList title="Certifications" entries={resume.certifications} />
        <EntryList title="Quantified achievements" entries={resume.achievements?.filter((a) => a.quantified)} plain />
      </div>
    </Card>
  )
}

function EntryList({ title, entries, plain = false }) {
  if (!entries?.length) return null
  return (
    <Disclosure summary={title} count={entries.length}>
      <ul className="space-y-2">
        {entries.map((entry, i) => (
          <li key={i} className="border-l-2 border-ink-600 pl-2.5">
            <p className="text-[11px] leading-relaxed text-slate-300">{entry.text}</p>
            {!plain && entry.skills?.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {entry.skills.map((s) => <Pill key={s} tone="neutral">{s}</Pill>)}
              </div>
            )}
            {entry.degree && <p className="mt-0.5 text-[10px] text-slate-500">Degree: {entry.degree}{entry.score ? ` · ${entry.score}` : ''}</p>}
          </li>
        ))}
      </ul>
    </Disclosure>
  )
}
