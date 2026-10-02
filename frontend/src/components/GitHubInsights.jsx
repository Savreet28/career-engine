import { Card, Disclosure, Field, Pill, SkillChips } from './ui.jsx'

/** Public GitHub activity, and the skill evidence derived from it. */
export default function GitHubInsights({ github, error }) {
  if (!github || github.unavailable || !github.profile) {
    return (
      <Card title="GitHub Insights" subtitle="Public repository evidence">
        <div className="rounded-lg border border-ink-700/60 bg-ink-850/50 p-4 text-center">
          <p className="text-xs text-slate-400">
            {error || github?.reason || 'No GitHub profile was analysed.'}
          </p>
          <p className="mt-1.5 text-[11px] text-slate-500">
            Adding a GitHub username contributes up to 5 ATS points and enables the
            evidence-corroboration component of the match score.
          </p>
        </div>
      </Card>
    )
  }

  const { profile, stats, languages, topics, top_repositories: repos, skills, skill_evidence } = github
  const totalBytes = Object.values(languages || {}).reduce((a, b) => a + b, 0)
  const topTopics = Object.entries(topics || {}).slice(0, 14)

  return (
    <Card
      title="GitHub Insights"
      subtitle={`Public activity for @${profile.username}`}
      action={<Pill tone="good">{skills.length} skills evidenced</Pill>}
    >
      <div className="flex items-center gap-3 rounded-lg border border-ink-700/60 bg-ink-850/50 p-3">
        {profile.avatar_url && (
          <img
            src={profile.avatar_url}
            alt=""
            className="h-11 w-11 shrink-0 rounded-full ring-1 ring-ink-600"
            loading="lazy"
          />
        )}
        <div className="min-w-0">
          <a href={profile.url} target="_blank" rel="noreferrer"
             className="truncate text-xs font-medium text-slate-100 hover:text-accent-300">
            {profile.name || profile.username}
          </a>
          {profile.bio && <p className="truncate text-[11px] text-slate-400">{profile.bio}</p>}
          <p className="mt-0.5 text-[11px] text-slate-500">
            {profile.followers} followers · {profile.public_repos} public repos
          </p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          ['Original repos', stats.original_repositories],
          ['Total stars', stats.total_stars],
          ['Languages', stats.distinct_languages],
          ['With topics', stats.repositories_with_topics],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-ink-700/60 bg-ink-850/50 px-2.5 py-2">
            <p className="text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-0.5 text-sm font-semibold text-slate-100 tabular-nums">{value ?? 0}</p>
          </div>
        ))}
      </div>

      {totalBytes > 0 && (
        <div className="mt-3">
          <h3 className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">
            Language mix (top repositories, by bytes)
          </h3>
          <div className="flex h-2 overflow-hidden rounded-full bg-ink-700">
            {Object.entries(languages).slice(0, 6).map(([language, bytes], i) => (
              <div
                key={language}
                title={`${language}: ${((bytes / totalBytes) * 100).toFixed(1)}%`}
                style={{ width: `${(bytes / totalBytes) * 100}%` }}
                className={['bg-accent-400', 'bg-good-400', 'bg-warn-400', 'bg-accent-600', 'bg-bad-400', 'bg-ink-600'][i]}
              />
            ))}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
            {Object.entries(languages).slice(0, 6).map(([language, bytes], i) => (
              <span key={language} className="flex items-center gap-1 text-[11px] text-slate-400">
                <span className={`h-2 w-2 rounded-sm ${['bg-accent-400', 'bg-good-400', 'bg-warn-400', 'bg-accent-600', 'bg-bad-400', 'bg-ink-600'][i]}`} />
                {language} {((bytes / totalBytes) * 100).toFixed(0)}%
              </span>
            ))}
          </div>
        </div>
      )}

      {topTopics.length > 0 && (
        <div className="mt-3">
          <h3 className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">Repository topics</h3>
          <div className="flex flex-wrap gap-1.5">
            {topTopics.map(([topic, count]) => (
              <Pill key={topic} tone="neutral" title={`Used on ${count} repositories`}>
                {topic}{count > 1 && <span className="text-slate-500">{count}</span>}
              </Pill>
            ))}
          </div>
        </div>
      )}

      <div className="mt-3 space-y-2">
        <Disclosure summary="Top repositories" count={repos.length}>
          <ul className="space-y-2">
            {repos.map((repo) => (
              <li key={repo.name} className="border-l-2 border-ink-600 pl-2.5">
                <div className="flex items-center justify-between gap-2">
                  <a href={repo.url} target="_blank" rel="noreferrer"
                     className="truncate text-[11px] font-medium text-slate-200 hover:text-accent-300">
                    {repo.name}
                  </a>
                  <span className="shrink-0 text-[10px] text-slate-500">
                    ★ {repo.stars} · ⑂ {repo.forks}
                  </span>
                </div>
                {repo.description && (
                  <p className="text-[11px] leading-relaxed text-slate-400">{repo.description}</p>
                )}
                <div className="mt-1 flex flex-wrap gap-1">
                  {repo.language && <Pill tone="accent">{repo.language}</Pill>}
                  {repo.topics.slice(0, 5).map((t) => <Pill key={t} tone="neutral">{t}</Pill>)}
                </div>
              </li>
            ))}
          </ul>
        </Disclosure>

        <Disclosure summary="Detected technical evidence" count={skills.length}>
          <ul className="space-y-1.5">
            {skills.map((skill) => (
              <li key={skill} className="flex flex-wrap items-baseline gap-x-2 border-b border-ink-800 pb-1.5 last:border-0">
                <span className="text-[11px] font-medium text-slate-200">{skill}</span>
                <span className="text-[11px] text-slate-500">
                  {(skill_evidence[skill] || []).join(' · ')}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-slate-500">
            A skill listed here means it appeared in a repository's language, topics or
            description. That is weaker than a demonstrated skill — a description
            mentioning a technology is not proof of proficiency, which is why GitHub
            evidence is reported separately from the resume.
          </p>
        </Disclosure>
      </div>

      {github.notes?.length > 0 && (
        <ul className="mt-3 space-y-1">
          {github.notes.map((note, i) => (
            <li key={i} className="text-[11px] text-slate-500">· {note}</li>
          ))}
        </ul>
      )}
    </Card>
  )
}
