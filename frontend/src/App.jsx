import { useCallback, useEffect, useRef, useState } from 'react'
import Navbar from './components/Navbar.jsx'
import Welcome from './components/Welcome.jsx'
import AnalysisForm from './components/AnalysisForm.jsx'
import LoadingStages from './components/LoadingStages.jsx'
import ScoreCard from './components/ScoreCard.jsx'
import ATSBreakdown from './components/ATSBreakdown.jsx'
import JobMatch from './components/JobMatch.jsx'
import KeySkills from './components/KeySkills.jsx'
import ResumeInsights from './components/ResumeInsights.jsx'
import GitHubInsights from './components/GitHubInsights.jsx'
import SummaryCard from './components/SummaryCard.jsx'
import { Pill } from './components/ui.jsx'
import { analyze, analyzeStream, getExperienceLevels, getRoles } from './services/api.js'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'ats', label: 'ATS Breakdown' },
  { id: 'match', label: 'Job Match' },
  { id: 'sources', label: 'Resume & GitHub' },
]

const INITIAL_FORM = {
  resumeFile: null,
  githubUsername: '',
  roleId: '',
  experienceLevel: 'fresher',
  jobDescriptionText: '',
}

const EMAIL_KEY = 'career-engine.email'
const LEVEL_KEY = 'career-engine.experience'

export default function App() {
  // 'welcome' -> 'setup' -> 'results'
  const [page, setPage] = useState('welcome')
  const [email, setEmail] = useState(null)

  const [roles, setRoles] = useState([])
  const [levels, setLevels] = useState([])
  const [backendError, setBackendError] = useState(null)

  const [form, setForm] = useState(INITIAL_FORM)
  const [busy, setBusy] = useState(false)
  const [stages, setStages] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('overview')

  const abortRef = useRef(null)

  // Remember the session across reloads so a refresh does not send the user
  // back to the welcome screen mid-task.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(EMAIL_KEY)
      const savedLevel = localStorage.getItem(LEVEL_KEY)
      if (savedLevel) setForm((f) => ({ ...f, experienceLevel: savedLevel }))
      if (saved) {
        setEmail(saved)
        setPage('setup')
      }
    } catch {
      /* storage unavailable (private window); the welcome screen still works */
    }
  }, [])

  const loadRoles = useCallback(() => {
    setBackendError(null)
    Promise.all([getRoles(), getExperienceLevels()])
      .then(([roleList, levelList]) => {
        setRoles(roleList)
        setLevels(levelList)
        setForm((f) => (f.roleId ? f : { ...f, roleId: roleList[0]?.id || '' }))
      })
      .catch((err) => setBackendError(err.message))
  }, [])

  useEffect(() => {
    if (page !== 'welcome') loadRoles()
  }, [page, loadRoles])

  const signIn = (value) => {
    setEmail(value)
    try { localStorage.setItem(EMAIL_KEY, value) } catch { /* ignore */ }
    setPage('setup')
  }

  const signOut = () => {
    try {
      localStorage.removeItem(EMAIL_KEY)
      localStorage.removeItem(LEVEL_KEY)
    } catch { /* ignore */ }
    abortRef.current?.abort()
    setEmail(null)
    setForm(INITIAL_FORM)
    setResult(null)
    setError(null)
    setStages({})
    setPage('welcome')
  }

  const runAnalysis = async () => {
    setBusy(true)
    setError(null)
    setResult(null)
    setStages({})
    setTab('overview')

    const controller = new AbortController()
    abortRef.current = controller

    // Keep the chosen level as the default for next time.
    try { localStorage.setItem(LEVEL_KEY, form.experienceLevel) } catch { /* ignore */ }

    const options = {
      resumeFile: form.resumeFile,
      roleId: form.roleId,
      experienceLevel: form.experienceLevel,
      githubUsername: form.githubUsername,
      jobDescriptionText: form.jobDescriptionText,
    }
    const onStage = (stage) => setStages((prev) => ({ ...prev, [stage.stage]: stage }))

    try {
      let data
      try {
        data = await analyzeStream(options, { onStage, signal: controller.signal })
      } catch (streamError) {
        // A 4xx/5xx from the backend is a real failure -- surface it. Only fall
        // back to the non-streaming endpoint if streaming itself was the problem.
        if (streamError.status || streamError.name === 'AbortError') throw streamError
        data = await analyze(options)
      }
      setResult(data)
      setPage('results')
      window.scrollTo({ top: 0 })
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message)
    } finally {
      setBusy(false)
      abortRef.current = null
    }
  }

  const startOver = () => {
    setResult(null)
    setError(null)
    setStages({})
    setPage('setup')
    window.scrollTo({ top: 0 })
  }

  // Cancel an in-flight request if the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), [])

  if (page === 'welcome') {
    return (
      <div className="relative min-h-screen">
        <Navbar />
        <Welcome onContinue={signIn} />
      </div>
    )
  }

  return (
    <div className="relative min-h-screen">
      <Navbar email={email} onSignOut={signOut} />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {backendError && (
          <div className="mb-5 rounded-xl border border-bad-400/30 bg-bad-400/5 px-4 py-3">
            <h2 className="text-xs font-semibold text-bad-400">Backend unavailable</h2>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-400">
              {backendError} Start it with{' '}
              <code className="rounded bg-ink-800 px-1 py-0.5 font-mono text-slate-300">
                uvicorn main:app --reload
              </code>{' '}
              from the <code className="font-mono">backend/</code> directory, then{' '}
              <button onClick={loadRoles} className="text-accent-300 underline underline-offset-2">
                retry
              </button>.
            </p>
          </div>
        )}

        {/* ---------- Step 2: inputs ---------- */}
        {page === 'setup' && (
          <div className="mx-auto max-w-2xl space-y-4">
            <AnalysisForm
              roles={roles}
              levels={levels}
              value={form}
              onChange={setForm}
              onSubmit={runAnalysis}
              busy={busy}
              disabled={Boolean(backendError)}
            />

            {busy && <LoadingStages stages={stages} />}

            {error && (
              <div className="rounded-xl border border-bad-400/30 bg-bad-400/5 px-4 py-3">
                <h2 className="text-xs font-semibold text-bad-400">Analysis failed</h2>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-400">{error}</p>
              </div>
            )}
          </div>
        )}

        {/* ---------- Step 3: results ---------- */}
        {page === 'results' && result && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <div className="mr-auto">
                <h2 className="text-base font-semibold text-slate-100">{result.role.title}</h2>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {result.resume.file?.name} · analysed against{' '}
                  {result.job_description.provided_by_user
                    ? 'the job description you provided'
                    : 'typical requirements for this role'}
                </p>
              </div>
              <Pill
                tone="accent"
                title={`Skill coverage is scored against the ${Math.round(
                  result.experience_level.skill_coverage_target * 100,
                )}% expected at this stage.`}
              >
                {result.experience_level.label}
              </Pill>
              {result.github_error && <Pill tone="warn">GitHub: {result.github_error}</Pill>}
              <button
                type="button"
                onClick={startOver}
                className="rounded-lg border border-ink-600 px-3 py-1.5 text-xs text-slate-300 transition hover:border-accent-400 hover:text-slate-100"
              >
                New analysis
              </button>
            </div>

            <ScoreCard ats={result.ats} match={result.job_match} />

            <nav className="flex flex-wrap gap-1.5 border-b border-ink-700/70 pb-2" role="tablist">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={tab === t.id}
                  onClick={() => setTab(t.id)}
                  className={`rounded-lg px-3 py-1.5 text-xs transition ${
                    tab === t.id
                      ? 'bg-accent-500/15 text-accent-300 ring-1 ring-accent-400/30'
                      : 'text-slate-400 hover:bg-ink-800/60 hover:text-slate-200'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </nav>

            {tab === 'overview' && (
              <div className="space-y-5">
                <SummaryCard summary={result.summary} />
                <KeySkills match={result.job_match} />
              </div>
            )}
            {tab === 'ats' && <ATSBreakdown ats={result.ats} />}
            {tab === 'match' && <JobMatch match={result.job_match} />}
            {tab === 'sources' && (
              <div className="space-y-5">
                <ResumeInsights resume={result.resume} />
                <GitHubInsights github={result.github} error={result.github_error} />
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-8 pt-2 sm:px-6">
        <p className="text-[11px] text-slate-600">
          Career Engine · ATS scoring is deterministic and rule-based; job matching compares
          resume and GitHub evidence against requirements retrieved from job-description data.
          Any language model is used only to describe results that were already computed.
        </p>
      </footer>
    </div>
  )
}
