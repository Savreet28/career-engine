import ResumeUpload from './ResumeUpload.jsx'

/**
 * Step 2 — the input page: resume, GitHub username, target role and the job
 * description the student is applying to.
 *
 * The job description is written in by the user. The local job-description
 * knowledge base is still what the RAG index retrieves over behind the scenes;
 * it is just no longer something the user has to pick from.
 */
export default function AnalysisForm({ roles, levels, value, onChange, onSubmit, busy, disabled }) {
  const set = (patch) => onChange({ ...value, ...patch })
  const canSubmit = Boolean(value.resumeFile && value.roleId) && !busy && !disabled

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); if (canSubmit) onSubmit() }}
      className="space-y-5 rounded-xl border border-ink-700/70 bg-ink-900/70 p-6 shadow-lg shadow-black/20 backdrop-blur-sm"
    >
      <div>
        <h2 className="text-base font-semibold text-slate-100">Your details</h2>
        <p className="mt-1 text-xs text-slate-400">
          Upload your resume and pick the role you are targeting. GitHub is optional
          but adds evidence that backs up what your resume claims.
        </p>
      </div>

      <ResumeUpload
        file={value.resumeFile}
        onChange={(f) => set({ resumeFile: f })}
        disabled={busy}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="github" className="mb-1.5 block text-xs font-medium text-slate-300">
            GitHub username <span className="text-slate-500">(optional)</span>
          </label>
          <div className="flex items-center rounded-lg border border-ink-600 bg-ink-850/70 focus-within:border-accent-500">
            <span className="pl-3 text-xs text-slate-500">github.com/</span>
            <input
              id="github"
              type="text"
              value={value.githubUsername}
              onChange={(e) => set({ githubUsername: e.target.value })}
              disabled={busy}
              placeholder="your-username"
              autoComplete="off"
              spellCheck="false"
              className="w-full bg-transparent px-1.5 py-2 text-xs text-slate-100 outline-none placeholder:text-slate-600 disabled:opacity-50"
            />
          </div>
        </div>

        <div>
          <label htmlFor="role" className="mb-1.5 block text-xs font-medium text-slate-300">
            Target job role <span className="text-bad-400">*</span>
          </label>
          <select
            id="role"
            value={value.roleId}
            onChange={(e) => set({ roleId: e.target.value })}
            disabled={busy || !roles.length}
            className="w-full rounded-lg border border-ink-600 bg-ink-850/70 px-3 py-2 text-xs text-slate-100 outline-none focus:border-accent-500 disabled:opacity-50"
          >
            {!roles.length && <option value="">Loading roles…</option>}
            {roles.map((role) => (
              <option key={role.id} value={role.id}>{role.title}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="experience-level" className="mb-1.5 block text-xs font-medium text-slate-300">
          Experience level <span className="text-bad-400">*</span>
        </label>
        <select
          id="experience-level"
          value={value.experienceLevel}
          onChange={(e) => set({ experienceLevel: e.target.value })}
          disabled={busy || !levels.length}
          className="w-full rounded-lg border border-ink-600 bg-ink-850/70 px-3 py-2 text-xs text-slate-100 outline-none focus:border-accent-500 disabled:opacity-50"
        >
          {!levels.length && <option value="">Loading…</option>}
          {levels.map((l) => (
            <option key={l.id} value={l.id}>{l.label}</option>
          ))}
        </select>
        <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">
          {(() => {
            const current = levels.find((l) => l.id === value.experienceLevel)
            return current
              ? `Skill coverage is scored against the ${Math.round(current.skill_coverage_target * 100)}% expected at this stage, not against 100%.`
              : 'Scores are measured against what is expected at this career stage.'
          })()}
        </p>
      </div>

      <div>
        <label htmlFor="jd" className="mb-1.5 block text-xs font-medium text-slate-300">
          Job description <span className="text-slate-500">(optional, but strongly recommended)</span>
        </label>
        <textarea
          id="jd"
          value={value.jobDescriptionText}
          onChange={(e) => set({ jobDescriptionText: e.target.value })}
          disabled={busy}
          rows={8}
          placeholder={
            'Paste the job description you are applying to.\n\n' +
            'Keep the original headings — "Required skills:" and "Nice to have:" are ' +
            'used to tell must-haves apart from nice-to-haves.'
          }
          className="w-full resize-y rounded-lg border border-ink-600 bg-ink-850/70 px-3 py-2.5 text-xs leading-relaxed text-slate-100 outline-none focus:border-accent-500 placeholder:text-slate-600 disabled:opacity-50"
        />
        <p className="mt-1.5 text-[11px] text-slate-500">
          {value.jobDescriptionText.trim()
            ? `${value.jobDescriptionText.trim().split(/\s+/).length} words — keyword matching will use this posting.`
            : 'Without a posting, keyword matching falls back to typical requirements for the selected role.'}
        </p>
      </div>

      <button
        type="submit"
        disabled={!canSubmit}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-ink-700 disabled:text-slate-500"
      >
        {busy ? (
          <>
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            Analysing…
          </>
        ) : 'Analyze'}
      </button>

      {!value.resumeFile && (
        <p className="text-center text-[11px] text-slate-500">
          A resume file is required to run the analysis.
        </p>
      )}
    </form>
  )
}
