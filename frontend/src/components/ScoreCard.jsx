import { Meter, Pill, scoreTone } from './ui.jsx'

/** Circular score dial. Pure SVG -- no chart library needed for one number. */
function Dial({ score, max, tone }) {
  const radius = 52
  const circumference = 2 * Math.PI * radius
  const pct = max ? Math.max(0, Math.min(1, score / max)) : 0
  return (
    <div className="relative grid h-32 w-32 shrink-0 place-items-center">
      <svg className="h-32 w-32 -rotate-90" viewBox="0 0 128 128" aria-hidden="true">
        <circle cx="64" cy="64" r={radius} className="fill-none stroke-ink-700" strokeWidth="10" />
        <circle
          cx="64" cy="64" r={radius}
          className={`fill-none ${tone.ring} transition-[stroke-dashoffset] duration-700`}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - pct)}
        />
      </svg>
      <div className="absolute text-center">
        <div className={`text-3xl font-bold tabular-nums ${tone.text}`}>{score}</div>
        <div className="text-[11px] text-slate-500">/ {max}</div>
      </div>
    </div>
  )
}

/**
 * The two headline numbers. Deliberately labelled with HOW each was produced,
 * because the distinction between the deterministic ATS score and the
 * evidence-based match score is the core idea of the project.
 */
export default function ScoreCard({ ats, match }) {
  const atsTone = scoreTone(ats.score, ats.max_score)
  const matchTone = scoreTone(match.score, match.max_score)

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <section className="rounded-xl border border-ink-700/70 bg-ink-900/70 p-5 shadow-lg shadow-black/20 backdrop-blur-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">ATS Score</h2>
            <p className="mt-0.5 text-[11px] text-slate-500">Rule-based · deterministic</p>
          </div>
          <Pill tone={atsTone.label === 'strong' ? 'good' : atsTone.label === 'weak' ? 'bad' : 'accent'}>
            {ats.band.label}
          </Pill>
        </div>
        <div className="mt-3 flex items-center gap-5">
          <Dial score={ats.score} max={ats.max_score} tone={atsTone} />
          <div className="min-w-0 space-y-2">
            <p className="text-xs leading-relaxed text-slate-300">{ats.band.summary}</p>
            <p className="text-[11px] leading-relaxed text-slate-500">
              Sum of {ats.components.length} weighted components. No language
              model contributes to this number.
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-ink-700/70 bg-ink-900/70 p-5 shadow-lg shadow-black/20 backdrop-blur-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Job Match Score</h2>
            <p className="mt-0.5 text-[11px] text-slate-500">Evidence vs RAG-retrieved requirements</p>
          </div>
          <Pill tone={matchTone.label === 'strong' ? 'good' : matchTone.label === 'weak' ? 'bad' : 'accent'}>
            {match.verdict.label}
          </Pill>
        </div>
        <div className="mt-3 flex items-center gap-5">
          <Dial score={match.score} max={match.max_score} tone={matchTone} />
          <div className="min-w-0 space-y-2.5">
            <p className="text-xs leading-relaxed text-slate-300">{match.verdict.summary}</p>
            <div>
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Core requirements</span>
                <span className="tabular-nums">
                  {match.core_skills.matched.length}/{match.core_skills.total}
                </span>
              </div>
              <Meter value={match.core_skills.matched.length} max={match.core_skills.total} className="mt-1" />
            </div>
            <div>
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Preferred requirements</span>
                <span className="tabular-nums">
                  {match.preferred_skills.matched.length}/{match.preferred_skills.total}
                </span>
              </div>
              <Meter value={match.preferred_skills.matched.length} max={match.preferred_skills.total} className="mt-1" />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
